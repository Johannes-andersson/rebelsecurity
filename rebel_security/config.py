"""Validated preferences, with atomic local persistence and no secret data."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

THEMES = {"rebel-green": "REBEL GREEN", "amber-terminal": "AMBER TERMINAL"}


@dataclass(frozen=True)
class Settings:
    theme: str = "rebel-green"
    reduced_motion: bool = False
    confirm_exit: bool = True


def load_settings(path: Path) -> tuple[Settings, str | None]:
    """Recover to defaults without overwriting unreadable or invalid files."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        theme = data.get("theme", "rebel-green")
        reduced = data.get("reduced_motion", False)
        confirm = data.get("confirm_exit", True)
        if not isinstance(theme, str) or theme not in THEMES:
            raise ValueError("Unknown theme")
        if type(reduced) is not bool or type(confirm) is not bool:
            raise ValueError("Expected boolean preferences")
        return Settings(theme, reduced, confirm), None
    except FileNotFoundError:
        return Settings(), None
    except (OSError, UnicodeError, ValueError, RecursionError):
        return Settings(), (
            "Settings could not be read or were invalid. Defaults are active. "
            "The original file is unchanged until you save settings."
        )


def save_settings(path: Path, settings: Settings) -> None:
    """Replace settings atomically; propagate write errors to the UI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = stream.name
            json.dump(asdict(settings), stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
