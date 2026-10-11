"""Uniform category-constrained passwords using OS-backed secrets.choice."""

import secrets
import string
from dataclasses import dataclass
from itertools import combinations

from rebel_security.utils.estimates import GeneratedSecret

AMBIGUOUS = frozenset('0Oo1lI')


@dataclass(frozen=True)
class PasswordOptions:
    length: int = 24
    uppercase: bool = True
    lowercase: bool = True
    numbers: bool = True
    symbols: bool = True
    exclude_ambiguous: bool = False

    def categories(self) -> tuple[str, ...]:
        if type(self.length) is not int or not 8 <= self.length <= 128:
            raise ValueError("Password length must be an integer from 8 to 128.")
        flags = (self.uppercase, self.lowercase, self.numbers, self.symbols)
        if any(type(flag) is not bool for flag in (*flags, self.exclude_ambiguous)):
            raise ValueError("Character options must be ON or OFF.")
        groups = (string.ascii_uppercase, string.ascii_lowercase,
                  string.digits, string.punctuation)
        selected = tuple(
            ''.join(c for c in group if not self.exclude_ambiguous or c not in AMBIGUOUS)
            for group, enabled in zip(groups, flags) if enabled
        )
        if not selected:
            raise ValueError("Select at least one character category.")
        return selected


def constrained_space(length: int, sizes: tuple[int, ...]) -> int:
    """Inclusion-exclusion count for disjoint, required character categories."""
    if type(length) is not int or length < 1 or not sizes or any(
        type(size) is not int or size < 1 for size in sizes
    ):
        raise ValueError("Positive length and category sizes are required.")
    total = sum(sizes)
    return sum(
        (-1)**count * (total - sum(subset))**length
        for count in range(len(sizes) + 1)
        for subset in combinations(sizes, count)
    )


def generate_password(options: PasswordOptions = PasswordOptions()) -> GeneratedSecret:
    groups = options.categories()
    alphabet = ''.join(groups)
    # Reject entire uniform samples that miss a category. Conditioning preserves
    # uniformity over valid strings; no biased mandatory-character shuffle.
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(options.length))
        if all(any(character in group for character in password) for group in groups):
            break
    return GeneratedSecret(
        password, constrained_space(options.length, tuple(map(len, groups))),
        "Uniform random password with every selected category present. "
        "Entropy counts only strings meeting those constraints.",
    )
