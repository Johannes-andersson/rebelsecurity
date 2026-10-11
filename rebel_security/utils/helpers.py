"""Platform detection without external dependencies."""

import os
import platform
from pathlib import Path


def platform_name() -> str:
    """Return a readable name for the actual host OS."""
    system = platform.system()
    return {"Darwin": "macOS"}.get(system, system or "Unknown")


def config_path() -> Path:
    """Use the host's standard per-user configuration location."""
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", "")
        base = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".config"
    return base / "rebel-security" / "settings.json"
