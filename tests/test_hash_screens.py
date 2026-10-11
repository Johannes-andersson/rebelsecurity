"""Integration checks using only public synthetic inputs."""
import threading
from unittest.mock import patch

import pytest
from textual.widgets import Button, Input, Select, Static, TextArea

from rebel_security.app import RebelSecurityApp
from rebel_security.config import Settings, save_settings
from rebel_security.ui.components import Dashboard


async def click(app, pilot, selector):
    app.screen.query_one(selector).scroll_visible(animate=False, immediate=True)
    await pilot.pause()
    assert await pilot.click(selector)
    await pilot.pause(0.3)


async def finish(app, pilot):
    for _ in range(100):
        if not app.screen.query_one('#run-hash', Button).disabled:
            return
        await pilot.pause(0.05)
    pytest.fail('Background operation did not finish')


@pytest.mark.parametrize('theme', ['rebel-green', 'amber-terminal'])
@pytest.mark.parametrize('width', [32, 90])
async def test_auditor_generate_verify_inspect_and_cleanup(tmp_path, theme, width):
    path = tmp_path / 'settings.json'
    save_settings(path, Settings(theme=theme))
    original = path.read_bytes()
    app = RebelSecurityApp(path)
    async with app.run_test(size=(width, 35)) as pilot:
        await pilot.press('1')
        screen = app.screen
        screen.query_one('#audit-mode', Select).value = 'generate'
        await pilot.pause()
        screen.query_one('#hash-algorithm', Select).value = 'sha512'
        password = screen.query_one('#hash-password', Input)
        assert password.password
        password.value = 'public-synthetic'
        await click(app, pilot, '#run-hash')
        await finish(app, pilot)
        assert password.value == ''
        output = screen.query_one('#hash-output', TextArea)
        assert len(output.text) == 128
        await click(app, pilot, '#inspect-generated')
        assert 'Possible match: SHA-512' in str(screen.query_one('#hash-result', Static).render())
        with patch('rebel_security.ui.hash_screens.copy_secret', return_value=True) as copy:
            await click(app, pilot, '#copy-hash')
            copy.assert_called_once_with(output.text)
            assert screen.query_one('#hash-result').display
            assert 'Copied.' in str(screen.query_one('#hash-result', Static).render())
        screen.query_one('#audit-mode', Select).value = 'verify'
        await pilot.pause()
        password.value = 'public-synthetic'
        await click(app, pilot, '#run-hash')
        await finish(app, pilot)
        assert 'MATCH FOUND' in str(screen.query_one('#hash-result', Static).render())
        assert screen.query_one('.page').max_scroll_x == 0
        await pilot.press('escape')
        assert isinstance(app.screen, Dashboard)
        assert password.value == '' and output.text == '' and screen._copy_value == ''
        assert not screen._payload
        assert path.read_bytes() == original and app.theme == theme


async def test_inspector_clear_and_invalid(tmp_path):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test(size=(40, 30)) as pilot:
        await pilot.press('7')
        field = app.screen.query_one('#hash-input', Input)
        field.value = 'a'*32
        await click(app, pilot, '#inspect-hash')
        assert 'Possible match' in str(app.screen.query_one('#hash-result', Static).render())
        field.value = 'bad-format'
        await click(app, pilot, '#inspect-hash')
        assert 'Unknown' in str(app.screen.query_one('#hash-result', Static).render())
        assert app.screen.query_one('#copy-hash', Button).disabled
        await click(app, pilot, '#clear-hash')
        assert field.value == ''
        field.value = 'a'*32
        await pilot.press('escape')
        assert field.value == ''


async def test_worker_responsive_cancel_and_no_argument_logging(tmp_path):
    started, release = threading.Event(), threading.Event()
    def slow_generate(password, algorithm):
        started.set()
        assert release.wait(10)
        return 'a'*64
    app = RebelSecurityApp(tmp_path / 'settings.json')
    with patch('rebel_security.ui.hash_screens.generate_hash', side_effect=slow_generate):
        async with app.run_test(size=(90, 35)) as pilot:
            await pilot.press('1')
            screen = app.screen
            screen.query_one('#audit-mode', Select).value = 'generate'
            await pilot.pause()
            screen.query_one('#hash-password', Input).value = 'NEVER-LOG-THIS'
            await click(app, pilot, '#run-hash')
            assert started.is_set()
            workers = list(app.workers)
            assert workers and all('NEVER-LOG-THIS' not in repr(w) and 'NEVER-LOG-THIS' not in w.description for w in workers)
            await pilot.resize_terminal(40, 30)
            await click(app, pilot, '#clear-hash')
            assert screen._cancel.is_set()
            await pilot.press('escape')
            assert isinstance(app.screen, Dashboard)
            release.set()
            await pilot.pause(0.3)
            assert not screen._copy_value and not screen._payload


async def test_demo_statistics_and_error_sanitization(tmp_path):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test(size=(80, 40)) as pilot:
        await pilot.press('1')
        app.screen.query_one('#audit-mode', Select).value = 'demo'
        app.screen.query_one('#hash-algorithm', Select).value = 'sha256'
        await pilot.pause()
        await click(app, pilot, '#run-hash')
        await finish(app, pilot)
        result = str(app.screen.query_one('#hash-result', Static).render())
        assert 'MATCH FOUND' in result and 'Candidates tested: 1' in result and 'Measured attempts/second' in result
        app.screen.query_one('#audit-mode', Select).value = 'generate'
        await pilot.pause()
        with patch('rebel_security.ui.hash_screens.generate_hash', side_effect=RuntimeError('PRIVATE')):
            await click(app, pilot, '#run-hash')
            await finish(app, pilot)
        result = str(app.screen.query_one('#hash-result', Static).render())
        assert 'could not complete' in result and 'PRIVATE' not in result


async def test_narrow_demo_clear_and_shutdown(tmp_path):
    app = RebelSecurityApp(tmp_path / 'settings.json')
    async with app.run_test(size=(32, 28)) as pilot:
        await pilot.press('1')
        screen = app.screen
        screen.query_one('#audit-mode', Select).value = 'demo'
        screen.query_one('#hash-algorithm', Select).value = 'sha256'
        screen.query_one('#demo-wordlist', Select).value = 'short'
        await pilot.pause()
        await click(app, pilot, '#run-hash')
        await finish(app, pilot)
        assert 'NOT FOUND' in str(screen.query_one('#hash-result', Static).render())
        assert screen.query_one('.page').max_scroll_x == 0
        assert not screen.query_one('#generated-fields').display
        await click(app, pilot, '#clear-hash')
        screen.query_one('#audit-mode', Select).value = 'generate'
        await pilot.pause()
        password = screen.query_one('#hash-password', Input)
        password.value = 'public-shutdown-test'
    assert password.value == '' and not screen._payload


@pytest.mark.parametrize('theme', ['rebel-green', 'amber-terminal'])
@pytest.mark.parametrize('width', [32, 90])
async def test_verify_default_reference_and_result_visibility(tmp_path, theme, width):
    path = tmp_path / 'settings.json'
    save_settings(path, Settings(theme=theme))
    app = RebelSecurityApp(path)
    reference = '729e9f6700389434fc21cb5575f398781cc71fc22df75100e86b6ffd77ad74ab'
    async with app.run_test(size=(width, 32)) as pilot:
        await pilot.press('1')
        screen = app.screen
        assert screen.query_one('#audit-mode', Select).value == 'verify'
        assert screen.query_one('#verify-fields').display
        assert not screen.query_one('#generated-fields').display
        assert not screen.query_one('#demo-fields').display
        assert not screen.query_one('#cancel-hash').display
        assert not screen.query_one('#hash-result').display
        screen.query_one('#hash-algorithm', Select).value = 'sha256'
        hash_field = screen.query_one('#verify-hash', Input)
        password = screen.query_one('#hash-password', Input)
        hash_field.value = reference
        assert hash_field.region.y < password.region.y
        for candidate, status, style in [('Sidarta', 'MATCH FOUND', 'match'), ('sidarta', 'NO MATCH', 'no-match')]:
            password.value = candidate
            await click(app, pilot, '#run-hash')
            await finish(app, pilot)
            await pilot.pause()
            panel = screen.query_one('#hash-result', Static)
            button = screen.query_one('#run-hash', Button)
            assert status in str(panel.render()) and panel.has_class(style)
            assert password.value == candidate and hash_field.value == reference
            assert app.screen is screen
            assert panel.region.y == button.region.bottom
            assert panel.region.y >= 0 and panel.region.bottom <= app.size.height - 1
            assert screen.query_one('.page').scroll_y > 0
        hash_field.value = 'invalid'
        await click(app, pilot, '#run-hash')
        await finish(app, pilot)
        assert screen.query_one('#hash-result').has_class('invalid')
        assert 'INVALID HASH' in str(screen.query_one('#hash-result', Static).render())
        for mode in ('generate', 'demo', 'verify'):
            screen.query_one('#audit-mode', Select).value = mode
            await pilot.pause()
            assert screen.query_one('#generated-fields').display == (mode == 'generate')
            assert screen.query_one('#verify-fields').display == (mode == 'verify')
            assert screen.query_one('#demo-fields').display == (mode == 'demo')
        await click(app, pilot, '#clear-hash')
        assert not password.value and not hash_field.value
        assert not screen.query_one('#hash-result').display
