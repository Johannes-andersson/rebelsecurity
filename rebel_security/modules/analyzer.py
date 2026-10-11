"""Pattern-aware estimation; returned summaries never contain password tokens."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from zxcvbn import zxcvbn

MAX_ANALYSIS_LENGTH = 128
RATINGS = ('VERY WEAK', 'WEAK', 'FAIR', 'STRONG', 'VERY STRONG')
PATTERNS = {
    'dictionary': 'Common password, name, or dictionary word',
    'repeat': 'Repeated characters or groups',
    'sequence': 'Sequential characters',
    'spatial': 'Keyboard pattern',
    'date': 'Date pattern',
    'regex': 'Predictable year or numeric pattern',
}


@dataclass(frozen=True)
class Analysis:
    length: int
    categories: int
    score: int
    guesses: int
    weaknesses: tuple[str, ...]
    recommendations: tuple[str, ...]

    @property
    def rating(self) -> str:
        return RATINGS[self.score]


def analyze_password(password: str) -> Analysis:
    if not isinstance(password, str) or not 1 <= len(password) <= MAX_ANALYSIS_LENGTH:
        raise ValueError("Enter a password from 1 to 128 characters; nothing is truncated.")
    result = zxcvbn(password, max_length=MAX_ANALYSIS_LENGTH)
    weaknesses = set()
    for match in result['sequence']:
        label = PATTERNS.get(match['pattern'])
        if label:
            weaknesses.add(label)
        if match.get('l33t'):
            weaknesses.add('Predictable character substitutions')
    categories = sum((any(c.islower() for c in password),
                      any(c.isupper() for c in password),
                      any(c.isdigit() for c in password),
                      any(not c.isalnum() for c in password)))
    # Do not return raw zxcvbn results: they contain the password and match tokens.
    return Analysis(
        len(password), categories, result['score'],
        max(1, int(Decimal(result['guesses']).to_integral_value(rounding=ROUND_CEILING))),
        tuple(sorted(weaknesses)),
        ('Use a longer randomly generated password or passphrase.',
         'Avoid words followed by dates, repetition, and predictable substitutions.',
         'Use a unique secret for each account; store it in a password manager.'),
    )
