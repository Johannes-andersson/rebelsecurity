"""Milestone 2 forms; secrets stay only in the current screen's memory."""

from rich.text import Text

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Input, Select, Static

from rebel_security.modules.advisor import (
    PassphraseOptions, generate_maximum, generate_passphrase, generate_pin,
)
from rebel_security.modules.analyzer import analyze_password
from rebel_security.modules.generator import PasswordOptions, generate_password
from rebel_security.ui.components import ModuleScreen
from rebel_security.utils.clipboard import copy_secret
from rebel_security.utils.estimates import (
    DISCLAIMER, GeneratedSecret, exhaustive_times, format_count, format_duration,
    parse_rate, pattern_time,
)


class SecretInput(Input):
    """Clear the value even when shutdown detaches children before their screen."""

    def on_unmount(self) -> None:
        self.value = ''
        self.password = True


class SecretScreen(ModuleScreen):
    """Shared result and rate controls; no secret is written to settings."""

    def __init__(self, module):
        super().__init__(module)
        self._secret = ''
        self._space: int | None = None
        self._guesses: int | None = None

    def form(self) -> ComposeResult:
        yield from ()

    def content(self) -> ComposeResult:
        yield from self.form()
        yield Static('', id='form-error', classes='form-error', markup=False)
        if self.module.key != '4':
            yield Static('GENERATED PASSWORD', classes='title')
            yield Static('', id='secret-output', classes='secret-output', markup=False)
            yield Button('Copy generated password', id='copy', disabled=True)
            yield Static(
                'Copy only on request. Clipboard contents may be accessible to other '
                'applications or synced by your OS. No automatic clearing.', classes='hint',
            )
        yield Static('', id='result', markup=False)
        yield Static('ESTIMATED OFFLINE GUESSING TIME', classes='title')
        yield Select([
            ('10 guesses / second', '10'), ('1,000 guesses / second', '1000'),
            ('1 million guesses / second', '1000000'),
            ('1 billion guesses / second', '1000000000'), ('Custom rate', 'custom'),
        ], value='1000000', allow_blank=False, id='scenario')
        with Vertical(id='custom-rate-row'):
            yield Static('Custom guesses / second (positive; scientific notation allowed)')
            yield Input('1000000', id='custom-rate', max_length=100)
        yield Static('', id='time-error', markup=False)
        yield Static('Generate or analyze a password to see estimates.', id='time-result', markup=False)
        yield Static('Illustrative offline rates, not hardware benchmarks. ' + DISCLAIMER, classes='hint')

    def on_mount(self) -> None:
        self.query_one('#custom-rate-row').display = False
        self.query_one(Input).focus()

    def number(self, selector: str, label: str) -> int:
        try:
            return int(self.query_one(selector, Input).value)
        except ValueError:
            raise ValueError(f'{label} must be a whole number.') from None

    def clear_result(self) -> None:
        self._secret = ''
        self._space = None
        self._guesses = None
        for selector in ('#secret-output', '#result', '#form-error', '#time-error'):
            for widget in self.query(selector):
                widget.update('')
        for button in self.query('#copy'):
            button.disabled = True
        for widget in self.query('#time-result'):
            widget.update('Generate or analyze a password to see estimates.')

    def clear_sensitive(self) -> None:
        self.clear_result()
        # Native Input copy/cut can populate Textual's in-process clipboard.
        # Release that copy without modifying the user's system clipboard.
        self.app._clipboard = ''
        for field in self.query('#password-input'):
            field.value = ''
            field.password = True

    def action_back(self) -> None:
        self.clear_sensitive()
        super().action_back()

    def on_unmount(self) -> None:
        self.clear_sensitive()

    def show_generated(self, generated: GeneratedSecret) -> None:
        self._secret = generated.value
        self._space = generated.search_space
        self.query_one('#secret-output', Static).update(self._secret)
        self.query_one('#copy', Button).disabled = False
        self.query_one('#result', Static).update(
            f'Generation entropy: ~{generated.entropy_bits:.2f} bits\n'
            + generated.explanation
        )
        self.update_time()
        self.query_one('#secret-output').scroll_visible(animate=False, top=True)

    @on(Button.Pressed, '#copy')
    def copy(self) -> None:
        message = ('Copied to local clipboard. Other applications may read it.'
                   if copy_secret(self._secret)
                   else 'Clipboard unavailable. No copy was confirmed.')
        self.query_one('#form-error', Static).update(message)

    @on(Select.Changed, '#scenario')
    def scenario_changed(self) -> None:
        if self.is_mounted:
            self.query_one('#custom-rate-row').display = (
                self.query_one('#scenario', Select).value == 'custom'
            )
            self.update_time()

    @on(Input.Changed, '#custom-rate')
    def rate_changed(self) -> None:
        if self.is_mounted:
            self.update_time()

    def update_time(self) -> None:
        self.query_one('#time-error', Static).update('')
        if self._space is None and self._guesses is None:
            return
        choice = self.query_one('#scenario', Select).value
        try:
            rate = parse_rate(self.query_one('#custom-rate', Input).value
                              if choice == 'custom' else str(choice))
            primary = self.app.current_theme.primary
            text = Text()
            if self._space is not None:
                times = exhaustive_times(self._space, rate)
                text.append('Expected cracking time:\n', style='bold')
                text.append(format_duration(times.expected).upper(), style=f'bold {primary}')
                text.append(f'\nAttack rate: {format_count(rate)} guesses/second\n\n')
                text.append('Worst-case cracking time:\n', style='bold')
                text.append(format_duration(times.maximum).upper(), style=f'bold {primary}')
                text.append('\nTheoretical exhaustive search (uniform generated target).')
            else:
                text.append('Estimated cracking time:\n', style='bold')
                duration = pattern_time(self._guesses, rate)
                text.append(format_duration(duration).upper(), style=f'bold {primary}')
                text.append(f'\nAttack rate: {format_count(rate)} guesses/second\n\n')
                text.append(
                    'Pattern-aware estimate (zxcvbn)\n'
                    f'Estimated guess count: {format_count(self._guesses)}\n'
                    'Not an exhaustive maximum or a guaranteed expected time.'
                )
            self.query_one('#time-result', Static).update(text)
        except ValueError as error:
            self.query_one('#time-result', Static).update('Estimate unavailable for this rate.')
            self.query_one('#time-error', Static).update(str(error))


class GeneratorScreen(SecretScreen):
    def form(self) -> ComposeResult:
        yield Static('REBEL FORGE', classes='title')
        yield Static('Password length (8–128)')
        yield Input('24', id='length', max_length=3)
        for name, label, enabled in (
            ('uppercase', 'Uppercase letters', True),
            ('lowercase', 'Lowercase letters', True), ('numbers', 'Numbers', True),
            ('symbols', 'Special characters', True),
            ('exclude-ambiguous', 'Exclude ambiguous characters (0 O o 1 l I)', False),
        ):
            yield Checkbox(label, value=enabled, id=name, compact=True)
        with Horizontal(classes='secret-actions'):
            yield Button('Generate password', id='generate', variant='primary')
            yield Button('Regenerate', id='regenerate')

    @on(Button.Pressed, '#generate')
    @on(Button.Pressed, '#regenerate')
    def generate(self) -> None:
        self.clear_result()
        try:
            options = PasswordOptions(
                length=self.number('#length', 'Length'),
                **{name: self.query_one('#' + name.replace('_', '-'), Checkbox).value
                   for name in ('uppercase', 'lowercase', 'numbers', 'symbols', 'exclude_ambiguous')},
            )
            self.show_generated(generate_password(options))
        except ValueError as error:
            self.query_one('#form-error', Static).update(str(error))
            self.query_one('#form-error').scroll_visible(animate=False, top=True)


class AdvisorScreen(SecretScreen):
    def form(self) -> ComposeResult:
        yield Select([
            ('Memorable passphrase', 'memorable'), ('Maximum security (48 characters)', 'maximum'),
            ('PIN / numeric password', 'pin'), ('Custom passphrase', 'custom'),
        ], value='memorable', allow_blank=False, id='advisor-mode')
        with Vertical(id='phrase-options'):
            yield Static('Word count (4–10; default 6)')
            yield Input('6', id='word-count', max_length=2)
            yield Static('Separator (1–8 punctuation characters or spaces)')
            yield Input('-', id='separator', max_length=8)
            yield Checkbox('Capitalize words', value=True, id='capitalize', compact=True)
            yield Static('Additional random digits (0–10)')
            yield Input('0', id='extra-digits', max_length=2)
        with Vertical(id='pin-options'):
            yield Static('Numeric password length (6–20)')
            yield Input('8', id='pin-length', max_length=2)
            yield Static('Short PINs rely heavily on rate limiting and authentication context.', classes='hint')
        with Horizontal(classes='secret-actions'):
            yield Button('Generate password', id='generate', variant='primary')
            yield Button('Regenerate', id='regenerate')

    def on_mount(self) -> None:
        super().on_mount()
        self.mode_changed()

    @on(Select.Changed, '#advisor-mode')
    def mode_changed(self) -> None:
        if self.is_mounted:
            mode = self.query_one('#advisor-mode', Select).value
            self.query_one('#phrase-options').display = mode in ('memorable', 'custom')
            self.query_one('#pin-options').display = mode == 'pin'
            self.clear_result()

    @on(Button.Pressed, '#generate')
    @on(Button.Pressed, '#regenerate')
    def generate(self) -> None:
        self.clear_result()
        try:
            mode = self.query_one('#advisor-mode', Select).value
            if mode == 'maximum':
                generated = generate_maximum()
            elif mode == 'pin':
                generated = generate_pin(self.number('#pin-length', 'PIN length'))
            else:
                generated = generate_passphrase(PassphraseOptions(
                    self.number('#word-count', 'Word count'),
                    self.query_one('#separator', Input).value,
                    self.query_one('#capitalize', Checkbox).value,
                    self.number('#extra-digits', 'Additional digits'),
                ))
            self.show_generated(generated)
        except ValueError as error:
            self.query_one('#form-error', Static).update(str(error))
            self.query_one('#form-error').scroll_visible(animate=False, top=True)


class AnalyzerScreen(SecretScreen):
    def form(self) -> ComposeResult:
        yield Static('Password to analyze (1–128 characters; never saved)')
        # No max_length truncation: the logic explicitly rejects oversized input.
        yield SecretInput(password=True, id='password-input')
        yield Checkbox('Show password', id='show-password', compact=True)
        yield Button('Analyze password', id='analyze', variant='primary')
        yield Static(
            'Pattern estimates can miss languages, personal information, and new '
            'attack techniques. Character diversity alone does not imply strength.', classes='hint',
        )

    @on(Checkbox.Changed, '#show-password')
    def toggle_password(self, event: Checkbox.Changed) -> None:
        self.query_one('#password-input', Input).password = not event.value

    @on(Input.Changed, '#password-input')
    def password_changed(self) -> None:
        if self.is_mounted:
            self.clear_result()

    @on(Button.Pressed, '#analyze')
    def analyze(self) -> None:
        self.clear_result()
        try:
            analysis = analyze_password(self.query_one('#password-input', Input).value)
            self._guesses = analysis.guesses
            weaknesses = analysis.weaknesses or ('No major known pattern detected; not a security guarantee.',)
            self.query_one('#result', Static).update(
                f'Password length: {analysis.length}\nCharacter categories: {analysis.categories}\n'
                f'Pattern-aware rating: {analysis.rating}\n\nDetected weaknesses:\n'
                + '\n'.join('- ' + item for item in weaknesses)
                + '\n\nRecommendations:\n'
                + '\n'.join('- ' + item for item in analysis.recommendations)
            )
            self.update_time()
            self.query_one('#result').scroll_visible(animate=False, top=True)
        except ValueError:
            # Third-party exceptions must not echo the supplied password.
            self.query_one('#form-error', Static).update('Enter a password from 1 to 128 characters.')
