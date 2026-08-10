# CI fix: PyInstaller/Kivy X11 analysis

The Linux release job previously ran the GUI smoke test under Xvfb, but ran
PyInstaller itself outside Xvfb.

Kivy's PyInstaller hook calls `collect_submodules()` for `kivy.core.window`.
During that analysis, the isolated hook process imports the X11 window provider.
Without `DISPLAY`, it aborts with:

- `Couldn't connect to X server`
- `PyInstaller.isolated._parent.SubprocessDiedError`
- child exit code `102`

The `Freeze LazuliNet` step now runs:

```sh
xvfb-run -a pyinstaller ...
```

and sets `KIVY_NO_ARGS=1`.

No LazuliNet core behavior is changed by this patch.
