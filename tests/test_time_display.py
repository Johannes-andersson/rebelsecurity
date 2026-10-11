"""Readable duration presentation without changing the security model."""

from decimal import Decimal, localcontext

import pytest
from textual.widgets import Select, Static

from rebel_security.app import RebelSecurityApp
from rebel_security.utils.estimates import (
    NAMED_POWERS, exhaustive_times, format_count, format_duration, pattern_time,
)

YEAR = 31557600


@pytest.mark.parametrize('seconds, expected', [
    (0, '0 seconds'), (Decimal('0.1'), '100 milliseconds'),
    (1, '1 seconds'), (Decimal('12.345'), '12.35 seconds'),
    (60, '1 minutes'), (3600, '1 hours'), (86400, '1 days'),
    (YEAR, '1 years'), (1000 * YEAR, '1 thousand years'),
    (1549382 * YEAR, '1.55 million years'),
    (8749382749283 * YEAR, '8.75 trillion years'),
    (123456789012345678901 * YEAR, '123.46 quintillion years'),
    (372 * 10**40 * YEAR, '3.72e42 years'),
    (482 * 10**37 * YEAR, '4.82e39 years'),
    (914 * 10**55 * YEAR, '9.14e57 years'),
    (10**10000 * YEAR, '1e10000 years'),
], ids=lambda v: 'huge-integer' if isinstance(v, int) and v.bit_length() > 1000 else None)
def test_duration_examples(seconds, expected):
    assert format_duration(seconds) == expected


@pytest.mark.parametrize('power, name', NAMED_POWERS)
def test_each_named_unit(power, name):
    assert format_duration(2 * 10**power * YEAR) == f'2 {name} years'


@pytest.mark.parametrize('seconds, expected', [
    (Decimal('0.999999'), '1 seconds'),
    (Decimal('59.994'), '59.99 seconds'),
    (Decimal('59.995'), '1 minutes'),
    (Decimal('3599.7'), '1 hours'),
    (Decimal('86382'), '1 days'),
    (Decimal(YEAR) - 1, '1 years'),
    (Decimal('999.995') * YEAR, '1 thousand years'),
    (Decimal('999994.99') * YEAR, '999.99 thousand years'),
    (Decimal('999995') * YEAR, '1 million years'),
    (999995 * 10**30 * YEAR, '1e36 years'),
])
def test_rounding_promotes_boundaries(seconds, expected):
    assert format_duration(seconds) == expected


def test_formatting_does_not_mutate_calculations_or_decimal_context():
    rate = Decimal('1000')
    before = exhaustive_times(10**120, rate)
    with localcontext() as context:
        context.prec = 9
        assert format_duration(1549382 * YEAR) == '1.55 million years'
        assert format_duration(123456789012345678901 * YEAR) == '123.46 quintillion years'
        assert context.prec == 9
    format_duration(before.expected)
    format_duration(before.maximum)
    assert exhaustive_times(10**120, rate) == before
    assert exhaustive_times(100, Decimal(10)).expected == Decimal('5.05')
    assert exhaustive_times(100, Decimal(10)).maximum == Decimal(10)
    assert pattern_time(100, Decimal(10)) == Decimal(10)


@pytest.mark.parametrize('value, expected', [
    (10, '10'), (1000, '1 thousand'), (10**9, '1 billion'),
    (10**10000, '1e10000'), (Decimal('0.000001'), '1e-6'),
    (Decimal('999.995'), '1 thousand'),
], ids=lambda v: 'huge-integer' if isinstance(v, int) and v.bit_length() > 1000 else None)
def test_counts_and_rates_are_compact(value, expected):
    assert format_count(value) == expected


@pytest.mark.parametrize('value', [Decimal('-1'), Decimal('NaN'), Decimal('Infinity')])
def test_invalid_duration(value):
    with pytest.raises(ValueError):
        format_duration(value)


@pytest.mark.parametrize('key', ['2', '3', '4'])
@pytest.mark.parametrize('width', [32, 40])
async def test_narrow_result_rendering(tmp_path, key, width):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test(size=(width, 40)) as pilot:
        await pilot.press(key)
        screen = app.screen
        if key == '4':
            screen._guesses = 10**10000
        else:
            screen._space = 10**10000
        screen.query_one('#scenario', Select).value = '1000000000'
        await pilot.pause()
        screen.update_time()
        result = screen.query_one('#time-result', Static)
        result.scroll_visible(animate=False, top=True, immediate=True)
        await pilot.pause()
        plain = result.render().plain
        assert 'Attack rate: 1 billion guesses/second' in plain
        if key == '4':
            assert 'Estimated cracking time:' in plain
            assert 'Worst-case cracking time:' not in plain
            assert 'Estimated guess count: 1e10000' in plain
        else:
            assert 'Expected cracking time:' in plain
            assert 'Worst-case cracking time:' in plain
        assert len(plain) < 400
        assert result.region.right <= width
        assert result.region.x >= 0
        # Check the rendered cells, not merely the logical widget bounds.
        lines = [result.render_line(i).text for i in range(result.size.height)]
        assert all(len(line) <= result.size.width for line in lines)
        assert '1 billion' in ' '.join(lines)
        assert screen.query_one('.page').max_scroll_x == 0
