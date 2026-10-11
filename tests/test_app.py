"""Startup, durable preferences, recovery, and layout behavior."""

import json
from unittest.mock import patch

import pytest
from textual.widgets import OptionList, Select, Static, Switch

from rebel_security.app import RebelSecurityApp
from rebel_security.config import Settings, load_settings, save_settings
from rebel_security.ui.branding import Branding, LOGO
from rebel_security.ui.components import Dashboard
from rebel_security.utils.helpers import config_path, platform_name


async def test_startup(tmp_path):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, Dashboard)
        menu = app.screen.query_one(OptionList)
        assert menu.option_count == 10
        assert menu.has_focus
        assert app.theme == "rebel-green"
        assert "MODE: OFFLINE" in str(app.screen.query_one(".status", Static).render())
        assert not app.settings_path.exists()


@pytest.mark.parametrize("size", [
    (100, 45), (80, 24), (65, 24), (64, 24), (40, 20), (24, 16),
])
async def test_resize_and_branding(tmp_path, size):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test(size=(100, 45)) as pilot:
        await pilot.resize_terminal(*size)
        await pilot.pause()
        branding = app.screen.query_one(Branding)
        text = branding.render().plain
        assert (LOGO.splitlines()[0] in text) == (size[0] >= 65)
        assert branding.region.right <= size[0]
        assert app.screen.query_one(OptionList).region.right <= size[0]
        if size[0] >= 65:
            assert [line.rstrip() for line in text.splitlines()[:6]] == LOGO.splitlines()
            # Inspect rendered cells as well as the underlying Rich Text.
            assert [branding.render_line(i).text.strip() for i in range(6)] == LOGO.splitlines()
        elif size[0] >= 40:
            lines = text.splitlines()[:4]
            assert lines[0].startswith("╔") and lines[-1].startswith("╚")
            assert len({len(line) for line in lines}) == 1
        await pilot.press("9")
        await pilot.press("escape")
        assert isinstance(app.screen, Dashboard)


@pytest.mark.parametrize("theme, color", [
    ("rebel-green", "#00ff88"), ("amber-terminal", "#ffcc00"),
])
async def test_branding_resize_round_trip(tmp_path, monkeypatch, theme, color):
    monkeypatch.delenv("NO_COLOR", raising=False)
    path = tmp_path / "settings.json"
    save_settings(path, Settings(theme=theme))
    app = RebelSecurityApp(path)
    async with app.run_test(size=(80, 24)) as pilot:
        for width in (80, 64, 65, 40, 100):
            await pilot.resize_terminal(width, 24)
            await pilot.pause()
            branding = app.screen.query_one(Branding)
            assert (LOGO.splitlines()[0] in branding.render().plain) == (width >= 65)
            assert branding.region.y >= 0
            if width >= 65:
                # The actual screen compositor must contain all six art rows.
                screen_lines = [
                    app.screen._compositor.render_strips()[i].text
                    for i in range(24)
                ]
                for line in LOGO.splitlines():
                    assert any(line in visible for visible in screen_lines)
                colors = {
                    segment.style.color.triplet.hex
                    for segment in branding.render_line(0)
                    if segment.style and segment.style.color
                    and segment.style.color.triplet
                }
                assert color in colors
        assert app.theme == theme
        assert load_settings(path)[0].theme == theme


@pytest.mark.parametrize("payload", [
    "broken{", "[]", "null", '{"theme": []}', '{"theme": "unknown"}',
    '{"confirm_exit": "false"}', '{"reduced_motion": 1}',
])
def test_invalid_config(tmp_path, payload):
    path = tmp_path / "settings.json"
    path.write_text(payload)
    settings, warning = load_settings(path)
    assert settings == Settings()
    assert warning
    assert path.read_text() == payload


def test_missing_and_unreadable_config(tmp_path):
    assert load_settings(tmp_path / "missing.json") == (Settings(), None)
    assert load_settings(tmp_path)[1]
    path = tmp_path / "bad-encoding.json"
    path.write_bytes(b"\xff\xfe")
    assert load_settings(path)[1]


async def test_settings_ui_persistence_and_reset(tmp_path):
    path = tmp_path / "nested" / "settings.json"
    app = RebelSecurityApp(path)
    async with app.run_test(size=(90, 48)) as pilot:
        await pilot.press("9")
        app.screen.query_one(Select).value = "amber-terminal"
        app.screen.query_one("#reduced-motion", Switch).value = True
        app.screen.query_one("#confirm-exit", Switch).value = False
        await pilot.click("#save")
        await pilot.pause()
        assert app.settings == Settings("amber-terminal", True, False)
        assert app.theme == "amber-terminal"
        assert app.animation_level == "none"
        assert json.loads(path.read_text())["confirm_exit"] is False
    restarted = RebelSecurityApp(path)
    async with restarted.run_test(size=(90, 48)) as pilot:
        assert restarted.theme == "amber-terminal"
        await pilot.press("9")
        await pilot.click("#reset")
        assert restarted.settings == Settings()
        assert restarted.theme == "rebel-green"
        assert restarted.animation_level == "basic"
        assert load_settings(path) == (Settings(), None)


async def test_save_failure_keeps_previous_settings(tmp_path):
    app = RebelSecurityApp(tmp_path / "settings.json")
    async with app.run_test(size=(90, 48)) as pilot:
        await pilot.press("9")
        app.screen.query_one(Select).value = "amber-terminal"
        with patch("rebel_security.app.save_settings", side_effect=PermissionError):
            await pilot.click("#save")
        assert app.settings == Settings()
        assert not app.settings_path.exists()
        assert "Could not save" in str(app.screen.query_one("#settings-result", Static).render())


def test_atomic_failure_preserves_existing_file(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(path, Settings())
    original = path.read_bytes()
    with patch("rebel_security.config.os.replace", side_effect=OSError):
        with pytest.raises(OSError):
            save_settings(path, Settings(confirm_exit=False))
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("system, label", [
    ("Darwin", "macOS"), ("Linux", "Linux"), ("Windows", "Windows"),
])
def test_platform_paths(monkeypatch, tmp_path, system, label):
    monkeypatch.setattr("platform.system", lambda: system)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    assert platform_name() == label
    expected = {
        "Darwin": tmp_path / "Library" / "Application Support",
        "Linux": tmp_path / "xdg", "Windows": tmp_path / "roaming",
    }
    assert config_path() == expected[system] / "rebel-security" / "settings.json"
