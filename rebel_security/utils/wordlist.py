"""Load bundled EFF data without any runtime download."""

from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=1)
def load_words() -> tuple[str, ...]:
    try:
        data = files('rebel_security').joinpath('data/eff_large_wordlist.txt').read_text('utf-8')
        # Exclude four hyphenated entries so separators remain unambiguous.
        entries = tuple(line.split()[1] for line in data.splitlines())
        if len(entries) != 7776 or len(set(entries)) != 7776:
            raise ValueError
        words = tuple(word for word in entries if word.isalpha())
        if len(words) != 7772 or len(set(words)) != 7772 or not all(
            word.isascii() and word.isalpha() and word.islower() for word in words
        ):
            raise ValueError
        return words
    except (OSError, ValueError, IndexError, UnicodeError):
        raise ValueError("Bundled wordlist is missing or invalid. Reinstall the application.") from None
