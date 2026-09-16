import os
import re
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line


BG = (0.015, 0.035, 0.075, 1)
PANEL = (0.03, 0.09, 0.15, 0.88)
PANEL_2 = (0.04, 0.13, 0.22, 0.92)
CARD = (0.04, 0.12, 0.20, 0.92)
ACCENT = (0.18, 0.68, 1.0, 1.0)
ACCENT_2 = (0.39, 0.82, 1.0, 1.0)
TEXT = (0.96, 0.98, 1.0, 1.0)
TEXT_2 = (0.68, 0.77, 0.86, 1.0)
MUTED = (0.45, 0.56, 0.66, 1.0)

SUPPORTED_AUDIO = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")


def fmt_time(seconds):
    try:
        seconds = max(0, int(seconds or 0))
    except Exception:
        seconds = 0
    return f"{seconds // 60}:{seconds % 60:02d}"


def clean_title(path):
    name = Path(path).stem
    name = re.sub(r"[_]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "Ismeretlen szám"


def parse_lrc(audio_path):
    lrc_path = Path(audio_path).with_suffix(".lrc")
    if not lrc_path.exists():
        return []

    try:
        text = lrc_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    rows = []
    for raw in text.splitlines():
        matches = re.findall(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]", raw)
        lyric = re.sub(r"\[[^\]]+\]", "", raw).strip()

        for mm, ss, fraction in matches:
            frac = 0.0
            if fraction:
                frac = int(fraction) / (1000 if len(fraction) == 3 else 100)

            rows.append((
                int(mm) * 60 + int(ss) + frac,
                lyric or "♪"
            ))

    rows.sort(key=lambda item: item[0])
    return rows


class GlassPanel(BoxLayout):
    radius = NumericProperty(dp(18))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*PANEL)
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.radius]
            )
            Color(*ACCENT, 0.40)
            self.border = Line(
                rounded_rectangle=(
                    self.x,
                    self.y,
                    self.width,
                    self.height,
                    self.radius
                ),
                width=1.1
            )

        self.bind(
            pos=self._sync_canvas,
            size=self._sync_canvas,
            radius=self._sync_canvas
        )

    def _sync_canvas(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_rect.radius = [self.radius]
        self.border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            self.radius
        )


class DarkOverlay(Widget):
    def __init__(self, opacity_value=0.54, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(0.0, 0.02, 0.05, opacity_value)
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


class PlayerBar(GlassPanel):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(6),
            size_hint_y=None,
            height=dp(142),
            **kwargs
        )

        self.info_row = BoxLayout(spacing=dp(8))
        self.title = Label(
            text="[b]JustMusic![/b]",
            markup=True,
            color=TEXT,
            halign="left",
            valign="middle",
            text_size=(None, None)
        )
        self.title.bind(
            size=lambda inst, val: setattr(
                inst, "text_size", (inst.width, None)
            )
        )

        self.lyrics_btn = Button(
            text="DALSZÖVEG",
            size_hint_x=None,
            width=dp(108),
            background_normal="",
            background_color=PANEL_2,
            color=ACCENT_2,
            bold=True
        )
        self.lyrics_btn.bind(
            on_release=lambda *_: App.get_running_app().open_lyrics()
        )

        self.info_row.add_widget(self.title)
        self.info_row.add_widget(self.lyrics_btn)
        self.add_widget(self.info_row)

        seek_row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(6))

        self.elapsed = Label(
            text="0:00",
            color=TEXT_2,
            size_hint_x=None,
            width=dp(42)
        )

        self.seek = SeekSlider(
            min=0,
            max=1,
            value=0
        )

        self.total = Label(
            text="0:00",
            color=TEXT_2,
            size_hint_x=None,
            width=dp(42)
        )

        seek_row.add_widget(self.elapsed)
        seek_row.add_widget(self.seek)
        seek_row.add_widget(self.total)
        self.add_widget(seek_row)

        controls = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8)
        )

        self.prev = self._control_button("⏮")
        self.play = self._control_button("▶", primary=True)
        self.next = self._control_button("⏭")
        self.scan = self._control_button("↻")

        self.prev.bind(on_release=lambda *_: App.get_running_app().previous())
        self.play.bind(on_release=lambda *_: App.get_running_app().toggle_play())
        self.next.bind(on_release=lambda *_: App.get_running_app().next())
        self.scan.bind(on_release=lambda *_: App.get_running_app().scan_music())

        controls.add_widget(Widget())
        controls.add_widget(self.prev)
        controls.add_widget(self.play)
        controls.add_widget(self.next)
        controls.add_widget(self.scan)
        controls.add_widget(Widget())
        self.add_widget(controls)

    def _control_button(self, text, primary=False):
        return Button(
            text=text,
            size_hint_x=None,
            width=dp(56 if primary else 48),
            background_normal="",
            background_color=ACCENT if primary else PANEL_2,
            color=(0.0, 0.07, 0.12, 1) if primary else TEXT,
            font_size="20sp",
            bold=True
        )


class LibraryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        bg = Image(
            source="party_bg.png",
            allow_stretch=True,
            keep_ratio=False
        )
        self.add_widget(bg)
        self.add_widget(DarkOverlay(opacity_value=0.62))

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(18), dp(14), dp(14)],
            spacing=dp(10)
        )

        header = BoxLayout(size_hint_y=None, height=dp(58))
        brand = Label(
            text="[b][color=63D2FF]JustMusic![/color][/b]",
            markup=True,
            font_size="28sp",
            halign="left",
            valign="middle"
        )
        brand.bind(
            size=lambda inst, val: setattr(
                inst, "text_size", (inst.width, inst.height)
            )
        )
        header.add_widget(brand)
        root.add_widget(header)

        self.search = TextInput(
            hint_text="Keresés a zenék között…",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_active="",
            background_color=(0.03, 0.11, 0.19, 0.96),
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=ACCENT_2,
            padding=[dp(14), dp(13)]
        )
        self.search.bind(text=lambda *_: self.refresh_list())
        root.add_widget(self.search)

        status_panel = GlassPanel(
            size_hint_y=None,
            height=dp(66),
            padding=[dp(14), dp(8)]
        )

        self.status = Label(
            text="Zenetár betöltése…",
            color=TEXT_2,
            halign="left",
            valign="middle"
        )
        self.status.bind(
            size=lambda inst, val: setattr(
                inst, "text_size", (inst.width, inst.height)
            )
        )
        status_panel.add_widget(self.status)
        root.add_widget(status_panel)

        self.scroll = ScrollView(do_scroll_x=False)
        self.list_box = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None,
            padding=[0, dp(4), 0, dp(8)]
        )
        self.list_box.bind(
            minimum_height=self.list_box.setter("height")
        )
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)

        self.player = PlayerBar()
        root.add_widget(self.player)

        self.add_widget(root)

    def refresh_list(self):
        app = App.get_running_app()
        if not app:
            return

        query = self.search.text.strip().lower()
        self.list_box.clear_widgets()

        visible = []
        for index, path in enumerate(app.songs):
            title = clean_title(path)
            if query and query not in title.lower():
                continue
            visible.append((index, path, title))

        self.status.text = (
            f"{len(visible)} dal"
            if app.songs
            else "Nem találtam zenét. Másolj zenéket a telefon Music mappájába, majd nyomd meg a ↻ gombot."
        )

        for index, path, title in visible:
            row = Button(
                text=f"♫   {title}",
                size_hint_y=None,
                height=dp(58),
                halign="left",
                valign="middle",
                text_size=(Window.width - dp(70), None),
                background_normal="",
                background_color=CARD,
                color=TEXT,
                font_size="16sp"
            )
            row.bind(
                on_release=lambda _, i=index: app.play_index(i)
            )
            self.list_box.add_widget(row)


class LyricsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        bg = Image(
            source="party_bg.png",
            allow_stretch=True,
            keep_ratio=False
        )
        self.add_widget(bg)
        self.add_widget(DarkOverlay(opacity_value=0.56))

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(24), dp(18), dp(18)],
            spacing=dp(8)
        )

        top = BoxLayout(size_hint_y=None, height=dp(56))

        back = Button(
            text="‹",
            size_hint_x=None,
            width=dp(54),
            background_normal="",
            background_color=(0.03, 0.11, 0.19, 0.90),
            color=TEXT,
            font_size="30sp"
        )
        back.bind(
            on_release=lambda *_: App.get_running_app().show_library()
        )

        self.track = Label(
            text="[b]JustMusic! • Dalszöveg[/b]",
            markup=True,
            color=TEXT,
            halign="left",
            valign="middle"
        )
        self.track.bind(
            size=lambda inst, val: setattr(
                inst, "text_size", (inst.width, inst.height)
            )
        )

        top.add_widget(back)
        top.add_widget(self.track)
        root.add_widget(top)

        root.add_widget(Widget())

        self.prev_line = Label(
            text="",
            color=(0.72, 0.86, 0.96, 0.90),
            font_size="20sp",
            bold=True,
            halign="center",
            valign="middle"
        )
        self.current_line = Label(
            text="Nincs dalszöveg",
            color=TEXT,
            font_size="30sp",
            bold=True,
            halign="center",
            valign="middle"
        )
        self.next_line = Label(
            text="",
            color=(0.72, 0.86, 0.96, 0.90),
            font_size="20sp",
            bold=True,
            halign="center",
            valign="middle"
        )

        for widget in (self.prev_line, self.current_line, self.next_line):
            widget.bind(
                size=lambda inst, val: setattr(
                    inst, "text_size", (inst.width - dp(20), None)
                )
            )
            root.add_widget(widget)

        root.add_widget(Widget())

        self.time = Label(
            text="0:00 / 0:00",
            size_hint_y=None,
            height=dp(34),
            color=ACCENT_2,
            bold=True
        )
        root.add_widget(self.time)

        self.add_widget(root)


class JustMusicMobileApp(App):
    def build(self):
        self.title = "JustMusic!"
        Window.clearcolor = BG

        self.songs = []
        self.current_index = -1
        self.sound = None
        self.current_path = None
        self.lyrics = []
        self.lyric_index = -1

        self.manager = ScreenManager()
        self.library_screen = LibraryScreen(name="library")
        self.lyrics_screen = LyricsScreen(name="lyrics")
        self.manager.add_widget(self.library_screen)
        self.manager.add_widget(self.lyrics_screen)

        Clock.schedule_interval(self._tick, 0.25)
        Clock.schedule_once(lambda *_: self.request_android_permissions(), 0.4)
        Clock.schedule_once(lambda *_: self.scan_music(), 1.2)

        return self.manager

    def request_android_permissions(self):
        if platform != "android":
            return

        try:
            from android.permissions import request_permissions
            request_permissions([
                "android.permission.READ_MEDIA_AUDIO",
                "android.permission.READ_EXTERNAL_STORAGE",
            ])
        except Exception as error:
            print("Permission hiba:", error)

    def music_roots(self):
        if platform == "android":
            return [
                "/storage/emulated/0/Music",
                "/storage/emulated/0/Download",
                "/sdcard/Music",
            ]

        return [
            str(Path.home() / "Music"),
            str(Path.cwd() / "music"),
        ]

    def scan_music(self):
        found = []

        for root in self.music_roots():
            if not os.path.isdir(root):
                continue

            for folder, _, files in os.walk(root):
                for filename in files:
                    if filename.lower().endswith(SUPPORTED_AUDIO):
                        found.append(os.path.join(folder, filename))

        found = sorted(set(found), key=lambda p: clean_title(p).lower())
        self.songs = found
        self.library_screen.refresh_list()

    def play_index(self, index):
        if not (0 <= index < len(self.songs)):
            return

        path = self.songs[index]

        if self.sound is not None:
            try:
                self.sound.stop()
            except Exception:
                pass
            try:
                self.sound.unload()
            except Exception:
                pass

        sound = SoundLoader.load(path)
        if sound is None:
            self.library_screen.status.text = (
                "Ezt a hangformátumot az Android lejátszó nem tudta megnyitni."
            )
            return

        self.sound = sound
        self.current_index = index
        self.current_path = path
        self.lyrics = parse_lrc(path)
        self.lyric_index = -1

        title = clean_title(path)
        self.library_screen.player.title.text = f"[b]{title}[/b]"
        self.lyrics_screen.track.text = (
            f"[b]JustMusic! • Dalszöveg[/b]\n{title}"
        )

        self.sound.play()
        self.library_screen.player.play.text = "Ⅱ"
        self._refresh_lyrics(force=True)

    def toggle_play(self):
        if self.sound is None:
            if self.songs:
                self.play_index(0)
            return

        state = getattr(self.sound, "state", "stop")

        if state == "play":
            self.sound.stop()
            self.library_screen.player.play.text = "▶"
        else:
            try:
                pos = max(0, self.library_screen.player.seek.value)
            except Exception:
                pos = 0
            self.sound.play()
            try:
                if pos > 0:
                    self.sound.seek(pos)
            except Exception:
                pass
            self.library_screen.player.play.text = "Ⅱ"

    def previous(self):
        if not self.songs:
            return
        if self.current_index < 0:
            self.play_index(0)
        else:
            self.play_index((self.current_index - 1) % len(self.songs))

    def next(self):
        if not self.songs:
            return
        if self.current_index < 0:
            self.play_index(0)
        else:
            self.play_index((self.current_index + 1) % len(self.songs))

    def seek_to(self, seconds):
        if self.sound is None:
            return
        try:
            self.sound.seek(float(seconds))
        except Exception as error:
            print("Seek hiba:", error)

    def show_library(self):
        self.manager.current = "library"

    def open_lyrics(self):
        self._refresh_lyrics(force=True)
        self.manager.current = "lyrics"

    def _current_position(self):
        if self.sound is None:
            return 0.0
        try:
            pos = self.sound.get_pos()
            return max(0.0, float(pos or 0))
        except Exception:
            return 0.0

    def _tick(self, _dt):
        if self.sound is None:
            return

        pos = self._current_position()

        try:
            length = max(0.0, float(self.sound.length or 0))
        except Exception:
            length = 0.0

        player = self.library_screen.player
        player.elapsed.text = fmt_time(pos)
        player.total.text = fmt_time(length)

        if not player.seek.dragging:
            player.seek.max = max(1, length)
            player.seek.value = min(pos, max(1, length))

        self.lyrics_screen.time.text = (
            f"{fmt_time(pos)} / {fmt_time(length)}"
        )

        self._refresh_lyrics()

        if (
            length > 0
            and pos >= length - 0.35
            and getattr(self.sound, "state", "") == "play"
        ):
            self.next()

    def _refresh_lyrics(self, force=False):
        if not self.lyrics:
            self.lyrics_screen.prev_line.text = ""
            self.lyrics_screen.current_line.text = (
                "Nincs .lrc dalszöveg ehhez a számhoz."
                if self.current_path
                else "Indíts el egy zenét."
            )
            self.lyrics_screen.next_line.text = ""
            return

        pos = self._current_position()

        index = -1
        for i, (timestamp, _) in enumerate(self.lyrics):
            if pos >= timestamp:
                index = i
            else:
                break

        if not force and index == self.lyric_index:
            return

        self.lyric_index = index

        def line(i):
            if 0 <= i < len(self.lyrics):
                return self.lyrics[i][1]
            return ""

        current = index if index >= 0 else 0
        self.lyrics_screen.prev_line.text = line(current - 1)
        self.lyrics_screen.current_line.text = line(current)
        self.lyrics_screen.next_line.text = line(current + 1)


if __name__ == "__main__":
    JustMusicMobileApp().run()
