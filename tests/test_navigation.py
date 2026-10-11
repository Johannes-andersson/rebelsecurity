"""Exercise actual Textual keyboard, mouse, navigation, and exit behavior."""

from unittest.mock import patch

import pytest
from textual.widgets import Button, Input, OptionList

from rebel_security.app import RebelSecurityApp
from rebel_security.config import Settings, load_settings, save_settings
from rebel_security.ui.components import Dashboard, ExitDialog, ModuleScreen
from rebel_security.ui.menus import MODULES


@pytest.mark.parametrize("module", MODULES)
async def test_module_navigation(tmp_path, module):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test(size=(90, 48)) as pilot:
        await pilot.press(module.key)
        assert isinstance(app.screen, ModuleScreen)
        assert app.screen.module == module
        await pilot.press("q")
        assert isinstance(app.screen, ModuleScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, Dashboard)
        await pilot.press(module.key)
        app.screen.query_one("#back").scroll_visible(animate=False, immediate=True)
        await pilot.pause()
        await pilot.click("#back")
        assert isinstance(app.screen, Dashboard)
        assert app.screen.query_one(OptionList).has_focus


async def test_keyboard_and_mouse_menu(tmp_path):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test() as pilot:
        await pilot.press("down", "enter")
        assert app.screen.module.key == "2"
        await pilot.press("escape")
        await pilot.click("#menu", offset=(4, 1))
        assert app.screen.module.key == "1"
        await pilot.press("escape")
        await pilot.press("x", "!", "escape")
        assert isinstance(app.screen, Dashboard)
        app.screen.action_open_module("invalid")
        assert isinstance(app.screen, Dashboard)


@pytest.mark.parametrize("key", ["q", "0", "ctrl+c"])
async def test_exit_confirmation(tmp_path, key):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test() as pilot:
        await pilot.press(key)
        assert isinstance(app.screen, ExitDialog)
        assert app.screen.query_one("#stay", Button).has_focus
        await pilot.press("escape")
        assert isinstance(app.screen, Dashboard)
        await pilot.press(key)
        await pilot.click("#stay")
        assert isinstance(app.screen, Dashboard)
        await pilot.press(key)
        with patch.object(app, "exit") as exit_mock:
            await pilot.click("#exit")
            exit_mock.assert_called_once()


async def test_immediate_exit(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(path, Settings(confirm_exit=False))
    app = RebelSecurityApp(path)
    async with app.run_test() as pilot:
        await pilot.press("q")
        assert not app.is_running


async def test_text_input_cannot_trigger_dashboard_shortcuts(tmp_path):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test() as pilot:
        field = Input()
        await app.screen.mount(field)
        field.focus()
        await pilot.press("q", "0", "9")
        assert field.value == "q09"
        assert isinstance(app.screen, Dashboard)


async def test_unsaved_settings_are_discarded(tmp_path):
    from textual.widgets import Switch

    path = tmp_path / "settings.json"
    app = RebelSecurityApp(path)
    async with app.run_test() as pilot:
        await pilot.press("9")
        app.screen.query_one("#confirm-exit", Switch).value = False
        await pilot.press("escape", "9")
        assert app.screen.query_one("#confirm-exit", Switch).value is True
        assert load_settings(path) == (Settings(), None)
