"""Offline hash tools with bounded, cancellable background work."""
from threading import Event, Lock

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Checkbox, Input, Select, Static, TextArea

from rebel_security.modules.auditor import EXAMPLES, WORDLISTS, run_demo
from rebel_security.ui.components import ModuleScreen
from rebel_security.ui.password_screens import SecretInput
from rebel_security.utils.clipboard import copy_secret
from rebel_security.utils.hashing import ALGORITHMS, HashError, generate_hash, inspect_hash, verify_hash

# Serialize expensive KDF calls, including workers finishing after a screen closes.
_CRYPTO_LOCK = Lock()


class HashOutput(TextArea):
    def on_unmount(self):
        self.load_text('')


class HashScreen(ModuleScreen):
    def __init__(self, module):
        super().__init__(module)
        self._cancel = Event()
        self._generation = 0
        self._copy_value = ''
        self._payload = {}

    def clear_sensitive(self):
        self._cancel.set()
        self._payload.clear()
        self._generation += 1
        self._copy_value = ''
        for field in self.query(Input):
            field.value = ''
        for field in self.query('#hash-password'):
            field.password = True
        for checkbox in self.query('#show-hash-password'):
            checkbox.value = False
        for field in self.query(TextArea):
            field.load_text('')
        for field in self.query('#hash-result'):
            field.update('')
        for button in self.query('#copy-hash'):
            button.disabled = True
        self.app._clipboard = ''

    def action_back(self):
        self.clear_sensitive()
        super().action_back()

    def on_unmount(self):
        self.clear_sensitive()

    @on(Button.Pressed, '#clear-hash')
    def clear(self):
        self.clear_sensitive()
        self.set_busy(False)

    def set_busy(self, busy):
        for button in self.query('#run-hash'):
            button.disabled = busy

    @on(Button.Pressed, '#copy-hash')
    def copy(self):
        if self._copy_value:
            ok = copy_secret(self._copy_value)
            self.show_result(
                'Copied. Clipboard may be retained by other applications.' if ok else 'Clipboard unavailable.')

    def show_result(self, text):
        self.query_one('#hash-result', Static).update(text)
        self.query_one('#hash-result').scroll_visible(animate=False)


class InspectorScreen(HashScreen):
    def content(self) -> ComposeResult:
        yield Static('Enter hash (format recognition is not proof of the algorithm).', classes='hint')
        yield SecretInput(placeholder='Paste a hash', id='hash-input')
        yield Button('Inspect hash', id='inspect-hash', variant='primary')
        yield Button('Clear', id='clear-hash')
        yield Button('Copy inspection', id='copy-hash', disabled=True)
        yield Static('', id='hash-result', markup=False)

    @on(Button.Pressed, '#inspect-hash')
    def inspect(self):
        try:
            self._copy_value = inspect_hash(self.query_one('#hash-input', Input).value.strip()).summary()
            self.show_result(self._copy_value)
            self.query_one('#copy-hash', Button).disabled = False
        except HashError as error:
            self._copy_value = ''
            self.query_one('#copy-hash', Button).disabled = True
            self.show_result(str(error))


class AuditorScreen(HashScreen):
    def content(self) -> ComposeResult:
        yield Static('MODE: OFFLINE • Password hashing is not encryption.', classes='hint')
        yield Select([('Verify password', 'verify'), ('Generate hash', 'generate'),
                      ('Local audit demonstration', 'demo')], value='verify', allow_blank=False, id='audit-mode')
        yield Static('Hash algorithm')
        yield Select([(label, key) for key, label in ALGORITHMS.items()], value='argon2id', allow_blank=False, id='hash-algorithm')
        yield Static('MD5 and SHA hashes are fast general-purpose hashes, unsuitable for direct modern password storage. '
                     'Included for education and legacy compatibility. Prefer Argon2id.', classes='hint', id='hash-guidance')
        with Vertical(id='verify-fields'):
            yield Static('Hash to verify')
            yield SecretInput(placeholder='Paste hash', id='verify-hash')
        with Vertical(id='candidate-fields'):
            yield Static('Password')
            yield SecretInput(password=True, id='hash-password')
            yield Checkbox('Show password', id='show-hash-password')
        with Vertical(id='demo-fields'):
            yield Static('Built-in example password (public test data only)')
            yield Select([(value, value) for value in EXAMPLES], value='password', allow_blank=False, id='demo-example')
            yield Static('Small demonstration wordlist')
            yield Select([('Common examples (6 candidates)', 'common'), ('Short examples (3 candidates)', 'short')],
                         value='common', allow_blank=False, id='demo-wordlist')
            yield Static('Creates a fresh local fixture, then tests only the selected built-in candidates. '
                         'Cancel stops after the current bounded hash operation.', classes='hint')
        yield Button('Verify password', id='run-hash', variant='primary')
        yield Static('', id='hash-result', markup=False)
        yield Button('Cancel', id='cancel-hash')
        yield Button('Clear', id='clear-hash')
        with Vertical(id='generated-fields'):
            yield Static('Generated hash (scroll to view long values)', classes='hint')
            yield HashOutput('', read_only=True, soft_wrap=False, id='hash-output')
            yield Button('Inspect generated hash', id='inspect-generated')
            yield Button('Copy generated hash', id='copy-hash', disabled=True)

    def on_mount(self):
        self.update_mode()

    def show_result(self, text):
        panel = self.query_one('#hash-result', Static)
        panel.update(text)
        panel.display = bool(text)
        panel.set_classes('match' if text.startswith('MATCH FOUND') else
                          'no-match' if text.startswith('NO MATCH') else
                          'invalid' if text.startswith('INVALID HASH') else '')
        if text:
            # Scroll after the new content has been laid out; keep the same screen.
            self.call_after_refresh(panel.scroll_visible, animate=False, immediate=True)

    def clear_sensitive(self):
        super().clear_sensitive()
        for panel in self.query('#hash-result'):
            panel.display = False

    @on(Select.Changed, '#audit-mode')
    def mode_changed(self):
        self._cancel.set()
        self._payload.clear()
        self._generation += 1
        self.query_one('#hash-password', Input).value = ''
        self.query_one('#hash-password', Input).password = True
        self.query_one('#show-hash-password', Checkbox).value = False
        self.query_one('#hash-result', Static).update('')
        self.query_one('#hash-result').display = False
        self.set_busy(False)
        self.update_mode()

    def update_mode(self):
        mode = self.query_one('#audit-mode', Select).value
        self.query_one('#candidate-fields').display = mode != 'demo'
        self.query_one('#verify-fields').display = mode == 'verify'
        self.query_one('#demo-fields').display = mode == 'demo'
        self.query_one('#generated-fields').display = mode == 'generate'
        self.query_one('#hash-guidance').display = mode == 'generate'
        self.query_one('#cancel-hash').display = mode == 'demo'
        self.query_one('#run-hash', Button).label = {
            'generate': 'Generate hash', 'verify': 'Verify password', 'demo': 'Run local demo',
        }[mode]

    @on(Checkbox.Changed, '#show-hash-password')
    def show_password(self, event):
        self.query_one('#hash-password', Input).password = not event.value

    @on(Button.Pressed, '#inspect-generated')
    def inspect_generated(self):
        if self._copy_value:
            self.show_result(inspect_hash(self._copy_value).summary())
        else:
            self.show_result('Generate a hash first.')

    @on(Button.Pressed, '#cancel-hash')
    def cancel(self):
        self._cancel.set()
        self._payload.clear()
        self.query_one('#hash-password', Input).value = ''
        self.show_result('Cancellation requested. Waiting for any current bounded operation to finish.')

    @on(Button.Pressed, '#run-hash')
    def run(self):
        self._cancel.set()
        self._payload.clear()
        self._cancel = Event()
        self._generation += 1
        mode = str(self.query_one('#audit-mode', Select).value)
        password = self.query_one('#hash-password', Input).value
        encoded = self.query_one('#verify-hash', Input).value.strip()
        algorithm = str(self.query_one('#hash-algorithm', Select).value)
        example = str(self.query_one('#demo-example', Select).value)
        wordlist = str(self.query_one('#demo-wordlist', Select).value)
        if mode != 'verify':
            self.query_one('#hash-password', Input).value = ''
        self.set_busy(True)
        self.show_result('Generating fixture…' if mode == 'demo' else 'Working locally…')
        self._payload = {'password': password, 'encoded': encoded}
        self.execute(self._generation, self._cancel, mode, self._payload, algorithm, example, wordlist)

    def deliver(self, generation, text, generated=None, finished=True):
        if generation != self._generation or not self.is_mounted:
            return
        self.show_result(text)
        if generated is not None and not self._cancel.is_set():
            self._copy_value = generated
            self.query_one('#hash-output', TextArea).load_text(generated)
            self.query_one('#verify-hash', Input).value = generated
            self.query_one('#copy-hash', Button).disabled = False
        if finished:
            self.set_busy(False)

    @work(thread=True, exit_on_error=False, description="Local password hashing")
    def execute(self, generation, cancel, mode, payload, algorithm, example, wordlist):
        acquired = False
        try:
            while not cancel.is_set():
                acquired = _CRYPTO_LOCK.acquire(timeout=0.05)
                if acquired:
                    break
            password = payload.pop('password', '')
            encoded = payload.pop('encoded', '')
            if cancel.is_set():
                result, generated = 'CANCELLED', None
            elif mode == 'generate':
                generated = generate_hash(password, algorithm)
                result = 'Hash generated. Inspect it below or switch to Verify password.'
            elif mode == 'verify':
                generated = None
                result = ('MATCH FOUND\nThe candidate matches the supplied hash.'
                          if verify_hash(password, encoded, algorithm) else
                          'NO MATCH\nThe candidate does not match. Passwords are case-sensitive.')
            else:
                generated = None
                def progress(count):
                    self.app.call_from_thread(self.deliver, generation, f'Candidates tested: {count}', None, False)
                result = run_demo(example, algorithm, wordlist, cancel, progress).summary()
            if cancel.is_set() and mode != 'demo':
                result, generated = 'CANCELLED', None
            self.app.call_from_thread(self.deliver, generation, result, generated)
        except HashError as error:
            self.app.call_from_thread(self.deliver, generation, 'INVALID HASH / INPUT\n' + str(error))
        except Exception:
            # Do not expose library exception strings, arguments, or user inputs.
            try:
                self.app.call_from_thread(self.deliver, generation, 'Local hashing operation could not complete.')
            except RuntimeError:
                pass  # Application already closed.
        finally:
            password = encoded = ''
            payload.clear()
            if acquired:
                _CRYPTO_LOCK.release()
