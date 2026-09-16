import os
import re
import json
import random
import time
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


def clean_title(path):
    name = Path(path).stem
    name = re.sub(r"[_]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "Ismeretlen szám"


def parse_lrc(audio_path):
    p = Path(audio_path).with_suffix(".lrc")
    if not p.exists():
        return []
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
        self.buttons["NEXT"].bind(on_release=lambda *_: App.get_running_app().next())
        self.buttons["REP"].bind(on_release=lambda *_: App.get_running_app().cycle_repeat())
        self.add_widget(controls)

        features = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        for text, target in (("MIX", "mix"), ("EQ", "eq"), ("RG", "rg"), ("QUEUE", "queue"), ("SLEEP", "sleep")):
            b = Button(text=text, background_normal="", background_color=(.03, .10, .17, .96), color=ACCENT_2, bold=True, font_size="10sp")
            b.bind(on_release=lambda _, n=target: App.get_running_app().open_screen(n))
            features.add_widget(b)
        self.add_widget(features)

    def set_playing(self, on): self.buttons["PLAY"].text = "PAUSE" if on else "PLAY"
    def set_shuffle(self, on): self.buttons["SHUF"].color = ACCENT_2 if on else TEXT
    def set_repeat(self, mode):
        self.buttons["REP"].text = {"off":"REP", "all":"REP ALL", "one":"REP 1"}[mode]
        self.buttons["REP"].color = ACCENT_2 if mode != "off" else TEXT


class LibraryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Image(source="party_bg.png", allow_stretch=True, keep_ratio=False))
        self.add_widget(DarkOverlay(.62))
        root = BoxLayout(orientation="vertical", padding=[dp(14), dp(15), dp(14), dp(12)], spacing=dp(8))
        brand = Label(text="[b][color=63D2FF]JustMusic![/color][/b]", markup=True, font_size="27sp", size_hint_y=None, height=dp(56), halign="left", valign="middle")
        brand.bind(size=lambda i,v: setattr(i,"text_size",(i.width,i.height))); root.add_widget(brand)
        self.search = TextInput(hint_text="Keresés a zenék között…", multiline=False, size_hint_y=None, height=dp(46), background_normal="", background_active="", background_color=(.03,.11,.19,.96), foreground_color=TEXT, hint_text_color=MUTED, cursor_color=ACCENT_2, padding=[dp(14),dp(12)])
        self.search.bind(text=lambda *_: self.refresh_list()); root.add_widget(self.search)
        p = GlassPanel(size_hint_y=None, height=dp(58), padding=[dp(13),dp(7)])
        self.status = Label(text="Zenetár betöltése…", color=TEXT_2, halign="left", valign="middle")
        self.status.bind(size=lambda i,v:setattr(i,"text_size",(i.width,i.height))); p.add_widget(self.status); root.add_widget(p)
        scroll = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None, padding=[0,dp(3),0,dp(7)])
        self.box.bind(minimum_height=self.box.setter("height")); scroll.add_widget(self.box); root.add_widget(scroll)
        self.player = PlayerBar(); root.add_widget(self.player); self.add_widget(root)

    def refresh_list(self):
        app = App.get_running_app(); self.box.clear_widgets(); q = self.search.text.strip().lower(); visible=[]
        for idx,p in enumerate(app.songs):
            title=clean_title(p)
            if not q or q in title.lower(): visible.append((idx,title))
        self.status.text = f"{len(visible)} dal • {app.backend_name}" if app.songs else "Nem találtam zenét a Music / Download mappában."
        for idx,title in visible:
            b=Button(text=title,size_hint_y=None,height=dp(55),halign="left",valign="middle",text_size=(Window.width-dp(70),None),background_normal="",background_color=CARD,color=TEXT,font_size="15sp")
            b.bind(on_release=lambda _,i=idx:app.play_index(i)); self.box.add_widget(b)


class LyricsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Image(source="party_bg.png", allow_stretch=True, keep_ratio=False)); self.add_widget(DarkOverlay(.56))
        root=BoxLayout(orientation="vertical",padding=dp(18),spacing=dp(8))
        top=BoxLayout(size_hint_y=None,height=dp(54)); back=Button(text="VISSZA",size_hint_x=None,width=dp(88),background_normal="",background_color=PANEL_2,color=TEXT,bold=True); back.bind(on_release=lambda *_:App.get_running_app().show_library())
        self.track=Label(text="[b]JustMusic! • Dalszöveg[/b]",markup=True,color=TEXT,halign="left",valign="middle"); self.track.bind(size=lambda i,v:setattr(i,"text_size",(i.width,i.height))); top.add_widget(back); top.add_widget(self.track); root.add_widget(top); root.add_widget(Widget())
        self.prev_line=self._line((.72,.86,.96,.9),"19sp"); self.current_line=self._line(TEXT,"30sp"); self.next_line=self._line((.72,.86,.96,.9),"19sp")
        root.add_widget(self.prev_line); root.add_widget(self.current_line); root.add_widget(self.next_line); root.add_widget(Widget())
        self.time=Label(text="0:00 / 0:00",size_hint_y=None,height=dp(34),color=ACCENT_2,bold=True); root.add_widget(self.time); self.add_widget(root)
    def _line(self,color,size):
        l=Label(text="",color=color,font_size=size,bold=True,halign="center",valign="middle"); l.bind(size=lambda i,v:setattr(i,"text_size",(i.width-dp(20),None))); return l


class BaseFeature(Screen):
    def make(self,title):
        self.add_widget(Image(source="party_bg.png",allow_stretch=True,keep_ratio=False)); self.add_widget(DarkOverlay(.68))
        root=BoxLayout(orientation="vertical",padding=dp(18),spacing=dp(12)); top=BoxLayout(size_hint_y=None,height=dp(54))
        back=Button(text="VISSZA",size_hint_x=None,width=dp(88),background_normal="",background_color=PANEL_2,color=TEXT,bold=True); back.bind(on_release=lambda *_:App.get_running_app().show_library())
        lab=Label(text=f"[b]{title}[/b]",markup=True,color=TEXT,font_size="23sp",halign="left",valign="middle"); lab.bind(size=lambda i,v:setattr(i,"text_size",(i.width,i.height))); top.add_widget(back); top.add_widget(lab); root.add_widget(top); self.add_widget(root); return root


class MixScreen(BaseFeature):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); r=self.make("MIX GAP / CROSSFADE"); self.value=Label(text="5.0 mp",color=ACCENT_2,font_size="28sp",size_hint_y=None,height=dp(60)); r.add_widget(self.value)
        self.slider=Slider(min=0,max=12,step=.5,value=5); self.slider.bind(value=self.changed); r.add_widget(self.slider)
        r.add_widget(Label(text="0 mp = ki • 3–7 mp = természetes • 8–12 mp = erősebb átmenet",color=TEXT_2,halign="center"))
    def on_pre_enter(self,*_): self.slider.value=App.get_running_app().mix_seconds
    def changed(self,_,v):
        a=App.get_running_app(); a.mix_seconds=float(v); self.value.text=f"{v:.1f} mp"; a.save_settings()


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
        self.title="JustMusic! Mobile v1.1"
        Window.clearcolor=BG
        self.songs=[]; self.current_index=-1; self.current_path=None; self.lyrics=[]; self.lyric_index=-1
        self.audio=NativeAudio(); self.backend_name="Android MediaPlayer" if self.audio.android else "Kivy fallback"
        self.shuffle_enabled=False; self.repeat_mode="off"; self.mix_seconds=5.0; self.mix_in_progress=False; self.mix_target_index=None
        self.eq_values=[0,0,0,0,0]; self.replaygain_enabled=True; self.user_volume=.92; self.current_rg_db=0.0; self.sleep_deadline=None; self.paused_position=0.0
        self.load_settings()
        self.manager=ScreenManager(); self.library=LibraryScreen(name="library"); self.lyrics_screen=LyricsScreen(name="lyrics")
        for s in (self.library,self.lyrics_screen,MixScreen(name="mix"),EQScreen(name="eq"),RGScreen(name="rg"),QueueScreen(name="queue"),SleepScreen(name="sleep")): self.manager.add_widget(s)
        self.library.player.set_shuffle(self.shuffle_enabled); self.library.player.set_repeat(self.repeat_mode)
        Clock.schedule_interval(self.tick,.10); Clock.schedule_once(lambda *_:self.permissions(),.4); Clock.schedule_once(lambda *_:self.scan(),1.2)
        return self.manager

    def settings_path(self): return Path("/storage/emulated/0/Music")/SETTINGS_NAME if platform=="android" else Path.home()/SETTINGS_NAME
    def load_settings(self):
        try:
            d=json.loads(self.settings_path().read_text(encoding="utf-8")); self.shuffle_enabled=bool(d.get("shuffle",False)); self.repeat_mode=d.get("repeat","off"); self.mix_seconds=float(d.get("mix",5)); self.eq_values=list(d.get("eq",[0,0,0,0,0]))[:5]; self.replaygain_enabled=bool(d.get("rg",True))
            while len(self.eq_values)<5:self.eq_values.append(0)
        except Exception: pass
    def save_settings(self):
        try:
            p=self.settings_path(); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps({"shuffle":self.shuffle_enabled,"repeat":self.repeat_mode,"mix":self.mix_seconds,"eq":self.eq_values,"rg":self.replaygain_enabled},ensure_ascii=False),encoding="utf-8")
        except Exception: pass
    def permissions(self):
        if platform!="android":return
        try:
            from android.permissions import request_permissions
            request_permissions(["android.permission.READ_MEDIA_AUDIO","android.permission.READ_EXTERNAL_STORAGE"])
        except Exception as e: print("Permission:",e)
    def scan(self):
        roots=["/storage/emulated/0/Music","/storage/emulated/0/Download"] if platform=="android" else [str(Path.home()/"Music")]
        found={}
        for root in roots:
            if not os.path.isdir(root):continue
            for folder,_,files in os.walk(root):
                for f in files:
                    if f.lower().endswith(SUPPORTED_AUDIO):
                        p=os.path.join(folder,f); found[os.path.realpath(p).lower()]=p
        self.songs=sorted(found.values(),key=lambda p:clean_title(p).lower()); self.library.refresh_list()
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
    def play_path(self,p):
        try:self.play_index(self.songs.index(p));self.show_library()
        except ValueError:pass
    def play_index(self,i):
        if not(0<=i<len(self.songs)):return
        p=self.songs[i]; self.mix_in_progress=False;self.mix_target_index=None
        try:ok=self.audio.load(p)
        except Exception as e:self.library.status.text=f"Lejátszási hiba: {e}";return
        if not ok:self.library.status.text="Ezt a fájlt nem sikerült megnyitni.";return
        self.current_index=i;self.current_path=p;self.lyrics=parse_lrc(p);self.lyric_index=-1;self.current_rg_db=replaygain_db(p)
        title=clean_title(p);self.library.player.title.text=f"[b]{title}[/b]";self.lyrics_screen.track.text=f"[b]JustMusic! • Dalszöveg[/b]\n{title}"
        self.audio.start();self.audio.apply_eq(self.eq_values);self.apply_volume();self.library.player.set_playing(True);self.refresh_lyrics(True)
    def apply_volume(self):
        gain=self.current_rg_db if self.replaygain_enabled else 0; self.audio.volume(max(0,min(1,self.user_volume*(10**(gain/20)))))
    def toggle_play(self):
        if self.current_path is None:
            if self.songs:self.play_index(0)
            return
        if self.audio.is_playing():self.paused_position=self.audio.position();self.audio.pause();self.library.player.set_playing(False)
        else:self.audio.start();self.audio.seek(self.paused_position);self.apply_volume();self.library.player.set_playing(True)
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
    def open_lyrics(self):self.refresh_lyrics(True);self.manager.current="lyrics"
    def open_screen(self,n):self.manager.current=n
    def start_crossfade(self):
        if not self.audio.android or self.mix_seconds<=0 or self.mix_in_progress:return
        target=self.next_index()
        if target<0:return
        try:
            if self.audio.prepare_next(self.songs[target]):self.audio.volume(1,0);self.audio.start_next();self.mix_in_progress=True;self.mix_target_index=target
        except Exception as e:print("Crossfade:",e);self.mix_in_progress=False
    def update_crossfade(self,remaining):
        if not self.mix_in_progress:return
        ratio=max(0,min(1,1-remaining/max(.1,self.mix_seconds)));base=max(0,min(1,self.user_volume*(10**((self.current_rg_db if self.replaygain_enabled else 0)/20))))
        self.audio.volume(base*(1-ratio),self.user_volume*ratio)
        if ratio>=.995 or remaining<=.08:
            if self.audio.swap_to_next():
                self.current_index=self.mix_target_index;self.current_path=self.songs[self.current_index];self.lyrics=parse_lrc(self.current_path);self.lyric_index=-1;self.current_rg_db=replaygain_db(self.current_path);self.audio.apply_eq(self.eq_values);self.apply_volume();t=clean_title(self.current_path);self.library.player.title.text=f"[b]{t}[/b]";self.lyrics_screen.track.text=f"[b]JustMusic! • Dalszöveg[/b]\n{t}"
            self.mix_in_progress=False;self.mix_target_index=None
    def tick(self,_):
        if self.sleep_deadline and time.time()>=self.sleep_deadline:self.sleep_deadline=None;self.audio.pause();self.library.player.set_playing(False)
        if self.current_path is None:return
        pos=self.audio.position();length=self.audio.duration();p=self.library.player;p.elapsed.text=fmt_time(pos);p.total.text=fmt_time(length)
        if not p.slider.dragging:p.slider.max=max(1,length);p.slider.value=min(pos,max(1,length))
        self.lyrics_screen.time.text=f"{fmt_time(pos)} / {fmt_time(length)}";self.refresh_lyrics()
        if self.audio.is_playing() and length>0:
            rem=max(0,length-pos)
            if self.audio.android and self.mix_seconds>0 and rem<=self.mix_seconds and not self.mix_in_progress:self.start_crossfade()
            if self.mix_in_progress:self.update_crossfade(rem)
            elif rem<=.20:self.next()
    def refresh_lyrics(self,force=False):
        if not self.lyrics:self.lyrics_screen.prev_line.text="";self.lyrics_screen.current_line.text="Nincs .lrc dalszöveg ehhez a számhoz." if self.current_path else "Indíts el egy zenét.";self.lyrics_screen.next_line.text="";return
        pos=self.audio.position();idx=-1
        for i,(ts,_) in enumerate(self.lyrics):
            if pos>=ts:idx=i
            else:break
        if not force and idx==self.lyric_index:return
        self.lyric_index=idx;cur=max(0,idx)
        line=lambda i:self.lyrics[i][1] if 0<=i<len(self.lyrics) else ""
        self.lyrics_screen.prev_line.text=line(cur-1);self.lyrics_screen.current_line.text=line(cur);self.lyrics_screen.next_line.text=line(cur+1)
    def on_stop(self):self.save_settings();self.audio.close()


if __name__ == "__main__":
    JustMusicApp().run()
