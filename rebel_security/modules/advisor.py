"""Independent uniform word selection and numeric passwords."""

import secrets
import string
from dataclasses import dataclass

from rebel_security.modules.generator import PasswordOptions, generate_password
from rebel_security.utils.estimates import GeneratedSecret
from rebel_security.utils.wordlist import load_words


@dataclass(frozen=True)
class PassphraseOptions:
    word_count: int = 6
    separator: str = '-'
    capitalize: bool = True
    extra_digits: int = 0

    def validate(self) -> None:
        if type(self.word_count) is not int or not 4 <= self.word_count <= 10:
            raise ValueError("Choose 4 to 10 words.")
        if type(self.extra_digits) is not int or not 0 <= self.extra_digits <= 10:
            raise ValueError("Additional digits must be from 0 to 10.")
        if type(self.capitalize) is not bool:
            raise ValueError("Capitalization must be ON or OFF.")
        if not isinstance(self.separator, str) or not 1 <= len(self.separator) <= 8 or any(
            c not in string.punctuation + ' ' for c in self.separator
        ):
            raise ValueError("Use 1–8 ASCII punctuation characters or spaces as separator.")


def generate_passphrase(options: PassphraseOptions = PassphraseOptions()) -> GeneratedSecret:
    options.validate()
    words = load_words()
    chosen = [secrets.choice(words) for _ in range(options.word_count)]
    if options.capitalize:
        chosen = [word.capitalize() for word in chosen]
    value = options.separator.join(chosen)
    if options.extra_digits:
        value += options.separator + ''.join(
            secrets.choice(string.digits) for _ in range(options.extra_digits)
        )
    return GeneratedSecret(
        value, len(words)**options.word_count * 10**options.extra_digits,
        f"{options.word_count} independent selections from {len(words):,} EFF words "
        f"with replacement, plus {options.extra_digits} random digits. "
        "Capitalization and separators add no entropy.",
    )


def generate_pin(length: int = 8) -> GeneratedSecret:
    if type(length) is not int or not 6 <= length <= 20:
        raise ValueError("Numeric passwords must contain 6 to 20 digits.")
    return GeneratedSecret(
        ''.join(secrets.choice(string.digits) for _ in range(length)), 10**length,
        "Uniform numeric password; leading zeroes are preserved. Short PINs depend "
        "heavily on rate limiting and the authentication context.",
    )


def generate_maximum() -> GeneratedSecret:
    return generate_password(PasswordOptions(length=48))
