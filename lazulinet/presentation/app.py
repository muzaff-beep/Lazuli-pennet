from __future__ import annotations

import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
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
        background_color=ACCENT if accent else PANEL_2,
        color=TEXT,
        font_size=dp(14),
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
    )


class BaseScreen(Screen):
    title = ""

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.body = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(12))
        self.add_widget(self.body)
        self.body.add_widget(label(self.title, 27, bold=True))

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
        self.summary = label("", 14, MUTED)
        self.body.add_widget(self.summary)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        try:
            health = self.app_ref.runtime.interface.health()
            interfaces = self.app_ref.runtime.interface.list_interfaces()
            sessions = self.app_ref.runtime.sessions.list_sessions()
            lines = [
                f"Platform: {health.pop('platform', 'unknown')}",
                f"Privilege: {health.pop('privilege', 'unknown')}",
                f"Interfaces: {len(interfaces)}",
                f"Saved sessions: {len(sessions)}",
                f"Storage: {self.app_ref.runtime.sessions.root}",
                "",
                "Dependencies:",
            ]
            lines.extend(f"  {k}: {v}" for k, v in health.items())
            self.summary.text = "\n".join(lines)
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

    def refresh(self, *_):
        self.rows.clear_widgets()
        try:
            items = self.app_ref.runtime.interface.list_interfaces()
        except Exception as exc:
            self.rows.add_widget(label(str(exc), 13, WARN))
            return
        for iface in items:
            row = BoxLayout(size_hint_y=None, height=dp(76), spacing=dp(8), padding=dp(8))
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
        form = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(148))
        form.add_widget(label("Interface", 13))
        default_iface = "android-wifi" if os.environ.get("ANDROID_ARGUMENT") else "wlan0"
        self.interface = text_input(default_iface)
        form.add_widget(self.interface)
        form.add_widget(label("Duration", 13))
        self.duration = text_input("30", numeric=True)
        form.add_widget(self.duration)
        form.add_widget(label("Channel (optional)", 13))
        self.channel = text_input("", numeric=True)
        form.add_widget(self.channel)
        self.body.add_widget(form)
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        actions.add_widget(button("Start scan", self.start, accent=True))
        actions.add_widget(button("Cancel", self.cancel))
        self.body.add_widget(actions)
        self.status = label("Ready.", 13, MUTED)
        self.body.add_widget(self.status)
        self.handle = None
        Clock.schedule_interval(self.poll, 0.25)

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
        snap = self.handle.snapshot()
        if snap.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
            if snap.state == TaskState.COMPLETED and isinstance(snap.result, dict):
                self.status.text = f"Completed — {snap.result.get('network_count', 0)} network(s), session {snap.result.get('session_id', '')}"
            elif snap.state == TaskState.CANCELLED:
                self.status.text = "Cancelled."
            else:
                self.status.text = snap.error or "Failed."


class NetworksScreen(BaseScreen):
    title = "Networks"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Latest completed normalized discovery session")
        self.body.add_widget(button("Reload", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.rows = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        self.scroll.add_widget(self.rows)
        self.body.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        self.rows.clear_widgets()
        session = self.app_ref.runtime.sessions.latest_completed()
        if not session:
            self.rows.add_widget(label("No completed session yet.", 13, MUTED))
            return
        networks = self.app_ref.runtime.sessions.load_networks(session.id)
        head = BoxLayout(size_hint_y=None, height=dp(38))
        for item in ("ESSID", "BSSID", "CH", "SECURITY", "SIGNAL"):
            head.add_widget(label(item, 11, MUTED, bold=True))
        self.rows.add_widget(head)
        for network in networks:
            row = BoxLayout(size_hint_y=None, height=dp(48))
            sec = " / ".join(v for v in (network.privacy, network.cipher, network.auth) if v)
            for item in (network.essid or "<hidden>", network.bssid, str(network.channel or "—"), sec or "—", str(network.signal_power if network.signal_power is not None else "—")):
                row.add_widget(label(item, 11))
            self.rows.add_widget(row)


class SessionsScreen(BaseScreen):
    title = "Sessions"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Session-scoped history; scans no longer overwrite one networks.json")
        self.body.add_widget(button("Refresh", self.refresh, accent=True))
        self.scroll = ScrollView()
        self.rows = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        self.scroll.add_widget(self.rows)
        self.body.add_widget(self.scroll)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self, *_):
        self.rows.clear_widgets()
        for session in self.app_ref.runtime.sessions.list_sessions():
            row = BoxLayout(size_hint_y=None, height=dp(52))
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
        return self.app_ref.runtime.sessions.latest_completed()

    def generate_txt(self, *_):
        session = self._latest()
        self.status.text = "No completed session." if not session else f"Created {self.reporter.generate_text(session.id)}"

    def generate_json(self, *_):
        session = self._latest()
        self.status.text = "No completed session." if not session else f"Created {self.reporter.export_json(session.id)}"


class LogsScreen(BaseScreen):
    title = "Logs"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Structured task events marshalled to the UI thread by polling")
        self.text = TextInput(readonly=True, background_normal="", background_color=PANEL, foreground_color=TEXT)
        self.body.add_widget(self.text)
        Clock.schedule_interval(self.refresh, 0.5)

    def refresh(self, _dt):
        self.text.text = "\n".join(self.app_ref.logs[-500:])


class SystemScreen(BaseScreen):
    title = "System"

    def __init__(self, app_ref, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.subtitle("Capabilities and dependency preflight")
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


class LazuliNetApp(App):
    title = "LazuliNet"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runtime = create_runtime()
        self.logs: list[str] = []

    def log(self, message: str):
        self.logs.append(f"[{datetime.now():%H:%M:%S}] {message}")

    def _poll_task_events(self, _dt):
        for event in self.runtime.tasks.poll_events(200):
            extra = f" ({event.progress:.0%})" if event.progress is not None else ""
            self.log(f"{event.kind}: {event.message}{extra}")

    def build(self):
        Clock.schedule_interval(self._poll_task_events, 0.15)
        shell = BoxLayout(orientation="horizontal")
        nav = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(205), padding=dp(12), spacing=dp(7))
        brand = label("LAZULINET", 21, ACCENT, bold=True)
        brand.size_hint_y = None
        brand.height = dp(58)
        nav.add_widget(brand)
        sm = ScreenManager()
        screens = [
            DashboardScreen(self, name="dashboard"),
            InterfacesScreen(self, name="interfaces"),
            DiscoveryScreen(self, name="discovery"),
            NetworksScreen(self, name="networks"),
            SessionsScreen(self, name="sessions"),
            ReportsScreen(self, name="reports"),
            LogsScreen(self, name="logs"),
            SystemScreen(self, name="system"),
        ]
        for screen in screens:
            sm.add_widget(screen)
        for title, name in (("Dashboard", "dashboard"), ("Interfaces", "interfaces"), ("Discovery", "discovery"), ("Networks", "networks"), ("Sessions", "sessions"), ("Reports", "reports"), ("Logs", "logs"), ("System", "system")):
            nav.add_widget(button(title, lambda _b, n=name: setattr(sm, "current", n)))
        nav.add_widget(Widget())
        footer = label("v0.2\nSafe discovery shell", 10, MUTED)
        footer.size_hint_y = None
        footer.height = dp(44)
        nav.add_widget(footer)
        shell.add_widget(nav)
        shell.add_widget(sm)
        return shell
