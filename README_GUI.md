# LazuliNet GUI Scaffold

This is a **drop-in Kivy GUI scaffold** for the `Lazuli-pennet-main.zip` architecture reviewed on 2026-08-10.

## What is implemented

- Dark desktop/touch-oriented application shell
- Dashboard
- OS interface inspection
- GUI-safe Discovery configuration shell
- Import and display of the newest `networks.json`
- Network observation table
- Structured-session discovery
- TXT report generation
- Runtime/dependency health checks
- GUI service log

## Deliberately not wired

The repository contains legacy security-sensitive attack/cracking/rogue-AP capability modules. This GUI does **not** expose those modules as executable controls.

The existing scanner is also not called directly from the Kivy thread. The repository architecture review found blocking sleeps/process loops and divergent scanner implementations. Discovery execution should first be moved behind:

1. a typed `DiscoveryAdapter`
2. a cancellable background `TaskRunner`
3. structured progress/result events

Then the Discovery screen can safely call that service.

## Installation

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt
python run_gui.py
```

On Debian, Kivy may need normal desktop/OpenGL dependencies depending on the system image.

## Drop-in layout

Copy these files into the root of `Lazuli-pennet-main/`:

```text
Lazuli-pennet-main/
├── run_gui.py
├── requirements-gui.txt
├── README_GUI.md
└── lazulinet_gui/
    ├── __init__.py
    ├── app.py
    ├── models.py
    └── services.py
```

The bridge automatically looks for the existing root/Debian project and for known `networks.json` locations.

## Next implementation step

Replace the placeholder Discovery execution surface with a shared application layer:

```text
Kivy screen
  -> DiscoveryController
  -> TaskRunner
  -> DiscoveryService
  -> DebianDiscoveryAdapter / AndroidDiscoveryAdapter
  -> OS tooling
```

Do not let the Kivy screen call `subprocess` or the old scanner modules directly.
