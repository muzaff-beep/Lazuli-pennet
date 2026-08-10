"""Kivy runtime smoke test for Debian/CI machines with a graphical backend."""
from __future__ import annotations

import os

os.environ.setdefault("LAZULINET_DATA_DIR", "/tmp/lazulinet-smoke")

from kivy.core.window import Window

from lazulinet.presentation.app import LazuliNetApp


REQUIRED_SCREENS = {
    "dashboard",
    "interfaces",
    "discovery",
    "networks",
    "sessions",
    "reports",
    "logs",
    "system",
    "more",
}


def smoke(width: int, height: int, compact: bool) -> None:
    Window.size = (width, height)
    app = LazuliNetApp()
    root = app.build()
    assert app.manager is not None
    assert REQUIRED_SCREENS.issubset({screen.name for screen in app.manager.screens})
    assert app.is_compact is compact
    expected_orientation = "vertical" if compact else "horizontal"
    assert root.orientation == expected_orientation
    print(f"PASS {width}x{height}: {expected_orientation} shell")


def main() -> int:
    smoke(1280, 800, compact=False)
    smoke(390, 844, compact=True)
    print("LazuliNet GUI smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
