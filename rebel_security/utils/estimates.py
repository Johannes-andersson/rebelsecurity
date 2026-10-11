"""Educational search models; arbitrary-size integers and Decimal durations."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from math import log2

DISCLAIMER = (
    "Estimates assume a specified offline guessing rate and do not guarantee "
    "real-world resistance. Actual results depend on password selection, "
    "hashing algorithms, hardware, and attack methods."
)


@dataclass(frozen=True)
class GeneratedSecret:
    value: str = field(repr=False)
    search_space: int
    explanation: str

    @property
    def entropy_bits(self) -> float:
        return log2(self.search_space)


def parse_rate(value: str | int | Decimal) -> Decimal:
    """Bound interactive inputs while accepting positive fractional rates."""
    if len(str(value)) > 100:
        raise ValueError("Enter a finite rate between 1e-12 and 1e100.")
    try:
        rate = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a numeric guesses-per-second rate.") from None
    if not rate.is_finite() or not Decimal('1e-12') <= rate <= Decimal('1e100'):
        raise ValueError("Enter a finite rate between 1e-12 and 1e100.")
    return rate


@dataclass(frozen=True)
class SearchTimes:
    expected: Decimal
    maximum: Decimal


def exhaustive_times(space: int, rate: Decimal) -> SearchTimes:
    """Uniform target, ordered exhaustive search without replacement."""
    if type(space) is not int or space < 1:
        raise ValueError("Search space must be a positive integer.")
    rate = parse_rate(rate)
    with localcontext() as context:
        context.prec = 40
        return SearchTimes((Decimal(space) + 1) / (2 * rate), Decimal(space) / rate)


def pattern_time(guesses: int, rate: Decimal) -> Decimal:
    if type(guesses) is not int or guesses < 1:
        raise ValueError("Guess estimate must be a positive integer.")
    with localcontext() as context:
        context.prec = 40
        return Decimal(guesses) / parse_rate(rate)


YEAR_SECONDS = Decimal(31557600)
NAMED_POWERS = (
    (3, 'thousand'), (6, 'million'), (9, 'billion'), (12, 'trillion'),
    (15, 'quadrillion'), (18, 'quintillion'), (21, 'sextillion'),
    (24, 'septillion'), (27, 'octillion'), (30, 'nonillion'), (33, 'decillion'),
)


def _scientific(value: Decimal) -> str:
    # ASCII fallback works independently of terminal/font superscript support.
    mantissa, exponent = f'{value:.2E}'.split('E')
    return f"{mantissa.rstrip('0').rstrip('.')}e{int(exponent)}"


def _abbreviate(value: Decimal, units: tuple[tuple[Decimal, str], ...],
                scientific_at: Decimal, scientific_scale: Decimal,
                scientific_label: str) -> str:
    """Round only the presentation; promote rounded values at unit boundaries."""
    with localcontext() as context:
        context.prec = max(40, len(value.as_tuple().digits) + 4)
        context.rounding = ROUND_HALF_UP
        if value >= scientific_at:
            return f'{_scientific(value / scientific_scale)} {scientific_label}'.strip()
        index = next(i for i in reversed(range(len(units))) if value >= units[i][0])
        while True:
            factor, label = units[index]
            rounded = (value / factor).quantize(Decimal('0.01'))
            next_factor = units[index + 1][0] if index + 1 < len(units) else scientific_at
            if rounded * factor >= next_factor:
                if index + 1 == len(units):
                    return f'{_scientific(value / scientific_scale)} {scientific_label}'.strip()
                index += 1
                continue
            number = format(rounded, 'f').rstrip('0').rstrip('.')
            return f'{number} {label}'.strip()


def format_count(value: int | Decimal) -> str:
    """Abbreviate rates and guess counts so they cannot flood the interface."""
    value = Decimal(value)
    if not value.is_finite() or value < 0:
        raise ValueError('Count must be finite and nonnegative.')
    if value == 0:
        return '0'
    if value < Decimal('0.01'):
        return _scientific(value)
    if value < 1:
        return f'{value:.2f}'.rstrip('0').rstrip('.')
    units = ((Decimal(1), ''),) + tuple(
        (Decimal(10**power), name) for power, name in NAMED_POWERS
    )
    return _abbreviate(value, units, Decimal(10**36), Decimal(1), '')


def format_duration(seconds: Decimal | int) -> str:
    seconds = Decimal(seconds)
    if not seconds.is_finite() or seconds < 0:
        raise ValueError('Duration must be finite and nonnegative.')
    if seconds == 0:
        return '0 seconds'
    if seconds < Decimal('0.001'):
        return 'less than 1 millisecond'
    # Construct thresholds with integers, independent of ambient Decimal precision.
    units = (
        (Decimal('0.001'), 'milliseconds'), (Decimal(1), 'seconds'),
        (Decimal(60), 'minutes'), (Decimal(3600), 'hours'),
        (Decimal(86400), 'days'), (YEAR_SECONDS, 'years'),
    ) + tuple((Decimal(31557600 * 10**power), name + ' years')
              for power, name in NAMED_POWERS)
    return _abbreviate(seconds, units, Decimal(31557600 * 10**36), YEAR_SECONDS, 'years')
