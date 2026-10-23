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
import shutil
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.instructions import InstructionGroup
from math import sin, cos, pi
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
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

APP_VERSION = "1.8.6"
APP_UI_REVISION = "REV7"  # thinner icons, one-line sidebar labels, compact settings header, media control icons
GITHUB_REPO = "szabozotya717-dot/JustMusic-Mobile-APK"
GITHUB_LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

MEDIA_ACTION_PREVIOUS = "hu.zs420ller.justmusic.action.PREVIOUS"
MEDIA_ACTION_TOGGLE = "hu.zs420ller.justmusic.action.TOGGLE"
MEDIA_ACTION_NEXT = "hu.zs420ller.justmusic.action.NEXT"

SUPPORTED_LANGUAGES = {
    "hu": "Magyar",
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
}

SUPPORTED_REGIONS = {
    "HU": "Magyarország",
    "GB": "United Kingdom",
    "DE": "Deutschland",
    "ES": "España",
    "FR": "France",
    "IT": "Italia",
}

UI_TEXT = {
    "hu": {
        "settings": "BEÁLLÍTÁSOK",
        "language_region": "NYELV ÉS RÉGIÓ",
        "language": "Nyelv",
        "region": "Régió",
        "updates": "FRISSÍTÉSEK",
        "check_updates": "FRISSÍTÉSEK KERESÉSE",
        "checking": "Frissítés keresése…",
        "up_to_date": "A JustMusic! naprakész.",
        "update_available": "Új verzió érhető el",
        "download": "LETÖLTÉS",
        "welcome": "Üdv a JustMusic!-ban!",
        "welcome_sub": "Válaszd ki a nyelvet és a régiót.",
        "continue": "FOLYTATÁS",
        "queue": "LEJÁTSZÁSI SOR",
        "queue_empty": "A kézi lejátszási sor üres.",
        "clear_queue": "SOR TÖRLÉSE",
        "about": "NÉVJEGY",
    },
    "en": {
        "settings": "SETTINGS",
        "language_region": "LANGUAGE & REGION",
        "language": "Language",
        "region": "Region",
        "updates": "UPDATES",
        "check_updates": "CHECK FOR UPDATES",
        "checking": "Checking for updates…",
        "up_to_date": "JustMusic! is up to date.",
        "update_available": "New version available",
        "download": "DOWNLOAD",
        "welcome": "Welcome to JustMusic!",
        "welcome_sub": "Choose your language and region.",
        "continue": "CONTINUE",
        "queue": "PLAY QUEUE",
        "queue_empty": "The manual play queue is empty.",
        "clear_queue": "CLEAR QUEUE",
        "about": "ABOUT",
    },
    "de": {
        "settings": "EINSTELLUNGEN",
        "language_region": "SPRACHE & REGION",
        "language": "Sprache",
        "region": "Region",
        "updates": "UPDATES",
        "check_updates": "NACH UPDATES SUCHEN",
        "checking": "Suche nach Updates…",
        "up_to_date": "JustMusic! ist aktuell.",
        "update_available": "Neue Version verfügbar",
        "download": "DOWNLOAD",
        "welcome": "Willkommen bei JustMusic!",
        "welcome_sub": "Wähle Sprache und Region.",
        "continue": "WEITER",
        "queue": "WARTESCHLANGE",
        "queue_empty": "Die manuelle Warteschlange ist leer.",
        "clear_queue": "WARTESCHLANGE LEEREN",
        "about": "INFO",
    },
    "es": {
        "settings": "AJUSTES",
        "language_region": "IDIOMA Y REGIÓN",
        "language": "Idioma",
        "region": "Región",
        "updates": "ACTUALIZACIONES",
        "check_updates": "BUSCAR ACTUALIZACIONES",
        "checking": "Buscando actualizaciones…",
        "up_to_date": "JustMusic! está actualizado.",
        "update_available": "Nueva versión disponible",
        "download": "DESCARGAR",
        "welcome": "¡Bienvenido a JustMusic!",
        "welcome_sub": "Elige idioma y región.",
        "continue": "CONTINUAR",
        "queue": "COLA",
        "queue_empty": "La cola manual está vacía.",
        "clear_queue": "VACIAR COLA",
        "about": "ACERCA DE",
    },
    "fr": {
        "settings": "PARAMÈTRES",
        "language_region": "LANGUE ET RÉGION",
        "language": "Langue",
        "region": "Région",
        "updates": "MISES À JOUR",
        "check_updates": "RECHERCHER LES MISES À JOUR",
        "checking": "Recherche de mise à jour…",
        "up_to_date": "JustMusic! est à jour.",
        "update_available": "Nouvelle version disponible",
        "download": "TÉLÉCHARGER",
        "welcome": "Bienvenue dans JustMusic !",
        "welcome_sub": "Choisissez la langue et la région.",
        "continue": "CONTINUER",
        "queue": "FILE D'ATTENTE",
        "queue_empty": "La file manuelle est vide.",
        "clear_queue": "VIDER LA FILE",
        "about": "À PROPOS",
    },
    "it": {
        "settings": "IMPOSTAZIONI",
        "language_region": "LINGUA E REGIONE",
        "language": "Lingua",
        "region": "Regione",
        "updates": "AGGIORNAMENTI",
        "check_updates": "CERCA AGGIORNAMENTI",
        "checking": "Ricerca aggiornamenti…",
        "up_to_date": "JustMusic! è aggiornato.",
        "update_available": "Nuova versione disponibile",
        "download": "SCARICA",
        "welcome": "Benvenuto in JustMusic!",
        "welcome_sub": "Scegli lingua e regione.",
        "continue": "CONTINUA",
        "queue": "CODA",
        "queue_empty": "La coda manuale è vuota.",
        "clear_queue": "SVUOTA CODA",
        "about": "INFO",
    },
}


def ui_text(app, key):
    """Safe translation lookup. Never requires App.get_running_app() at import time."""
    lang = getattr(app, "language", "hu") if app is not None else "hu"
    table = UI_TEXT.get(lang, UI_TEXT["hu"])
    return table.get(key, UI_TEXT["hu"].get(key, key))


def version_tuple(value):
    numbers = re.findall(r"\d+", str(value or ""))
    return tuple(int(x) for x in numbers[:3]) if numbers else (0, 0, 0)


def detect_system_locale_safe():
    """
    Locale detection is intentionally called only AFTER the Kivy UI exists.
    If Android/JNI is not ready, Hungarian/Hungary is used without failing startup.
    """
    language, region = "hu", "HU"
    if platform == "android":
        try:
            from jnius import autoclass
            Locale = autoclass("java.util.Locale")
            current = Locale.getDefault()
            language = str(current.getLanguage() or language).lower()
            region = str(current.getCountry() or region).upper()
        except BaseException as error:
            print("LOCALE DETECTION SKIP:", error)
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    if region not in SUPPORTED_REGIONS:
        region = "HU" if language == "hu" else "GB"
    return language, region



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


_TRACK_META_CACHE = {}
_TRACK_META_CACHE_LIMIT = 2500

def track_metadata(path):
    """artist / title / album mobil könyvtárnézetekhez, gyorsítótárral."""
    path = str(path or "")
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0.0

    cached = _TRACK_META_CACHE.get(path)
    if cached and cached[0] == mtime:
        return dict(cached[1])

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

    info = {"artist": artist, "title": title or "Ismeretlen szám", "album": album}
    if len(_TRACK_META_CACHE) >= _TRACK_META_CACHE_LIMIT:
        _TRACK_META_CACHE.clear()
    _TRACK_META_CACHE[path] = (mtime, dict(info))
    return info



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


# JustMusic! 1.8.5: canvas-based icons. No extra fonts or image files are needed.
# Kivy draws the icons as lines, so Android font glyph availability does not matter.
def draw_justmusic_icon(group, name, x, y, size, tint):
    scale = size / 24.0
    stroke = max(dp(1.0), scale * 1.25)

    def path(points, closed=False):
        coords = []
        for xx, yy in points:
            coords.extend((x + xx * scale, y + yy * scale))
        group.add(Line(points=coords, close=closed, width=stroke))

    def ring(cx, cy, radius):
        group.add(Line(circle=(x + cx * scale, y + cy * scale,
                               radius * scale), width=stroke))

    group.add(Color(*tint))
    if name == "back":
        path([(20, 12), (4, 12), (11, 19)])
        path([(4, 12), (11, 5)])
    elif name == "gear":
        ring(12, 12, 7)
        ring(12, 12, 2.7)
        for degree in range(0, 360, 45):
            a = degree * pi / 180.0
            path([(12 + 8 * cos(a), 12 + 8 * sin(a)),
                  (12 + 11 * cos(a), 12 + 11 * sin(a))])
    elif name == "chevron_left":
        path([(16, 20), (8, 12), (16, 4)])
    elif name == "chevron_right":
        path([(8, 20), (16, 12), (8, 4)])
    elif name == "auto_next":
        path([(3, 5), (3, 19), (14, 12), (3, 5)], True)
        path([(17, 5), (17, 19)])
        path([(21, 5), (21, 19)])
    elif name == "play":
        path([(7, 5), (7, 19), (19, 12), (7, 5)], True)
    elif name == "pause":
        path([(8, 5), (8, 19)])
        path([(16, 5), (16, 19)])
    elif name == "previous":
        path([(18, 5), (8, 12), (18, 19)])
        path([(8, 5), (8, 19)])
    elif name == "next":
        path([(6, 5), (16, 12), (6, 19)])
        path([(16, 5), (16, 19)])
    elif name == "home":
        path([(3, 12), (12, 21), (21, 12)])
        path([(5, 12), (5, 3), (19, 3), (19, 12)])
        path([(10, 3), (10, 10), (14, 10), (14, 3)])
    elif name == "artists":
        ring(9, 17, 3.5)
        path([(2, 5), (2, 9), (6, 13), (12, 13), (16, 9), (16, 5)])
        ring(18, 16, 2.4)
        path([(17, 12), (22, 10), (22, 5)])
    elif name == "albums":
        path([(3, 3), (3, 21), (21, 21), (21, 3), (3, 3)], True)
        ring(12, 12, 6)
        ring(12, 12, 1.5)
    elif name == "stats":
        path([(2, 4), (2, 19)])
        path([(2, 4), (22, 4)])
        path([(4, 7), (9, 11), (13, 9), (18, 17), (22, 20)])
    elif name == "smart":
        ring(12, 12, 6)
        for degree in range(0, 360, 90):
            a = degree * pi / 180
            path([(12 + 8*cos(a), 12 + 8*sin(a)), (12 + 10*cos(a), 12 + 10*sin(a))])
    elif name == "sleep":
        path([(17, 20), (13, 17), (11, 13), (12, 9), (16, 5), (20, 5),
              (16, 2), (8, 4), (4, 9), (4, 15), (8, 20), (17, 20)])
    elif name == "search":
        ring(10, 14, 7)
        path([(15, 8), (22, 2)])
    elif name == "download":
        path([(12, 21), (12, 6), (6, 12)])
        path([(12, 6), (18, 12)])
        path([(4, 4), (4, 2), (20, 2), (20, 4)])
    elif name == "add":
        path([(12, 3), (12, 21)])
        path([(3, 12), (21, 12)])
    elif name == "heart":
        path([(12, 3), (19, 9), (21, 12), (22, 15), (20, 18),
              (17, 20), (14, 20), (12, 18), (10, 20), (7, 20),
              (4, 18), (2, 15), (3, 12), (5, 9), (12, 3)], True)
    elif name == "trash":
        path([(5, 18), (19, 18)])
        path([(9, 18), (9, 20), (15, 20), (15, 18)])
        path([(6, 16), (7.2, 4), (16.8, 4), (18, 16)])
        path([(10, 14), (10.5, 7)])
        path([(14, 14), (13.5, 7)])
    elif name in ("globe", "language", "language_region"):
        ring(12, 12, 10)
        path([(2, 12), (22, 12)])
        path([(12, 2), (12, 22)])
        path([(12, 2), (8, 6), (7.5, 12), (8, 18), (12, 22)])
        path([(12, 2), (16, 6), (16.5, 12), (16, 18), (12, 22)])
    elif name == "region":
        path([(12, 2), (6, 10), (4, 13), (4, 16),
              (6, 20), (9, 22), (15, 22), (18, 20),
              (20, 16), (20, 13), (18, 10), (12, 2)], True)
        ring(12, 15, 2.6)
    elif name == "mix":
        path([(2, 19), (6, 19), (18, 5), (22, 5)])
        path([(18, 9), (22, 5), (18, 2)])
        path([(2, 5), (6, 5), (18, 19), (22, 19)])
        path([(18, 22), (22, 19), (18, 16)])
    elif name == "eq":
        for xx, knob in ((5, 15), (12, 9), (19, 14)):
            path([(xx, 3), (xx, 21)])
            path([(xx - 3, knob - 1.8), (xx + 3, knob - 1.8),
                  (xx + 3, knob + 1.8), (xx - 3, knob + 1.8)], True)
    elif name == "rg":
        path([(2, 9), (6, 9), (11, 5), (11, 19),
              (6, 15), (2, 15)], True)
        path([(14, 8), (16, 10), (16, 14), (14, 16)])
        path([(17, 5), (20, 9), (20, 15), (17, 19)])
    elif name == "folders":
        path([(2, 5), (22, 5), (22, 17), (12, 17),
              (9, 20), (2, 20), (2, 5)], True)
    elif name == "playlists":
        path([(2, 19), (16, 19)])
        path([(2, 14), (16, 14)])
        path([(2, 9), (11, 9)])
        path([(19, 19), (19, 7)])
        ring(16.3, 6.1, 2.6)
    elif name == "queue":
        path([(3, 19), (16, 19)])
        path([(3, 14), (16, 14)])
        path([(3, 9), (12, 9)])
        path([(18, 17), (22, 13), (18, 9)])
        path([(22, 13), (22, 4)])
    elif name == "connect":
        path([(3, 5), (3, 20), (21, 20), (21, 5), (3, 5)], True)
        path([(3, 10), (7, 10), (12, 5)])
        path([(3, 15), (10, 15), (18, 7)])
    elif name == "updates":
        path([(12, 21), (12, 7), (7, 12)])
        path([(12, 7), (17, 12)])
        path([(3, 6), (3, 3), (21, 3), (21, 6)])
    elif name == "about":
        ring(12, 12, 10)
        ring(12, 17, 1)
        path([(12, 12), (12, 6)])
    elif name == "music":
        path([(10, 7), (10, 19), (21, 21), (21, 9)])
        ring(6.5, 6.5, 3)
        ring(17.5, 8.5, 3)
    else:
        ring(12, 12, 8)


class JustMusicIcon(Widget):
    """Drawn icon used beside a label; no special Unicode or font necessary."""
    def __init__(self, icon_name="music", icon_color=ACCENT_2, **kwargs):
        self.icon_name = icon_name
        self.icon_color = icon_color
        super().__init__(**kwargs)
        self._icon_group = InstructionGroup()
        self.canvas.after.add(self._icon_group)
        self.bind(pos=self._refresh_icon, size=self._refresh_icon)
        self._refresh_icon()

    def _refresh_icon(self, *_):
        self._icon_group.clear()
        size = min(dp(24), self.width * 0.72, self.height * 0.72)
        if size > 0:
            draw_justmusic_icon(self._icon_group, self.icon_name,
                                self.center_x - size / 2,
                                self.center_y - size / 2,
                                size, self.icon_color)


class JustMusicIconButton(Button):
    """Rounded, touch-friendly icon button, optionally with label to its right."""
    def __init__(self, icon_name="gear", icon_color=ACCENT_2,
                 icon_align="center", fill_color=PANEL_2,
                 edge_color=(0.18, 0.68, 1, 0.26), **kwargs):
        self.icon_name = icon_name
        self.icon_color = icon_color
        self.icon_align = icon_align
        self._base_fill = fill_color
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs["background_color"] = (0, 0, 0, 0)
        if icon_align == "left":
            kwargs.setdefault("halign", "left")
            kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fill_instruction = Color(*fill_color)
            self._rounded_bg = RoundedRectangle(pos=self.pos, size=self.size,
                                                radius=[dp(11)])
            Color(*edge_color)
            self._rounded_border = Line(rounded_rectangle=(self.x, self.y,
                self.width, self.height, dp(11)), width=1.0)
        self._icon_group = InstructionGroup()
        self.canvas.after.add(self._icon_group)
        self.bind(pos=self._refresh_icon, size=self._refresh_icon,
                  state=self._pressed_style)
        if icon_align == "left":
            self.bind(size=self._align_label)
            self._align_label()
        self._refresh_icon()

    def _align_label(self, *_):
        # Label texture is centered: half the removed width becomes left margin.
        self.text_size = (max(dp(20), self.width - dp(94)), self.height)

    def _pressed_style(self, *_):
        if self.state == "down":
            self._fill_instruction.rgba = tuple(min(1, c * 1.20)
                for c in self._base_fill[:3]) + (self._base_fill[3],)
        else:
            self._fill_instruction.rgba = self._base_fill

    def set_icon_color(self, new_color):
        self.icon_color = new_color
        self._refresh_icon()

    def set_icon_name(self, new_name):
        self.icon_name = new_name
        self._refresh_icon()

    def _refresh_icon(self, *_):
        self._rounded_bg.pos = self.pos
        self._rounded_bg.size = self.size
        self._rounded_border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(11))
        self._icon_group.clear()
        size = min(dp(23), self.height * 0.59)
        x = self.x + dp(14) if self.icon_align == "left" else self.center_x - size / 2
        y = self.center_y - size / 2
        if size > 0:
            draw_justmusic_icon(self._icon_group, self.icon_name, x, y,
                                size, self.icon_color)


def icon_text_row(icon, label, icon_color=ACCENT_2):
    """Return a compact title with a vector icon before the existing text."""
    row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(5))
    glyph = JustMusicIcon(icon_name=icon, icon_color=icon_color,
                          size_hint_x=None, width=dp(28))
    label.halign = "left"
    label.valign = "middle"
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    row.add_widget(glyph)
    row.add_widget(label)
    return row


class SidebarNavButton(Button):
    """Compact PC-style left navigation for narrow Android phone screens."""
    def __init__(self, icon_name="music", selected=False, **kwargs):
        self.icon_name = icon_name
        self.selected = selected
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs["background_color"] = (0, 0, 0, 0)
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", "8.7sp")
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("shorten", True)
        kwargs.setdefault("shorten_from", "right")
        kwargs.setdefault("color", (0.02, 0.08, 0.12, 1) if selected else TEXT)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fill = Color(*(ACCENT if selected else (.04, .15, .24, .84)))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self._icon_instructions = InstructionGroup()
        self.canvas.after.add(self._icon_instructions)
        self.bind(size=self._layout, pos=self._layout)
        self._layout()

    def _layout(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self.text_size = (max(dp(28), self.width-dp(42)), self.height-dp(2))
        self._icon_instructions.clear()
        draw_justmusic_icon(self._icon_instructions, self.icon_name,
            self.x + dp(8), self.center_y-dp(8), dp(16),
            (0.02, .08, .12, 1) if self.selected else ACCENT_2)


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
        self.completed = False
        self.on_completed = None
        self._playback_generation = 0
        self._next_generation = None
        self._completion_listeners = []
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

    def _new(self, path, generation):
        p = self.MediaPlayer()
        try:
            from jnius import autoclass
            AudioAttributes = autoclass("android.media.AudioAttributes")
            attributes = autoclass("android.media.AudioAttributes$Builder")()
            attributes.setUsage(AudioAttributes.USAGE_MEDIA)
            attributes.setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
            p.setAudioAttributes(attributes.build())
        except BaseException as error:
            print("AUDIO ATTRIBUTES SKIP:", error)
        if self.android:
            try:
                from jnius import autoclass
                current_activity = autoclass("org.kivy.android.PythonActivity").mActivity
                PowerManager = autoclass("android.os.PowerManager")
                p.setWakeMode(current_activity, PowerManager.PARTIAL_WAKE_LOCK)
            except BaseException as error:
                print("MEDIAPLAYER WAKE MODE SKIP:", error)
        p.setDataSource(str(path))
        p.prepare()
        try:
            # Android invokes this on a Java thread when a song actually ends.
            # The Python/Kivy screen is only touched later on its own Clock thread.
            from jnius import PythonJavaClass, java_method
            audio = self
            class OnSongFinished(PythonJavaClass):
                __javainterfaces__ = ["android/media/MediaPlayer$OnCompletionListener"]

                @java_method('(Landroid/media/MediaPlayer;)V')
                def onCompletion(self, _player):
                    if audio._playback_generation == generation:
                        audio.completed = True
                        Clock.schedule_once(lambda _dt:
                            audio._send_completion(generation), 0)

            listener = OnSongFinished()
            p.setOnCompletionListener(listener)
            self._completion_listeners.append(listener)
        except BaseException as error:
            # The 250ms end-of-song check remains available as fallback.
            print("MEDIA COMPLETION LISTENER SKIP:", error)
        return p

    def _send_completion(self, generation):
        if generation != self._playback_generation or not self.completed:
            return
        if self.on_completed is not None:
            self.on_completed()

    def load(self, path):
        self._release_eq()
        if self.android:
            self._release(self.player)
            self._release(self.next_player)
            self.next_player = None
            self._playback_generation += 1
            self.completed = False
            self._completion_listeners.clear()
            self.player = self._new(path, self._playback_generation)
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
        self._next_generation = self._playback_generation + 1
        self.next_player = self._new(path, self._next_generation)
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
        self._playback_generation = self._next_generation or self._playback_generation + 1
        self._next_generation = None
        self.completed = False
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
        self._completion_listeners.clear()
        self.on_completed = None


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

        controls = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        self.buttons = {}

        shuffle = Button(text="SHUF", background_normal="", background_color=PANEL_2,
                         color=TEXT, bold=True, font_size="11sp")
        previous = JustMusicIconButton(icon_name="previous", fill_color=PANEL_2, icon_color=TEXT)
        play = JustMusicIconButton(icon_name="play", fill_color=ACCENT, icon_color=(0, .07, .12, 1))
        next_btn = JustMusicIconButton(icon_name="next", fill_color=PANEL_2, icon_color=TEXT)
        repeat = Button(text="REP", background_normal="", background_color=PANEL_2,
                        color=TEXT, bold=True, font_size="11sp")

        self.buttons["SHUF"] = shuffle
        self.buttons["PREV"] = previous
        self.buttons["PLAY"] = play
        self.buttons["NEXT"] = next_btn
        self.buttons["REP"] = repeat

        for widget in (shuffle, previous, play, next_btn, repeat):
            controls.add_widget(widget)

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

    def set_playing(self, on):
        play_btn = self.buttons["PLAY"]
        if hasattr(play_btn, "set_icon_name"):
            play_btn.set_icon_name("pause" if on else "play")
        else:
            play_btn.text = "PAUSE" if on else "PLAY"
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
            height=dp(58),
            padding=[dp(12), dp(4)],
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
            height=dp(26)
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
    row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(5))

    cover_path = cover_for_track(path)
    if cover_path:
        cover = Image(
            source=cover_path,
            size_hint_x=None,
            width=dp(50),
            allow_stretch=True,
            keep_ratio=True
        )
    else:
        cover = JustMusicIcon(icon_name="music", icon_color=ACCENT_2,
                              size_hint_x=None, width=dp(50))

    row.add_widget(cover)

    title = clean_title(path)
    play = Button(
        text=title,
        halign="left",
        valign="middle",
        background_normal="",
        background_color=CARD,
        color=TEXT,
        font_size="13sp"
    )
    play.bind(size=lambda inst, size: setattr(inst, "text_size",
                  (max(dp(30), size[0] - dp(10)), size[1])))
    play.bind(on_release=lambda *_: app.play_path(path))

    fav = JustMusicIconButton(
        icon_name="heart",
        icon_color=(1, .35, .47, 1) if app.is_favorite(path) else TEXT_2,
        size_hint_x=None,
        width=dp(42),
        fill_color=PANEL_2
    )

    def toggle(*_):
        app.toggle_favorite(path)
        fav.set_icon_color((1, .35, .47, 1) if app.is_favorite(path) else TEXT_2)
        if refresh_callback:
            refresh_callback()

    fav.bind(on_release=toggle)

    next_btn = Button(
        text="NEXT",
        size_hint_x=None,
        width=dp(42),
        background_normal="",
        background_color=PANEL_2,
        color=ACCENT_2,
        bold=True,
        font_size="8sp"
    )
    next_btn.bind(on_release=lambda *_: app.add_play_next(path))

    queue_btn = Button(
        text="Q+",
        size_hint_x=None,
        width=dp(34),
        background_normal="",
        background_color=PANEL_2,
        color=ACCENT_2,
        bold=True,
        font_size="9sp"
    )
    queue_btn.bind(on_release=lambda *_: app.add_to_queue(path))

    row.add_widget(play)
    row.add_widget(next_btn)
    row.add_widget(queue_btn)
    row.add_widget(fav)
    return row


def make_compact_song_row(path, refresh_callback=None):
    """Keskeny mobilnézet: borító + cím + kedvenc + hárompontos műveletek."""
    app = App.get_running_app()
    row = BoxLayout(size_hint_y=None, height=dp(53), spacing=dp(3))
    art = cover_for_track(path)
    if art:
        image = Image(source=art, size_hint_x=None, width=dp(35),
                      allow_stretch=True, keep_ratio=True)
    else:
        image = JustMusicIcon(icon_name="music", size_hint_x=None, width=dp(35))
    row.add_widget(image)
    title = Button(text=clean_title(path), halign="left", valign="middle",
        font_size="11sp", background_normal="", background_color=CARD,
        color=TEXT, shorten=True, shorten_from="right")
    title.bind(size=lambda inst, sz: setattr(inst, "text_size", (max(dp(15),sz[0]-dp(6)),sz[1])))
    title.bind(on_release=lambda *_: app.play_path(path))
    row.add_widget(title)
    heart = JustMusicIconButton(icon_name="heart", size_hint_x=None,
        width=dp(31), icon_color=(1,.35,.47,1) if app.is_favorite(path) else TEXT_2)
    def favorite(*_):
        app.toggle_favorite(path)
        heart.set_icon_color((1,.35,.47,1) if app.is_favorite(path) else TEXT_2)
    heart.bind(on_release=favorite)
    row.add_widget(heart)
    menu = Button(text="⋮", size_hint_x=None, width=dp(30), bold=True,
        font_size="20sp", background_normal="", background_color=PANEL_2, color=ACCENT_2)
    def options(*_):
        body=BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10))
        pop=Popup(title=clean_title(path)[:55], content=body, size_hint=(.9, None), height=dp(270))
        for label, callback in (
            ("LEJÁTSZÁS", lambda: app.play_path(path)),
            ("KÖVETKEZŐNEK", lambda: app.add_play_next(path)),
            ("SOR VÉGÉRE", lambda: app.add_to_queue(path)),
            ("KEDVENC", lambda: favorite()),
        ):
            b=Button(text=label, background_normal="", background_color=PANEL_2, color=TEXT,
                     size_hint_y=None, height=dp(45), font_size="12sp")
            def pressed(_btn, action=callback):
                pop.dismiss()
                action()
            b.bind(on_release=pressed)
            body.add_widget(b)
        pop.open()
    menu.bind(on_release=options)
    row.add_widget(menu)
    return row


class LibraryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Image(source="party_bg.png", allow_stretch=True, keep_ratio=False))
        self.add_widget(DarkOverlay(.62))

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(7), dp(10), dp(7), dp(8)],
            spacing=dp(7)
        )

        brand_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        brand = Label(
            text="[b][color=63D2FF]JustMusic![/color][/b]",
            markup=True,
            font_size="27sp",
            halign="left",
            valign="middle"
        )
        brand.bind(size=lambda i, v: setattr(i, "text_size", (i.width, i.height)))

        settings_button = JustMusicIconButton(
            icon_name="gear", icon_color=ACCENT_2,
            size_hint_x=None, width=dp(48),
            fill_color=PANEL_2
        )
        settings_button.bind(
            on_release=lambda *_:
                App.get_running_app().open_screen("settings")
        )

        build_label = Label(
            text=f"v{APP_VERSION} {APP_UI_REVISION}", color=ACCENT_2,
            size_hint_x=None, width=dp(91), font_size="10sp", bold=True,
            halign="center", valign="middle"
        )
        brand_row.add_widget(brand)
        brand_row.add_widget(build_label)
        brand_row.add_widget(settings_button)
        root.add_widget(brand_row)
        root.add_widget(MadeInHungaryBanner())

        # REV6: a PC-s JustMusic! oldalsavjat koveti.
        # BAL: ikon + felirat egymas alatt. Egy elvalaszto a navigacio es
        # a helyi zene/letoltes eszkozei kozott. JOBB: dalok es kereses.
        content_row = BoxLayout(orientation="horizontal", spacing=dp(6))
        music_column = BoxLayout(orientation="vertical", spacing=dp(6))

        side = GlassPanel(orientation="vertical", size_hint_x=None, width=dp(182),
            padding=[dp(5), dp(7), dp(5), dp(6)], spacing=dp(5))
        menu_header = Label(text="JustMusic!", color=ACCENT_2, bold=True,
            font_size="14sp", halign="left", valign="middle",
            size_hint_y=None, height=dp(36))
        menu_header.bind(size=lambda widget, _size:
            setattr(widget, "text_size", (widget.width, widget.height)))
        side.add_widget(menu_header)

        side_scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        side_items = BoxLayout(orientation="vertical", size_hint_y=None,
            spacing=dp(3), padding=[dp(1), dp(2), dp(1), dp(8)])
        side_items.bind(minimum_height=side_items.setter("height"))
        self.nav_buttons = {}

        navigation = (
            ("KEZDŐLAP", "library", "home"),
            ("ELŐADÓK", "artists", "artists"),
            ("ALBUMOK", "albums", "albums"),
            ("KEDVENCEK", "favorites", "heart"),
            ("ÖSSZES DAL", "library_all", "music"),
            ("PLAYLISTEK", "playlists", "playlists"),
            ("SMART LISTÁK", "smart", "smart"),
            ("STATISZTIKÁK", "stats", "stats"),
            ("LEJÁTSZÁSI SOR", "queue", "queue"),
            ("SLEEP TIMER", "sleep", "sleep"),
            ("MOST SZÓL", "now_playing", "music"),
            ("CONNECT", "connect", "connect"),
        )
        tools = (
            ("HELYI ZENE +", "import", "add"),
            ("LETÖLTÉS", "archive", "download"),
            ("ZÁRKÉPERNYŐ", "notification", "music"),
            ("ZENE MAPPÁK", "folders", "folders"),
            ("FRISSÍTÉS", "refresh", "updates"),
        )

        def add_menu_item(label, target, glyph):
            selected = target == "library"
            button = SidebarNavButton(text=label, icon_name=glyph, selected=selected,
                size_hint_y=None, height=dp(46) if len(label) < 19 else dp(55))
            if target == "refresh":
                button.bind(on_release=lambda *_: App.get_running_app().scan())
            elif target == "import":
                button.bind(on_release=lambda *_: App.get_running_app().pick_local_music())
            elif target == "notification":
                button.bind(on_release=lambda *_: App.get_running_app().open_notification_access())
            elif target == "library_all":
                button.bind(on_release=lambda *_: (
                    setattr(self.search, "text", ""),
                    App.get_running_app().open_screen("library")))
            else:
                button.bind(on_release=lambda _, t=target:
                    App.get_running_app().open_screen(t))
            self.nav_buttons[target] = button
            side_items.add_widget(button)

        for label, target, glyph in navigation:
            add_menu_item(label, target, glyph)
        # A PC-s kepen kert VALODI elvalaszto a ket menucsoport kozott.
        rule = Widget(size_hint_y=None, height=dp(17))
        with rule.canvas:
            Color(ACCENT_2[0], ACCENT_2[1], ACCENT_2[2], .65)
            rule._separator_line = Line(points=[0, 0, 0, 0], width=1.0)
        def sync_rule(w, *_):
            w._separator_line.points = [w.x + dp(9), w.center_y,
                                        w.right - dp(9), w.center_y]
        rule.bind(pos=sync_rule, size=sync_rule)
        side_items.add_widget(rule)
        for label, target, glyph in tools:
            add_menu_item(label, target, glyph)

        side_scroll.add_widget(side_items)
        side.add_widget(side_scroll)

        self.search = TextInput(
            hint_text="Keresés a zenék között…",
            multiline=False,
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_active="",
            background_color=(.03, .11, .19, .96),
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=ACCENT_2,
            padding=[dp(14), dp(12)]
        )
        self._search_event = None
        self._render_generation = 0
        self._render_queue = []
        self.search.bind(text=self._on_search_text)
        music_column.add_widget(self.search)

        # A dalok száma és az AUTO állapot a keskeny bal hasábban is látható.
        summary = GlassPanel(
            size_hint_y=None, height=dp(44), padding=[dp(10), dp(5)],
            spacing=dp(5)
        )
        self.status = Label(
            text="ZENÉIM • Betöltés…", color=ACCENT_2,
            halign="left", valign="middle", bold=True,
            font_size="12sp"
        )
        self.status.bind(size=lambda inst, val:
            setattr(inst, "text_size", (inst.width, inst.height)))
        self.auto_next_button = Button(
            text="AUTO: BE", size_hint_x=None, width=dp(84),
            font_size="10sp", bold=True, background_normal="",
            background_color=PANEL_2, color=ACCENT_2
        )
        self.auto_next_button.bind(on_release=lambda *_:
            App.get_running_app().toggle_auto_next())
        summary.add_widget(self.status)
        summary.add_widget(self.auto_next_button)
        music_column.add_widget(summary)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["content"])
        self.box = BoxLayout(orientation="vertical", spacing=dp(5),
                             size_hint_y=None, padding=[0, dp(3), 0, dp(8)])
        self.box.bind(minimum_height=self.box.setter("height"))
        scroll.add_widget(self.box)
        music_column.add_widget(scroll)
        # BAL oldalt valamennyi menüpont, egyetlen görgethető oszlopban.
        # JOBB oldalt a kereső, a zenelista és az AUTO kapcsoló.
        content_row.add_widget(side)
        content_row.add_widget(music_column)
        root.add_widget(content_row)

        self.player = PlayerBar()
        root.add_widget(self.player)
        self.add_widget(root)

    def on_pre_enter(self, *_):
        self.refresh_list()

    def refresh_auto_next_button(self):
        enabled = bool(getattr(App.get_running_app(), "auto_next_enabled", True))
        self.auto_next_button.text = "AUTO: BE" if enabled else "AUTO: KI"
        self.auto_next_button.color = ACCENT_2 if enabled else TEXT_2

    def _on_search_text(self, *_):
        if self._search_event is not None:
            try:self._search_event.cancel()
            except Exception:pass
        self._search_event = Clock.schedule_once(lambda *_: self.refresh_list(), .18)

    def refresh_list(self):
        app = App.get_running_app()
        self._render_generation += 1
        generation = self._render_generation
        self.box.clear_widgets()
        q = self.search.text.strip().lower()
        visible = [p for p in app.songs if (not q or q in clean_title(p).lower())]
        self.refresh_auto_next_button()
        if app._scan_in_progress and not app.songs:
            self.status.text = "ZENÉIM • KERESÉS…"
            message = "Zenék keresése a telefonon…"
        elif app.songs:
            self.status.text = f"ZENÉIM • {len(visible)} / {len(app.songs)}"
            message = "Nincs találat a keresésre." if q else ""
        else:
            self.status.text = "ZENÉIM • 0 DAL"
            message = "A BEÁLLÍTÁSOK → ZENE MAPPÁK menüben adj hozzá zenemappát."
        if not visible and message:
            label = Label(text=message, color=TEXT_2, font_size="13sp",
                          halign="center", valign="middle",
                          size_hint_y=None, height=dp(90))
            label.bind(size=lambda widget, size:
                       setattr(widget, "text_size", (max(dp(20), size[0]-dp(20)), size[1])))
            self.box.add_widget(label)
        self._render_queue = visible
        self._render_chunk(generation)

    def _render_chunk(self, generation):
        if generation != self._render_generation or not self._render_queue:
            return
        chunk = self._render_queue[:28]
        self._render_queue = self._render_queue[28:]
        for path in chunk:
            self.box.add_widget(make_compact_song_row(path, self.refresh_list))
        if self._render_queue:
            Clock.schedule_once(lambda *_: self._render_chunk(generation), 0)


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
        back = JustMusicIconButton(
            icon_name="back", icon_color=ACCENT_2,
            size_hint_x=None, width=dp(50), fill_color=PANEL_2
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
        back = JustMusicIconButton(
            icon_name="back", icon_color=ACCENT_2,
            size_hint_x=None, width=dp(50), fill_color=PANEL_2
        )
        back.bind(on_release=lambda *_: App.get_running_app().show_library())
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
                remove = JustMusicIconButton(
                    icon_name="trash", icon_color=(1, .52, .54, 1),
                    size_hint_x=None, width=dp(48),
                    fill_color=(.20, .07, .10, .95),
                    edge_color=(1, .32, .42, .3)
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

            remove = JustMusicIconButton(
                icon_name="trash", icon_color=(1, .52, .54, 1),
                size_hint_x=None, width=dp(48),
                fill_color=(.20, .07, .10, .95),
                edge_color=(1, .32, .42, .3)
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
        self.fav_button = JustMusicIconButton(
            icon_name="heart", icon_color=TEXT_2,
            fill_color=PANEL_2, size_hint_x=None, width=dp(58)
        )
        lyrics = Button(text="DALSZÖVEG", background_normal="", background_color=PANEL_2, color=ACCENT_2, bold=True)
        self.fav_button.bind(on_release=lambda *_: self.toggle_favorite())
        lyrics.bind(on_release=lambda *_: App.get_running_app().open_lyrics())
        row.add_widget(self.fav_button); row.add_widget(lyrics); root.add_widget(row)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.fav_button.set_icon_color(
            (1, .35, .47, 1) if app.current_path and app.is_favorite(app.current_path)
            else TEXT_2
        )
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
            self.fav_button.set_icon_color(
                (1, .35, .47, 1) if app.is_favorite(app.current_path) else TEXT_2
            )


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
        self.top_label=Label(text="", color=TEXT_2, font_size="14sp", halign="left", valign="top")
        self.top_label.bind(size=lambda i,v:setattr(i,"text_size",(i.width-dp(20), None)))
        root.add_widget(self.top_label)

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
        self.top_label.text="\n".join(lines)


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


class SettingsScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("BEÁLLÍTÁSOK")

        self.locale_info = Label(
            text="", color=ACCENT_2, size_hint_y=None,
            height=dp(58), bold=True, font_size="10sp",
            halign="left", valign="middle"
        )
        self.locale_info.bind(size=lambda inst, sz: setattr(inst, "text_size", (max(dp(20), sz[0]-dp(8)), sz[1])))
        root.add_widget(self.locale_info)

        # Keep every original label. Icons are drawn BEFORE the texts.
        entries = (
            ("NYELV ÉS RÉGIÓ", "language_region", "globe"),
            ("MIX / CROSSFADE", "mix", "mix"),
            ("EQUALIZER", "eq", "eq"),
            ("REPLAYGAIN", "rg", "rg"),
            ("ZENE MAPPÁK", "folders", "folders"),
            ("HELYI ZENE HOZZÁADÁSA", "import", "music"),
            ("INTERNET ARCHIVE", "archive", "updates"),
            ("ZÁRKÉPERNYŐ / ENGEDÉLY", "notification", "music"),
            ("PLAYLISTEK", "playlists", "playlists"),
            ("LEJÁTSZÁSI SOR", "queue", "queue"),
            ("CONNECT", "connect", "connect"),
            ("FRISSÍTÉSEK", "updates", "updates"),
            ("NÉVJEGY", "about", "about"),
        )
        # Allow all settings to stay reachable on compact Android displays.
        settings_scroll = ScrollView(do_scroll_x=False)
        settings_list = BoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(7), padding=[dp(2), dp(3), dp(2), dp(12)]
        )
        settings_list.bind(minimum_height=settings_list.setter("height"))

        self.buttons = {}
        for label, target, icon in entries:
            selected = target == "language_region"
            button = JustMusicIconButton(
                text=label, icon_name=icon, icon_align="left",
                size_hint_y=None, height=dp(48),
                fill_color=ACCENT if selected else PANEL_2,
                icon_color=(0, .09, .16, 1) if selected else ACCENT_2,
                color=(0, .09, .16, 1) if selected else TEXT,
                bold=True, font_size="13sp"
            )
            if target == "import":
                button.bind(on_release=lambda *_: App.get_running_app().pick_local_music())
            elif target == "notification":
                button.bind(on_release=lambda *_: App.get_running_app().open_notification_access())
            else:
                button.bind(on_release=lambda _, t=target:
                            App.get_running_app().open_screen(t))
            settings_list.add_widget(button)
            self.buttons[target] = button
        settings_scroll.add_widget(settings_list)
        root.add_widget(settings_scroll)

    def on_pre_enter(self, *_):
        app = App.get_running_app()
        self.title_label.text = f"[b]{ui_text(app, 'settings')}[/b]"
        prefix = "" if app.setup_complete else "ELSŐ BEÁLLÍTÁS • "
        first = f"{ui_text(app, 'language')}: {SUPPORTED_LANGUAGES.get(app.language, app.language)}"
        second = f"{ui_text(app, 'region')}: {SUPPORTED_REGIONS.get(app.region, app.region)}"
        self.locale_info.text = (prefix + first + "\n" + second) if prefix else (first + "\n" + second)
        if "language_region" in self.buttons:
            self.buttons["language_region"].text = ui_text(app, "language_region")
        if "updates" in self.buttons:
            self.buttons["updates"].text = ui_text(app, "updates")
        if "about" in self.buttons:
            self.buttons["about"].text = ui_text(app, "about")


class LanguageRegionScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("NYELV ÉS RÉGIÓ")

        self.current = Label(
            text="",
            color=ACCENT_2,
            size_hint_y=None,
            height=dp(44),
            bold=True
        )
        root.add_widget(self.current)

        self.lang_title = Label(
            text="Nyelv",
            color=TEXT_2,
            bold=True,
            size_hint_y=None,
            height=dp(28)
        )
        root.add_widget(icon_text_row("language", self.lang_title))

        lang_rows = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(108),
            spacing=dp(5)
        )
        l1 = BoxLayout(spacing=dp(5))
        l2 = BoxLayout(spacing=dp(5))
        lang_rows.add_widget(l1)
        lang_rows.add_widget(l2)

        for idx, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
            b = Button(
                text=name,
                background_normal="",
                background_color=PANEL_2,
                color=TEXT,
                bold=True,
                font_size="10sp"
            )
            b.bind(
                on_release=lambda _, c=code:
                    self.set_language(c)
            )
            (l1 if idx < 3 else l2).add_widget(b)

        root.add_widget(lang_rows)

        self.region_title = Label(
            text="Régió",
            color=TEXT_2,
            bold=True,
            size_hint_y=None,
            height=dp(28)
        )
        root.add_widget(icon_text_row("region", self.region_title))

        reg_rows = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(108),
            spacing=dp(5)
        )
        r1 = BoxLayout(spacing=dp(5))
        r2 = BoxLayout(spacing=dp(5))
        reg_rows.add_widget(r1)
        reg_rows.add_widget(r2)

        for idx, (code, name) in enumerate(SUPPORTED_REGIONS.items()):
            b = Button(
                text=name,
                background_normal="",
                background_color=PANEL_2,
                color=TEXT,
                bold=True,
                font_size="9sp"
            )
            b.bind(
                on_release=lambda _, c=code:
                    self.set_region(c)
            )
            (r1 if idx < 3 else r2).add_widget(b)

        root.add_widget(reg_rows)

        root.add_widget(Label(
            text=(
                "A stabil CLEAN buildben a nyelv/régió választás mentődik.\\n"
                "A teljes app-fordítást külön, biztonságosan bővítjük tovább."
            ),
            color=TEXT_2,
            halign="center"
        ))

    def on_pre_enter(self, *_):
        app = App.get_running_app()
        self.title_label.text = f"[b]{ui_text(app, 'language_region')}[/b]"
        self.lang_title.text = ui_text(app, "language")
        self.region_title.text = ui_text(app, "region")
        self.current.text = (
            f"{SUPPORTED_LANGUAGES.get(app.language, app.language)} • "
            f"{SUPPORTED_REGIONS.get(app.region, app.region)}"
        )

    def set_language(self, language):
        app = App.get_running_app()
        if language in SUPPORTED_LANGUAGES:
            app.language = language
            app.setup_complete = True
            app.save_settings()
            self.on_pre_enter()

    def set_region(self, region):
        app = App.get_running_app()
        if region in SUPPORTED_REGIONS:
            app.region = region
            app.setup_complete = True
            app.save_settings()
            self.on_pre_enter()


class UpdatesScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("FRISSÍTÉSEK")

        self.status = Label(
            text=f"Jelenlegi verzió: {APP_VERSION}",
            color=TEXT_2,
            halign="center"
        )
        root.add_widget(self.status)

        check = Button(
            text="FRISSÍTÉSEK KERESÉSE",
            size_hint_y=None,
            height=dp(54),
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True
        )
        check.bind(on_release=lambda *_: App.get_running_app().check_for_updates())
        root.add_widget(check)

        self.download = Button(
            text="LETÖLTÉS",
            size_hint_y=None,
            height=dp(54),
            background_normal="",
            background_color=PANEL_2,
            color=ACCENT_2,
            bold=True,
            disabled=True
        )
        self.download.bind(
            on_release=lambda *_:
                App.get_running_app().open_latest_update()
        )
        root.add_widget(self.download)

    def on_pre_enter(self, *_):
        app = App.get_running_app()
        self.title_label.text = f"[b]{ui_text(app, 'updates')}[/b]"
        if not app.latest_version:
            self.status.text = (
                f"{ui_text(app, 'current_version') if 'current_version' in UI_TEXT.get(app.language, {}) else 'Jelenlegi verzió'}: "
                f"{APP_VERSION}"
            )

    def show_result(self, version, available):
        app = App.get_running_app()
        if available:
            self.status.text = (
                f"{ui_text(app, 'update_available')}: v{version}\\n"
                f"Jelenlegi: v{APP_VERSION}"
            )
            self.download.text = ui_text(app, "download")
            self.download.disabled = False
        else:
            self.status.text = ui_text(app, "up_to_date")
            self.download.disabled = True


class AboutScreen(BaseFeature):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("NÉVJEGY")
        root.add_widget(Label(
            text=(
                f"[b][color=63D2FF]JustMusic! Mobile v{APP_VERSION}[/color][/b]\\n\\n"
                "Made In Hungary 🇭🇺\\n"
                "Szabó Zoltán\\n"
                "IG: @ZS420LLER\\n\\n"
                "Your music. Your style. 🎧"
            ),
            markup=True,
            color=TEXT,
            font_size="20sp",
            halign="center"
        ))



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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("LEJÁTSZÁSI SOR")

        tools = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))

        current = Button(
            text="AKTUÁLIS +",
            background_normal="",
            background_color=ACCENT,
            color=(0, .07, .12, 1),
            bold=True,
            font_size="10sp"
        )
        current.bind(on_release=lambda *_: self.add_current())

        clear = JustMusicIconButton(
            text="SOR TÖRLÉSE", icon_name="trash", icon_align="left",
            icon_color=(1, .52, .54, 1),
            fill_color=(.20, .07, .10, .95),
            edge_color=(1, .32, .42, .3),
            color=TEXT, bold=True, font_size="10sp"
        )
        clear.bind(on_release=lambda *_: self.clear_queue())

        tools.add_widget(current)
        tools.add_widget(clear)
        root.add_widget(tools)

        self.info = Label(
            text="",
            color=ACCENT_2,
            size_hint_y=None,
            height=dp(34),
            halign="left"
        )
        root.add_widget(self.info)

        self.scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6)
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        root.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def add_current(self):
        app = App.get_running_app()
        if app.current_path:
            app.add_to_queue(app.current_path)
        self.refresh()

    def clear_queue(self):
        app = App.get_running_app()
        app.manual_queue = []
        app.save_settings()
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        self.box.clear_widgets()
        app.clean_manual_queue()
        self.info.text = f"KÉZI SOR • {len(app.manual_queue)} dal"

        if not app.manual_queue:
            self.box.add_widget(Label(
                text="A kézi lejátszási sor üres.",
                color=TEXT_2,
                size_hint_y=None,
                height=dp(96),
                halign="center"
            ))
            return

        for index, path in enumerate(list(app.manual_queue)):
            row = BoxLayout(
                size_hint_y=None,
                height=dp(58),
                spacing=dp(4)
            )

            play = Button(
                text=clean_title(path),
                background_normal="",
                background_color=CARD,
                color=TEXT,
                halign="left",
                valign="middle"
            )
            play.bind(
                size=lambda i, v:
                    setattr(i, "text_size", (max(dp(80), i.width-dp(8)), None))
            )
            play.bind(on_release=lambda _, p=path: app.play_path(p))

            up = Button(
                text="↑",
                size_hint_x=None,
                width=dp(38),
                background_normal="",
                background_color=PANEL_2,
                color=ACCENT_2
            )
            down = Button(
                text="↓",
                size_hint_x=None,
                width=dp(38),
                background_normal="",
                background_color=PANEL_2,
                color=ACCENT_2
            )
            remove = JustMusicIconButton(
                icon_name="trash", icon_color=(1, .52, .54, 1),
                size_hint_x=None, width=dp(42),
                fill_color=(.20, .07, .10, .95),
                edge_color=(1, .32, .42, .3)
            )

            up.bind(
                on_release=lambda _, i=index:
                    self.move(i, -1)
            )
            down.bind(
                on_release=lambda _, i=index:
                    self.move(i, 1)
            )
            remove.bind(
                on_release=lambda _, i=index:
                    self.remove(i)
            )

            row.add_widget(play)
            row.add_widget(up)
            row.add_widget(down)
            row.add_widget(remove)
            self.box.add_widget(row)

    def move(self, index, delta):
        app = App.get_running_app()
        new_index = index + delta
        if (
            0 <= index < len(app.manual_queue)
            and 0 <= new_index < len(app.manual_queue)
        ):
            app.manual_queue[index], app.manual_queue[new_index] = (
                app.manual_queue[new_index],
                app.manual_queue[index],
            )
            app.save_settings()
        self.refresh()

    def remove(self, index):
        app = App.get_running_app()
        if 0 <= index < len(app.manual_queue):
            app.manual_queue.pop(index)
            app.save_settings()
        self.refresh()


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


class ArchiveScreen(BaseFeature):
    """Internet Archive: metaadatok, jogtisztán letölthető hangfájlok."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = self.make("ARCHIVE • ZENE LETÖLTÉS")
        root.add_widget(Label(text="Internet Archive • CC / közkincs zenék",
            color=TEXT_2, size_hint_y=None, height=dp(30), font_size="12sp"))
        search_row=BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        self.query=TextInput(hint_text="Előadó vagy zeneszám...", multiline=False,
            background_normal="", background_active="", background_color=PANEL_2,
            foreground_color=TEXT, hint_text_color=MUTED, size_hint_x=1)
        self.query.bind(on_text_validate=lambda *_:self.search())
        start=Button(text="KERESÉS", size_hint_x=None, width=dp(91),
            background_normal="", background_color=ACCENT, color=BG, bold=True)
        start.bind(on_release=lambda *_:self.search())
        search_row.add_widget(self.query);search_row.add_widget(start)
        root.add_widget(search_row)
        self.status=Label(text="Írj be egy címet, majd nyomj a KERESÉS-re.",
            color=ACCENT_2, size_hint_y=None, height=dp(42), font_size="11sp")
        root.add_widget(self.status)
        self.scroll=ScrollView(do_scroll_x=False)
        self.results=BoxLayout(orientation="vertical", size_hint_y=None,
            spacing=dp(5), padding=[dp(2),dp(2),dp(2),dp(10)])
        self.results.bind(minimum_height=self.results.setter("height"))
        self.scroll.add_widget(self.results)
        root.add_widget(self.scroll)
        self.generation=0

    def _status(self, msg):
        self.status.text=str(msg)

    def search(self):
        phrase=self.query.text.strip()
        if len(phrase)<2:
            self._status("Legalább két betűt írj be.");return
        self.generation+=1; token=self.generation
        self.results.clear_widgets()
        self._status("Archive keresés folyamatban…")
        def worker():
            try:
                # Kizárólag audio-elemek, a letöltés előtt licencellenőrzéssel.
                query='(mediatype:audio OR mediatype:etree) AND (' + ' '.join(
                    re.findall(r"[\w-]+",phrase,flags=re.UNICODE)[:9]) + ')'
                params=[("q",query),("output","json"),("rows","22"),
                    ("fl[]","identifier"),("fl[]","title"),("fl[]","creator"),
                    ("fl[]","licenseurl")]
                url="https://archive.org/advancedsearch.php?"+urllib.parse.urlencode(params)
                req=urllib.request.Request(url,headers={"User-Agent":"JustMusic-Mobile/1.8.6 (+Archive search)"})
                with urllib.request.urlopen(req,timeout=22) as res:
                    docs=json.loads(res.read(1_500_000)).get("response",{}).get("docs",[])
                Clock.schedule_once(lambda _dt:self._render_results(token,docs),0)
            except Exception as error:
                msg=f"Archive keresési hiba: {str(error)[:100]}"
                Clock.schedule_once(lambda _dt:self._status(msg),0)
        threading.Thread(target=worker,daemon=True).start()

    def _render_results(self, token, docs):
        if token!=self.generation:return
        self.results.clear_widgets()
        self._status(f"{len(docs)} találat • válaszd a FÁJLOK gombot")
        if not docs:self._status("Nincs találat. Próbálj másik keresést.")
        for item in docs:
            identifier=str(item.get("identifier") or "")
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",identifier):continue
            title=str(item.get("title") or identifier)[:120]
            creator=item.get("creator") or "Ismeretlen előadó"
            if isinstance(creator,list):creator=", ".join(map(str,creator[:2]))
            row=BoxLayout(size_hint_y=None,height=dp(68),spacing=dp(5))
            label=Label(text=f"{title}\n{str(creator)[:60]}",color=TEXT,
                font_size="11sp",halign="left",valign="middle",shorten=True)
            label.bind(size=lambda inst,sz:setattr(inst,"text_size",(sz[0],sz[1])))
            btn=Button(text="FÁJLOK",size_hint_x=None,width=dp(78),
                background_normal="",background_color=PANEL_2,color=ACCENT_2,
                font_size="10sp",bold=True)
            btn.bind(on_release=lambda _,id=identifier,name=title: self.view_files(id,name))
            row.add_widget(label);row.add_widget(btn);self.results.add_widget(row)

    def view_files(self, identifier, title):
        self._status("Fájlok és licenc ellenőrzése…")
        def worker():
            try:
                url="https://archive.org/metadata/"+urllib.parse.quote(identifier)
                req=urllib.request.Request(url,headers={"User-Agent":"JustMusic-Mobile/1.8.6"})
                with urllib.request.urlopen(req,timeout=22) as res:
                    data=json.loads(res.read(3_000_000))
                meta=data.get("metadata",{}) or {}
                license_value=str(meta.get("licenseurl") or "").lower()
                rights=str(meta.get("rights") or "").lower()
                allowed=("creativecommons.org/licenses/" in license_value
                    or "creativecommons.org/publicdomain/" in license_value
                    or "public domain" in rights or "közkincs" in rights)
                files=[f for f in data.get("files",[]) if
                       str(f.get("name") or "").lower().endswith(SUPPORTED_AUDIO)
                       and str(f.get("source") or "") != "metadata"
                       and (not f.get("size") or (str(f.get("size")).isdigit() and int(f["size"])<550_000_000))]
                Clock.schedule_once(lambda _dt:self._render_files(title,identifier,files,allowed,license_value),0)
            except Exception as error:
                msg=f"Nem tölthetők be a fájlok: {str(error)[:100]}"
                Clock.schedule_once(lambda _dt:self._status(msg),0)
        threading.Thread(target=worker,daemon=True).start()

    def _render_files(self,title,identifier,files,allowed,license_value):
        self.results.clear_widgets()
        self._status(("Letölthető fájlok: " if allowed else "Licenc nem igazolt: csak megtekintés")
                     +str(len(files)))
        back=Button(text="← VISSZA A KERESÉSHEZ",size_hint_y=None,height=dp(43),
                    background_normal="",background_color=PANEL_2,color=ACCENT_2)
        back.bind(on_release=lambda *_:self.search())
        self.results.add_widget(back)
        if not files:
            self.results.add_widget(Label(text="Nincs támogatott hangfájl ebben az elemben.",
                size_hint_y=None,height=dp(75),color=TEXT_2))
        if not allowed:
            self.results.add_widget(Label(text="Nincs igazolható CC / közkincs megjelölés.\n"
                "A fájlokat itt nem kínáljuk letöltésre.",size_hint_y=None,
                height=dp(65),color=TEXT_2))
        for info in files[:80]:
            filename=str(info.get("name") or "")
            row=BoxLayout(size_hint_y=None,height=dp(52),spacing=dp(4))
            label=Label(text=Path(filename).name[:65],color=TEXT,font_size="11sp",shorten=True)
            btn=Button(text="LE ↓" if allowed else "INFO",size_hint_x=None,width=dp(61),
                background_normal="",background_color=ACCENT if allowed else PANEL_2,
                color=BG if allowed else ACCENT_2,bold=True, font_size="10sp")
            if allowed:
                btn.bind(on_release=lambda _,id=identifier,n=filename:self.download_file(id,n))
            else:
                btn.bind(on_release=lambda _,id=identifier:App.get_running_app().open_url(
                    "https://archive.org/details/"+urllib.parse.quote(id)))
            row.add_widget(label);row.add_widget(btn);self.results.add_widget(row)

    def download_file(self, identifier, filename):
        App.get_running_app().download_archive_track(identifier,filename,self._status)



class JustMusicApp(App):
    def build(self):
        self.title="JustMusic! Mobile v1.8.6 REV6"
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
        self._scan_in_progress=False
        self._scan_pending=False

        # CLEAN rebuild state. No Android/JNI call happens here.
        self.language="hu"
        self.region="HU"
        self.setup_complete=False
        self.manual_queue=[]
        self.latest_version=""
        self.latest_release_url=""
        self.latest_download_url=""
        self._media_intent_bound=False
        self._media_session = None
        self._music_service_started = False
        self._music_service_seq = 0
        self._music_service_launch_time = 0.0
        self._music_service_sync_tick = 0.0
        self._media_state_last_sync = 0.0
        self._playback_wake_lock = None
        self._notification_permission_attempted = False
        self._user_notification_permission_requested = False
        self._local_file_request_code = 7617
        self._playing_expected = False

        self.audio=NativeAudio()
        self.audio.on_completed = self.on_audio_completed
        self.backend_name="Android MediaPlayer" if self.audio.android else "Kivy fallback"
        self.shuffle_enabled=False; self.repeat_mode="off"
        self.auto_next_enabled=True
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
        self.mix_target_from_queue=False
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
        self.archive_screen=ArchiveScreen(name="archive")
        # ULTRA SAFE: extra v1.7/v1.8 screens are lazy-loaded.
        self.settings_screen=None
        self.language_region_screen=None
        self.updates_screen=None
        self.about_screen=None
        for s in (
            self.library, self.lyrics_screen,
            self.artists_screen, self.artist_tracks_screen,
            self.albums_screen, self.album_tracks_screen,
            self.favorites_screen, self.connect_screen,
            self.folders_screen, self.playlists_screen, self.playlist_tracks_screen,
            self.now_playing_screen, self.history_screen, self.stats_screen,
            self.smart_screen, self.archive_screen,
            MixScreen(name="mix"), EQScreen(name="eq"), RGScreen(name="rg"),
            QueueScreen(name="queue"), SleepScreen(name="sleep")
        ):
            self.manager.add_widget(s)
        self.library.player.set_shuffle(self.shuffle_enabled); self.library.player.set_repeat(self.repeat_mode)
        self.library.player.set_mix_status(self.crossfade_enabled,self.mix_gapless_enabled,self.mix_fade_out_seconds,self.mix_fade_in_seconds)
        Clock.schedule_interval(self.tick,.25)
        Clock.schedule_once(lambda *_:self.permissions(),.4)
        Clock.schedule_once(lambda *_:self.scan(),1.2)

        # ULTRA SAFE:
        # no popup, locale/JNI, update check or media-control setup during startup.
        # Language/region can be selected later from the gear menu.
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
            self.auto_next_enabled=bool(d.get("auto_next", True))
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
            self.language=str(d.get("language", self.language) or self.language)
            if self.language not in SUPPORTED_LANGUAGES:
                self.language="hu"
            self.region=str(d.get("region", self.region) or self.region).upper()
            if self.region not in SUPPORTED_REGIONS:
                self.region="HU"
            self.setup_complete=bool(d.get("setup_complete", False))
            self.manual_queue=[
                str(p) for p in d.get("manual_queue", [])
                if str(p).strip()
            ][:500]
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
                "auto_next":self.auto_next_enabled,
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
                "listen_seconds":self.listen_seconds,
                "language":self.language,
                "region":self.region,
                "setup_complete":self.setup_complete,
                "manual_queue":self.manual_queue[:500]
            },ensure_ascii=False, indent=2),encoding="utf-8")
        except Exception: pass
    def imported_music_dir(self):
        return Path(self.user_data_dir) / "Helyi_Zenek"

    def downloaded_music_dir(self):
        return Path(self.user_data_dir) / "Archive_Letoltesek"

    @staticmethod
    def _safe_file_name(filename):
        name = str(filename or "hangfelvetel.mp3").replace("\\", "/").split("/")[-1]
        name = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", name).strip(" .")
        return name[:160] or "hangfelvetel.mp3"

    @staticmethod
    def _unused_target(folder, filename):
        folder.mkdir(parents=True, exist_ok=True)
        filename = JustMusicApp._safe_file_name(filename)
        base, suffix = os.path.splitext(filename)
        candidate = folder / filename
        n=2
        while candidate.exists():
            candidate=folder / f"{base[:125]} ({n}){suffix}"
            n+=1
        return candidate

    def pick_local_music(self):
        """ACTION_OPEN_DOCUMENT: rendszerfájl-választó, akár sok hangfájllal."""
        if platform != "android":
            try:
                from kivy.uix.filechooser import FileChooserListView
                content=BoxLayout(orientation="vertical",spacing=dp(6))
                fc=FileChooserListView(path=str(Path.home()),multiselect=True,
                                       filters=["*.mp3","*.wav","*.ogg","*.flac","*.m4a","*.aac"])
                content.add_widget(fc)
                btn=Button(text="KIJELÖLTEK IMPORTÁLÁSA",size_hint_y=None,height=dp(45))
                content.add_widget(btn)
                popup=Popup(title="Helyi zenék hozzáadása",content=content,size_hint=(.96,.85))
                def selected(*_):
                    success=0
                    for file in fc.selection:
                        if Path(file).suffix.lower() in SUPPORTED_AUDIO:
                            target=self._unused_target(self.imported_music_dir(),Path(file).name)
                            shutil.copyfile(file,target);success+=1
                    popup.dismiss();self.scan()
                    self.show_safe_message("HELYI ZENE",f"Importálva: {success} fájl")
                btn.bind(on_release=selected);popup.open()
            except Exception as error:self.show_safe_message("HELYI ZENE",str(error))
            return
        try:
            from android import activity
            from jnius import autoclass
            Intent=autoclass("android.content.Intent")
            PythonActivity=autoclass("org.kivy.android.PythonActivity")
            activity.unbind(on_activity_result=self._on_local_file_result)
            activity.bind(on_activity_result=self._on_local_file_result)
            intent=Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("audio/*")
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            PythonActivity.mActivity.startActivityForResult(intent,self._local_file_request_code)
        except Exception as error:
            print("HELYI ZENE PICKER HIBA:",error)
            self.show_safe_message("HELYI ZENE", "Nem sikerült megnyitni a fájlválasztót: "+str(error)[:140])

    def _on_local_file_result(self, request_code, result_code, intent):
        if request_code != self._local_file_request_code:return
        try:
            from android import activity
            activity.unbind(on_activity_result=self._on_local_file_result)
        except Exception:pass
        if result_code != -1 or intent is None:return
        try:
            uri_list=[]
            clip=intent.getClipData()
            if clip is not None:
                for i in range(min(100,int(clip.getItemCount()))):
                    uri_list.append(str(clip.getItemAt(i).getUri().toString()))
            elif intent.getData() is not None:
                uri_list.append(str(intent.getData().toString()))
            if not uri_list:return
            self.show_safe_message("HELYI ZENE",f"Importálás elindult: {len(uri_list)} fájl.")
            def worker():
                count=0;errors=[]
                for uri in uri_list:
                    try:
                        if self._import_android_uri(uri):count+=1
                    except Exception as exc: errors.append(str(exc)[:75])
                def finished(_dt):
                    self.scan()
                    text=f"Sikeresen hozzáadva: {count} zenefájl."
                    if errors:text += "\nHibák: " + "; ".join(errors[:2])
                    self.show_safe_message("HELYI ZENE",text)
                Clock.schedule_once(finished,0)
            threading.Thread(target=worker,daemon=True).start()
        except Exception as error:
            print("HELYI ZENE VÁLASZTÁS HIBA:",error)

    def _import_android_uri(self, uri_text):
        from jnius import autoclass
        Uri=autoclass("android.net.Uri")
        PythonActivity=autoclass("org.kivy.android.PythonActivity")
        OpenableColumns=autoclass("android.provider.OpenableColumns")
        resolver=PythonActivity.mActivity.getContentResolver()
        uri=Uri.parse(uri_text)
        name="hangfelvetel.mp3"
        cursor=None
        try:
            cursor=resolver.query(uri,None,None,None,None)
            if cursor is not None and cursor.moveToFirst():
                idx=cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if idx>=0:name=str(cursor.getString(idx))
        finally:
            if cursor is not None:cursor.close()
        if not name.lower().endswith(SUPPORTED_AUDIO):
            raise ValueError("Nem támogatott hangformátum: "+name[:45])
        dest=self._unused_target(self.imported_music_dir(),name)
        # Buffer másolás: az Android provider content:// URI-ját kell olvasni,
        # nem lehet azt egyszerű fájlútvonalként használni.
        input_stream=resolver.openInputStream(uri)
        if input_stream is None: raise IOError("A fájl nem olvasható.")
        try:
            buf=bytearray(65536)
            with dest.open("wb") as out:
                total=0
                while True:
                    amount=int(input_stream.read(buf))
                    if amount<0:break
                    if amount==0:continue
                    total+=amount
                    if total>550_000_000:raise ValueError("Túl nagy fájl (>550 MB)")
                    out.write(buf[:amount])
            if dest.stat().st_size==0:raise ValueError("Üres fájl")
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        finally:
            input_stream.close()
        return True

    def download_archive_track(self, identifier, filename, status_callback):
        """Letöltés csak a kiválasztott, ellenőrzött CC / közkincs Archive elemről."""
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",str(identifier)):
            return
        if not str(filename).lower().endswith(SUPPORTED_AUDIO):return
        # Ne fogadjunk el tetszőleges URL-t vagy külső domain-t.
        url="https://archive.org/download/"+urllib.parse.quote(identifier)+"/"+urllib.parse.quote(filename,safe="/")
        target=self._unused_target(self.downloaded_music_dir(),Path(filename).name)
        def progress(message):
            Clock.schedule_once(lambda _dt:status_callback(message),0)
        progress("Letöltés indul: "+target.name[:48])
        def worker():
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"JustMusic-Mobile/1.8.6"})
                total=0; last_report=0
                with urllib.request.urlopen(req,timeout=40) as response, target.open("wb") as output:
                    while True:
                        chunk=response.read(128*1024)
                        if not chunk:break
                        total+=len(chunk)
                        if total>550_000_000:raise ValueError("A fájl túl nagy (550 MB felett)")
                        output.write(chunk)
                        if total-last_report>=2_000_000:
                            last_report=total
                            progress(f"Letöltés: {total/1_048_576:.1f} MB")
                if total<100:raise ValueError("Nem érkezett használható zenefájl.")
                progress(f"KÉSZ! {target.name[:35]} • {total/1_048_576:.1f} MB")
                Clock.schedule_once(lambda _dt:self.scan(),0)
            except Exception as error:
                target.unlink(missing_ok=True)
                progress("Archive hiba: "+str(error)[:95])
        threading.Thread(target=worker,daemon=True).start()

    def request_notification_permission(self, auto=False):
        if platform!="android":return
        if auto and self._notification_permission_attempted:return
        self._notification_permission_attempted=True
        try:
            from jnius import autoclass
            Version=autoclass("android.os.Build$VERSION")
            if Version.SDK_INT < 33:return
            PythonActivity=autoclass("org.kivy.android.PythonActivity")
            activity=PythonActivity.mActivity
            perm="android.permission.POST_NOTIFICATIONS"
            if activity.checkSelfPermission(perm)==0:return
            from android.permissions import request_permissions
            def permission_result(_permissions, grants):
                if any(bool(granted) for granted in (grants or [])):
                    Clock.schedule_once(lambda _dt: self.show_android_notification(
                        clean_title(self.current_path), self.audio.is_playing()
                    ) if self.current_path else None, 0)
            self._notification_permission_callback = permission_result
            request_permissions([perm], self._notification_permission_callback)
        except BaseException as error:print("NOTIFIKÁCIÓ ENGEDÉLYKÉRÉS HIBA:",error)

    def open_notification_access(self):
        """REV5: közvetlen értesítési oldal helyett a saját app adatlapját nyissa.

        Az ACTION_APP_NOTIFICATION_SETTINGS egyes Android-gyártóknál az
        'alkalmazás nem található' hibát mutatja. A hivatalosan támogatott
        ACTION_APPLICATION_DETAILS_SETTINGS + package: URI útvonalat használjuk.
        A média-zárképernyő megjelenéséhez nincs külön runtime engedély.
        """
        help_text = (
            "A JustMusic! alkalmazásinformációs lapján nyisd meg az "
            "Értesítések részt, engedélyezd a lejátszási értesítéseket "
            "és a zárolt képernyőn való megjelenítést. "
            "Az Akkumulátor résznél a háttérműködést is engedélyezd. "
            "A zárképernyős médiakártya csak elindított zenénél jelenhet meg."
        )
        if platform != "android":
            self.show_safe_message("ZÁRKÉPERNYŐ", help_text)
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            BuildVersion = autoclass("android.os.Build$VERSION")
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            if activity is None:
                raise RuntimeError("Android activity még nem elérhető")
            package_name = str(activity.getPackageName())

            # Android 13+: az értesítési engedély hiánya esetén először a
            # valódi rendszer-engedélykérő ablakot mutassuk, ne egy Settings
            # átirányítás fedje le a párbeszédet.
            notification_perm = "android.permission.POST_NOTIFICATIONS"
            if (BuildVersion.SDK_INT >= 33 and
                    activity.checkSelfPermission(notification_perm) != 0 and
                    not self._user_notification_permission_requested):
                self._user_notification_permission_requested = True
                self.request_notification_permission(auto=False)
                return
            # Második koppintáskor a rendszer appadatlapjára lépünk akkor is,
            # ha az első engedélykérést a felhasználó elutasította.

            # Stabilabb gyártófüggetlen út: JustMusic! -> Alkalmazásinformációk.
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(Uri.parse("package:" + package_name))
            activity.startActivity(intent)
        except BaseException as error:
            print("JUSTMUSIC APP DETAILS HIBA:", error)
            try:
                # Egyes gyártók még az app-adatlapot sem tudják megnyitni.
                # Ilyenkor legalább a telepített alkalmazások listája nyíljon meg.
                activity.startActivity(Intent(Settings.ACTION_APPLICATION_SETTINGS))
                return
            except BaseException as fallback_error:
                print("JUSTMUSIC APP LIST HIBA:", fallback_error)
            self.show_safe_message("ZÁRKÉPERNYŐ / SÚGÓ", help_text)

    def update_playback_wake_lock(self, playing):
        """Képernyő kikapcsolásakor maradjon futó a lejátszó, amíg aktív."""
        if platform!="android":return
        try:
            if playing:
                if self._playback_wake_lock is None:
                    from jnius import autoclass
                    PythonActivity=autoclass("org.kivy.android.PythonActivity")
                    Context=autoclass("android.content.Context")
                    PowerManager=autoclass("android.os.PowerManager")
                    manager=PythonActivity.mActivity.getSystemService(Context.POWER_SERVICE)
                    self._playback_wake_lock=manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,
                                                               "JustMusic:Playback")
                    self._playback_wake_lock.setReferenceCounted(False)
                if not self._playback_wake_lock.isHeld():self._playback_wake_lock.acquire()
            elif self._playback_wake_lock is not None and self._playback_wake_lock.isHeld():
                self._playback_wake_lock.release()
        except BaseException as error:
            print("WAKE LOCK HIBA:",error)

    def permissions(self):
        if platform!="android":return
        try:
            from android.permissions import request_permissions
            request_permissions([
                "android.permission.READ_MEDIA_AUDIO",
                "android.permission.READ_EXTERNAL_STORAGE",
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.BLUETOOTH_SCAN",
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
        if self._scan_in_progress:
            self._scan_pending = True
            return
        self._scan_in_progress = True
        self._scan_pending = False
        try:
            self.library.refresh_list()
        except Exception:
            pass
        roots = list(self.music_roots())
        roots += [str(self.imported_music_dir()), str(self.downloaded_music_dir())]

        def worker():
            found = {}
            try:
                for root in roots:
                    if not os.path.isdir(root):
                        continue
                    for folder, _, files in os.walk(root):
                        for filename in files:
                            if filename.lower().endswith(SUPPORTED_AUDIO):
                                path = os.path.join(folder, filename)
                                try:key = os.path.realpath(path).lower()
                                except Exception:key = path.lower()
                                found[key] = path
                songs = sorted(found.values(), key=lambda p: clean_title(p).lower())
            except Exception as error:
                print("ZENETÁR SCAN HIBA:", error)
                songs = []
            Clock.schedule_once(lambda *_: self._finish_scan(songs), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_scan(self, songs):
        self.songs = list(songs)
        self._scan_in_progress = False
        try:self.library.refresh_list()
        except Exception as error:print("LIBRARY REFRESH HIBA:", error)

        if self.restore_path:
            path = self.restore_path
            position = self.restore_position
            self.restore_path = ""
            self.restore_position = 0.0
            self.restore_last_track(path, position)

        if self._scan_pending:
            self._scan_pending = False
            Clock.schedule_once(lambda *_: self.scan(), .1)
    def clean_manual_queue(self):
        if not self.manual_queue:
            return
        self.manual_queue = [
            p for p in self.manual_queue
            if p in self.songs and os.path.exists(p)
        ]

    def add_to_queue(self, path):
        if path and path in self.songs:
            self.manual_queue.append(path)
            self.save_settings()
            try:
                if self.manager.has_screen("queue"):
                    self.manager.get_screen("queue").refresh()
            except Exception:
                pass

    def add_play_next(self, path):
        if path and path in self.songs:
            self.manual_queue = [p for p in self.manual_queue if p != path]
            self.manual_queue.insert(0, path)
            self.save_settings()
            try:
                if self.manager.has_screen("queue"):
                    self.manager.get_screen("queue").refresh()
            except Exception:
                pass

    def queue_snapshot(self):
        self.clean_manual_queue()
        if self.manual_queue:
            return list(self.manual_queue)
        if not self.songs:
            return []
        if self.current_index < 0:
            return list(self.songs)
        return self.songs[self.current_index:] + self.songs[:self.current_index]

    def manual_next_index(self):
        self.clean_manual_queue()
        while self.manual_queue:
            path = self.manual_queue[0]
            try:
                return self.songs.index(path)
            except ValueError:
                self.manual_queue.pop(0)
        return -1

    def consume_manual_queue_target(self, index):
        if not (0 <= index < len(self.songs)):
            return
        path = self.songs[index]
        if self.manual_queue and self.manual_queue[0] == path:
            self.manual_queue.pop(0)
            self.save_settings()

    def next_index(self):
        if not self.songs:return -1
        if self.repeat_mode=="one" and self.current_index>=0:return self.current_index
        manual = self.manual_next_index()
        if manual >= 0:
            return manual
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
            self._playing_expected = False

        except Exception as error:
            print("UTOLSÓ DAL VISSZAÁLLÍTÁSI HIBA:", error)

    def open_playlist(self, name):
        self.playlist_tracks_screen.set_playlist(name)
        self.manager.current = "playlist_tracks"

    def show_safe_message(self, title, message):
        try:
            content = BoxLayout(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(10)
            )
            content.add_widget(Label(
                text=str(message),
                color=TEXT,
                halign="center",
                valign="middle"
            ))
            close = Button(
                text="OK",
                size_hint_y=None,
                height=dp(48),
                background_normal="",
                background_color=ACCENT,
                color=(0, .07, .12, 1),
                bold=True
            )
            content.add_widget(close)
            popup = Popup(
                title=str(title),
                content=content,
                size_hint=(.88, .55)
            )
            close.bind(on_release=lambda *_: popup.dismiss())
            popup.open()
        except BaseException as error:
            print("SAFE MESSAGE HIBA:", error)

    def show_first_setup(self, *_):
        """
        First-run selector. It is intentionally delayed until the main UI is already alive.
        Any failure here is caught and cannot kill application startup.
        """
        if self.setup_complete:
            return

        try:
            auto_lang, auto_region = detect_system_locale_safe()
            selected = {
                "language": auto_lang,
                "region": auto_region,
            }

            box = BoxLayout(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(8)
            )

            title = Label(
                text=ui_text(self, "welcome"),
                color=TEXT,
                bold=True,
                font_size="22sp",
                size_hint_y=None,
                height=dp(42)
            )
            subtitle = Label(
                text=ui_text(self, "welcome_sub"),
                color=TEXT_2,
                size_hint_y=None,
                height=dp(36)
            )
            box.add_widget(title)
            box.add_widget(subtitle)

            box.add_widget(Label(
                text="Nyelv / Language",
                color=ACCENT_2,
                bold=True,
                size_hint_y=None,
                height=dp(28)
            ))

            lwrap = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(100),
                spacing=dp(5)
            )
            l1 = BoxLayout(spacing=dp(5))
            l2 = BoxLayout(spacing=dp(5))
            lwrap.add_widget(l1)
            lwrap.add_widget(l2)
            language_buttons = {}

            def refresh_language_buttons():
                for code, button in language_buttons.items():
                    active = code == selected["language"]
                    button.background_color = ACCENT if active else PANEL_2
                    button.color = (0, .07, .12, 1) if active else TEXT

            def choose_language(code):
                selected["language"] = code
                self.language = code
                title.text = ui_text(self, "welcome")
                subtitle.text = ui_text(self, "welcome_sub")
                save.text = ui_text(self, "continue")
                refresh_language_buttons()

            for idx, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
                b = Button(
                    text=name,
                    background_normal="",
                    background_color=PANEL_2,
                    color=TEXT,
                    font_size="10sp",
                    bold=True
                )
                b.bind(on_release=lambda _, c=code: choose_language(c))
                (l1 if idx < 3 else l2).add_widget(b)
                language_buttons[code] = b

            box.add_widget(lwrap)

            box.add_widget(Label(
                text="Régió / Region",
                color=ACCENT_2,
                bold=True,
                size_hint_y=None,
                height=dp(28)
            ))

            rwrap = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(100),
                spacing=dp(5)
            )
            r1 = BoxLayout(spacing=dp(5))
            r2 = BoxLayout(spacing=dp(5))
            rwrap.add_widget(r1)
            rwrap.add_widget(r2)
            region_buttons = {}

            def refresh_region_buttons():
                for code, button in region_buttons.items():
                    active = code == selected["region"]
                    button.background_color = ACCENT if active else PANEL_2
                    button.color = (0, .07, .12, 1) if active else TEXT

            def choose_region(code):
                selected["region"] = code
                refresh_region_buttons()

            for idx, (code, name) in enumerate(SUPPORTED_REGIONS.items()):
                b = Button(
                    text=name,
                    background_normal="",
                    background_color=PANEL_2,
                    color=TEXT,
                    font_size="9sp",
                    bold=True
                )
                b.bind(on_release=lambda _, c=code: choose_region(c))
                (r1 if idx < 3 else r2).add_widget(b)
                region_buttons[code] = b

            box.add_widget(rwrap)

            save = Button(
                text=ui_text(self, "continue"),
                size_hint_y=None,
                height=dp(54),
                background_normal="",
                background_color=ACCENT,
                color=(0, .07, .12, 1),
                bold=True
            )
            box.add_widget(save)

            popup = Popup(
                title="JustMusic!",
                content=box,
                size_hint=(.94, .88),
                auto_dismiss=False
            )

            def finish(*_):
                self.language = selected["language"]
                self.region = selected["region"]
                self.setup_complete = True
                self.save_settings()
                popup.dismiss()

            save.bind(on_release=finish)
            refresh_language_buttons()
            refresh_region_buttons()
            popup.open()

        except BaseException as error:
            print("FIRST SETUP HIBA:", error)

    def check_for_updates(self):
        try:
            if not self.manager.has_screen("updates"):
                self.ensure_extra_screen("updates")
            if self.updates_screen is not None:
                self.updates_screen.status.text = ui_text(self, "checking")
                self.updates_screen.download.disabled = True
        except BaseException as error:
            print("UPDATE SCREEN PREP HIBA:", error)

        def worker():
            try:
                request = urllib.request.Request(
                    GITHUB_LATEST_API,
                    headers={
                        "User-Agent": f"JustMusic-Mobile/{APP_VERSION}",
                        "Accept": "application/vnd.github+json",
                    }
                )
                with urllib.request.urlopen(request, timeout=15) as response:
                    release = json.loads(
                        response.read().decode("utf-8", errors="replace")
                    )

                tag = str(release.get("tag_name") or "")
                latest = version_tuple(tag)
                current = version_tuple(APP_VERSION)

                latest_text = ".".join(str(x) for x in latest)
                release_url = str(release.get("html_url") or "")
                download_url = ""

                for asset in release.get("assets", []) or []:
                    name = str(asset.get("name") or "").lower()
                    if name.endswith(".apk") and "arm64-v8a" in name:
                        download_url = str(
                            asset.get("browser_download_url") or ""
                        )
                        break

                def finish(*_):
                    self.latest_version = latest_text
                    self.latest_release_url = release_url
                    self.latest_download_url = download_url or release_url
                    try:
                        if self.updates_screen is not None:
                            self.updates_screen.show_result(
                                latest_text,
                                latest > current
                            )
                    except BaseException as error:
                        print("UPDATE UI HIBA:", error)

                Clock.schedule_once(finish, 0)

            except BaseException as error:
                message = str(error)

                def failed(*_):
                    try:
                        self.updates_screen.status.text = (
                            "Update checker hiba:\\n" + message
                        )
                    except Exception:
                        pass

                Clock.schedule_once(failed, 0)

        threading.Thread(target=worker, daemon=True).start()

    def open_url(self, url):
        url = str(url or "").strip()
        if not url:
            return
        try:
            if platform == "android":
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                PythonActivity.mActivity.startActivity(intent)
            else:
                import webbrowser
                webbrowser.open(url)
        except BaseException as error:
            print("URL OPEN HIBA:", error)

    def open_latest_update(self):
        self.open_url(self.latest_download_url or self.latest_release_url)

    def _music_service_state_path(self):
        return Path(self.user_data_dir) / "justmusic_media_state.json"

    def _publish_music_service_state(self, playing=None, shutdown=False):
        """Cross-process state for the Android mediaPlayback foreground service.

        The Kivy UI retains its existing MediaPlayer, mixer and auto-next logic;
        the service owns the Android media notification/session. No dummy
        lockscreen permission dialog or browser handoff is needed.
        """
        if platform != "android":
            return False
        try:
            path = self._music_service_state_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._music_service_seq += 1
            info = track_metadata(self.current_path) if self.current_path else {}
            data = {
                "seq": self._music_service_seq,
                "shutdown": bool(shutdown),
                "playing": bool(self.audio.is_playing() if playing is None else playing),
                "title": str(info.get("title") or "JustMusic!"),
                "artist": str(info.get("artist") or "Ismeretlen előadó"),
                "album": str(info.get("album") or ""),
                "cover": str(cover_for_track(self.current_path) or "") if self.current_path else "",
                "position_ms": int(max(0., self.audio.position()) * 1000) if self.current_path else 0,
                "duration_ms": int(max(0., self.audio.duration()) * 1000) if self.current_path else 0,
            }
            # Atomic replace prevents half-read JSON in the other Android process.
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(str(temp), str(path))
            if shutdown:
                return True
            if self._music_service_started:
                # Never suppress the old notification forever if the service
                # crashes or was stopped by a vendor's battery policy.
                heartbeat = Path(str(path) + ".heartbeat")
                if heartbeat.exists():
                    fresh = time.time() - heartbeat.stat().st_mtime < 14.0
                else:
                    fresh = time.time() - self._music_service_launch_time < 10.0
                if fresh:
                    return True
                self._music_service_started = False
                print("JUSTMUSIC SERVICE NEM VALASZOL, VISSZAALLAS A REGI ERTESITESRE")
                return False
            from jnius import autoclass
            service_cls = autoclass("hu.zs420ller.justmusic.ServiceMusic")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            service_cls.start(activity, str(path))
            self._music_service_started = True
            self._music_service_launch_time = time.time()
            print("JUSTMUSIC FOREGROUND MEDIA SERVICE ELINDULT")
            # Az első indításnál még nem biztos, hogy a háttérszolgáltatás
            # létrehozta a saját médiaértesítését. Ilyenkor a hívó fél NE
            # nyelje el azonnal a régi notificationt, különben a felhasználó
            # nem lát semmit a zárolt képernyőn.
            return False
        except BaseException as error:
            print("JUSTMUSIC SERVICE BRIDGE HIBA:", error)
            return False

    def setup_android_media_controls(self):
        """
        Media intent listener is attached ONLY after the user starts playback.
        It is not part of startup and can fail safely without closing the app.
        """
        if platform != "android" or self._media_intent_bound:
            return False
        try:
            from android import activity
            activity.bind(on_new_intent=self.on_android_media_intent)
            self._media_intent_bound = True
            return True
        except BaseException as error:
            print("MEDIA INTENT BIND HIBA:", error)
            self._media_intent_bound = False
            return False

    def on_android_media_intent(self, intent):
        try:
            action = str(intent.getAction() or "")
        except BaseException:
            return

        if action == MEDIA_ACTION_PREVIOUS:
            Clock.schedule_once(lambda *_: self.previous(), 0)
        elif action == MEDIA_ACTION_TOGGLE:
            Clock.schedule_once(lambda *_: self.toggle_play(), 0)
        elif action == MEDIA_ACTION_NEXT:
            Clock.schedule_once(lambda *_: self.next_pressed(), 0)

    def _media_pending_intent(self, action, request_code):
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        BuildVersion = autoclass("android.os.Build$VERSION")

        activity = PythonActivity.mActivity
        intent = Intent(activity, PythonActivity)
        intent.setAction(action)
        intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)

        flags = PendingIntent.FLAG_UPDATE_CURRENT
        if BuildVersion.SDK_INT >= 23:
            flags |= PendingIntent.FLAG_IMMUTABLE

        return PendingIntent.getActivity(
            activity,
            int(request_code),
            intent,
            flags
        )

    def _content_pending_intent(self):
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        BuildVersion = autoclass("android.os.Build$VERSION")

        activity = PythonActivity.mActivity
        intent = Intent(activity, PythonActivity)
        intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)

        flags = PendingIntent.FLAG_UPDATE_CURRENT
        if BuildVersion.SDK_INT >= 23:
            flags |= PendingIntent.FLAG_IMMUTABLE

        return PendingIntent.getActivity(activity, 4200, intent, flags)

    def update_android_media_state(self, playing, position=None):
        """Update the Android MediaSession position (lock-screen progress)."""
        if platform != "android" or self._media_session is None:
            return
        try:
            from jnius import autoclass
            PlaybackState = autoclass("android.media.session.PlaybackState")
            actions = (PlaybackState.ACTION_PLAY | PlaybackState.ACTION_PAUSE |
                       PlaybackState.ACTION_PLAY_PAUSE |
                       PlaybackState.ACTION_SKIP_TO_NEXT |
                       PlaybackState.ACTION_SKIP_TO_PREVIOUS |
                       PlaybackState.ACTION_SEEK_TO)
            if position is None:
                position = self.audio.position()
            state = autoclass("android.media.session.PlaybackState$Builder")()
            state.setActions(actions)
            state.setState(PlaybackState.STATE_PLAYING if playing else
                           PlaybackState.STATE_PAUSED, int(max(0.0, position) * 1000),
                           1.0 if playing else 0.0)
            self._media_session.setPlaybackState(state.build())
        except BaseException as error:
            print("MEDIASESSION PLAYBACK STATE SKIP:", error)

    def update_android_media_session(self, playing, info, bitmap=None):
        """Expose the current song/cover/playback to Android's media controls."""
        if platform != "android":
            return
        try:
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            if activity is None:
                return
            if self._media_session is None:
                MediaSession = autoclass("android.media.session.MediaSession")
                session = MediaSession(activity, "JustMusic!")
                try:
                    session.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS |
                                     MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS)
                except BaseException:
                    pass
                try:
                    session.setSessionActivity(self._content_pending_intent())
                except BaseException:
                    pass
                session.setActive(True)
                self._media_session = session

            MediaMetadata = autoclass("android.media.MediaMetadata")
            meta = autoclass("android.media.MediaMetadata$Builder")()
            meta.putString(MediaMetadata.METADATA_KEY_TITLE,
                           str(info.get("title") or "JustMusic!"))
            meta.putString(MediaMetadata.METADATA_KEY_DISPLAY_TITLE,
                           str(info.get("title") or "JustMusic!"))
            meta.putString(MediaMetadata.METADATA_KEY_DISPLAY_SUBTITLE,
                           str(info.get("artist") or "Ismeretlen előadó"))
            meta.putString(MediaMetadata.METADATA_KEY_ARTIST,
                           str(info.get("artist") or "Ismeretlen előadó"))
            meta.putString(MediaMetadata.METADATA_KEY_ALBUM,
                           str(info.get("album") or ""))
            meta.putLong(MediaMetadata.METADATA_KEY_DURATION,
                         int(max(0.0, self.audio.duration()) * 1000))
            if bitmap is not None:
                meta.putBitmap(MediaMetadata.METADATA_KEY_ART, bitmap)
                meta.putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART, bitmap)
            self._media_session.setMetadata(meta.build())
            self.update_android_media_state(playing)
        except BaseException as error:
            # Notification buttons still work through PendingIntents if this fails.
            print("MEDIASESSION INIT SKIP:", error)

    def show_android_notification(self, title, playing=True):
        if platform != "android":
            return
        self.update_playback_wake_lock(bool(playing))
        if playing:
            self.request_notification_permission(auto=True)
        # Android 14+ mediaPlayback foreground service: durable media session.
        # If a vendor/toolchain rejects service startup, keep old notification.
        if self._publish_music_service_state(playing=playing):
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
            Notification = autoclass("android.app.Notification")
            android_R_drawable = autoclass("android.R$drawable")

            activity = PythonActivity.mActivity
            if activity is None:
                return

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

            info = (
                track_metadata(self.current_path)
                if self.current_path
                else {"artist": "JustMusic!", "album": ""}
            )

            builder.setSmallIcon(android_R_drawable.ic_media_play)
            builder.setContentTitle(str(info.get("title") or title or "JustMusic!"))
            builder.setContentText(str(info.get("artist") or "JustMusic!"))
            builder.setSubText(str(info.get("album") or ""))
            builder.setOngoing(bool(playing))
            builder.setOnlyAlertOnce(True)
            builder.setCategory(Notification.CATEGORY_TRANSPORT)
            builder.setVisibility(Notification.VISIBILITY_PUBLIC)

            try:
                builder.setContentIntent(self._content_pending_intent())
            except BaseException as error:
                print("NOTIFICATION CONTENT INTENT HIBA:", error)

            cover_bitmap = None
            try:
                cover = cover_for_track(self.current_path) if self.current_path else ""
                if cover:
                    BitmapFactory = autoclass("android.graphics.BitmapFactory")
                    cover_bitmap = BitmapFactory.decodeFile(cover)
                    if cover_bitmap is not None:
                        builder.setLargeIcon(cover_bitmap)
            except BaseException as error:
                print("NOTIFICATION COVER SKIP:", error)

            # A real MediaSession makes Android's lock-screen media card aware
            # of the title, artwork, playback state and current position.
            self.update_android_media_session(playing, info, cover_bitmap)

            # Existing notification action intents: prev / play-pause / next.
            try:
                self.setup_android_media_controls()

                previous_pi = self._media_pending_intent(
                    MEDIA_ACTION_PREVIOUS, 4201
                )
                toggle_pi = self._media_pending_intent(
                    MEDIA_ACTION_TOGGLE, 4202
                )
                next_pi = self._media_pending_intent(
                    MEDIA_ACTION_NEXT, 4203
                )

                builder.addAction(
                    android_R_drawable.ic_media_previous,
                    "Previous",
                    previous_pi
                )
                builder.addAction(
                    android_R_drawable.ic_media_pause
                    if playing
                    else android_R_drawable.ic_media_play,
                    "Pause" if playing else "Play",
                    toggle_pi
                )
                builder.addAction(
                    android_R_drawable.ic_media_next,
                    "Next",
                    next_pi
                )

                try:
                    MediaStyle = autoclass(
                        "android.app.Notification$MediaStyle"
                    )
                    style = MediaStyle()
                    if self._media_session is not None:
                        style.setMediaSession(self._media_session.getSessionToken())
                    try:
                        style.setShowActionsInCompactView([0, 1, 2])
                    except BaseException as error:
                        print("MEDIASTYLE COMPACT SKIP:", error)
                    builder.setStyle(style)
                except BaseException as error:
                    print("MEDIASTYLE SKIP:", error)

            except BaseException as error:
                print("MEDIA ACTION SKIP:", error)

            manager.notify(420, builder.build())

        except BaseException as error:
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
        self._playing_expected = True
        self.audio.start();self.audio.apply_eq(self.eq_values);self.apply_volume();self.library.player.set_playing(True);self.refresh_lyrics(True)
        try:
            self.setup_android_media_controls()
        except BaseException as error:
            print("MEDIA CONTROL INIT SKIP:", error)
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
            self._playing_expected = False
            self.audio.pause()
            self.library.player.set_playing(False)
            self.show_android_notification(
                clean_title(self.current_path),
                False
            )
            self.save_settings()
        else:
            self.audio.completed = False
            self._playing_expected = True
            # Resume at the actual saved position (not an old value).
            self.audio.seek(self.paused_position)
            self.audio.start()
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
        i=self.next_index()
        if i>=0:
            self.consume_manual_queue_target(i)
            self.play_index(i)
        else:
            self._playing_expected = False
            self.audio.pause()
            self.library.player.set_playing(False)
            if self.current_path:
                self.show_android_notification(clean_title(self.current_path), False)
    def on_audio_completed(self):
        """Advance exactly once after natural completion, if AUTO is enabled."""
        if not self._playing_expected or self.mix_in_progress or not self.current_path:
            return
        self._playing_expected = False  # guard against duplicate Java/tick callbacks
        self.audio.completed = False
        if self.auto_next_enabled:
            self.next()
        else:
            self.library.player.set_playing(False)
            self.show_android_notification(clean_title(self.current_path), False)

    def toggle_auto_next(self):
        self.auto_next_enabled = not self.auto_next_enabled
        self.library.refresh_auto_next_button()
        self.save_settings()

    def toggle_shuffle(self):self.shuffle_enabled=not self.shuffle_enabled;self.library.player.set_shuffle(self.shuffle_enabled);self.save_settings()
    def cycle_repeat(self):
        seq=["off","all","one"];self.repeat_mode=seq[(seq.index(self.repeat_mode)+1)%3];self.library.player.set_repeat(self.repeat_mode);self.save_settings()
    def seek_to(self,s):self.audio.seek(s)
    def show_library(self):self.manager.current="library"
    def open_lyrics(self):
        try:self.lyrics_screen.rebuild_lyrics()
        except Exception:pass
        self.refresh_lyrics(True);self.manager.current="lyrics"
    def ensure_extra_screen(self, name):
        """
        Create v1.7/v1.8 screens only when the user opens them.
        Any construction error is caught so it cannot kill JustMusic startup.
        """
        if self.manager.has_screen(name):
            return True

        factories = {
            "settings": SettingsScreen,
            "language_region": LanguageRegionScreen,
            "updates": UpdatesScreen,
            "about": AboutScreen,
        }

        screen_class = factories.get(name)
        if screen_class is None:
            return False

        try:
            screen = screen_class(name=name)
            self.manager.add_widget(screen)

            if name == "settings":
                self.settings_screen = screen
            elif name == "language_region":
                self.language_region_screen = screen
            elif name == "updates":
                self.updates_screen = screen
            elif name == "about":
                self.about_screen = screen

            return True

        except BaseException as error:
            print("EXTRA SCREEN INIT HIBA:", name, error)
            self.show_safe_message(
                "JustMusic!",
                f"A(z) {name} menü most nem nyitható meg.\n\n{error}"
            )
            return False

    def open_screen(self, n):
        if n in {"settings", "language_region", "updates", "about"}:
            if not self.ensure_extra_screen(n):
                return
        if self.manager.has_screen(n):
            self.manager.current = n


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

        queued_target = (
            bool(self.manual_queue)
            and self.manual_queue[0] == self.songs[target]
        )

        # GAPLESS = PC-hez hasonlóan fade nélküli azonnali váltás.
        if self.mix_gapless_enabled:
            if queued_target:
                self.consume_manual_queue_target(target)
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
            self.mix_target_from_queue = queued_target
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
                if self.mix_target_from_queue:
                    self.consume_manual_queue_target(self.current_index)
                self._playing_expected = True
                self.show_android_notification(title, True)

            self.mix_in_progress=False
            self.mix_target_index=None
            self.mix_target_from_queue=False
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
        if now - self.last_save_tick >= 20.0:
            self.last_save_tick = now
            self.save_settings()

        if self.sleep_deadline and time.time()>=self.sleep_deadline:
            self.sleep_deadline = None
            self._playing_expected = False
            self.audio.pause()
            self.library.player.set_playing(False)
            if self.current_path:
                self.show_android_notification(clean_title(self.current_path), False)
        if self.current_path is None:return
        pos=self.audio.position();length=self.audio.duration();p=self.library.player;p.elapsed.text=fmt_time(pos);p.total.text=fmt_time(length)
        if not p.slider.dragging:p.slider.max=max(1,length);p.slider.value=min(pos,max(1,length))
        self.lyrics_screen.time.text=f"{fmt_time(pos)} / {fmt_time(length)}";self.refresh_lyrics()
        try:
            if self.manager.current=="now_playing":
                self.now_playing_screen.progress.text=f"{fmt_time(pos)} / {fmt_time(length)}"
        except Exception:pass
        playing_now = self.audio.is_playing()
        # Complete a crossfade even after the outgoing MediaPlayer has stopped.
        if self.mix_in_progress:
            self.update_crossfade()
            return
        if self._playing_expected and self.audio.completed:
            self.on_audio_completed()
            return
        # MediaPlayer.isPlaying() becomes false at the exact end. The old code
        # skipped that state, so the next track sometimes never started.
        if (self._playing_expected and not self.mix_in_progress and not playing_now
                and length > 0 and pos >= max(0, length - 0.6)):
            self.on_audio_completed()
            return
        if self._music_service_started and now - self._music_service_sync_tick >= 2.0:
            self._music_service_sync_tick = now
            self._publish_music_service_state(playing=self._playing_expected)
        if self._media_session is not None and now - self._media_state_last_sync >= 5.0:
            self._media_state_last_sync = now
            self.update_android_media_state(self._playing_expected, pos)
        if playing_now and length>0:
            rem=max(0,length-pos)
            trigger=max(self.mix_fade_out_seconds,self.mix_fade_in_seconds)
            if (
                self.audio.android
                and self.crossfade_enabled
                and self.mix_auto_transition_enabled
                and self.auto_next_enabled
                and trigger>0
                and rem<=trigger
                and not self.mix_in_progress
            ):
                self.start_next_transition(auto=True)
            if not self.mix_in_progress and rem<=.20:
                if (self.auto_next_enabled and self.mix_gapless_enabled
                        and self.mix_auto_transition_enabled):
                    self.start_next_transition(auto=True)
                else:
                    self.on_audio_completed()
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
        # Visszatéréskor frissüljön a zárképernyős értesítés is.
        if self.current_path:
            Clock.schedule_once(lambda *_: self.show_android_notification(
                clean_title(self.current_path), self.audio.is_playing()), .3)
        Clock.schedule_once(lambda *_: self.scan(), 0.8)

    def on_stop(self):
        self.save_settings()
        if platform == "android" and self._media_intent_bound:
            try:
                from android import activity
                activity.unbind(
                    on_new_intent=self.on_android_media_intent
                )
            except BaseException:
                pass
        if self._music_service_started:
            self._publish_music_service_state(playing=False, shutdown=True)
        self.update_playback_wake_lock(False)
        self.hide_android_notification()
        if self._media_session is not None:
            try:
                self._media_session.setActive(False)
                self._media_session.release()
            except BaseException:
                pass
            self._media_session = None
        self.audio.close()


if __name__ == "__main__":
    try:
        JustMusicApp().run()
    except BaseException as fatal:
        import traceback
        message = "".join(
            traceback.format_exception(
                type(fatal),
                fatal,
                fatal.__traceback__
            )
        )
        print("JUSTMUSIC FATAL STARTUP ERROR:")
        print(message)

        # Best-effort private crash log.
        try:
            crash_root = Path(
                os.environ.get("ANDROID_PRIVATE")
                or os.environ.get("HOME")
                or "."
            )
            crash_file = crash_root / "justmusic_startup_error.txt"
            crash_file.write_text(message, encoding="utf-8")
            print("Crash log:", crash_file)
        except BaseException:
            pass

        # Best-effort Android toast with the actual exception.
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass(
                    "org.kivy.android.PythonActivity"
                )
                Toast = autoclass("android.widget.Toast")
                activity = PythonActivity.mActivity
                if activity is not None:
                    short_message = (
                        "JustMusic hiba: "
                        + str(fatal)[:180]
                    )
                    Toast.makeText(
                        activity,
                        short_message,
                        Toast.LENGTH_LONG
                    ).show()
                    time.sleep(2.5)
            except BaseException:
                pass

        raise
