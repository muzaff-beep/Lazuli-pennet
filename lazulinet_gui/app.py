from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from .services import RepositoryBridge

Window.clearcolor = (0.035, 0.047, 0.072, 1)

BG = (0.035, 0.047, 0.072, 1)
PANEL = (0.065, 0.082, 0.12, 1)
PANEL_2 = (0.085, 0.105, 0.15, 1)
ACCENT = (0.10, 0.55, 1.0, 1)
TEXT = (0.92, 0.95, 1.0, 1)
MUTED = (0.58, 0.66, 0.77, 1)
GOOD = (0.25, 0.85, 0.58, 1)
WARN = (1.0, 0.68, 0.25, 1)


def lbl(text="", size=15, color=TEXT, bold=False, halign="left"):
    w = Label(
        text=("[b]" + text + "[/b]") if bold else text,
        markup=True,
        font_size=dp(size),
        color=color,
        halign=halign,
        valign="middle",
    )
    w.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    return w


def btn(text, on_press=None, accent=False, height=44):
    b = Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_color=ACCENT if accent else PANEL_2,
        color=TEXT,
        font_size=dp(14),
    )
    if on_press:
        b.bind(on_press=on_press)
    return b


def panel(orientation="vertical", padding=16, spacing=10):
    return BoxLayout(
        orientation=orientation,
        padding=dp(padding),
        spacing=dp(spacing),
    )


class BaseScreen(Screen):
    title = StringProperty("")

    def __init__(self, bridge: RepositoryBridge, **kwargs):
        super().__init__(**kwargs)
        self.bridge = bridge
        self.root_box = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16))
        self.add_widget(self.root_box)

    def add_title(self, subtitle=""):
        self.root_box.add_widget(lbl(self.title, 28, bold=True))
        if subtitle:
            s = lbl(subtitle, 13, MUTED)
            s.size_hint_y = None
            s.height = dp(30)
            self.root_box.add_widget(s)


class DashboardScreen(BaseScreen):
    title = "Dashboard"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("LazuliNet operational overview")
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        actions.add_widget(btn("Refresh", self.refresh, accent=True))
        actions.add_widget(Widget())
        self.root_box.add_widget(actions)

        self.cards = GridLayout(cols=4, spacing=dp(12), size_hint_y=None, height=dp(120))
        self.root_box.add_widget(self.cards)
        self.summary = lbl("", 14, MUTED)
        self.root_box.add_widget(self.summary)
        Clock.schedule_once(lambda _dt: self.refresh(), 0)

    def refresh(self, *_):
        deps = self.bridge.dependency_status()
        ifaces = self.bridge.list_interfaces()
        nets, source = self.bridge.load_latest_networks()

        self.cards.clear_widgets()
        stats = [
            ("Platform", self.bridge.platform_name()),
            ("Privilege", self.bridge.privilege_status()),
            ("Interfaces", str(len(ifaces))),
            ("Networks", str(len(nets))),
        ]
        for name, value in stats:
            box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(4))
            box.add_widget(lbl(name, 12, MUTED))
            box.add_widget(lbl(value, 18, TEXT, bold=True))
            self.cards.add_widget(box)
        missing = [k for k, v in deps.items() if v == "missing"]
        self.summary.text = (
            f"Latest data: {source or 'no networks.json found'}\n"
            f"Dependencies missing: {', '.join(missing) if missing else 'none detected'}"
        )


class InterfacesScreen(BaseScreen):
    title = "Interfaces"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("Inspect actual OS interface state")
        self.root_box.add_widget(btn("Refresh interfaces", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.list_box = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        self.root_box.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        self.list_box.clear_widgets()
        for iface in self.bridge.list_interfaces():
            row = BoxLayout(size_hint_y=None, height=dp(72), padding=dp(12), spacing=dp(10))
            status = "UP" if iface.is_up else "DOWN"
            row.add_widget(lbl(iface.name, 16, bold=True))
            row.add_widget(lbl(iface.mode, 13, MUTED))
            row.add_widget(lbl(iface.mac_address or "—", 13, MUTED))
            row.add_widget(lbl(status, 13, GOOD if iface.is_up else WARN, bold=True, halign="right"))
            self.list_box.add_widget(row)


class DiscoveryScreen(BaseScreen):
    title = "Discovery"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("GUI-safe discovery shell")
        info = lbl(
            "This scaffold does not call the legacy scanner directly. "
            "Wire discovery through the shared TaskRunner + typed platform adapter first, "
            "so the Kivy main thread never blocks.",
            14,
            MUTED,
        )
        info.size_hint_y = None
        info.height = dp(90)
        self.root_box.add_widget(info)

        form = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(120))
        form.add_widget(lbl("Interface", 14))
        self.interface = TextInput(
            text="wlan0",
            multiline=False,
            background_normal="",
            background_active="",
            background_color=PANEL_2,
            foreground_color=TEXT,
            cursor_color=ACCENT,
            padding=(dp(12), dp(10)),
        )
        form.add_widget(self.interface)
        form.add_widget(lbl("Duration (seconds)", 14))
        self.duration = TextInput(
            text="30",
            multiline=False,
            input_filter="int",
            background_normal="",
            background_active="",
            background_color=PANEL_2,
            foreground_color=TEXT,
            cursor_color=ACCENT,
            padding=(dp(12), dp(10)),
        )
        form.add_widget(self.duration)
        self.root_box.add_widget(form)

        self.root_box.add_widget(btn("Import latest networks.json", self.import_latest, accent=True))
        self.status = lbl("Ready.", 14, MUTED)
        self.root_box.add_widget(self.status)

    def import_latest(self, *_):
        nets, source = self.bridge.load_latest_networks()
        self.status.text = f"Imported {len(nets)} observations from {source or 'no source'}."


class NetworksScreen(BaseScreen):
    title = "Networks"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("Normalized observations")
        self.root_box.add_widget(btn("Reload", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.table = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.table.bind(minimum_height=self.table.setter("height"))
        self.scroll.add_widget(self.table)
        self.root_box.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        nets, _source = self.bridge.load_latest_networks()
        self.table.clear_widgets()

        header = BoxLayout(size_hint_y=None, height=dp(42), padding=(dp(10), 0))
        for t in ("ESSID", "BSSID", "CH", "SECURITY", "SIGNAL"):
            header.add_widget(lbl(t, 11, MUTED, bold=True))
        self.table.add_widget(header)

        if not nets:
            self.table.add_widget(lbl("No observations loaded.", 14, MUTED))
            return

        for n in nets:
            row = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(10), 0))
            security = " / ".join(x for x in [n.privacy, n.cipher, n.auth] if x)
            values = (n.essid or "<hidden>", n.bssid or "—", n.channel or "—", security or "—", n.signal_power or "—")
            for value in values:
                row.add_widget(lbl(str(value), 12, TEXT))
            self.table.add_widget(row)


class SessionsScreen(BaseScreen):
    title = "Sessions"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("Historical scan/session storage")
        self.root_box.add_widget(btn("Refresh sessions", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.box = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.root_box.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        self.box.clear_widgets()
        sessions = self.bridge.find_sessions()
        if not sessions:
            self.box.add_widget(lbl("No structured sessions found yet.", 14, MUTED))
        for s in sessions:
            row = BoxLayout(size_hint_y=None, height=dp(58), padding=dp(10), spacing=dp(10))
            row.add_widget(lbl(s["id"], 14, bold=True))
            row.add_widget(lbl(s["path"], 11, MUTED))
            row.add_widget(lbl("networks.json: " + s["networks"], 11, MUTED))
            self.box.add_widget(row)


class ReportsScreen(BaseScreen):
    title = "Reports"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("Generate a report from normalized GUI data")
        self.root_box.add_widget(btn("Load latest data", self.load_data))
        self.root_box.add_widget(btn("Generate TXT report", self.generate, accent=True))
        self.status = lbl("No report generated in this session.", 14, MUTED)
        self.root_box.add_widget(self.status)

    def load_data(self, *_):
        nets, source = self.bridge.load_latest_networks()
        self.status.text = f"Loaded {len(nets)} observations from {source or 'no source'}."

    def generate(self, *_):
        if not self.bridge.networks:
            self.bridge.load_latest_networks()
        path = self.bridge.generate_report()
        self.status.text = f"Report: {path}"


class LogsScreen(BaseScreen):
    title = "Logs"

    def __init__(self, bridge, log_buffer, **kwargs):
        self.log_buffer = log_buffer
        super().__init__(bridge, **kwargs)
        self.add_title("GUI service log")
        self.root_box.add_widget(btn("Refresh view", self.refresh, accent=True))
        self.text = TextInput(
            readonly=True,
            multiline=True,
            background_normal="",
            background_active="",
            background_color=PANEL,
            foreground_color=TEXT,
            font_size=dp(13),
            padding=(dp(12), dp(12)),
        )
        self.root_box.add_widget(self.text)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        self.text.text = "\n".join(self.log_buffer[-500:])


class SystemScreen(BaseScreen):
    title = "System"

    def __init__(self, bridge, **kwargs):
        super().__init__(bridge, **kwargs)
        self.add_title("Runtime and dependency health")
        self.root_box.add_widget(btn("Run checks", self.refresh, accent=True))
        self.status = lbl("", 14, TEXT)
        self.root_box.add_widget(self.status)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        deps = self.bridge.dependency_status()
        lines = [
            f"Repository root: {self.bridge.find_repo_root()}",
            f"Platform: {self.bridge.platform_name()}",
            f"Privilege: {self.bridge.privilege_status()}",
            "",
        ]
        for name, state in deps.items():
            lines.append(f"{name:14} {state}")
        self.status.text = "\n".join(lines)


class LazuliNetGUI(App):
    title = "LazuliNet"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log_buffer: list[str] = []
        self.bridge = RepositoryBridge(logger=self.log)

    def log(self, message: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_buffer.append(f"[{stamp}] {message}")

    def build(self):
        self.bridge.find_repo_root()

        shell = BoxLayout(orientation="horizontal")

        sidebar = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(220),
            padding=dp(14),
            spacing=dp(8),
        )
        brand = lbl("LAZULINET", 22, ACCENT, bold=True)
        brand.size_hint_y = None
        brand.height = dp(58)
        sidebar.add_widget(brand)
        sub = lbl("GUI / v0.1", 11, MUTED)
        sub.size_hint_y = None
        sub.height = dp(24)
        sidebar.add_widget(sub)

        sm = ScreenManager()

        screens = [
            DashboardScreen(self.bridge, name="dashboard"),
            InterfacesScreen(self.bridge, name="interfaces"),
            DiscoveryScreen(self.bridge, name="discovery"),
            NetworksScreen(self.bridge, name="networks"),
            SessionsScreen(self.bridge, name="sessions"),
            ReportsScreen(self.bridge, name="reports"),
            LogsScreen(self.bridge, self.log_buffer, name="logs"),
            SystemScreen(self.bridge, name="system"),
        ]
        for screen in screens:
            sm.add_widget(screen)

        def go(name):
            def handler(_button):
                sm.current = name
            return handler

        nav = [
            ("Dashboard", "dashboard"),
            ("Interfaces", "interfaces"),
            ("Discovery", "discovery"),
            ("Networks", "networks"),
            ("Sessions", "sessions"),
            ("Reports", "reports"),
            ("Logs", "logs"),
            ("System", "system"),
        ]
        for text, name in nav:
            sidebar.add_widget(btn(text, go(name)))

        sidebar.add_widget(Widget())
        footer = lbl("Safe GUI shell\nNo legacy attack actions", 11, MUTED)
        footer.size_hint_y = None
        footer.height = dp(48)
        sidebar.add_widget(footer)

        shell.add_widget(sidebar)
        shell.add_widget(sm)
        self.log(f"GUI started at repository root {self.bridge.repo_root}")
        return shell
