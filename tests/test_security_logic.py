"""Mathematical cases, safe summaries, validation, and randomness contracts."""

from decimal import Decimal
from itertools import product
from math import log2
import string
from unittest.mock import patch

import pytest

from rebel_security.modules.generator import (
    AMBIGUOUS, PasswordOptions, constrained_space, generate_password,
)
from rebel_security.modules.advisor import (
    PassphraseOptions, generate_maximum, generate_passphrase, generate_pin,
)
from rebel_security.modules.analyzer import analyze_password
from rebel_security.utils.estimates import (
    exhaustive_times, format_duration, parse_rate, pattern_time,
)
from rebel_security.utils.wordlist import load_words
from rebel_security.utils.clipboard import copy_secret


@pytest.mark.parametrize('length', [8, 24, 128])
@pytest.mark.parametrize('flags', list(product([False, True], repeat=4))[1:])
def test_password_categories(length, flags):
    options = PasswordOptions(length, *flags, exclude_ambiguous=True)
    secret = generate_password(options)
    assert len(secret.value) == length
    groups = options.categories()
    assert set(secret.value) <= set(''.join(groups))
    assert not set(secret.value) & AMBIGUOUS
    assert all(set(secret.value) & set(group) for group in groups)
    assert secret.entropy_bits <= length * log2(sum(map(len, groups)))
    assert secret.value not in repr(secret)


@pytest.mark.parametrize('options', [
    PasswordOptions(7), PasswordOptions(129), PasswordOptions(True),
    PasswordOptions(uppercase=False, lowercase=False, numbers=False, symbols=False),
    PasswordOptions(symbols=1),
])
def test_password_invalid(options):
    with pytest.raises(ValueError):
        generate_password(options)


def test_rejection_uses_secrets_and_retains_category_constraints():
    # First candidate misses uppercase and is rejected; second is valid.
    stream = iter('aaaaaaaa' + 'Abcdefgh')
    with patch('rebel_security.modules.generator.secrets.choice', side_effect=lambda _: next(stream)) as choice:
        result = generate_password(PasswordOptions(8, numbers=False, symbols=False))
        assert result.value == 'Abcdefgh'
        assert choice.call_count == 16
        assert set(choice.call_args.args[0]) == set(string.ascii_letters)


@pytest.mark.parametrize('length, sizes', [(2, (1, 1)), (3, (2, 1)), (4, (1, 1, 1))])
def test_constrained_space_against_enumeration(length, sizes):
    alphabet = list(range(sum(sizes)))
    groups = []
    offset = 0
    for size in sizes:
        groups.append(set(alphabet[offset:offset + size]))
        offset += size
    valid = sum(all(set(candidate) & group for group in groups)
                for candidate in product(alphabet, repeat=length))
    assert constrained_space(length, sizes) == valid
    assert constrained_space(8, (10,)) == 10**8
    assert constrained_space(2, (1, 1)) == 2


def test_passphrase_wordlist_and_random_selection():
    words = load_words()
    assert len(words) == len(set(words)) == 7772
    assert all(word.isalpha() and word.isascii() for word in words)
    with patch('rebel_security.modules.advisor.secrets.choice', side_effect=lambda seq: seq[0]) as choice:
        secret = generate_passphrase(PassphraseOptions(5, '::', False, 2))
        assert secret.value == '::'.join([words[0]] * 5) + '::00'
        assert choice.call_count == 7
    assert secret.search_space == 7772**5 * 100
    assert secret.entropy_bits == pytest.approx(5 * log2(7772) + log2(100))
    default = generate_passphrase()
    assert len(default.value.split('-')) == 6
    assert all(word.lower() in words for word in default.value.split('-'))


@pytest.mark.parametrize('options', [
    PassphraseOptions(3), PassphraseOptions(11), PassphraseOptions(separator=''),
    PassphraseOptions(separator='abc'), PassphraseOptions(separator='\n'),
    PassphraseOptions(extra_digits=-1), PassphraseOptions(extra_digits=11),
])
def test_passphrase_validation(options):
    with pytest.raises(ValueError):
        generate_passphrase(options)


@pytest.mark.parametrize('length', [6, 8, 20])
def test_pin(length):
    with patch('rebel_security.modules.advisor.secrets.choice', return_value='0'):
        result = generate_pin(length)
    assert result.value == '0' * length
    assert result.search_space == 10**length
    assert 'rate limiting' in result.explanation


@pytest.mark.parametrize('length', [5, 21, True])
def test_pin_invalid(length):
    with pytest.raises(ValueError):
        generate_pin(length)


def test_maximum():
    assert len(generate_maximum().value) == 48


def test_times_and_custom_rate():
    times = exhaustive_times(100, Decimal('10'))
    assert times.expected == Decimal('5.05')
    assert times.maximum == 10
    assert exhaustive_times(1, Decimal('0.5')).expected == 2
    assert pattern_time(100, Decimal('10')) == 10
    assert parse_rate('1e9') == 10**9
    assert exhaustive_times(10**10000, Decimal('1e-12')).maximum.is_finite()


@pytest.mark.parametrize('value', ['0', '-1', 'NaN', 'Infinity', 'abc', '1e101', '1e-13'])
def test_invalid_rate(value):
    with pytest.raises(ValueError):
        parse_rate(value)


@pytest.mark.parametrize('seconds, unit', [
    ('0', 'seconds'), ('0.0001', 'less than 1 millisecond'), ('0.1', 'milliseconds'),
    ('1', 'seconds'), ('60', 'minutes'), ('3600', 'hours'), ('86400', 'days'),
    ('31557600', 'years'), ('31557600000000', 'million years'),
    ('31557600000000000', 'billion years'), ('31557600000000000000', 'trillion years'),
    ('1e1000', 'e'),
])
def test_duration_units(seconds, unit):
    assert unit in format_duration(Decimal(seconds))


@pytest.mark.parametrize('secret, weakness', [
    ('password', 'dictionary'), ('aaaaaaaaaaaa', 'Repeated'),
    ('abcdefghijk', 'Sequential'), ('qwertyuiop', 'Keyboard'),
    ('p@ssw0rd', 'substitutions'),
])
def test_analyzer_patterns(secret, weakness):
    result = analyze_password(secret)
    assert result.score <= 2
    # qwerty may be recognized as a common password rather than spatial pattern.
    if secret == 'qwertyuiop':
        assert any('Keyboard' in item or 'dictionary' in item for item in result.weaknesses)
    else:
        assert any(weakness in item for item in result.weaknesses)
    assert not hasattr(result, 'password')
    assert not hasattr(result, 'sequence')
    assert result.recommendations


def test_analyzer_strong_and_safe_empty():
    assert analyze_password('K8!vzP2$mdR7@qL5#xT9&bW3').score == 4
    for value in ('', 'x' * 129):
        with pytest.raises(ValueError):
            analyze_password(value)


def test_clipboard_success_and_failure():
    with (patch('rebel_security.utils.clipboard.pyperclip.copy') as copy,
          patch('rebel_security.utils.clipboard.pyperclip.paste', return_value='synthetic-test-only')):
        assert copy_secret('synthetic-test-only')
        copy.assert_called_once_with('synthetic-test-only')
    with patch('rebel_security.utils.clipboard.pyperclip.copy', side_effect=RuntimeError('secret')):
        assert not copy_secret('synthetic-test-only')
    assert not copy_secret('')
