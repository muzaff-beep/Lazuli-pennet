from __future__ import annotations

import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from lazulinet.application.report_service import ReportService
from lazulinet.domain.models import ScanRequest, TaskState, WirelessMode
from lazulinet.platform.factory import create_runtime

BG = (0.025, 0.035, 0.055, 1)
PANEL = (0.055, 0.075, 0.11, 1)
PANEL_2 = (0.075, 0.10, 0.145, 1)
ACCENT = (0.05, 0.62, 1.0, 1)
TEXT = (0.93, 0.96, 1, 1)
MUTED = (0.58, 0.66, 0.77, 1)
GOOD = (0.25, 0.85, 0.58, 1)
WARN = (1.0, 0.68, 0.25, 1)
DANGER = (1.0, 0.34, 0.42, 1)
Window.clearcolor = BG


def label(text="", size=14, color=TEXT, bold=False, halign="left"):
    widget = Label(
        text=(f"[b]{text}[/b]" if bold else text),
        markup=True,
        font_size=dp(size),
        color=color,
        halign=halign,
        valign="middle",
    )
    widget.bind(size=lambda inst, value: setattr(inst, "text_size", value))
    return widget


def button(text, callback=None, accent=False, height=46):
    widget = Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_down="",
        background_color=ACCENT if accent else PANEL_2,
        color=TEXT,
        font_size=dp(13),
    )
    if callback:
        widget.bind(on_press=callback)
    return widget


def text_input(text="", hint="", numeric=False):
    return TextInput(
        text=text,
        hint_text=hint,
        multiline=False,
        input_filter="int" if numeric else None,
        background_normal="",
        background_active="",
        background_color=PANEL_2,
        foreground_color=TEXT,
        hint_text_color=MUTED,
        cursor_color=ACCENT,
        padding=(dp(12), dp(11)),
        font_size=dp(14),
    )


class Surface(BoxLayout):
    """Simple themed panel that remains lightweight on desktop and Android."""

    def __init__(self, fill=PANEL, radius=12, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color = Color(*fill)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
        self.bind(pos=self._sync_background, size=self._sync_background)

    def _sync_background(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class BaseScreen(Screen):
    title = ""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.body = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        self.add_widget(self.body)
        title = label(self.title, 27, bold=True)
        title.size_hint_y = None
        title.height = dp(42)
        self.body.add_widget(title)

    @property
    def compact(self) -> bool:
        return self.app_ref.is_compact

    def subtitle(self, text):
        item = label(text, 12, MUTED)
        item.size_hint_y = None
        item.height = dp(34)
        self.body.add_widget(item)


class DashboardScreen(BaseScreen):
    title = "Dashboard"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Shared LazuliNet runtime — Debian + Android")
        self.body.add_widget(button("Refresh", self.refresh, accent=True))
        self.cards = GridLayout(cols=4, spacing=dp(10), size_hint_y=None, height=dp(112))
        self.body.add_widget(self.cards)
        self.summary = label("", 13, MUTED)
        self.body.add_widget(self.summary)

    def on_pre_enter(self):
        self.refresh()

    def _card(self, title, value):
        box = Surface(orientation="vertical", padding=dp(12), spacing=dp(3))
        box.add_widget(label(title, 11, MUTED))
        box.add_widget(label(str(value), 16, bold=True))
        return box

    def refresh(self, *_):
        try:
            health = dict(self.app_ref.runtime.interface.health())
            interfaces = self.app_ref.runtime.interface.list_interfaces()
            sessions = self.app_ref.runtime.sessions.list_sessions()
            platform = health.pop("platform", "unknown")
            privilege = health.pop("privilege", "unknown")
            self.cards.cols = 2 if self.compact else 4
            self.cards.height = dp(218 if self.compact else 112)
            self.cards.clear_widgets()
            for key, value in (
                ("Platform", platform),
                ("Privilege", privilege),
                ("Interfaces", len(interfaces)),
                ("Sessions", len(sessions)),
            ):
                self.cards.add_widget(self._card(key, value))
            deps = "\n".join(f"{k}: {v}" for k, v in health.items()) or "No external dependency checks."
            self.summary.text = f"Storage: {self.app_ref.runtime.sessions.root}\n\n{deps}"
        except Exception as exc:
            self.summary.text = f"Health check failed: {exc}"


class InterfacesScreen(BaseScreen):
    title = "Interfaces"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Actual interface state from the platform adapter")
        self.body.add_widget(button("Refresh", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.rows = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        self.scroll.add_widget(self.rows)
        self.body.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def _mode(self, iface, mode):
        try:
            updated = self.app_ref.runtime.interface.set_mode(iface, mode)
            self.app_ref.log(f"{iface}: mode -> {updated.mode.value}")
        except Exception as exc:
            self.app_ref.log(f"Mode change failed for {iface}: {exc}")
        self.refresh()

    def _compact_card(self, iface):
        card = Surface(orientation="vertical", size_hint_y=None, height=dp(132), padding=dp(12), spacing=dp(6))
        top = BoxLayout(size_hint_y=None, height=dp(28))
        top.add_widget(label(iface.name, 15, bold=True))
        top.add_widget(label("UP" if iface.is_up else "DOWN", 12, GOOD if iface.is_up else WARN, bold=True, halign="right"))
        card.add_widget(top)
        card.add_widget(label(f"{iface.mode.value}  •  {iface.mac_address or '—'}", 11, MUTED))
        actions = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        if iface.supports_monitor:
            actions.add_widget(button("Monitor", lambda _b, n=iface.name: self._mode(n, WirelessMode.MONITOR), height=40))
            actions.add_widget(button("Managed", lambda _b, n=iface.name: self._mode(n, WirelessMode.MANAGED), height=40))
        else:
            actions.add_widget(label("Managed platform interface", 11, MUTED))
        card.add_widget(actions)
        return card

    def refresh(self, *_):
        self.rows.clear_widgets()
        try:
            items = self.app_ref.runtime.interface.list_interfaces()
        except Exception as exc:
            self.rows.add_widget(label(str(exc), 13, WARN))
            return
        if not items:
            self.rows.add_widget(label("No interfaces detected.", 13, MUTED))
            return
        for iface in items:
            if self.compact:
                self.rows.add_widget(self._compact_card(iface))
                continue
            row = Surface(orientation="horizontal", size_hint_y=None, height=dp(76), spacing=dp(8), padding=dp(8))
            row.add_widget(label(iface.name, 15, bold=True))
            row.add_widget(label(iface.mode.value, 12, MUTED))
            row.add_widget(label(iface.mac_address or "—", 11, MUTED))
            row.add_widget(label("UP" if iface.is_up else "DOWN", 12, GOOD if iface.is_up else WARN))
            if iface.supports_monitor:
                row.add_widget(button("Monitor", lambda _b, n=iface.name: self._mode(n, WirelessMode.MONITOR), height=38))
                row.add_widget(button("Managed", lambda _b, n=iface.name: self._mode(n, WirelessMode.MANAGED), height=38))
            self.rows.add_widget(row)


class DiscoveryScreen(BaseScreen):
    title = "Discovery"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Passive Wi-Fi discovery through a cancellable background task")
        default_iface = "android-wifi" if os.environ.get("ANDROID_ARGUMENT") else "wlan0"
        self.interface = text_input(default_iface)
        self.duration = text_input("30", numeric=True)
        self.channel = text_input("", hint="All channels", numeric=True)
        form = Surface(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(168))
        for field_name, field in (("Interface", self.interface), ("Duration (seconds)", self.duration), ("Channel (optional)", self.channel)):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            caption = label(field_name, 12, MUTED)
            caption.size_hint_x = 0.38
            row.add_widget(caption)
            row.add_widget(field)
            form.add_widget(row)
        self.body.add_widget(form)
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        actions.add_widget(button("Start scan", self.start, accent=True))
        actions.add_widget(button("Cancel", self.cancel))
        self.body.add_widget(actions)
        self.progress = ProgressBar(max=1.0, value=0, size_hint_y=None, height=dp(8))
        self.body.add_widget(self.progress)
        self.status = label("Ready.", 13, MUTED)
        self.body.add_widget(self.status)
        self.handle = None
        Clock.schedule_interval(self.poll, 0.2)

    def start(self, *_):
        if self.handle and self.handle.snapshot().state in (TaskState.RUNNING, TaskState.CANCELLING, TaskState.QUEUED):
            self.status.text = "A discovery task is already active."
            return
        try:
            channel = int(self.channel.text) if self.channel.text.strip() else None
            request = ScanRequest(
                interface=self.interface.text.strip(),
                duration_seconds=int(self.duration.text or "30"),
                channel=channel,
            )
            self.handle = self.app_ref.runtime.discovery.start_scan(request)
            self.progress.value = 0
            self.status.text = f"Task {self.handle.id[:8]} started."
        except Exception as exc:
            self.status.text = f"Start failed: {exc}"

    def cancel(self, *_):
        if self.handle:
            self.handle.cancel()
            self.status.text = "Cancelling…"

    def poll(self, _dt):
        if not self.handle:
            return
        event = self.app_ref.latest_task_events.get(self.handle.id)
        if event is not None:
            if event.progress is not None:
                self.progress.value = max(0.0, min(1.0, event.progress))
            if event.message:
                self.status.text = event.message
        snap = self.handle.snapshot()
        if snap.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
            self.progress.value = 1.0 if snap.state == TaskState.COMPLETED else self.progress.value
            if snap.state == TaskState.COMPLETED and isinstance(snap.result, dict):
                self.status.text = f"Completed — {snap.result.get('network_count', 0)} network(s), session {snap.result.get('session_id', '')}"
            elif snap.state == TaskState.CANCELLED:
                count = snap.result.get("network_count", 0) if isinstance(snap.result, dict) else 0
                self.status.text = f"Cancelled — {count} partial observation(s) preserved."
            else:
                self.status.text = snap.error or "Failed."


class NetworksScreen(BaseScreen):
    title = "Networks"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Newest normalized discovery session, including preserved partial scans")
        self.body.add_widget(button("Reload", self.refresh, accent=True))
        self.session_status = label("", 11, MUTED)
        self.session_status.size_hint_y = None
        self.session_status.height = dp(26)
        self.body.add_widget(self.session_status)
        self.scroll = ScrollView()
        self.rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        self.scroll.add_widget(self.rows)
        self.body.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def _network_card(self, network):
        card = Surface(orientation="vertical", size_hint_y=None, height=dp(118), padding=dp(12), spacing=dp(4))
        card.add_widget(label(network.essid or "<hidden>", 15, bold=True))
        card.add_widget(label(network.bssid or "—", 11, MUTED))
        security = " / ".join(v for v in (network.privacy, network.cipher, network.auth) if v) or "Open / unknown"
        card.add_widget(label(f"CH {network.channel or '—'}  •  Signal {network.signal_power if network.signal_power is not None else '—'}", 11))
        card.add_widget(label(security, 11, MUTED))
        return card

    def refresh(self, *_):
        self.rows.clear_widgets()
        session = self.app_ref.runtime.sessions.latest_with_networks()
        if not session:
            self.session_status.text = ""
            self.rows.add_widget(label("No normalized session yet.", 13, MUTED))
            return
        networks = self.app_ref.runtime.sessions.load_networks(session.id)
        self.session_status.text = f"{session.id}  •  {session.status.value}  •  {len(networks)} observation(s)"
        if self.compact:
            for network in networks:
                self.rows.add_widget(self._network_card(network))
            if not networks:
                self.rows.add_widget(label("Session contains no observations.", 13, MUTED))
            return
        head = BoxLayout(size_hint_y=None, height=dp(38))
        for item in ("ESSID", "BSSID", "CH", "SECURITY", "SIGNAL"):
            head.add_widget(label(item, 11, MUTED, bold=True))
        self.rows.add_widget(head)
        for network in networks:
            row = Surface(orientation="horizontal", size_hint_y=None, height=dp(50), padding=(dp(8), 0))
            sec = " / ".join(v for v in (network.privacy, network.cipher, network.auth) if v)
            for item in (
                network.essid or "<hidden>",
                network.bssid,
                str(network.channel or "—"),
                sec or "—",
                str(network.signal_power if network.signal_power is not None else "—"),
            ):
                row.add_widget(label(item, 11))
            self.rows.add_widget(row)


class SessionsScreen(BaseScreen):
    title = "Sessions"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Session-scoped discovery history")
        self.body.add_widget(button("Refresh", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        self.scroll.add_widget(self.rows)
        self.body.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        self.rows.clear_widgets()
        sessions = self.app_ref.runtime.sessions.list_sessions()
        if not sessions:
            self.rows.add_widget(label("No saved sessions.", 13, MUTED))
            return
        for session in sessions:
            if self.compact:
                card = Surface(orientation="vertical", size_hint_y=None, height=dp(96), padding=dp(10), spacing=dp(3))
                card.add_widget(label(session.id, 12, bold=True))
                status_color = GOOD if session.status.value == "completed" else WARN if session.status.value == "cancelled" else DANGER if session.status.value == "failed" else MUTED
                card.add_widget(label(f"{session.status.value}  •  {session.platform}  •  {session.interface}", 11, status_color))
                card.add_widget(label(f"{session.network_count} observation(s)", 11, MUTED))
                self.rows.add_widget(card)
                continue
            row = Surface(orientation="horizontal", size_hint_y=None, height=dp(52), padding=(dp(8), 0))
            for item in (session.id, session.platform, session.interface, session.status.value, str(session.network_count)):
                row.add_widget(label(item, 11))
            self.rows.add_widget(row)


class ReportsScreen(BaseScreen):
    title = "Reports"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Generate reports from normalized session state")
        self.reporter = ReportService(app_ref.runtime.sessions)
        self.body.add_widget(button("Generate latest TXT", self.generate_txt, accent=True))
        self.body.add_widget(button("Export latest JSON", self.generate_json))
        self.status = label("", 13, MUTED)
        self.body.add_widget(self.status)

    def _latest(self):
        return self.app_ref.runtime.sessions.latest_with_networks()

    def generate_txt(self, *_):
        session = self._latest()
        self.status.text = "No normalized session." if not session else f"Created {self.reporter.generate_text(session.id)}"

    def generate_json(self, *_):
        session = self._latest()
        self.status.text = "No normalized session." if not session else f"Created {self.reporter.export_json(session.id)}"


class LogsScreen(BaseScreen):
    title = "Logs"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Structured task events marshalled to the Kivy UI thread")
        self.text = TextInput(
            readonly=True,
            background_normal="",
            background_active="",
            background_color=PANEL,
            foreground_color=TEXT,
            font_size=dp(12),
            padding=(dp(12), dp(12)),
        )
        self.body.add_widget(self.text)
        Clock.schedule_interval(self.refresh, 0.5)

    def refresh(self, _dt=0):
        self.text.text = "\n".join(self.app_ref.logs[-500:])


class SystemScreen(BaseScreen):
    title = "System"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Capabilities, permissions, and dependency preflight")
        if os.environ.get("ANDROID_ARGUMENT"):
            self.body.add_widget(button("Request Wi-Fi permissions", self.permissions, accent=True))
        self.body.add_widget(button("Run checks", self.refresh, accent=True))
        self.status = label("", 13, MUTED)
        self.body.add_widget(self.status)

    def on_pre_enter(self):
        self.refresh()

    def permissions(self, *_):
        from lazulinet.platform.android.wifi import request_wifi_permissions

        self.status.text = "Permission request dispatched." if request_wifi_permissions() else "Permission request unavailable."

    def refresh(self, *_):
        try:
            health = self.app_ref.runtime.interface.health()
            self.status.text = "\n".join(f"{k}: {v}" for k, v in health.items())
        except Exception as exc:
            self.status.text = str(exc)


class MoreScreen(BaseScreen):
    title = "More"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("History, reporting, diagnostics, and runtime configuration")
        menu = Surface(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(230))
        for title, name in (("Sessions", "sessions"), ("Reports", "reports"), ("Logs", "logs"), ("System", "system")):
            menu.add_widget(button(title, lambda _b, n=name: setattr(self.manager, "current", n)))
        self.body.add_widget(menu)
        self.body.add_widget(Widget())


class ResponsiveShell(BoxLayout):
    """Desktop sidebar / mobile bottom-navigation shell sharing one ScreenManager."""

    def __init__(self, app_ref, manager, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.manager = manager
        self.desktop_nav = self._build_desktop_nav()
        self.mobile_nav = self._build_mobile_nav()
        self.rebuild()

    def _go(self, name):
        def callback(_button):
            self.manager.current = name
        return callback

    def _build_desktop_nav(self):
        nav = Surface(
            orientation="vertical",
            size_hint_x=None,
            width=dp(205),
            padding=dp(12),
            spacing=dp(7),
            radius=0,
        )
        brand = label("LAZULINET", 21, ACCENT, bold=True)
        brand.size_hint_y = None
        brand.height = dp(58)
        nav.add_widget(brand)
        for title, name in (
            ("Dashboard", "dashboard"),
            ("Interfaces", "interfaces"),
            ("Discovery", "discovery"),
            ("Networks", "networks"),
            ("Sessions", "sessions"),
            ("Reports", "reports"),
            ("Logs", "logs"),
            ("System", "system"),
        ):
            nav.add_widget(button(title, self._go(name)))
        nav.add_widget(Widget())
        footer = label("v0.3\nSafe discovery shell", 10, MUTED)
        footer.size_hint_y = None
        footer.height = dp(44)
        nav.add_widget(footer)
        return nav

    def _build_mobile_nav(self):
        nav = Surface(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(62),
            padding=dp(6),
            spacing=dp(4),
            radius=0,
        )
        for title, name in (
            ("Home", "dashboard"),
            ("Interfaces", "interfaces"),
            ("Scan", "discovery"),
            ("Networks", "networks"),
            ("More", "more"),
        ):
            nav.add_widget(button(title, self._go(name), height=50))
        return nav

    def rebuild(self, *_):
        self.clear_widgets()
        if self.app_ref.is_compact:
            self.orientation = "vertical"
            self.add_widget(self.manager)
            self.add_widget(self.mobile_nav)
        else:
            self.orientation = "horizontal"
            self.add_widget(self.desktop_nav)
            self.add_widget(self.manager)


class LazuliNetApp(App):
    title = "LazuliNet"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runtime = create_runtime()
        self.logs: list[str] = []
        self.latest_task_events = {}
        self.shell: ResponsiveShell | None = None
        self.manager: ScreenManager | None = None

    @property
    def is_compact(self) -> bool:
        return Window.width < dp(720)

    def log(self, message: str):
        self.logs.append(f"[{datetime.now():%H:%M:%S}] {message}")

    def _poll_task_events(self, _dt):
        for event in self.runtime.tasks.poll_events(200):
            self.latest_task_events[event.task_id] = event
            extra = f" ({event.progress:.0%})" if event.progress is not None else ""
            self.log(f"{event.kind}: {event.message}{extra}")

    def _on_window_size(self, *_):
        if self.shell:
            self.shell.rebuild()
        if self.manager and self.manager.current_screen:
            refresh = getattr(self.manager.current_screen, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except TypeError:
                    pass

    def build(self):
        Clock.schedule_interval(self._poll_task_events, 0.15)
        Window.bind(size=self._on_window_size)
        sm = ScreenManager()
        self.manager = sm
        screens = [
            DashboardScreen(self, name="dashboard"),
            InterfacesScreen(self, name="interfaces"),
            DiscoveryScreen(self, name="discovery"),
            NetworksScreen(self, name="networks"),
            SessionsScreen(self, name="sessions"),
            ReportsScreen(self, name="reports"),
            LogsScreen(self, name="logs"),
            SystemScreen(self, name="system"),
            MoreScreen(self, name="more"),
        ]
        for screen in screens:
            sm.add_widget(screen)
        self.shell = ResponsiveShell(self, sm)
        self.log("GUI initialized.")
        return self.shell
