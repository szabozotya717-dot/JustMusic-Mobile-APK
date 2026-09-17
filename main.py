import os
import re
import json
import random
import time
import hashlib
import threading
import base64
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line

try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None

BG = (0.015, 0.035, 0.075, 1)
PANEL = (0.03, 0.09, 0.15, 0.92)
PANEL_2 = (0.04, 0.13, 0.22, 0.95)
CARD = (0.04, 0.12, 0.20, 0.95)
ACCENT = (0.18, 0.68, 1.0, 1.0)
ACCENT_2 = (0.39, 0.82, 1.0, 1.0)
TEXT = (0.96, 0.98, 1.0, 1.0)
TEXT_2 = (0.68, 0.77, 0.86, 1.0)
MUTED = (0.45, 0.56, 0.66, 1.0)
SUPPORTED_AUDIO = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")
SETTINGS_NAME = ".justmusic_mobile_settings.json"


def fmt_time(seconds):
    try:
        seconds = max(0, int(seconds or 0))
    except Exception:
        seconds = 0
    return f"{seconds // 60}:{seconds % 60:02d}"


def _clean_title_text(text):
    """Erős JustMusic! cím-takarítás letöltött / YouTube-os fájlnevekhez."""
    text = str(text or "").strip()

    if " _ " in text:
        text = text.split(" _ ", 1)[0].strip()

    text = re.sub(r"[_]+", " ", text)

    # Zárójeles/bracketes sallangok: Official, Visualizer, Lyrics, évszám stb.
    junk_inside = (
        r"official(?:\s+music)?(?:\s+video|\s+audio|\s+visuali[sz]er)?|"
        r"music\s+video|official\s+clip|video\s+clip|audio|video|"
        r"visual|visuali[sz]er|lyrics?|lyric\s+video|"
        r"hd|full\s*hd|4k|8k|clean|explicit|remaster(?:ed)?|"
        r"\d{2,4}\s*kbps|m|19\d{2}|20\d{2}"
    )

    pattern = rf"\s*[\(\[\{{]\s*(?:{junk_inside})\s*[\)\]\}}]"
    previous = None
    while previous != text:
        previous = text
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Olyan zárójeles rész, amiben a fenti kulcsszavak valamelyike szerepel.
    text = re.sub(
        rf"\s*[\(\[\{{][^\)\]\}}]*(?:official|visuali[sz]er|visual|lyrics?|"
        rf"music\s+video|video|audio|4k|8k|full\s*hd|remaster(?:ed)?|\b(?:19\d{{2}}|20\d{{2}})\b)[^\)\]\}}]*[\)\]\}}]",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # Végi sallangok kötőjel / pipe után.
    text = re.sub(
        r"\s*[-–—|:]\s*(?:official(?:\s+music)?\s*)?(?:video|audio|visuali[sz]er|visual|lyrics?|music\s+video)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # Évszám a cím legvégén: 1990–2099.
    text = re.sub(r"(?:\s*[-–—|:]?\s*)\b(?:19\d{2}|20\d{2})\b\s*$", "", text).strip()

    # Bitráta / minőség a végén.
    text = re.sub(r"\s*[-–—_|:]*\s*(?:\d{2,4}\s*kbps|(?:full\s*)?hd|4k|8k)\s*$", "", text, flags=re.I).strip()

    # Klasszikus YouTube ID (11 karakter) a végén.
    text = re.sub(r"(?:\s+|\s*[-–—_]\s*)[A-Za-z0-9_-]{11}\s*$", "", text).strip()

    # Rövidebb, véletlenszerűnek tűnő vég-tokenek (pl. Bskyjs).
    # Csak akkor töröljük, ha 6–16 ASCII betű/szám és nincs benne normál magánhangzó,
    # vagy szám / _ / - is van benne, így a rendes szavakat nem bántjuk annyira agresszíven.
    m = re.search(r"\s+([A-Za-z0-9_-]{6,16})\s*$", text)
    if m:
        token = m.group(1)
        looks_id = (
            not re.search(r"[AEIOUaeiou]", token)
            or bool(re.search(r"[0-9_-]", token))
        )
        if looks_id:
            text = text[:m.start()].strip()

    # Többször ismétlődő 'Official' / 'Video' sima szövegként is a végén.
    text = re.sub(
        r"\s+(?:official|official\s+video|official\s+audio|official\s+visuali[sz]er|visuali[sz]er|visual|lyrics?|video|audio)\s*$",
        "",
        text,
        flags=re.I,
    ).strip()

    # Pár nélküli szélső zárójelek.
    for opening, closing in (("[", "]"), ("(", ")"), ("{", "}")):
        if text.startswith(opening) and text.count(opening) > text.count(closing):
            text = text[1:].strip()
        if text.endswith(closing) and text.count(closing) > text.count(opening):
            text = text[:-1].strip()

    text = text.strip(" \t\r\n-_–—|:;,.!~")
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _metadata_artist_title(path):
    if MutagenFile is None:
        return "", ""

    try:
        audio = MutagenFile(path, easy=True)
        tags = getattr(audio, "tags", None) or {}

        def first(key):
            value = tags.get(key)
            if isinstance(value, (list, tuple)):
                value = value[0] if value else ""
            return str(value or "").strip()

        artist = _clean_title_text(first("artist"))
        title = _clean_title_text(first("title"))
        return artist, title
    except Exception:
        return "", ""


def track_metadata(path):
    """artist / title / album mobil könyvtárnézetekhez."""
    artist = ""
    title = ""
    album = ""

    if MutagenFile is not None:
        try:
            audio = MutagenFile(path, easy=True)
            tags = getattr(audio, "tags", None) or {}

            def first(key):
                value = tags.get(key)
                if isinstance(value, (list, tuple)):
                    value = value[0] if value else ""
                return str(value or "").strip()

            artist = _clean_title_text(first("artist"))
            title = _clean_title_text(first("title"))
            album = _clean_title_text(first("album"))
        except Exception:
            pass

    fallback = _clean_title_text(Path(path).stem)

    if not title:
        if " - " in fallback:
            left, right = fallback.split(" - ", 1)
            if not artist:
                artist = left.strip()
            title = right.strip()
        else:
            title = fallback

    if not artist:
        artist = "Ismeretlen előadó"

    if not album:
        album = "Ismeretlen album"

    return {
        "artist": artist,
        "title": title or "Ismeretlen szám",
        "album": album,
    }



def _cover_cache_dir():
    try:
        base = Path(App.get_running_app().user_data_dir) / "cover_cache"
    except Exception:
        base = Path.home() / ".justmusic_cover_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def cover_for_track(path):
    """
    Beágyazott borító kinyerése MP3 / M4A / FLAC fájlokból.
    A képet az app saját cache mappájába menti.
    """
    if MutagenFile is None or not path:
        return ""

    try:
        key = hashlib.sha1(
            str(path).encode("utf-8", errors="ignore")
        ).hexdigest()[:24]

        cache_dir = _cover_cache_dir()

        # Már kiszedett borító.
        for ext in (".jpg", ".jpeg", ".png"):
            cached = cache_dir / f"{key}{ext}"
            if cached.exists() and cached.stat().st_size > 100:
                return str(cached)

        audio = MutagenFile(path, easy=False)
        if audio is None:
            return ""

        data = None
        ext = ".jpg"

        # FLAC / hasonló: pictures.
        pictures = getattr(audio, "pictures", None)
        if pictures:
            pic = pictures[0]
            data = getattr(pic, "data", None)
            mime = str(getattr(pic, "mime", "") or "").lower()
            if "png" in mime:
                ext = ".png"

        # MP3 ID3 APIC frame.
        if data is None:
            tags = getattr(audio, "tags", None)
            if tags:
                try:
                    values = list(tags.values())
                except Exception:
                    values = []

                for item in values:
                    if item.__class__.__name__.startswith("APIC"):
                        data = getattr(item, "data", None)
                        mime = str(getattr(item, "mime", "") or "").lower()
                        if "png" in mime:
                            ext = ".png"
                        break

                # MP4/M4A 'covr'
                if data is None:
                    try:
                        covers = tags.get("covr")
                    except Exception:
                        covers = None

                    if covers:
                        raw = covers[0]
                        data = bytes(raw)
                        # PNG signature
                        if data[:8] == b"\x89PNG\r\n\x1a\n":
                            ext = ".png"

        if not data:
            return ""

        target = cache_dir / f"{key}{ext}"
        target.write_bytes(bytes(data))
        return str(target)

    except Exception as error:
        print("BORÍTÓ KIOLVASÁSI HIBA:", error)
        return ""


def album_cover(album, artist, songs):
    for path in songs:
        info = track_metadata(path)
        if (
            info["album"] == album
            and info["artist"] == artist
        ):
            cover = cover_for_track(path)
            if cover:
                return cover
    return ""


def clean_title(path):
    info = track_metadata(path)
    artist = info["artist"]
    title = info["title"]

    if artist and artist != "Ismeretlen előadó":
        return f"{artist} - {title}"
    return title


def clean_song_title_only(path):
    return track_metadata(path)["title"]


def _lyrics_cache_path(audio_path):
    """Android-barát LRC cache: nem kell írni a Music/Download mappába."""
    try:
        app = App.get_running_app()
        base = Path(app.user_data_dir) / "lyrics_cache"
    except Exception:
        base = Path.home() / ".justmusic_lyrics_cache"

    key = hashlib.sha1(
        str(audio_path).encode("utf-8", errors="ignore")
    ).hexdigest()[:20]

    return base / f"{key}.lrc"


def find_lrc_file(audio_path):
    # 1) Kézzel mellétett .lrc mindig elsőbbséget kap.
    sidecar = Path(audio_path).with_suffix(".lrc")
    if sidecar.exists():
        return sidecar

    # 2) Automatikusan letöltött / generált LRC cache.
    cached = _lyrics_cache_path(audio_path)
    if cached.exists():
        return cached

    return None


def parse_lrc(audio_path):
    p = find_lrc_file(audio_path)
    if p is None:
        return []

    try:
        text = p.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

    rows = []
    for raw in text.splitlines():
        stamps = re.findall(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]", raw)
        lyric = re.sub(r"\[[^\]]+\]", "", raw).strip() or "♪"
        for mm, ss, fraction in stamps:
            frac = 0.0
            if fraction:
                frac = int(fraction) / (1000 if len(fraction) == 3 else 100)
            rows.append((int(mm) * 60 + int(ss) + frac, lyric))

    rows.sort(key=lambda x: x[0])
    return rows


def _save_auto_lrc(audio_path, lrc_text):
    text = str(lrc_text or "").strip()
    if not text:
        return None

    # Android 11+ alatt a Music mappa gyakran read-only az app számára,
    # ezért biztosan az app saját tárhelyére mentünk.
    cache = _lyrics_cache_path(audio_path)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8-sig")

    # Ha a rendszer engedi, sidecar .lrc-t is készítünk a zenéhez.
    try:
        sidecar = Path(audio_path).with_suffix(".lrc")
        sidecar.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8-sig")
    except Exception:
        pass

    return cache


def _normalize_lyrics_search(text):
    text = _clean_title_text(text)
    text = str(text or "").strip().casefold()
    return re.sub(r"\s+", " ", text)


def _lrclib_request(endpoint, params):
    query = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v not in (None, "")}
    )
    url = "https://lrclib.net" + endpoint
    if query:
        url += "?" + query

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "JustMusic-Mobile/1.4 (Android music player; https://lrclib.net)"
        }
    )

    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _score_lrclib(item, title, artist, duration):
    score = 0
    rt = _normalize_lyrics_search(item.get("trackName") or item.get("name"))
    ra = _normalize_lyrics_search(item.get("artistName"))
    wt = _normalize_lyrics_search(title)
    wa = _normalize_lyrics_search(artist)

    if wt and rt == wt:
        score += 140
    elif wt and (wt in rt or rt in wt):
        score += 75

    if wa and ra == wa:
        score += 125
    elif wa and (wa in ra or ra in wa):
        score += 55

    try:
        rd = float(item.get("duration") or 0)
        if duration and rd:
            diff = abs(float(duration) - rd)
            if diff <= 2:
                score += 90
            elif diff <= 5:
                score += 55
            elif diff <= 10:
                score += 25
            elif diff > 30:
                score -= 35
    except Exception:
        pass

    if item.get("syncedLyrics"):
        score += 60

    return score


def _find_online_lyrics(audio_path, duration):
    meta = track_metadata(audio_path)
    title = _clean_title_text(meta.get("title"))
    artist = _clean_title_text(meta.get("artist"))
    album = _clean_title_text(meta.get("album"))

    if artist in ("Ismeretlen előadó", "Unknown Artist"):
        artist = ""
    if album in ("Ismeretlen album", "Unknown Album"):
        album = ""

    exact_plain = None
    results = []

    # 1) LRCLIB exact — ugyanaz az elsődleges út, mint PC-n.
    if title and artist and duration and duration > 0:
        params = {
            "track_name": title,
            "artist_name": artist,
            "duration": int(round(duration)),
        }
        if album:
            params["album_name"] = album

        try:
            data = _lrclib_request("/api/get", params)
            synced = str(data.get("syncedLyrics") or "").strip()
            plain = str(data.get("plainLyrics") or "").strip()
            if synced:
                return {
                    "kind": "synced",
                    "text": synced,
                    "source": "LRCLIB",
                    "match": data,
                }
            if plain:
                exact_plain = plain
        except urllib.error.HTTPError as error:
            if error.code != 404:
                print("LRCLIB GET HTTP:", error.code)
        except Exception as error:
            print("LRCLIB GET HIBA:", error)

    # 2) LRCLIB több, lazább keresése.
    searches = []
    if title:
        params = {"track_name": title}
        if artist:
            params["artist_name"] = artist
        searches.append(params)

    query = " ".join(x for x in (artist, title) if x).strip()
    if query:
        searches.append({"q": query})
    if title:
        searches.append({"q": title})

    for params in searches:
        try:
            found = _lrclib_request("/api/search", params)
            if isinstance(found, list):
                results.extend(found)
        except Exception as error:
            print("LRCLIB SEARCH HIBA:", error)

    unique = []
    seen = set()
    for item in results:
        key = item.get("id") or (
            item.get("trackName"), item.get("artistName"), item.get("duration")
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    synced = [x for x in unique if x.get("syncedLyrics")]
    if synced:
        synced.sort(
            key=lambda x: _score_lrclib(x, title, artist, duration),
            reverse=True,
        )
        best = synced[0]
        # Nagyon gyenge találatot ne mentsünk el automatikusan.
        if _score_lrclib(best, title, artist, duration) >= 70:
            return {
                "kind": "synced",
                "text": best.get("syncedLyrics"),
                "source": "LRCLIB",
                "match": best,
            }

    plain = [x for x in unique if x.get("plainLyrics")]
    if plain:
        plain.sort(
            key=lambda x: _score_lrclib(x, title, artist, duration),
            reverse=True,
        )
        best = plain[0]
        if _score_lrclib(best, title, artist, duration) >= 70:
            return {
                "kind": "plain",
                "text": best.get("plainLyrics"),
                "source": "LRCLIB plain",
                "match": best,
            }

    if exact_plain:
        return {
            "kind": "plain",
            "text": exact_plain,
            "source": "LRCLIB plain",
            "match": None,
        }

    # 3) lyrics.ovh plain fallback.
    if artist and title:
        try:
            url = (
                "https://api.lyrics.ovh/v1/"
                + urllib.parse.quote(artist, safe="")
                + "/"
                + urllib.parse.quote(title, safe="")
            )
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "JustMusic-Mobile/1.4"}
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            plain_text = str(data.get("lyrics") or "").strip()
            if plain_text:
                return {
                    "kind": "plain",
                    "text": plain_text,
                    "source": "lyrics.ovh",
                    "match": None,
                }
        except Exception as error:
            print("LYRICS.OVH HIBA:", error)

    return None


def _plain_to_estimated_lrc(plain_text, duration, meta=None):
    """Plain lyrics -> automatikus, becsült időzítés. Nem kézi munka."""
    lines = []
    for raw in str(plain_text or "").replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        # API-k néha fölösleges fejlécet adnak vissza.
        if line.casefold().startswith(("paroles de", "lyrics of")):
            continue
        lines.append(line)

    if not lines:
        return ""

    try:
        duration = float(duration or 0)
    except Exception:
        duration = 0.0

    if duration <= 10:
        duration = max(30.0, len(lines) * 4.2)

    intro = min(8.0, max(2.0, duration * 0.025))
    outro = min(8.0, max(2.0, duration * 0.02))
    usable = max(10.0, duration - intro - outro)

    # Hosszabb soroknak kicsit több időt hagyunk.
    weights = [max(1.0, min(3.2, len(line) / 22.0)) for line in lines]
    total_weight = sum(weights) or float(len(lines))

    result = []
    meta = meta or {}
    artist = str(meta.get("artist") or "").strip()
    title = str(meta.get("title") or "").strip()
    if artist:
        result.append(f"[ar:{artist}]")
    if title:
        result.append(f"[ti:{title}]")
    result.append("[re:JustMusic! Auto Sync]")

    elapsed = intro
    for line, weight in zip(lines, weights):
        mm = int(elapsed // 60)
        ss = elapsed - mm * 60
        result.append(f"[{mm:02d}:{ss:05.2f}]{line}")
        elapsed += usable * (weight / total_weight)

    return "\n".join(result)


def replaygain_db(path):
    if MutagenFile is None:
        return 0.0
    try:
        audio = MutagenFile(path, easy=False)
        tags = getattr(audio, "tags", None)
        if not tags:
            return 0.0
        for key in tags.keys():
            if "replaygain_track_gain" in str(key).lower():
                value = tags[key]
                if isinstance(value, (list, tuple)):
                    value = value[0]
                m = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
                if m:
                    return float(m.group(0))
    except Exception:
        pass
    return 0.0


class GlassPanel(BoxLayout):
    radius = NumericProperty(dp(18))
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*PANEL)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.40)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius), width=1.1)
        self.bind(pos=self._sync, size=self._sync, radius=self._sync)
    def _sync(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_rect.radius = [self.radius]
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)


class DarkOverlay(Widget):
    def __init__(self, opacity_value=0.60, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(0, 0.02, 0.05, opacity_value)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)
    def _sync(self, *_):
        self.rect.pos = self.pos
        self.rect.size = self.size


class SeekSlider(Slider):
    dragging = BooleanProperty(False)
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.dragging = True
        return super().on_touch_down(touch)
    def on_touch_up(self, touch):
        result = super().on_touch_up(touch)
        if self.dragging:
            self.dragging = False
            app = App.get_running_app()
            if app:
                app.seek_to(self.value)
        return result


class NativeAudio:
    """Android MediaPlayer + Android Equalizer. Desktopon SoundLoader fallback."""
    def __init__(self):
        self.android = platform == "android"
        self.player = None
        self.next_player = None
        self.eq = None
        self.desktop = None
        if self.android:
            try:
                from jnius import autoclass
                self.MediaPlayer = autoclass("android.media.MediaPlayer")
                self.Equalizer = autoclass("android.media.audiofx.Equalizer")
            except Exception as e:
                print("MediaPlayer init hiba:", e)
                self.android = False

    def _release_eq(self):
        if self.eq is not None:
            try: self.eq.setEnabled(False)
            except Exception: pass
            try: self.eq.release()
            except Exception: pass
            self.eq = None

    def _release(self, player):
        if player is None:
            return
        try: player.stop()
        except Exception: pass
        try: player.reset()
        except Exception: pass
        try: player.release()
        except Exception: pass

    def _new(self, path):
        p = self.MediaPlayer()
        p.setDataSource(str(path))
        p.prepare()
        return p

    def load(self, path):
        self._release_eq()
        if self.android:
            self._release(self.player)
            self._release(self.next_player)
            self.next_player = None
            self.player = self._new(path)
            return True
        if self.desktop is not None:
            try: self.desktop.stop(); self.desktop.unload()
            except Exception: pass
        self.desktop = SoundLoader.load(path)
        return self.desktop is not None

    def prepare_next(self, path):
        if not self.android:
            return False
        self._release(self.next_player)
        self.next_player = self._new(path)
        return True

    def start(self):
        if self.android:
            if self.player is not None: self.player.start()
        elif self.desktop is not None:
            self.desktop.play()

    def start_next(self):
        if self.android and self.next_player is not None:
            self.next_player.start()

    def pause(self):
        if self.android:
            try:
                if self.player is not None and self.player.isPlaying(): self.player.pause()
            except Exception: pass
        elif self.desktop is not None:
            try: self.desktop.stop()
            except Exception: pass

    def is_playing(self):
        if self.android:
            try: return bool(self.player and self.player.isPlaying())
            except Exception: return False
        return bool(self.desktop is not None and getattr(self.desktop, "state", "") == "play")

    def position(self):
        if self.android:
            try: return max(0.0, self.player.getCurrentPosition() / 1000.0)
            except Exception: return 0.0
        try: return max(0.0, float(self.desktop.get_pos() or 0))
        except Exception: return 0.0

    def duration(self):
        if self.android:
            try: return max(0.0, self.player.getDuration() / 1000.0)
            except Exception: return 0.0
        try: return max(0.0, float(self.desktop.length or 0))
        except Exception: return 0.0

    def seek(self, seconds):
        if self.android:
            try: self.player.seekTo(int(float(seconds) * 1000))
            except Exception: pass
        elif self.desktop is not None:
            try: self.desktop.seek(float(seconds))
            except Exception: pass

    def volume(self, current, next_value=None):
        current = max(0, min(1, float(current)))
        if self.android:
            try:
                if self.player is not None: self.player.setVolume(current, current)
            except Exception: pass
            if next_value is not None:
                n = max(0, min(1, float(next_value)))
                try:
                    if self.next_player is not None: self.next_player.setVolume(n, n)
                except Exception: pass
        elif self.desktop is not None:
            try: self.desktop.volume = current
            except Exception: pass

    def swap_to_next(self):
        if not self.android or self.next_player is None:
            return False
        old = self.player
        self.player = self.next_player
        self.next_player = None
        self._release_eq()
        self._release(old)
        return True

    def apply_eq(self, values):
        if not self.android or self.player is None:
            return
        try:
            if self.eq is None:
                self.eq = self.Equalizer(0, self.player.getAudioSessionId())
                self.eq.setEnabled(True)
            count = int(self.eq.getNumberOfBands())
            bounds = self.eq.getBandLevelRange()
            low, high = int(bounds[0]), int(bounds[1])
            for band in range(count):
                src = round(band * (len(values) - 1) / max(1, count - 1))
                level = max(low, min(high, int(float(values[src]) * 100)))
                self.eq.setBandLevel(band, level)
        except Exception as e:
            print("EQ hiba:", e)
            self._release_eq()

    def close(self):
        self._release_eq()
        self._release(self.player)
        self._release(self.next_player)
        self.player = self.next_player = None


class PlayerBar(GlassPanel):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(5), size_hint_y=None, height=dp(184), **kwargs)

        row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.title = Label(text="[b]JustMusic![/b]", markup=True, color=TEXT, halign="left", valign="middle")
        self.title.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        lyrics = Button(text="DALSZÖVEG", size_hint_x=None, width=dp(105), background_normal="", background_color=PANEL_2, color=ACCENT_2, bold=True)
        lyrics.bind(on_release=lambda *_: App.get_running_app().open_lyrics())
        row.add_widget(self.title); row.add_widget(lyrics); self.add_widget(row)

        seek = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(5))
        self.elapsed = Label(text="0:00", color=TEXT_2, size_hint_x=None, width=dp(42))
        self.slider = SeekSlider(min=0, max=1, value=0)
        self.total = Label(text="0:00", color=TEXT_2, size_hint_x=None, width=dp(42))
        seek.add_widget(self.elapsed); seek.add_widget(self.slider); seek.add_widget(self.total); self.add_widget(seek)

        controls = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(5))
        self.buttons = {}
        for name in ("SHUF", "PREV", "PLAY", "NEXT", "REP"):
            btn = Button(text=name, background_normal="", background_color=ACCENT if name == "PLAY" else PANEL_2,
                         color=(0, .07, .12, 1) if name == "PLAY" else TEXT, bold=True, font_size="11sp")
            self.buttons[name] = btn
            controls.add_widget(btn)
        self.buttons["SHUF"].bind(on_release=lambda *_: App.get_running_app().toggle_shuffle())
        self.buttons["PREV"].bind(on_release=lambda *_: App.get_running_app().previous())
        self.buttons["PLAY"].bind(on_release=lambda *_: App.get_running_app().toggle_play())
        self.buttons["NEXT"].bind(on_release=lambda *_: App.get_running_app().next_pressed())
        self.buttons["REP"].bind(on_release=lambda *_: App.get_running_app().cycle_repeat())
        self.add_widget(controls)

        features = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.feature_buttons = {}
        for text, target in (("MIX", "mix"), ("EQ", "eq"), ("RG", "rg"), ("QUEUE", "queue"), ("SLEEP", "sleep")):
            b = Button(text=text, background_normal="", background_color=(.03, .10, .17, .96), color=ACCENT_2, bold=True, font_size="10sp")
            b.bind(on_release=lambda _, n=target: App.get_running_app().open_screen(n))
            self.feature_buttons[target] = b
            features.add_widget(b)
        self.add_widget(features)

    def set_playing(self, on): self.buttons["PLAY"].text = "PAUSE" if on else "PLAY"
    def set_shuffle(self, on): self.buttons["SHUF"].color = ACCENT_2 if on else TEXT
    def set_repeat(self, mode):
        self.buttons["REP"].text = {"off":"REP", "all":"REP ALL", "one":"REP 1"}[mode]
        self.buttons["REP"].color = ACCENT_2 if mode != "off" else TEXT
    def set_mix_status(self, crossfade, gapless, fade_out, fade_in):
        b = self.feature_buttons.get("mix")
        if not b: return
        if gapless:
            b.text = "MIX GAP"; b.color = ACCENT_2
        elif crossfade:
            b.text = f"MIX {fade_out:.1f}/{fade_in:.1f}"; b.color = ACCENT_2
        else:
            b.text = "MIX"; b.color = TEXT_2


class MadeInHungaryBanner(GlassPanel):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(86),
            padding=[dp(14), dp(8)],
            spacing=dp(1),
            **kwargs
        )
        self.add_widget(Label(
            text="[b][color=63D2FF]MADE IN HUNGARY[/color][/b]",
            markup=True,
            color=TEXT,
            font_size="18sp",
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(32)
        ))
        info = Label(
            text="Szabó Zoltán  •  IG: ZS420LLER",
            color=TEXT_2,
            font_size="12sp",
            halign="left",
            valign="middle"
        )
        info.bind(size=lambda inst, val: setattr(inst, "text_size", (inst.width, inst.height)))
        self.add_widget(info)


def make_song_row(path, refresh_callback=None):
    app = App.get_running_app()
    row = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(6))

    cover_path = cover_for_track(path)
    if cover_path:
        cover = Image(
            source=cover_path,
            size_hint_x=None,
            width=dp(58),
            allow_stretch=True,
            keep_ratio=True
        )
    else:
        cover = Label(
            text="♫",
            size_hint_x=None,
            width=dp(58),
            color=ACCENT_2,
            font_size="24sp"
        )

    row.add_widget(cover)

    title = clean_title(path)
    play = Button(
        text=title,
        halign="left",
        valign="middle",
        text_size=(Window.width - dp(130), None),
        background_normal="",
        background_color=CARD,
        color=TEXT,
        font_size="15sp"
    )
    play.bind(on_release=lambda *_: app.play_path(path))

    fav = Button(
        text="★" if app.is_favorite(path) else "☆",
        size_hint_x=None,
        width=dp(52),
        background_normal="",
        background_color=PANEL_2,
        color=ACCENT_2 if app.is_favorite(path) else TEXT_2,
        font_size="21sp",
        bold=True
    )

    def toggle(*_):
        app.toggle_favorite(path)
        fav.text = "★" if app.is_favorite(path) else "☆"
        fav.color = ACCENT_2 if app.is_favorite(path) else TEXT_2
        if refresh_callback:
            refresh_callback()

    fav.bind(on_release=toggle)
    row.add_widget(play)
    row.add_widget(fav)
    return row


class LibraryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Image(source="party_bg.png", allow_stretch=True, keep_ratio=False))
        self.add_widget(DarkOverlay(.62))

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(12), dp(14), dp(10)],
            spacing=dp(7)
        )

        brand = Label(
            text="[b][color=63D2FF]JustMusic![/color][/b]",
            markup=True,
            font_size="27sp",
            size_hint_y=None,
            height=dp(48),
            halign="left",
            valign="middle"
        )
        brand.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        root.add_widget(brand)
        root.add_widget(MadeInHungaryBanner())

        # Mobil könyvtár-navigáció: a PC-s fő nézetekből áthozva.
        nav1 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        nav2 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        for parent, text, target in (
            (nav1, "DALOK", "library"),
            (nav1, "ELŐADÓK", "artists"),
            (nav1, "ALBUMOK", "albums"),
            (nav2, "KEDVENCEK", "favorites"),
            (nav2, "CONNECT", "connect"),
            (nav2, "FRISSÍTÉS", "refresh"),
        ):
            b = Button(
                text=text,
                background_normal="",
                background_color=PANEL_2,
                color=ACCENT_2 if target != "refresh" else TEXT_2,
                bold=True,
                font_size="10sp"
            )
            if target == "refresh":
                b.bind(on_release=lambda *_: App.get_running_app().scan())
            else:
                b.bind(on_release=lambda _, t=target: App.get_running_app().open_screen(t))
            parent.add_widget(b)
        root.add_widget(nav1)
        root.add_widget(nav2)

        nav3 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        for text, target in (
            ("MAPPÁK", "folders"),
            ("PLAYLISTEK", "playlists"),
            ("MOST SZÓL", "now_playing"),
        ):
            b = Button(
                text=text,
                background_normal="",
                background_color=PANEL_2,
                color=ACCENT_2,
                bold=True,
                font_size="9sp"
            )
            b.bind(
                on_release=lambda _, t=target:
                    App.get_running_app().open_screen(t)
            )
            nav3.add_widget(b)

        root.add_widget(nav3)

        nav4 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        for text, target in (
            ("ELŐZMÉNY", "history"),
            ("STAT", "stats"),
            ("SMART", "smart"),
        ):
            b = Button(
                text=text,
                background_normal="",
                background_color=(.025, .085, .145, .96),
                color=TEXT_2,
                bold=True,
                font_size="9sp"
            )
            b.bind(
                on_release=lambda _, t=target:
                    App.get_running_app().open_screen(t)
            )
            nav4.add_widget(b)
        root.add_widget(nav4)

        self.search = TextInput(
            hint_text="Keresés a zenék között…",
            multiline=False,
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_active="",
            background_color=(.03, .11, .19, .96),
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=ACCENT_2,
            padding=[dp(14), dp(12)]
        )
        self.search.bind(text=lambda *_: self.refresh_list())
        root.add_widget(self.search)

        p = GlassPanel(size_hint_y=None, height=dp(54), padding=[dp(13), dp(7)])
        self.status = Label(text="Zenetár betöltése…", color=TEXT_2, halign="left", valign="middle")
        self.status.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        p.add_widget(self.status)
        root.add_widget(p)

        scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None, padding=[0, dp(3), 0, dp(7)])
        self.box.bind(minimum_height=self.box.setter("height"))
        scroll.add_widget(self.box)
        root.add_widget(scroll)

        self.player = PlayerBar()
        root.add_widget(self.player)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.refresh_list()

    def refresh_list(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        q = self.search.text.strip().lower()
        visible = []

        for path in app.songs:
            title = clean_title(path)
            if not q or q in title.lower():
                visible.append(path)

        self.status.text = (
            f"{len(visible)} dal • {app.backend_name}"
            if app.songs
            else "Nem találtam zenét a beállított zene mappákban."
        )

        for path in visible:
            self.box.add_widget(make_song_row(path, self.refresh_list))


class LyricsScreen(Screen):
    """Teljes, görgethető, szinkronizált LRC nézet."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Image(source="party_bg.png", allow_stretch=True, keep_ratio=False))
        self.add_widget(DarkOverlay(.60))

        self.lyric_widgets = []
        self.active_index = -1

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(7))
        top = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(6))
        back = Button(
            text="VISSZA",
            size_hint_x=None,
            width=dp(88),
            background_normal="",
            background_color=PANEL_2,
            color=TEXT,
            bold=True
        )
        back.bind(on_release=lambda *_: App.get_running_app().show_library())
        self.track = Label(
            text="[b]JustMusic! • Dalszöveg[/b]",
            markup=True,
            color=TEXT,
            halign="left",
            valign="middle"
        )
        self.track.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        top.add_widget(back)
        top.add_widget(self.track)
        root.add_widget(top)

        self.search_status = Label(
            text="",
            size_hint_y=None,
            height=dp(30),
            color=ACCENT_2,
            bold=True,
            font_size="12sp",
            halign="center",
            valign="middle"
        )
        self.search_status.bind(
            size=lambda i, v: setattr(i, "text_size", (i.width, i.height))
        )
        root.add_widget(self.search_status)

        self.scroll = ScrollView(do_scroll_x=False)
        self.lyrics_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
            padding=[dp(4), dp(100), dp(4), dp(160)]
        )
        self.lyrics_box.bind(minimum_height=self.lyrics_box.setter("height"))
        self.scroll.add_widget(self.lyrics_box)
        root.add_widget(self.scroll)

        self.time = Label(
            text="0:00 / 0:00",
            size_hint_y=None,
            height=dp(34),
            color=ACCENT_2,
            bold=True
        )
        root.add_widget(self.time)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.rebuild_lyrics()

    def set_search_status(self, text, color=None):
        try:
            self.search_status.text = str(text or "")
            self.search_status.color = color or ACCENT_2
        except Exception:
            pass

    def rebuild_lyrics(self):
        app = App.get_running_app()
        self.lyrics_box.clear_widgets()
        self.lyric_widgets = []
        self.active_index = -1

        if not app.lyrics:
            searching = bool(
                app.current_path
                and app.current_path in getattr(app, "lyrics_fetching", set())
            )
            message = (
                "Automatikus dalszöveg-szinkron keresése…\nLRCLIB + online fallback"
                if searching
                else "Ehhez a számhoz még nincs szinkronizált dalszöveg."
            )
            label = Label(
                text=message,
                color=TEXT,
                font_size="22sp",
                bold=True,
                size_hint_y=None,
                height=dp(180),
                halign="center",
                valign="middle"
            )
            label.bind(size=lambda i, v: setattr(i, "text_size", (i.width - dp(20), i.height)))
            self.lyrics_box.add_widget(label)
            return

        for index, (timestamp, text) in enumerate(app.lyrics):
            row = Button(
                text=text,
                size_hint_y=None,
                height=dp(62),
                background_normal="",
                background_color=(0.03, 0.09, 0.15, 0.45),
                color=(0.72, 0.84, 0.94, 1),
                font_size="18sp",
                bold=True,
                halign="center",
                valign="middle",
                text_size=(Window.width - dp(52), None)
            )
            row.bind(on_release=lambda _, ts=timestamp: app.seek_to(ts))
            self.lyrics_box.add_widget(row)
            self.lyric_widgets.append(row)

        self.set_active(app.lyric_index, force=True)

    def set_active(self, index, force=False):
        if not self.lyric_widgets:
            return
        if not force and index == self.active_index:
            return

        old = self.active_index
        self.active_index = index

        if 0 <= old < len(self.lyric_widgets):
            widget = self.lyric_widgets[old]
            widget.color = (0.72, 0.84, 0.94, 1)
            widget.background_color = (0.03, 0.09, 0.15, 0.45)
            widget.font_size = "18sp"

        if 0 <= index < len(self.lyric_widgets):
            widget = self.lyric_widgets[index]
            widget.color = TEXT
            widget.background_color = (0.10, 0.34, 0.52, 0.72)
            widget.font_size = "23sp"
            Clock.schedule_once(lambda *_: self.scroll.scroll_to(widget, padding=dp(115), animate=True), 0.03)


class BaseFeature(Screen):

    def make(self,title):
        self.add_widget(Image(source="party_bg.png",allow_stretch=True,keep_ratio=False)); self.add_widget(DarkOverlay(.68))
        root=BoxLayout(orientation="vertical",padding=dp(18),spacing=dp(12)); top=BoxLayout(size_hint_y=None,height=dp(54))
        back=Button(text="VISSZA",size_hint_x=None,width=dp(88),background_normal="",background_color=PANEL_2,color=TEXT,bold=True); back.bind(on_release=lambda *_:App.get_running_app().show_library())
        lab=Label(text=f"[b]{title}[/b]",markup=True,color=TEXT,font_size="23sp",halign="left",valign="middle"); lab.bind(size=lambda i,v:setattr(i,"text_size",(i.width,i.height))); self.title_label=lab; top.add_widget(back); top.add_widget(lab); root.add_widget(top); self.add_widget(root); return root


class ArtistsScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ELŐADÓK")
        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        groups = {}
        for path in app.songs:
            artist = track_metadata(path)["artist"]
            groups.setdefault(artist, []).append(path)

        for artist in sorted(groups, key=str.casefold):
            tracks = groups[artist]
            b = Button(
                text=f"{artist}\n{len(tracks)} dal",
                size_hint_y=None,
                height=dp(66),
                background_normal="",
                background_color=CARD,
                color=TEXT,
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(58), None),
                bold=True
            )
            b.bind(on_release=lambda _, a=artist: app.open_artist(a))
            self.box.add_widget(b)


class ArtistTracksScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ELŐADÓ")
        self.artist = None
        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def set_artist(self, artist):
        self.artist = artist
        self.title_label.text = f"[b]{artist}[/b]"
        self.refresh()

    def refresh(self):
        self.box.clear_widgets()
        app = App.get_running_app()
        for path in app.songs:
            if track_metadata(path)["artist"] == self.artist:
                self.box.add_widget(make_song_row(path, self.refresh))


class AlbumsScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ALBUMOK")
        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        groups = {}
        for path in app.songs:
            info = track_metadata(path)
            key = (info["album"], info["artist"])
            groups.setdefault(key, []).append(path)

        for album, artist in sorted(groups, key=lambda x: (x[0].casefold(), x[1].casefold())):
            tracks = groups[(album, artist)]

            row = BoxLayout(
                size_hint_y=None,
                height=dp(76),
                spacing=dp(7)
            )

            cover_path = album_cover(
                album,
                artist,
                tracks
            )

            if cover_path:
                row.add_widget(Image(
                    source=cover_path,
                    size_hint_x=None,
                    width=dp(70),
                    allow_stretch=True,
                    keep_ratio=True
                ))
            else:
                row.add_widget(Label(
                    text="💿",
                    size_hint_x=None,
                    width=dp(70),
                    color=ACCENT_2,
                    font_size="24sp"
                ))

            b = Button(
                text=f"{album}\n{artist} • {len(tracks)} dal",
                background_normal="",
                background_color=CARD,
                color=TEXT,
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(140), None),
                bold=True
            )
            b.bind(
                on_release=lambda _, a=album, ar=artist:
                    app.open_album(a, ar)
            )

            row.add_widget(b)
            self.box.add_widget(row)


class AlbumTracksScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ALBUM")
        self.album = None
        self.artist = None
        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def set_album(self, album, artist):
        self.album = album
        self.artist = artist
        self.title_label.text = f"[b]{album}[/b]"
        self.refresh()

    def refresh(self):
        self.box.clear_widgets()
        app = App.get_running_app()
        for path in app.songs:
            info = track_metadata(path)
            if info["album"] == self.album and info["artist"] == self.artist:
                self.box.add_widget(make_song_row(path, self.refresh))


class FavoritesScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("KEDVENCEK")
        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        paths = [p for p in app.songs if app.is_favorite(p)]

        if not paths:
            self.box.add_widget(Label(
                text="Még nincs kedvenc dalod.\nA csillaggal tudsz hozzáadni.",
                color=TEXT_2,
                size_hint_y=None,
                height=dp(130),
                halign="center"
            ))
            return

        for path in paths:
            self.box.add_widget(make_song_row(path, self.refresh))


class ConnectScreen(BaseFeature):
    """Android Bluetooth / Connect nézet, a PC-s Connect mobil megfelelője."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("CONNECT")

        current = GlassPanel(
            orientation="vertical",
            size_hint_y=None,
            height=dp(106),
            padding=dp(12),
            spacing=dp(3)
        )
        current.add_widget(Label(
            text="[b]Ez a telefon[/b]   •   [color=63D2FF]AKTÍV[/color]",
            markup=True,
            color=TEXT,
            font_size="19sp",
            halign="left",
            valign="middle"
        ))
        self.now = Label(text="JustMusic!", color=TEXT_2, halign="left", valign="middle")
        self.now.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        current.add_widget(self.now)
        root.add_widget(current)

        controls = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        refresh = Button(
            text="ESZKÖZÖK FRISSÍTÉSE",
            background_normal="",
            background_color=PANEL_2,
            color=ACCENT_2,
            bold=True
        )
        settings = Button(
            text="BLUETOOTH BEÁLLÍTÁSOK",
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True
        )
        refresh.bind(on_release=lambda *_: self.refresh_devices())
        settings.bind(on_release=lambda *_: App.get_running_app().open_bluetooth_settings())
        controls.add_widget(refresh)
        controls.add_widget(settings)
        root.add_widget(controls)

        self.output_info = Label(
            text="Elérhető audio kimenetek",
            color=ACCENT_2,
            size_hint_y=None,
            height=dp(30),
            halign="left"
        )
        root.add_widget(self.output_info)

        self.output_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(70),
            spacing=dp(3)
        )
        root.add_widget(self.output_box)

        self.info = Label(
            text="Párosított Bluetooth-eszközök",
            color=MUTED,
            size_hint_y=None,
            height=dp(34),
            halign="left"
        )
        root.add_widget(self.info)

        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        app = App.get_running_app()
        self.now.text = clean_title(app.current_path) if app.current_path else "Nincs lejátszás"
        self.refresh_devices()

    def refresh_devices(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        outputs = app.audio_output_devices()
        self.output_box.clear_widgets()
        if outputs:
            text="  •  ".join(name for name,_ in outputs[:4])
        else:
            text="A rendszer nem adott vissza audio kimenetet."
        self.output_box.add_widget(Label(
            text=text,
            color=TEXT_2,
            halign="left",
            valign="middle",
            text_size=(Window.width-dp(60), None)
        ))

        devices = app.bluetooth_devices()

        if not devices:
            self.box.add_widget(Label(
                text="Nem találtam párosított Bluetooth-eszközt.\nNyisd meg a Bluetooth beállításokat a párosításhoz.",
                color=TEXT_2,
                size_hint_y=None,
                height=dp(120),
                halign="center"
            ))
            return

        for name, address in devices:
            b = Button(
                text=f"{name}\n{address}",
                size_hint_y=None,
                height=dp(68),
                background_normal="",
                background_color=CARD,
                color=TEXT,
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(58), None)
            )
            # Androidon az output-váltást a rendszer kezeli; koppintásra megnyitjuk a BT panelt.
            b.bind(on_release=lambda *_: app.open_bluetooth_settings())
            self.box.add_widget(b)



class FoldersScreen(BaseFeature):
    """
    Zene mappák kezelése.
    Androidon teljes elérési út adható meg, és az app megjegyzi.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ZENE MAPPÁK")

        info = Label(
            text=(
                "A JustMusic! ezeket a mappákat vizsgálja.\n"
                "Androidon a MAPPA KIVÁLASZTÁSA gomb a legegyszerűbb."
            ),
            color=TEXT_2,
            size_hint_y=None,
            height=dp(64),
            halign="center"
        )
        root.add_widget(info)

        picker = Button(
            text="MAPPA KIVÁLASZTÁSA",
            size_hint_y=None,
            height=dp(54),
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True
        )
        picker.bind(
            on_release=lambda *_:
                App.get_running_app().pick_music_folder()
        )
        root.add_widget(picker)

        self.picker_status = Label(
            text="Vagy add meg kézzel a teljes elérési utat:",
            color=MUTED,
            size_hint_y=None,
            height=dp(32),
            halign="left",
            valign="middle"
        )
        self.picker_status.bind(
            size=lambda i, v: setattr(i, "text_size", (i.width, i.height))
        )
        root.add_widget(self.picker_status)

        self.path_input = TextInput(
            hint_text="/storage/emulated/0/SajatZene",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_active="",
            background_color=(.03, .11, .19, .96),
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=ACCENT_2,
            padding=[dp(12), dp(12)]
        )
        root.add_widget(self.path_input)

        add = Button(
            text="MAPPA HOZZÁADÁSA",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True
        )
        add.bind(on_release=lambda *_: self.add_folder())
        root.add_widget(add)

        quick = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(5))
        for label, path in (
            ("MUSIC", "/storage/emulated/0/Music"),
            ("DOWNLOAD", "/storage/emulated/0/Download"),
            ("BLUETOOTH", "/storage/emulated/0/Bluetooth"),
        ):
            b = Button(
                text=label,
                background_normal="",
                background_color=PANEL_2,
                color=ACCENT_2,
                bold=True,
                font_size="10sp"
            )
            b.bind(
                on_release=lambda _, p=path:
                    self.quick_add(p)
            )
            quick.add_widget(b)
        root.add_widget(quick)

        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(7)
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def quick_add(self, path):
        self.path_input.text = path
        self.add_folder()

    def add_folder(self):
        app = App.get_running_app()
        path = self.path_input.text.strip()
        if not path:
            return
        app.add_music_folder(path)
        self.path_input.text = ""
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()

        for path in app.music_roots():
            custom = path in app.custom_folders
            row = BoxLayout(
                size_hint_y=None,
                height=dp(58),
                spacing=dp(5)
            )
            label = Label(
                text=path,
                color=TEXT if os.path.isdir(path) else MUTED,
                halign="left",
                valign="middle"
            )
            label.bind(
                size=lambda i, v:
                    setattr(i, "text_size", (i.width, i.height))
            )
            row.add_widget(label)

            if custom:
                remove = Button(
                    text="TÖRLÉS",
                    size_hint_x=None,
                    width=dp(82),
                    background_normal="",
                    background_color=(.20, .07, .10, .95),
                    color=TEXT,
                    bold=True
                )
                remove.bind(
                    on_release=lambda _, p=path:
                        self.remove_folder(p)
                )
                row.add_widget(remove)

            self.box.add_widget(row)

    def remove_folder(self, path):
        app = App.get_running_app()
        app.remove_music_folder(path)
        self.refresh()


class PlaylistsScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("PLAYLISTEK")

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        self.name_input = TextInput(
            hint_text="Új playlist neve",
            multiline=False,
            background_normal="",
            background_active="",
            background_color=(.03, .11, .19, .96),
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=ACCENT_2
        )
        create = Button(
            text="LÉTREHOZÁS",
            size_hint_x=None,
            width=dp(120),
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True
        )
        create.bind(on_release=lambda *_: self.create_playlist())
        row.add_widget(self.name_input)
        row.add_widget(create)
        root.add_widget(row)

        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(7)
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def create_playlist(self):
        app = App.get_running_app()
        name = self.name_input.text.strip()
        if not name:
            return
        app.playlists.setdefault(name, [])
        app.save_settings()
        self.name_input.text = ""
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()

        if not app.playlists:
            self.box.add_widget(Label(
                text="Még nincs saját playlisted.",
                color=TEXT_2,
                size_hint_y=None,
                height=dp(100)
            ))
            return

        for name in sorted(app.playlists, key=str.casefold):
            tracks = app.playlists.get(name, [])
            b = Button(
                text=f"{name}\\n{len(tracks)} dal",
                size_hint_y=None,
                height=dp(66),
                background_normal="",
                background_color=CARD,
                color=TEXT,
                bold=True,
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(58), None)
            )
            b.bind(
                on_release=lambda _, n=name:
                    app.open_playlist(n)
            )
            self.box.add_widget(b)


class PlaylistTracksScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("PLAYLIST")
        self.playlist_name = ""

        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))

        add_current = Button(
            text="AKTUÁLIS DAL +",
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True
        )
        add_current.bind(on_release=lambda *_: self.add_current())

        delete = Button(
            text="PLAYLIST TÖRLÉSE",
            background_normal="",
            background_color=(.20, .07, .10, .95),
            color=TEXT,
            bold=True
        )
        delete.bind(on_release=lambda *_: self.delete_playlist())

        actions.add_widget(add_current)
        actions.add_widget(delete)
        root.add_widget(actions)

        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(7)
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def set_playlist(self, name):
        self.playlist_name = name
        self.title_label.text = f"[b]{name}[/b]"
        self.refresh()

    def add_current(self):
        app = App.get_running_app()
        if not app.current_path or not self.playlist_name:
            return
        items = app.playlists.setdefault(self.playlist_name, [])
        key = app.favorite_key(app.current_path)
        if key not in items:
            items.append(key)
        app.save_settings()
        self.refresh()

    def delete_playlist(self):
        app = App.get_running_app()
        if self.playlist_name in app.playlists:
            del app.playlists[self.playlist_name]
        app.save_settings()
        app.manager.current = "playlists"

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()

        paths = [
            p for p in app.playlists.get(self.playlist_name, [])
            if os.path.exists(p)
        ]

        if not paths:
            self.box.add_widget(Label(
                text="A playlist még üres.\\nIndíts el egy dalt, majd nyomd meg az 'AKTUÁLIS DAL +' gombot.",
                color=TEXT_2,
                size_hint_y=None,
                height=dp(120),
                halign="center"
            ))
            return

        for path in paths:
            row = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(5))
            play = Button(
                text=clean_title(path),
                background_normal="",
                background_color=CARD,
                color=TEXT,
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(130), None)
            )
            play.bind(on_release=lambda _, p=path: app.play_path(p))

            remove = Button(
                text="X",
                size_hint_x=None,
                width=dp(48),
                background_normal="",
                background_color=(.20, .07, .10, .95),
                color=TEXT,
                bold=True
            )
            remove.bind(
                on_release=lambda _, p=path:
                    self.remove_track(p)
            )

            row.add_widget(play)
            row.add_widget(remove)
            self.box.add_widget(row)

    def remove_track(self, path):
        app = App.get_running_app()
        items = app.playlists.get(self.playlist_name, [])
        key = app.favorite_key(path)
        app.playlists[self.playlist_name] = [
            p for p in items
            if p != key
        ]
        app.save_settings()
        self.refresh()




class NowPlayingScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("MOST SZÓL")

        self.cover = Image(
            source="icon.png",
            size_hint_y=None,
            height=dp(300),
            allow_stretch=True,
            keep_ratio=True
        )
        root.add_widget(self.cover)

        self.title = Label(
            text="Nincs lejátszás",
            color=TEXT,
            bold=True,
            font_size="23sp",
            size_hint_y=None,
            height=dp(72),
            halign="center",
            valign="middle"
        )
        self.title.bind(size=lambda i,v:setattr(i,"text_size",(i.width, i.height)))
        root.add_widget(self.title)

        self.meta = Label(
            text="",
            color=TEXT_2,
            size_hint_y=None,
            height=dp(58),
            halign="center",
            valign="middle"
        )
        self.meta.bind(size=lambda i,v:setattr(i,"text_size",(i.width, i.height)))
        root.add_widget(self.meta)

        self.progress = Label(
            text="0:00 / 0:00",
            color=ACCENT_2,
            bold=True,
            size_hint_y=None,
            height=dp(34)
        )
        root.add_widget(self.progress)

        actions = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        for text, callback in (
            ("PREV", lambda: App.get_running_app().previous()),
            ("PLAY/PAUSE", lambda: App.get_running_app().toggle_play()),
            ("NEXT", lambda: App.get_running_app().next_pressed()),
        ):
            b = Button(
                text=text,
                background_normal="",
                background_color=ACCENT if text == "PLAY/PAUSE" else PANEL_2,
                color=(0,.07,.12,1) if text == "PLAY/PAUSE" else TEXT,
                bold=True,
                font_size="10sp"
            )
            b.bind(on_release=lambda _, cb=callback: cb())
            actions.add_widget(b)
        root.add_widget(actions)

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        fav = Button(text="KEDVENC", background_normal="", background_color=PANEL_2, color=ACCENT_2, bold=True)
        lyrics = Button(text="DALSZÖVEG", background_normal="", background_color=PANEL_2, color=ACCENT_2, bold=True)
        fav.bind(on_release=lambda *_: self.toggle_favorite())
        lyrics.bind(on_release=lambda *_: App.get_running_app().open_lyrics())
        row.add_widget(fav); row.add_widget(lyrics); root.add_widget(row)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        if not app.current_path:
            self.cover.source = "icon.png"
            self.title.text = "Nincs lejátszás"
            self.meta.text = ""
            self.progress.text = "0:00 / 0:00"
            return
        info = track_metadata(app.current_path)
        cover = cover_for_track(app.current_path)
        self.cover.source = cover or "icon.png"
        try:self.cover.reload()
        except Exception:pass
        self.title.text = info["title"]
        self.meta.text = f'{info["artist"]}\n{info["album"]}'
        self.progress.text = f'{fmt_time(app.audio.position())} / {fmt_time(app.audio.duration())}'

    def toggle_favorite(self):
        app = App.get_running_app()
        if app.current_path:
            app.toggle_favorite(app.current_path)


class HistoryScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("NEMRÉG HALLGATOTT")
        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(7))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box); root.add_widget(self.scroll)

    def on_pre_enter(self,*_): self.refresh()

    def refresh(self):
        app=App.get_running_app(); self.box.clear_widgets()
        paths=[p for p in app.history if p in app.songs]
        if not paths:
            self.box.add_widget(Label(text="Még nincs hallgatási előzmény.", color=TEXT_2, size_hint_y=None, height=dp(110)))
            return
        for p in paths[:100]:
            self.box.add_widget(make_song_row(p, self.refresh))


class StatsScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root=self.make("STATISZTIKÁK")
        self.summary=Label(text="", color=TEXT, font_size="18sp", halign="center", valign="middle")
        self.summary.bind(size=lambda i,v:setattr(i,"text_size",(i.width-dp(20), None)))
        root.add_widget(self.summary)
        self.top=Label(text="", color=TEXT_2, font_size="14sp", halign="left", valign="top")
        self.top.bind(size=lambda i,v:setattr(i,"text_size",(i.width-dp(20), None)))
        root.add_widget(self.top)

    def on_pre_enter(self,*_): self.refresh()

    def refresh(self):
        app=App.get_running_app()
        plays=sum(int(v or 0) for v in app.play_counts.values())
        seconds=sum(float(v or 0) for v in app.listen_seconds.values())
        h=int(seconds//3600); m=int((seconds%3600)//60)
        self.summary.text=f"Összes lejátszás: {plays}\nHallgatási idő: {h} óra {m} perc\nKedvencek: {len(app.favorites)}"
        ranked=sorted(app.play_counts.items(), key=lambda kv: kv[1], reverse=True)
        lines=["LEGTÖBBET HALLGATOTT"]
        for idx,(path,count) in enumerate(ranked[:8],1):
            lines.append(f"{idx}. {clean_title(path)} — {count}x")
        if len(lines)==1: lines.append("Még nincs elég adat.")
        self.top.text="\n".join(lines)


class SmartScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root=self.make("SMART LISTÁK")
        tabs=BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        for text,mode in (("TOP","top"),("FRISS","new"),("RECENT","recent"),("KEDVENC","fav")):
            b=Button(text=text, background_normal="", background_color=PANEL_2, color=ACCENT_2, bold=True, font_size="10sp")
            b.bind(on_release=lambda _,m=mode:self.show_mode(m)); tabs.add_widget(b)
        root.add_widget(tabs)
        self.scroll=ScrollView(do_scroll_x=False)
        self.box=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(7));self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box);root.add_widget(self.scroll)
        self.mode="top"

    def on_pre_enter(self,*_): self.show_mode(self.mode)

    def show_mode(self,mode):
        self.mode=mode;app=App.get_running_app();self.box.clear_widgets()
        if mode=="top":
            paths=[p for p,_ in sorted(app.play_counts.items(),key=lambda kv:kv[1],reverse=True) if p in app.songs]
        elif mode=="new":
            paths=sorted(app.songs,key=lambda p: app.safe_mtime(p),reverse=True)
        elif mode=="recent":
            paths=[p for p in app.history if p in app.songs]
        else:
            paths=[p for p in app.songs if app.is_favorite(p)]
        seen=set();unique=[]
        for p in paths:
            if p in seen:continue
            seen.add(p);unique.append(p)
        if not unique:
            self.box.add_widget(Label(text="Ehhez a Smart listához még nincs adat.",color=TEXT_2,size_hint_y=None,height=dp(110)))
            return
        for p in unique[:100]:self.box.add_widget(make_song_row(p, lambda:self.show_mode(mode)))


class MixScreen(BaseFeature):
    """A PC-s Advanced Mixer mobilos, funkcióazonos változata."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ADVANCED MIXER")

        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(10),
            padding=[0, dp(4), 0, dp(18)]
        )
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        root.add_widget(scroll)

        subtitle = Label(
            text=(
                "Fade Out / Fade In külön • Auto / kézi Next külön • "
                "Gapless • DJ Mode • Mix presetek"
            ),
            color=MUTED,
            font_size="11sp",
            size_hint_y=None,
            height=dp(52),
            halign="center",
            valign="middle"
        )
        subtitle.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        body.add_widget(subtitle)

        self.status = Label(
            text="",
            color=ACCENT_2,
            font_size="14sp",
            bold=True,
            size_hint_y=None,
            height=dp(55),
            halign="center",
            valign="middle"
        )
        self.status.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        body.add_widget(self.status)

        self.mode = Label(
            text="",
            color=TEXT_2,
            font_size="11sp",
            size_hint_y=None,
            height=dp(38),
            halign="center",
            valign="middle"
        )
        self.mode.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))
        body.add_widget(self.mode)

        # --- FŐ KAPCSOLÓK ---
        toggles = GlassPanel(
            orientation="vertical",
            size_hint_y=None,
            height=dp(160),
            padding=dp(8),
            spacing=dp(7)
        )
        row1 = BoxLayout(spacing=dp(6))
        row2 = BoxLayout(spacing=dp(6))
        toggles.add_widget(row1)
        toggles.add_widget(row2)
        body.add_widget(toggles)

        self.crossfade_btn = self._button("CROSSFADE BE / KI", primary=True)
        self.auto_btn = self._button("AUTO VÁLTÁS")
        self.manual_btn = self._button("KÉZI NEXT MIX")
        row1.add_widget(self.crossfade_btn)
        row1.add_widget(self.auto_btn)
        row1.add_widget(self.manual_btn)

        self.gapless_btn = self._button("GAPLESS")
        self.dj_btn = self._button("DJ MODE")
        self.nextmix_btn = self._button("NEXT MIX MOST")
        row2.add_widget(self.gapless_btn)
        row2.add_widget(self.dj_btn)
        row2.add_widget(self.nextmix_btn)

        self.crossfade_btn.bind(on_release=lambda *_: self.toggle_crossfade())
        self.auto_btn.bind(on_release=lambda *_: self.toggle_auto())
        self.manual_btn.bind(on_release=lambda *_: self.toggle_manual())
        self.gapless_btn.bind(on_release=lambda *_: self.toggle_gapless())
        self.dj_btn.bind(on_release=lambda *_: self.toggle_dj())
        self.nextmix_btn.bind(on_release=lambda *_: App.get_running_app().start_next_transition(auto=False, force=True))

        # --- FADE OUT / FADE IN KÜLÖN ---
        fade_box = GlassPanel(
            orientation="vertical",
            size_hint_y=None,
            height=dp(230),
            padding=[dp(12), dp(10)],
            spacing=dp(5)
        )
        body.add_widget(fade_box)

        self.out_value = Label(text="1.5 mp", color=ACCENT_2, bold=True, size_hint_y=None, height=dp(30))
        fade_box.add_widget(Label(text="FADE OUT", color=TEXT, bold=True, size_hint_y=None, height=dp(28)))
        fade_box.add_widget(self.out_value)
        self.out_slider = Slider(min=0, max=10, step=.25, value=1.5, size_hint_y=None, height=dp(44))
        self.out_slider.bind(value=self._fade_out_changed)
        fade_box.add_widget(self.out_slider)

        self.in_value = Label(text="1.5 mp", color=ACCENT_2, bold=True, size_hint_y=None, height=dp(30))
        fade_box.add_widget(Label(text="FADE IN", color=TEXT, bold=True, size_hint_y=None, height=dp(28)))
        fade_box.add_widget(self.in_value)
        self.in_slider = Slider(min=0, max=10, step=.25, value=1.5, size_hint_y=None, height=dp(44))
        self.in_slider.bind(value=self._fade_in_changed)
        fade_box.add_widget(self.in_slider)

        self.total_value = Label(text="3.0 mp összesen", color=MUTED, size_hint_y=None, height=dp(26))
        fade_box.add_widget(self.total_value)

        # --- PC-S PRESETEK, ugyanazokkal az értékekkel ---
        body.add_widget(Label(text="MIX PRESETEK", color=MUTED, bold=True, size_hint_y=None, height=dp(30)))
        preset_box = BoxLayout(size_hint_y=None, height=dp(98), spacing=dp(5))
        left = BoxLayout(orientation="vertical", spacing=dp(5))
        right = BoxLayout(orientation="vertical", spacing=dp(5))
        preset_box.add_widget(left)
        preset_box.add_widget(right)
        body.add_widget(preset_box)

        for parent, text, name in (
            (left, "QUICK", "quick"),
            (left, "RADIO", "radio"),
            (left, "DJ", "dj"),
            (right, "SMOOTH", "smooth"),
            (right, "CINEMATIC", "cinematic"),
            (right, "GAPLESS", "gapless"),
        ):
            btn = self._button(text)
            btn.bind(on_release=lambda _, n=name: self.apply_preset(n))
            parent.add_widget(btn)

        # --- MANUÁLIS MIX ESZKÖZÖK ---
        body.add_widget(Label(text="MANUÁLIS MIX ESZKÖZÖK", color=MUTED, bold=True, size_hint_y=None, height=dp(30)))
        tools = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(6))
        fade_now = self._button("FADE OUT MOST")
        restart = self._button("ÚJRAINDÍTÁS FADE IN-NEL")
        fade_now.bind(on_release=lambda *_: App.get_running_app().fade_out_current())
        restart.bind(on_release=lambda *_: App.get_running_app().restart_current_with_fade())
        tools.add_widget(fade_now)
        tools.add_widget(restart)
        body.add_widget(tools)

    def _button(self, text, primary=False):
        return Button(
            text=text,
            background_normal="",
            background_color=ACCENT if primary else PANEL_2,
            color=(0, .07, .12, 1) if primary else TEXT,
            bold=True,
            font_size="10sp"
        )

    def on_pre_enter(self, *_):
        app = App.get_running_app()
        self.out_slider.value = app.mix_fade_out_seconds
        self.in_slider.value = app.mix_fade_in_seconds
        self.refresh()

    def refresh(self):
        app = App.get_running_app()

        if app.mix_gapless_enabled:
            self.status.text = "GAPLESS • azonnali dalváltás"
            self.status.color = ACCENT_2
        elif app.crossfade_enabled:
            self.status.text = (
                f"MIX: BE • Fade Out {app.mix_fade_out_seconds:.1f}s • "
                f"Fade In {app.mix_fade_in_seconds:.1f}s"
            )
            self.status.color = ACCENT_2
        else:
            self.status.text = "MIX: KI"
            self.status.color = MUTED

        parts = [
            "AUTO: BE" if app.mix_auto_transition_enabled else "AUTO: KI",
            "KÉZI NEXT: BE" if app.mix_manual_transition_enabled else "KÉZI NEXT: KI",
        ]
        if app.mix_dj_mode_enabled:
            parts.append("DJ MODE")
        self.mode.text = "   •   ".join(parts)

        self.out_value.text = f"{app.mix_fade_out_seconds:.1f} mp"
        self.in_value.text = f"{app.mix_fade_in_seconds:.1f} mp"
        self.total_value.text = f"{app.mix_fade_out_seconds + app.mix_fade_in_seconds:.1f} mp összesen"

        self.auto_btn.color = ACCENT_2 if app.mix_auto_transition_enabled else TEXT_2
        self.manual_btn.color = ACCENT_2 if app.mix_manual_transition_enabled else TEXT_2
        self.gapless_btn.color = ACCENT_2 if app.mix_gapless_enabled else TEXT_2
        self.dj_btn.color = ACCENT_2 if app.mix_dj_mode_enabled else TEXT_2
        self.crossfade_btn.background_color = ACCENT if app.crossfade_enabled else PANEL_2
        self.crossfade_btn.color = (0, .07, .12, 1) if app.crossfade_enabled else TEXT

        try:
            app.library.player.set_mix_status(
                app.crossfade_enabled, app.mix_gapless_enabled,
                app.mix_fade_out_seconds, app.mix_fade_in_seconds
            )
        except Exception:
            pass

    def _fade_out_changed(self, _, value):
        app = App.get_running_app()
        app.mix_fade_out_seconds = max(0.0, min(10.0, float(value)))
        app.save_settings()
        self.refresh()

    def _fade_in_changed(self, _, value):
        app = App.get_running_app()
        app.mix_fade_in_seconds = max(0.0, min(10.0, float(value)))
        app.save_settings()
        self.refresh()

    def toggle_crossfade(self):
        app = App.get_running_app()
        app.crossfade_enabled = not app.crossfade_enabled
        if app.crossfade_enabled:
            app.mix_gapless_enabled = False
        app.save_settings()
        self.refresh()

    def toggle_auto(self):
        app = App.get_running_app()
        app.mix_auto_transition_enabled = not app.mix_auto_transition_enabled
        app.save_settings()
        self.refresh()

    def toggle_manual(self):
        app = App.get_running_app()
        app.mix_manual_transition_enabled = not app.mix_manual_transition_enabled
        app.save_settings()
        self.refresh()

    def toggle_gapless(self):
        app = App.get_running_app()
        app.mix_gapless_enabled = not app.mix_gapless_enabled
        if app.mix_gapless_enabled:
            app.crossfade_enabled = False
        app.save_settings()
        self.refresh()

    def toggle_dj(self):
        app = App.get_running_app()
        app.set_dj_mode(not app.mix_dj_mode_enabled)
        self.refresh()

    def apply_preset(self, name):
        App.get_running_app().apply_mix_preset(name)
        self.out_slider.value = App.get_running_app().mix_fade_out_seconds
        self.in_slider.value = App.get_running_app().mix_fade_in_seconds
        self.refresh()


class EQScreen(BaseFeature):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); r=self.make("5-SÁVOS EQ"); self.sliders=[]
        for idx,name in enumerate(("BASS","LOW MID","MID","HIGH MID","TREBLE")):
            row=BoxLayout(size_hint_y=None,height=dp(55),spacing=dp(6)); lab=Label(text=name,color=TEXT_2,size_hint_x=None,width=dp(82)); s=Slider(min=-12,max=12,step=1,value=0); out=Label(text="0 dB",color=ACCENT_2,size_hint_x=None,width=dp(60)); s.bind(value=lambda _,v,i=idx,o=out:self.changed(i,v,o)); row.add_widget(lab); row.add_widget(s); row.add_widget(out); r.add_widget(row); self.sliders.append(s)
        p=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(5))
        for name,vals in {"FLAT":[0,0,0,0,0],"BASS":[8,5,1,0,-1],"PARTY":[6,3,0,3,6],"VOCAL":[-2,1,5,4,1]}.items():
            b=Button(text=name,background_normal="",background_color=PANEL_2,color=TEXT,bold=True); b.bind(on_release=lambda _,x=vals:self.preset(x)); p.add_widget(b)
        r.add_widget(p)
    def on_pre_enter(self,*_):
        for s,v in zip(self.sliders,App.get_running_app().eq_values): s.value=v
    def changed(self,i,v,out):
        a=App.get_running_app(); a.eq_values[i]=float(v); out.text=f"{int(v):+d} dB"; a.audio.apply_eq(a.eq_values); a.save_settings()
    def preset(self,vals):
        for s,v in zip(self.sliders,vals): s.value=v


class RGScreen(BaseFeature):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); r=self.make("REPLAYGAIN"); r.add_widget(Label(text="Track gain metaadat alapján hangerő-kiegyenlítés.",color=TEXT_2)); self.status=Label(text="",color=ACCENT_2,font_size="25sp"); r.add_widget(self.status)
        b=Button(text="REPLAYGAIN BE / KI",size_hint_y=None,height=dp(56),background_normal="",background_color=ACCENT,color=(0,.07,.12,1),bold=True); b.bind(on_release=lambda *_:self.toggle()); r.add_widget(b)
    def on_pre_enter(self,*_): self.refresh()
    def refresh(self): self.status.text="BEKAPCSOLVA" if App.get_running_app().replaygain_enabled else "KIKAPCSOLVA"
    def toggle(self):
        a=App.get_running_app(); a.replaygain_enabled=not a.replaygain_enabled; a.apply_volume(); a.save_settings(); self.refresh()


class QueueScreen(BaseFeature):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); r=self.make("LEJÁTSZÁSI SOR"); sc=ScrollView(do_scroll_x=False); self.box=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(6)); self.box.bind(minimum_height=self.box.setter("height")); sc.add_widget(self.box); r.add_widget(sc)
    def on_pre_enter(self,*_):
        a=App.get_running_app(); self.box.clear_widgets()
        for p in a.queue_snapshot():
            b=Button(text=clean_title(p),size_hint_y=None,height=dp(52),background_normal="",background_color=CARD,color=TEXT); b.bind(on_release=lambda _,path=p:a.play_path(path)); self.box.add_widget(b)


class SleepScreen(BaseFeature):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); r=self.make("SLEEP TIMER"); self.status=Label(text="Kikapcsolva",color=ACCENT_2,font_size="24sp"); r.add_widget(self.status); row=BoxLayout(size_hint_y=None,height=dp(56),spacing=dp(5))
        for m in (15,30,45,60):
            b=Button(text=f"{m}p",background_normal="",background_color=PANEL_2,color=TEXT,bold=True); b.bind(on_release=lambda _,x=m:self.set_timer(x)); row.add_widget(b)
        r.add_widget(row); off=Button(text="KIKAPCSOLÁS",size_hint_y=None,height=dp(52),background_normal="",background_color=(.18,.08,.10,1),color=TEXT,bold=True); off.bind(on_release=lambda *_:self.set_timer(0)); r.add_widget(off)
    def on_pre_enter(self,*_): self.refresh()
    def set_timer(self,m):
        a=App.get_running_app(); a.sleep_deadline=None if m<=0 else time.time()+m*60; self.refresh()
    def refresh(self):
        d=App.get_running_app().sleep_deadline; self.status.text="Kikapcsolva" if not d else f"Kb. {max(1,int((d-time.time())/60)+1)} perc"


class JustMusicApp(App):
    def build(self):
        self.title="JustMusic! Mobile v1.6"
        Window.clearcolor=BG
        self.songs=[]; self.current_index=-1; self.current_path=None; self.lyrics=[]; self.lyric_index=-1; self.favorites=set(); self.lyrics_fetching=set(); self.lyrics_source=""
        self.custom_folders=[]
        self.playlists={}
        self.last_saved_position=0.0
        self.last_save_tick=0.0
        self.restore_path=""
        self.restore_position=0.0
        self.history=[]
        self.play_counts={}
        self.listen_seconds={}
        self._listen_stat_tick=time.time()
        self._folder_request_code=7616
        self.audio=NativeAudio(); self.backend_name="Android MediaPlayer" if self.audio.android else "Kivy fallback"
        self.shuffle_enabled=False; self.repeat_mode="off"
        # PC-s Advanced Mixer állapotok — 1/1 ugyanazok az opciók.
        self.crossfade_enabled=False
        self.mix_fade_out_seconds=1.5
        self.mix_fade_in_seconds=1.5
        self.mix_auto_transition_enabled=True
        self.mix_manual_transition_enabled=True
        self.mix_gapless_enabled=False
        self.mix_dj_mode_enabled=False
        self.mix_in_progress=False
        self.mix_target_index=None
        self.mix_started_at=None
        self.mix_target_rg_db=0.0
        self.eq_values=[0,0,0,0,0]; self.replaygain_enabled=True; self.user_volume=.92; self.current_rg_db=0.0; self.sleep_deadline=None; self.paused_position=0.0
        self.load_settings()
        self.manager=ScreenManager(); self.library=LibraryScreen(name="library"); self.lyrics_screen=LyricsScreen(name="lyrics")
        self.artists_screen=ArtistsScreen(name="artists")
        self.artist_tracks_screen=ArtistTracksScreen(name="artist_tracks")
        self.albums_screen=AlbumsScreen(name="albums")
        self.album_tracks_screen=AlbumTracksScreen(name="album_tracks")
        self.favorites_screen=FavoritesScreen(name="favorites")
        self.connect_screen=ConnectScreen(name="connect")
        self.folders_screen=FoldersScreen(name="folders")
        self.playlists_screen=PlaylistsScreen(name="playlists")
        self.playlist_tracks_screen=PlaylistTracksScreen(name="playlist_tracks")
        self.now_playing_screen=NowPlayingScreen(name="now_playing")
        self.history_screen=HistoryScreen(name="history")
        self.stats_screen=StatsScreen(name="stats")
        self.smart_screen=SmartScreen(name="smart")
        for s in (
            self.library, self.lyrics_screen,
            self.artists_screen, self.artist_tracks_screen,
            self.albums_screen, self.album_tracks_screen,
            self.favorites_screen, self.connect_screen,
            self.folders_screen, self.playlists_screen, self.playlist_tracks_screen,
            self.now_playing_screen, self.history_screen, self.stats_screen, self.smart_screen,
            MixScreen(name="mix"), EQScreen(name="eq"), RGScreen(name="rg"),
            QueueScreen(name="queue"), SleepScreen(name="sleep")
        ):
            self.manager.add_widget(s)
        self.library.player.set_shuffle(self.shuffle_enabled); self.library.player.set_repeat(self.repeat_mode)
        self.library.player.set_mix_status(self.crossfade_enabled,self.mix_gapless_enabled,self.mix_fade_out_seconds,self.mix_fade_in_seconds)
        Clock.schedule_interval(self.tick,.10); Clock.schedule_once(lambda *_:self.permissions(),.4); Clock.schedule_once(lambda *_:self.scan(),1.2)
        return self.manager

    def settings_path(self):
        # Az app saját írható tárhelye: frissítéskor megmarad.
        return Path(self.user_data_dir) / "justmusic_settings.json"

    def legacy_settings_path(self):
        return Path("/storage/emulated/0/Music") / SETTINGS_NAME

    def load_settings(self):
        try:
            p = self.settings_path()

            # v1.4 -> v1.5 automatikus settings migráció.
            if (
                not p.exists()
                and platform == "android"
                and self.legacy_settings_path().exists()
            ):
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(
                        self.legacy_settings_path().read_text(encoding="utf-8"),
                        encoding="utf-8"
                    )
                except Exception:
                    pass

            d=json.loads(p.read_text(encoding="utf-8")); self.shuffle_enabled=bool(d.get("shuffle",False)); self.repeat_mode=d.get("repeat","off")
            mix=d.get("mixer",{})
            self.crossfade_enabled=bool(mix.get("crossfade_enabled", d.get("mix", 0) not in (0, None)))
            legacy=float(d.get("mix",3.0) or 3.0)
            self.mix_fade_out_seconds=float(mix.get("fade_out", legacy/2.0))
            self.mix_fade_in_seconds=float(mix.get("fade_in", legacy/2.0))
            self.mix_auto_transition_enabled=bool(mix.get("auto",True))
            self.mix_manual_transition_enabled=bool(mix.get("manual",True))
            self.mix_gapless_enabled=bool(mix.get("gapless",False))
            self.mix_dj_mode_enabled=bool(mix.get("dj",False))
            if self.mix_gapless_enabled:self.crossfade_enabled=False
            self.eq_values=list(d.get("eq",[0,0,0,0,0]))[:5]; self.replaygain_enabled=bool(d.get("rg",True))
            self.favorites=set(str(p) for p in d.get("favorites", []))
            self.custom_folders=[
                str(p) for p in d.get("custom_folders", [])
                if str(p).strip()
            ]
            self.playlists={
                str(name): [str(p) for p in paths]
                for name, paths in (d.get("playlists", {}) or {}).items()
                if isinstance(paths, list)
            }
            self.user_volume=float(d.get("volume", self.user_volume))
            self.restore_path=str(d.get("last_path", "") or "")
            self.restore_position=float(d.get("last_position", 0.0) or 0.0)
            self.history=[str(p) for p in d.get("history", []) if str(p).strip()][:200]
            self.play_counts={str(k):int(v or 0) for k,v in (d.get("play_counts", {}) or {}).items()}
            self.listen_seconds={str(k):float(v or 0.0) for k,v in (d.get("listen_seconds", {}) or {}).items()}
            while len(self.eq_values)<5:self.eq_values.append(0)
        except Exception: pass
    def save_settings(self):
        try:
            p=self.settings_path(); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps({
                "shuffle":self.shuffle_enabled,
                "repeat":self.repeat_mode,
                "mixer":{
                    "crossfade_enabled":self.crossfade_enabled,
                    "fade_out":self.mix_fade_out_seconds,
                    "fade_in":self.mix_fade_in_seconds,
                    "auto":self.mix_auto_transition_enabled,
                    "manual":self.mix_manual_transition_enabled,
                    "gapless":self.mix_gapless_enabled,
                    "dj":self.mix_dj_mode_enabled,
                },
                "eq":self.eq_values,
                "rg":self.replaygain_enabled,
                "favorites":sorted(self.favorites),
                "custom_folders":list(self.custom_folders),
                "playlists":self.playlists,
                "volume":self.user_volume,
                "last_path":self.current_path or self.restore_path or "",
                "last_position":(
                    self.audio.position()
                    if self.current_path
                    else self.restore_position
                ),
                "history":self.history[:200],
                "play_counts":self.play_counts,
                "listen_seconds":self.listen_seconds
            },ensure_ascii=False, indent=2),encoding="utf-8")
        except Exception: pass
    def permissions(self):
        if platform!="android":return
        try:
            from android.permissions import request_permissions
            request_permissions([
                "android.permission.READ_MEDIA_AUDIO",
                "android.permission.READ_EXTERNAL_STORAGE",
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.BLUETOOTH_SCAN",
                "android.permission.POST_NOTIFICATIONS",
            ])
        except Exception as e: print("Permission:",e)
    def default_music_roots(self):
        if platform == "android":
            return [
                "/storage/emulated/0/Music",
                "/storage/emulated/0/Download",
            ]
        return [str(Path.home() / "Music")]

    def music_roots(self):
        roots = []
        for path in self.default_music_roots() + list(self.custom_folders):
            path = str(path).strip()
            if path and path not in roots:
                roots.append(path)
        return roots

    def add_music_folder(self, path):
        path = os.path.normpath(str(path).strip())
        if (
            path
            and path not in self.default_music_roots()
            and path not in self.custom_folders
        ):
            self.custom_folders.append(path)
            self.save_settings()
        self.scan()

    def remove_music_folder(self, path):
        self.custom_folders = [
            p for p in self.custom_folders
            if p != path
        ]
        self.save_settings()
        self.scan()

    def scan(self):
        roots=self.music_roots()
        found={}
        for root in roots:
            if not os.path.isdir(root):continue
            for folder,_,files in os.walk(root):
                for f in files:
                    if f.lower().endswith(SUPPORTED_AUDIO):
                        p=os.path.join(folder,f); found[os.path.realpath(p).lower()]=p
        self.songs=sorted(found.values(),key=lambda p:clean_title(p).lower())
        self.library.refresh_list()
        try:self.artists_screen.refresh()
        except Exception:pass
        try:self.albums_screen.refresh()
        except Exception:pass
        try:self.favorites_screen.refresh()
        except Exception:pass
        try:self.folders_screen.refresh()
        except Exception:pass

        # Első könyvtár-betöltés után visszaállítjuk az utolsó dalt.
        if self.restore_path:
            path = self.restore_path
            position = self.restore_position
            self.restore_path = ""
            self.restore_position = 0.0
            self.restore_last_track(path, position)
    def queue_snapshot(self):
        if not self.songs:return []
        if self.current_index<0:return list(self.songs)
        return self.songs[self.current_index:]+self.songs[:self.current_index]
    def next_index(self):
        if not self.songs:return -1
        if self.repeat_mode=="one" and self.current_index>=0:return self.current_index
        if self.shuffle_enabled and len(self.songs)>1:return random.choice([i for i in range(len(self.songs)) if i!=self.current_index])
        if self.current_index<0:return 0
        n=self.current_index+1
        if n<len(self.songs):return n
        return 0 if self.repeat_mode=="all" else -1
    def previous_index(self):
        if not self.songs:return -1
        if self.shuffle_enabled and len(self.songs)>1:return random.choice([i for i in range(len(self.songs)) if i!=self.current_index])
        if self.current_index<=0:return len(self.songs)-1 if self.repeat_mode=="all" else 0
        return self.current_index-1
    def restore_last_track(self, path, position):
        if not path or path not in self.songs:
            return

        try:
            index = self.songs.index(path)
            ok = self.audio.load(path)
            if not ok:
                return

            self.current_index=index
            self.current_path=path
            self.lyrics=parse_lrc(path)
            self.lyric_index=-1
            self.current_rg_db=replaygain_db(path)
            self.paused_position=max(0.0, float(position or 0.0))

            title=clean_title(path)
            self.library.player.title.text=f"[b]{title}[/b]"
            self.lyrics_screen.track.text=f"[b]JustMusic! • Dalszöveg[/b]\\n{title}"
            self.audio.apply_eq(self.eq_values)
            self.apply_volume()

            if self.paused_position > 0:
                self.audio.seek(self.paused_position)

            self.library.player.set_playing(False)

        except Exception as error:
            print("UTOLSÓ DAL VISSZAÁLLÍTÁSI HIBA:", error)

    def open_playlist(self, name):
        self.playlist_tracks_screen.set_playlist(name)
        self.manager.current = "playlist_tracks"

    def show_android_notification(self, title, playing=True):
        """
        Egyszerű JustMusic! now-playing értesítés.
        A teljes MediaStyle gombos notification egy későbbi verzióban jön.
        """
        if platform != "android":
            return

        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            NotificationChannel = autoclass("android.app.NotificationChannel")
            NotificationManager = autoclass("android.app.NotificationManager")
            NotificationBuilder = autoclass("android.app.Notification$Builder")
            BuildVersion = autoclass("android.os.Build$VERSION")
            BuildVersionCodes = autoclass("android.os.Build$VERSION_CODES")

            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)

            channel_id = "justmusic_playback"

            if BuildVersion.SDK_INT >= BuildVersionCodes.O:
                channel = NotificationChannel(
                    channel_id,
                    "JustMusic! lejátszás",
                    NotificationManager.IMPORTANCE_LOW
                )
                manager.createNotificationChannel(channel)
                builder = NotificationBuilder(activity, channel_id)
            else:
                builder = NotificationBuilder(activity)

            # Android beépített ikon.
            android_R_drawable = autoclass("android.R$drawable")
            builder.setSmallIcon(android_R_drawable.ic_media_play)
            builder.setContentTitle("JustMusic!")
            builder.setContentText(str(title or "Zenelejátszás"))
            builder.setOngoing(bool(playing))
            builder.setOnlyAlertOnce(True)
            try:
                Notification=autoclass("android.app.Notification")
                builder.setCategory(Notification.CATEGORY_TRANSPORT)
                builder.setVisibility(Notification.VISIBILITY_PUBLIC)
            except Exception:pass
            try:
                cover=cover_for_track(self.current_path) if self.current_path else ""
                if cover:
                    BitmapFactory=autoclass("android.graphics.BitmapFactory")
                    bmp=BitmapFactory.decodeFile(cover)
                    if bmp:builder.setLargeIcon(bmp)
            except Exception:pass

            manager.notify(420, builder.build())

        except Exception as error:
            print("NOTIFICATION HIBA:", error)

    def hide_android_notification(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            manager.cancel(420)
        except Exception:
            pass

    def safe_mtime(self, path):
        try:return os.path.getmtime(path)
        except Exception:return 0.0

    def record_play(self, path):
        if not path:return
        key=self.favorite_key(path)
        self.play_counts[key]=int(self.play_counts.get(key,0))+1
        self.history=[key]+[p for p in self.history if p!=key]
        self.history=self.history[:200]
        self._listen_stat_tick=time.time()
        try:self.history_screen.refresh()
        except Exception:pass
        try:self.stats_screen.refresh()
        except Exception:pass
        self.save_settings()

    def add_listen_time(self):
        now=time.time();delta=max(0.0,min(2.0,now-self._listen_stat_tick));self._listen_stat_tick=now
        if self.current_path and self.audio.is_playing():
            key=self.favorite_key(self.current_path)
            self.listen_seconds[key]=float(self.listen_seconds.get(key,0.0))+delta

    def pick_music_folder(self):
        """Android SAF mappaválasztó. Primary shared-storage mappát automatikusan útvonallá alakít."""
        if platform!="android":
            self.folders_screen.path_input.text=str(Path.home()/"Music")
            self.folders_screen.picker_status.text="Asztali teszt: a Music mappát választottam."
            return
        try:
            from android import activity
            from jnius import autoclass
            Intent=autoclass("android.content.Intent")
            PythonActivity=autoclass("org.kivy.android.PythonActivity")
            activity.bind(on_activity_result=self._on_folder_result)
            intent=Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)
            PythonActivity.mActivity.startActivityForResult(intent,self._folder_request_code)
            self.folders_screen.picker_status.text="Válassz ki egy zene mappát az Android fájlkezelőben..."
        except Exception as error:
            print("MAPPA PICKER HIBA:",error)
            self.folders_screen.picker_status.text="A mappaválasztó nem indult el. A kézi útvonal továbbra is használható."

    def _on_folder_result(self, request_code, result_code, intent):
        if request_code!=self._folder_request_code:return
        try:
            from android import activity
            activity.unbind(on_activity_result=self._on_folder_result)
        except Exception:pass
        if intent is None:return
        try:
            from jnius import autoclass
            PythonActivity=autoclass("org.kivy.android.PythonActivity")
            DocumentsContract=autoclass("android.provider.DocumentsContract")
            uri=intent.getData()
            flags=intent.getFlags()
            resolver=PythonActivity.mActivity.getContentResolver()
            try:resolver.takePersistableUriPermission(uri, flags & 3)
            except Exception:pass
            doc_id=str(DocumentsContract.getTreeDocumentId(uri))
            path=""
            if doc_id.lower().startswith("primary:"):
                rel=doc_id.split(":",1)[1].strip("/")
                path="/storage/emulated/0" + (("/"+rel) if rel else "")
            if path:
                self.add_music_folder(path)
                self.folders_screen.picker_status.text=f"Kiválasztva: {path}"
                self.folders_screen.path_input.text=path
                self.folders_screen.refresh()
            else:
                self.folders_screen.picker_status.text="A mappa kiválasztva, de ezt a tárhelyet még nem tudom közvetlen fájlútvonallá alakítani."
        except Exception as error:
            print("MAPPA RESULT HIBA:",error)
            try:self.folders_screen.picker_status.text="Nem sikerült feldolgozni a kiválasztott mappát."
            except Exception:pass

    def audio_output_devices(self):
        if platform!="android":return [("Teszt audio kimenet","DESKTOP")]
        try:
            from jnius import autoclass
            PythonActivity=autoclass("org.kivy.android.PythonActivity")
            Context=autoclass("android.content.Context")
            AudioManager=autoclass("android.media.AudioManager")
            manager=PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE)
            devices=manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            result=[]
            for d in devices:
                try:name=str(d.getProductName() or "Audio eszköz")
                except Exception:name="Audio eszköz"
                try:dtype=str(d.getType())
                except Exception:dtype="?"
                item=(name,dtype)
                if item not in result:result.append(item)
            return result
        except Exception as error:
            print("AUDIO OUTPUT LISTA HIBA:",error);return []

    def auto_fetch_lyrics(self, audio_path):
        """Ha nincs LRC, háttérben automatikusan keres és elmenti."""
        if not audio_path:
            return

        # Ha közben már lett helyi/cache LRC, nincs teendő.
        existing = parse_lrc(audio_path)
        if existing:
            if self.current_path == audio_path:
                self.lyrics = existing
            return

        key = str(audio_path)
        if key in self.lyrics_fetching:
            return

        self.lyrics_fetching.add(key)
        self.lyrics_source = "Keresés…"

        try:
            if self.current_path == audio_path:
                self.lyrics_screen.set_search_status(
                    "Automatikus LRC keresés… • LRCLIB",
                    ACCENT_2
                )
                self.lyrics_screen.rebuild_lyrics()
        except Exception:
            pass

        duration = self.audio.duration() if self.current_path == audio_path else 0.0
        meta = track_metadata(audio_path)

        def worker():
            result = None
            error_text = None
            try:
                result = _find_online_lyrics(audio_path, duration)
            except Exception as error:
                error_text = str(error)
                print("AUTO LRC HIBA:", error)

            saved = None
            source = ""
            mode = ""

            try:
                if result:
                    source = str(result.get("source") or "Online")
                    kind = result.get("kind")
                    text = str(result.get("text") or "").strip()

                    if kind == "synced" and text:
                        saved = _save_auto_lrc(audio_path, text)
                        mode = "PONTOS SZINKRON"

                    elif kind == "plain" and text:
                        estimated = _plain_to_estimated_lrc(
                            text,
                            duration,
                            meta
                        )
                        if estimated:
                            saved = _save_auto_lrc(audio_path, estimated)
                            mode = "AUTO BECSÜLT SZINKRON"
            except Exception as error:
                error_text = str(error)
                print("AUTO LRC MENTÉSI HIBA:", error)

            def finish(_dt):
                self.lyrics_fetching.discard(key)

                if saved:
                    print("AUTO LRC ELMENTVE:", saved)

                if self.current_path != audio_path:
                    return

                if saved:
                    self.lyrics = parse_lrc(audio_path)
                    self.lyric_index = -1
                    self.lyrics_source = source
                    try:
                        self.lyrics_screen.set_search_status(
                            f"{mode} • {source}",
                            (0.45, 1.0, 0.72, 1.0)
                        )
                        self.lyrics_screen.rebuild_lyrics()
                        self.refresh_lyrics(True)
                    except Exception:
                        pass
                else:
                    self.lyrics_source = ""
                    try:
                        self.lyrics_screen.set_search_status(
                            "Nem találtam automatikusan dalszöveget.",
                            (1.0, 0.62, 0.62, 1.0)
                        )
                        self.lyrics_screen.rebuild_lyrics()
                    except Exception:
                        pass

            Clock.schedule_once(finish, 0)

        threading.Thread(target=worker, daemon=True).start()

    def play_path(self,p):
        try:self.play_index(self.songs.index(p));self.show_library()
        except ValueError:pass
    def play_index(self,i):
        if not(0<=i<len(self.songs)):return
        p=self.songs[i]; self.mix_in_progress=False;self.mix_target_index=None;self.mix_started_at=None
        try:ok=self.audio.load(p)
        except Exception as e:self.library.status.text=f"Lejátszási hiba: {e}";return
        if not ok:self.library.status.text="Ezt a fájlt nem sikerült megnyitni.";return
        self.current_index=i;self.current_path=p;self.lyrics=parse_lrc(p);self.lyric_index=-1;self.lyrics_source="Helyi/cache LRC" if self.lyrics else "";self.current_rg_db=replaygain_db(p)
        self.record_play(p)
        title=clean_title(p);self.library.player.title.text=f"[b]{title}[/b]";self.lyrics_screen.track.text=f"[b]JustMusic! • Dalszöveg[/b]\n{title}"
        try:self.lyrics_screen.rebuild_lyrics()
        except Exception:pass
        try:self.connect_screen.now.text=title
        except Exception:pass
        self.audio.start();self.audio.apply_eq(self.eq_values);self.apply_volume();self.library.player.set_playing(True);self.refresh_lyrics(True)
        self.show_android_notification(title, True)
        try:self.now_playing_screen.refresh()
        except Exception:pass
        self.save_settings()
        if not self.lyrics:
            self.auto_fetch_lyrics(p)
        else:
            try:self.lyrics_screen.set_search_status("LRC betöltve • helyi/cache", (0.45,1.0,0.72,1.0))
            except Exception:pass
    def apply_volume(self):
        gain=self.current_rg_db if self.replaygain_enabled else 0; self.audio.volume(max(0,min(1,self.user_volume*(10**(gain/20)))))
    def toggle_play(self):
        if self.current_path is None:
            if self.songs:self.play_index(0)
            return
        if self.audio.is_playing():
            self.paused_position=self.audio.position()
            self.audio.pause()
            self.library.player.set_playing(False)
            self.show_android_notification(
                clean_title(self.current_path),
                False
            )
            self.save_settings()
        else:
            self.audio.start()
            self.audio.seek(self.paused_position)
            self.apply_volume()
            self.library.player.set_playing(True)
            self.show_android_notification(
                clean_title(self.current_path),
                True
            )
    def previous(self):
        i=self.previous_index();
        if i>=0:self.play_index(i)
    def next(self):
        i=self.next_index();
        if i>=0:self.play_index(i)
        else:self.audio.pause();self.library.player.set_playing(False)
    def toggle_shuffle(self):self.shuffle_enabled=not self.shuffle_enabled;self.library.player.set_shuffle(self.shuffle_enabled);self.save_settings()
    def cycle_repeat(self):
        seq=["off","all","one"];self.repeat_mode=seq[(seq.index(self.repeat_mode)+1)%3];self.library.player.set_repeat(self.repeat_mode);self.save_settings()
    def seek_to(self,s):self.audio.seek(s)
    def show_library(self):self.manager.current="library"
    def open_lyrics(self):
        try:self.lyrics_screen.rebuild_lyrics()
        except Exception:pass
        self.refresh_lyrics(True);self.manager.current="lyrics"
    def open_screen(self,n):self.manager.current=n

    def favorite_key(self, path):
        try:return os.path.realpath(str(path))
        except Exception:return str(path)

    def is_favorite(self, path):
        return self.favorite_key(path) in self.favorites

    def toggle_favorite(self, path):
        key=self.favorite_key(path)
        if key in self.favorites:self.favorites.remove(key)
        else:self.favorites.add(key)
        self.save_settings()

    def open_artist(self, artist):
        self.artist_tracks_screen.set_artist(artist)
        self.manager.current="artist_tracks"

    def open_album(self, album, artist):
        self.album_tracks_screen.set_album(album, artist)
        self.manager.current="album_tracks"

    def bluetooth_devices(self):
        if platform != "android":
            return [("Androidon jelennek meg a párosított eszközök", "TESZT MÓD")]
        try:
            from jnius import autoclass
            BluetoothAdapter=autoclass("android.bluetooth.BluetoothAdapter")
            adapter=BluetoothAdapter.getDefaultAdapter()
            if adapter is None:return []
            bonded=adapter.getBondedDevices()
            iterator=bonded.iterator()
            devices=[]
            while iterator.hasNext():
                device=iterator.next()
                try:name=str(device.getName() or "Bluetooth eszköz")
                except Exception:name="Bluetooth eszköz"
                try:address=str(device.getAddress() or "")
                except Exception:address=""
                devices.append((name,address))
            devices.sort(key=lambda x:x[0].casefold())
            return devices
        except Exception as e:
            print("Bluetooth lista hiba:",e)
            return []

    def open_bluetooth_settings(self):
        if platform != "android":return
        try:
            from jnius import autoclass
            Intent=autoclass("android.content.Intent")
            Settings=autoclass("android.provider.Settings")
            PythonActivity=autoclass("org.kivy.android.PythonActivity")
            intent=Intent(Settings.ACTION_BLUETOOTH_SETTINGS)
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            print("Bluetooth settings hiba:",e)
    def _base_volume_for_gain(self, gain_db):
        gain = gain_db if self.replaygain_enabled else 0.0
        return max(0.0, min(1.0, self.user_volume * (10 ** (gain / 20.0))))

    def _refresh_mix_screen(self):
        try:
            screen = self.manager.get_screen("mix")
            screen.refresh()
        except Exception:
            pass

    def set_dj_mode(self, enabled):
        self.mix_dj_mode_enabled = bool(enabled)
        if self.mix_dj_mode_enabled:
            self.repeat_mode = "all"
            self.shuffle_enabled = True
            self.crossfade_enabled = True
            self.mix_gapless_enabled = False
            self.mix_fade_out_seconds = 2.0
            self.mix_fade_in_seconds = 2.5
            self.library.player.set_shuffle(True)
            self.library.player.set_repeat("all")
        self.save_settings()
        self._refresh_mix_screen()

    def apply_mix_preset(self, name):
        preset = str(name).lower()
        self.mix_dj_mode_enabled = False

        if preset == "quick":
            self.mix_gapless_enabled=False; self.crossfade_enabled=True
            self.mix_auto_transition_enabled=True; self.mix_manual_transition_enabled=True
            self.mix_fade_out_seconds=.5; self.mix_fade_in_seconds=.8
        elif preset == "smooth":
            self.mix_gapless_enabled=False; self.crossfade_enabled=True
            self.mix_auto_transition_enabled=True; self.mix_manual_transition_enabled=True
            self.mix_fade_out_seconds=2.0; self.mix_fade_in_seconds=2.5
        elif preset == "radio":
            self.mix_gapless_enabled=False; self.crossfade_enabled=True
            self.mix_auto_transition_enabled=True; self.mix_manual_transition_enabled=True
            self.mix_fade_out_seconds=1.0; self.mix_fade_in_seconds=1.2
        elif preset == "cinematic":
            self.mix_gapless_enabled=False; self.crossfade_enabled=True
            self.mix_auto_transition_enabled=True; self.mix_manual_transition_enabled=True
            self.mix_fade_out_seconds=4.0; self.mix_fade_in_seconds=4.0
        elif preset == "gapless":
            self.mix_gapless_enabled=True; self.crossfade_enabled=False
            self.mix_auto_transition_enabled=False; self.mix_manual_transition_enabled=False
            self.mix_fade_out_seconds=0.0; self.mix_fade_in_seconds=0.0
        elif preset == "dj":
            self.mix_gapless_enabled=False; self.crossfade_enabled=True
            self.mix_auto_transition_enabled=True; self.mix_manual_transition_enabled=True
            self.mix_dj_mode_enabled=True
            self.mix_fade_out_seconds=2.0; self.mix_fade_in_seconds=2.5
            self.repeat_mode="all"; self.shuffle_enabled=True
            self.library.player.set_repeat("all"); self.library.player.set_shuffle(True)

        self.save_settings()
        self._refresh_mix_screen()

    def next_pressed(self):
        if self.mix_manual_transition_enabled and (self.crossfade_enabled or self.mix_gapless_enabled):
            self.start_next_transition(auto=False, force=True)
        else:
            self.next()

    def start_next_transition(self, auto=False, force=False):
        if self.mix_in_progress or not self.songs:
            return

        if auto and not self.mix_auto_transition_enabled and not force:
            self.next()
            return

        if (not auto) and not self.mix_manual_transition_enabled and not force:
            self.next()
            return

        target = self.next_index()
        if target < 0:
            return

        # GAPLESS = PC-hez hasonlóan fade nélküli azonnali váltás.
        if self.mix_gapless_enabled:
            self.play_index(target)
            return

        if not self.crossfade_enabled or not self.audio.android:
            self.next()
            return

        try:
            if not self.audio.prepare_next(self.songs[target]):
                self.next()
                return

            self.mix_target_index = target
            self.mix_target_rg_db = replaygain_db(self.songs[target])
            self.mix_started_at = time.time()
            self.mix_in_progress = True

            current_base = self._base_volume_for_gain(self.current_rg_db)
            self.audio.volume(current_base, 0.0)
            self.audio.start_next()

        except Exception as error:
            print("MIX TRANSITION HIBA:", error)
            self.mix_in_progress=False
            self.mix_target_index=None
            self.mix_started_at=None
            self.next()

    def update_crossfade(self):
        if not self.mix_in_progress or self.mix_started_at is None:
            return

        elapsed = max(0.0, time.time() - self.mix_started_at)
        out_s = max(0.0, float(self.mix_fade_out_seconds))
        in_s = max(0.0, float(self.mix_fade_in_seconds))

        out_ratio = 1.0 if out_s <= 0 else min(1.0, elapsed / out_s)
        in_ratio = 1.0 if in_s <= 0 else min(1.0, elapsed / in_s)

        current_base = self._base_volume_for_gain(self.current_rg_db)
        next_base = self._base_volume_for_gain(self.mix_target_rg_db)

        self.audio.volume(
            current_base * (1.0 - out_ratio),
            next_base * in_ratio
        )

        if elapsed >= max(out_s, in_s, 0.05):
            if self.audio.swap_to_next():
                self.current_index=self.mix_target_index
                self.current_path=self.songs[self.current_index]
                self.record_play(self.current_path)
                self.lyrics=parse_lrc(self.current_path)
                self.lyric_index=-1
                self.current_rg_db=self.mix_target_rg_db
                self.audio.apply_eq(self.eq_values)
                self.apply_volume()
                title=clean_title(self.current_path)
                self.library.player.title.text=f"[b]{title}[/b]"
                self.lyrics_screen.track.text=f"[b]JustMusic! • Dalszöveg[/b]\n{title}"
                try:self.lyrics_screen.rebuild_lyrics()
                except Exception:pass
                if not self.lyrics:
                    self.auto_fetch_lyrics(self.current_path)
                else:
                    try:self.lyrics_screen.set_search_status("LRC betöltve • helyi/cache", (0.45,1.0,0.72,1.0))
                    except Exception:pass
                try:self.connect_screen.now.text=title
                except Exception:pass

            self.mix_in_progress=False
            self.mix_target_index=None
            self.mix_started_at=None

    def fade_out_current(self):
        if self.current_path is None:
            return
        duration = self.mix_fade_out_seconds if self.mix_fade_out_seconds > 0 else 1.0
        start = time.time()
        base = self._base_volume_for_gain(self.current_rg_db)

        def step(_dt):
            ratio = min(1.0, (time.time() - start) / max(.05, duration))
            self.audio.volume(base * (1.0 - ratio))
            if ratio >= 1.0:
                return False
            return True
        Clock.schedule_interval(step, .05)

    def restart_current_with_fade(self):
        if self.current_path is None:
            return
        duration = self.mix_fade_in_seconds if self.mix_fade_in_seconds > 0 else 1.0
        self.audio.seek(0)
        self.audio.start()
        self.audio.volume(0.0)
        start = time.time()
        base = self._base_volume_for_gain(self.current_rg_db)

        def step(_dt):
            ratio = min(1.0, (time.time() - start) / max(.05, duration))
            self.audio.volume(base * ratio)
            if ratio >= 1.0:
                return False
            return True
        Clock.schedule_interval(step, .05)

    def tick(self,_):
        now = time.time()
        self.add_listen_time()

        # Automatikus állapotmentés kb. 5 másodpercenként.
        if now - self.last_save_tick >= 5.0:
            self.last_save_tick = now
            self.save_settings()

        if self.sleep_deadline and time.time()>=self.sleep_deadline:self.sleep_deadline=None;self.audio.pause();self.library.player.set_playing(False)
        if self.current_path is None:return
        pos=self.audio.position();length=self.audio.duration();p=self.library.player;p.elapsed.text=fmt_time(pos);p.total.text=fmt_time(length)
        if not p.slider.dragging:p.slider.max=max(1,length);p.slider.value=min(pos,max(1,length))
        self.lyrics_screen.time.text=f"{fmt_time(pos)} / {fmt_time(length)}";self.refresh_lyrics()
        try:
            if self.manager.current=="now_playing":
                self.now_playing_screen.progress.text=f"{fmt_time(pos)} / {fmt_time(length)}"
        except Exception:pass
        if self.audio.is_playing() and length>0:
            rem=max(0,length-pos)
            trigger=max(self.mix_fade_out_seconds,self.mix_fade_in_seconds)
            if (
                self.audio.android
                and self.crossfade_enabled
                and self.mix_auto_transition_enabled
                and trigger>0
                and rem<=trigger
                and not self.mix_in_progress
            ):
                self.start_next_transition(auto=True)
            if self.mix_in_progress:
                self.update_crossfade()
            elif rem<=.20:
                if self.mix_gapless_enabled and self.mix_auto_transition_enabled:
                    self.start_next_transition(auto=True)
                else:
                    self.next()
    def refresh_lyrics(self,force=False):
        if not self.lyrics:
            return
        pos=self.audio.position();idx=-1
        for i,(ts,_) in enumerate(self.lyrics):
            if pos>=ts:idx=i
            else:break
        if not force and idx==self.lyric_index:return
        self.lyric_index=idx
        try:self.lyrics_screen.set_active(idx, force=force)
        except Exception:pass
    def on_pause(self):
        # Androidon az app háttérbe küldésekor ne állítsuk le a MediaPlayert.
        self.save_settings()
        if self.current_path:
            self.show_android_notification(
                clean_title(self.current_path),
                self.audio.is_playing()
            )
        return True

    def on_resume(self):
        # Visszatéréskor automatikus könyvtár-frissítés.
        Clock.schedule_once(lambda *_: self.scan(), 0.4)

    def on_stop(self):
        self.save_settings()
        self.hide_android_notification()
        self.audio.close()


if __name__ == "__main__":
    JustMusicApp().run()
