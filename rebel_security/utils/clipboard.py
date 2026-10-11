"""User-requested local clipboard writes; read-back verification, no history or auto-clearing."""

import pyperclip


def copy_secret(value: str) -> bool:
    if not value:
        return False
    try:
        pyperclip.copy(value)
        return pyperclip.paste() == value
    except Exception:
        # Provider exceptions may contain their input; never render or log them.
        return False
