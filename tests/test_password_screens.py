"""UI integration with synthetic test secrets only; never use real credentials."""

from unittest.mock import patch

import pytest
from textual import constants
from textual.widgets import Button, Checkbox, Input, Select, Static

from rebel_security.app import RebelSecurityApp, safe_diagnostic
from rebel_security.config import Settings, save_settings
from rebel_security.ui.components import Dashboard


async def click_visible(app, pilot, selector):
    app.screen.query_one(selector).scroll_visible(animate=False, immediate=True)
    await pilot.pause()
    assert await pilot.click(selector)
    await pilot.pause(0.3)


@pytest.mark.parametrize('key', ['2', '3', '4'])
@pytest.mark.parametrize('theme', ['rebel-green', 'amber-terminal'])
async def test_forms_output_and_cleanup(tmp_path, key, theme):
    path = tmp_path / 'settings.json'
    save_settings(path, Settings(theme=theme))
    original = path.read_bytes()
    app = RebelSecurityApp(path)
    async with app.run_test(size=(90, 40)) as pilot:
        await pilot.press(key)
        screen = app.screen
        if key == '4':
            field = screen.query_one('#password-input', Input)
            assert field.password
            field.value = 'synthetic-password-123'
            await pilot.pause()
            await click_visible(app, pilot, '#show-password')
            assert not field.password
            await click_visible(app, pilot, '#analyze')
            assert screen._guesses is not None
            assert 'Pattern-aware rating:' in str(screen.query_one('#result', Static).render())
            assert 'synthetic-password-123' not in str(screen.query_one('#result', Static).render())
        else:
            await click_visible(app, pilot, '#generate')
            first = screen._secret
            assert first
            assert first in str(screen.query_one('#secret-output', Static).render())
            await click_visible(app, pilot, '#regenerate')
            assert screen._secret and screen._space
            assert not screen.query_one('#copy', Button).disabled
            with patch('rebel_security.ui.password_screens.copy_secret', return_value=True) as copy:
                await click_visible(app, pilot, '#copy')
                copy.assert_called_once_with(screen._secret)
            assert 'Copied to local clipboard' in str(screen.query_one('#form-error', Static).render())
        screen.query_one('#scenario', Select).value = 'custom'
        await pilot.pause()
        screen.query_one('#custom-rate', Input).value = '0'
        await pilot.pause()
        assert 'finite rate' in str(screen.query_one('#time-error', Static).render())
        screen.query_one('#custom-rate', Input).value = '1000'
        await pilot.pause()
        assert 'time:' in str(screen.query_one('#time-result', Static).render())
        await pilot.resize_terminal(40, 24)
        await pilot.press('escape')
        assert isinstance(app.screen, Dashboard)
        assert screen._secret == '' and screen._space is None and screen._guesses is None
        if key == '4':
            assert field.value == ''
        assert path.read_bytes() == original
        assert app.theme == theme


async def test_generator_validation_and_keyboard(tmp_path):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test() as pilot:
        await pilot.press('2')
        field = app.screen.query_one('#length', Input)
        field.value = 'abc'
        await click_visible(app, pilot, '#generate')
        assert 'whole number' in str(app.screen.query_one('#form-error', Static).render())
        field.value = '8'
        for name in ('uppercase', 'lowercase', 'numbers', 'symbols'):
            app.screen.query_one('#' + name, Checkbox).value = False
        await click_visible(app, pilot, '#generate')
        assert 'at least one' in str(app.screen.query_one('#form-error', Static).render())
        app.screen.query_one('#numbers', Checkbox).value = True
        await click_visible(app, pilot, '#generate')
        assert len(app.screen._secret) == 8 and app.screen._secret.isdigit()
        field.focus()
        await pilot.press('q')
        assert app.screen.module.key == '2'
        screen = app.screen
        await click_visible(app, pilot, '#back')
        assert screen._secret == ''


@pytest.mark.parametrize('mode', ['maximum', 'pin', 'custom'])
async def test_advisor_modes(tmp_path, mode):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test() as pilot:
        await pilot.press('3')
        app.screen.query_one('#advisor-mode', Select).value = mode
        await pilot.pause()
        if mode == 'custom':
            app.screen.query_one('#word-count', Input).value = '4'
            app.screen.query_one('#separator', Input).value = '::'
        await click_visible(app, pilot, '#generate')
        value = app.screen._secret
        if mode == 'maximum':
            assert len(value) == 48
        elif mode == 'pin':
            assert len(value) == 8 and value.isdigit()
        else:
            assert len(value.split('::')) == 4
        app.screen.query_one('#advisor-mode', Select).value = 'memorable'
        await pilot.pause()
        assert app.screen._secret == ''


async def test_analyzer_invalid_and_stale_result_clear(tmp_path):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test() as pilot:
        await pilot.press('4')
        await click_visible(app, pilot, '#analyze')
        assert '1 to 128' in str(app.screen.query_one('#form-error', Static).render())
        field = app.screen.query_one('#password-input', Input)
        field.value = 'x' * 129
        await pilot.pause()
        await click_visible(app, pilot, '#analyze')
        assert app.screen._guesses is None
        field.value = 'password'
        await pilot.pause()
        await click_visible(app, pilot, '#analyze')
        assert app.screen._guesses
        field.value = 'different'
        await pilot.pause()
        assert app.screen._guesses is None


@pytest.mark.parametrize('debug', [False, True])
async def test_failure_never_reports_secrets(tmp_path, capsys, debug):
    app = RebelSecurityApp(tmp_path / 'settings.json', debug=debug)
    marker = 'SYNTHETIC_PRIVATE_MARKER'
    with pytest.raises(RuntimeError, match='unexpected error'):
        async with app.run_test() as pilot:
            await pilot.press('4')
            field = app.screen.query_one('#password-input', Input)
            field.value = marker
            await pilot.pause()
            assert constants.LOG_FILE is None
            assert app.devtools is None
            try:
                raise ValueError(marker)
            except ValueError as error:
                assert marker not in safe_diagnostic(error, debug)
                app._handle_exception(error)
    assert field.value == ''
    output = capsys.readouterr()
    assert marker not in output.out + output.err
    assert not app.settings_path.exists()


async def test_exit_clears_input_and_internal_clipboard(tmp_path):
    path = tmp_path / 'settings.json'
    save_settings(path, Settings(confirm_exit=False))
    app = RebelSecurityApp(path)
    async with app.run_test() as pilot:
        await pilot.press('4')
        screen = app.screen
        field = screen.query_one('#password-input', Input)
        field.value = 'SYNTHETIC_EXIT_SECRET'
        app._clipboard = 'SYNTHETIC_EXIT_SECRET'
        await pilot.pause()
        await pilot.press('ctrl+c')
    assert field.value == ''
    assert app.clipboard == ''
    assert screen._secret == '' and screen._guesses is None
