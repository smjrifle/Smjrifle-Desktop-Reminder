"""
Smjrifle Desktop Reminder - Autostart & Background-Presence Helpers
Cross-platform "launch at login" toggle (macOS LaunchAgent, Windows registry
Run key, Linux XDG autostart .desktop) plus the macOS Dock-icon hide.

Every function here fails soft: if the platform mechanism isn't reachable
(sandboxed environment, missing pyobjc, restricted registry access, etc.)
it prints a warning and returns rather than raising, so a broken autostart
toggle never takes the whole app down with it.
"""

import os
import sys
import plistlib
from pathlib import Path

APP_DISPLAY_NAME = "Smjrifle Desktop Reminder"
BUNDLE_ID = "com.smjrifle.desktopreminder"


def _launch_command() -> list:
    """The command to run at login: the frozen binary itself, or
    `<python> <main.py>` when running from source."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    main_script = os.path.abspath(sys.argv[0])
    return [sys.executable, main_script]


# ---------------------------------------------------------------- macOS ----

def _macos_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _macos_is_enabled() -> bool:
    return _macos_agent_path().exists()


def _macos_set_enabled(enabled: bool) -> bool:
    path = _macos_agent_path()
    try:
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            plist = {
                "Label": BUNDLE_ID,
                "ProgramArguments": _launch_command(),
                "RunAtLoad": True,
                "KeepAlive": False,
                "ProcessType": "Interactive",
            }
            with open(path, "wb") as f:
                plistlib.dump(plist, f)
            os.system(f'launchctl unload "{path}" >/dev/null 2>&1')
            os.system(f'launchctl load "{path}" >/dev/null 2>&1')
        elif path.exists():
            os.system(f'launchctl unload "{path}" >/dev/null 2>&1')
            path.unlink()
        return True
    except Exception as e:
        print(f"[Smjrifle Reminder] Autostart (macOS) failed: {e}")
        return False


# -------------------------------------------------------------- Windows ----

_WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _windows_is_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_DISPLAY_NAME)
            return True
    except Exception:
        return False


def _windows_set_enabled(enabled: bool) -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = " ".join(f'"{p}"' for p in _launch_command())
                winreg.SetValueEx(key, APP_DISPLAY_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_DISPLAY_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[Smjrifle Reminder] Autostart (Windows) failed: {e}")
        return False


# ---------------------------------------------------------------- Linux ----

def _linux_autostart_path() -> Path:
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "autostart" / f"{BUNDLE_ID}.desktop"


def _linux_is_enabled() -> bool:
    return _linux_autostart_path().exists()


def _linux_set_enabled(enabled: bool) -> bool:
    path = _linux_autostart_path()
    try:
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            exec_cmd = " ".join(_launch_command())
            path.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={APP_DISPLAY_NAME}\n"
                f"Exec={exec_cmd}\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Terminal=false\n",
                encoding="utf-8",
            )
        elif path.exists():
            path.unlink()
        return True
    except Exception as e:
        print(f"[Smjrifle Reminder] Autostart (Linux) failed: {e}")
        return False


# --------------------------------------------------------------- Public ----

def is_autostart_enabled() -> bool:
    """Reads the actual OS-level state (not a cached config flag) so the
    checkbox never drifts from what's really registered with the OS."""
    try:
        if sys.platform == "darwin":
            return _macos_is_enabled()
        if sys.platform == "win32":
            return _windows_is_enabled()
        return _linux_is_enabled()
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    if sys.platform == "darwin":
        return _macos_set_enabled(enabled)
    if sys.platform == "win32":
        return _windows_set_enabled(enabled)
    return _linux_set_enabled(enabled)


def hide_from_macos_dock() -> None:
    """Switch the running app to a menu-bar-only (Accessory) activation
    policy so no Dock icon appears. macOS only; silently does nothing on
    other platforms or if pyobjc isn't installed (the app still runs fine,
    it just keeps its Dock icon in that case)."""
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception as e:
        print(f"[Smjrifle Reminder] Could not hide Dock icon (pyobjc-framework-Cocoa not installed?): {e}")
