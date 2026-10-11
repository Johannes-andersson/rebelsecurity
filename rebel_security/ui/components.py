"""Native Textual screens for the dashboard, modules, and preferences."""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, OptionList, Select, Static, Switch, TextArea
from textual.widgets.option_list import Option

from rebel_security import __version__
from rebel_security.config import Settings, THEMES
from rebel_security.ui.branding import Branding
from rebel_security.ui.menus import MODULES, Module
from rebel_security.utils.helpers import platform_name


class Dashboard(Screen):
    BINDINGS = [
        Binding(str(i), f"open_module('{i}')", show=False) for i in range(1, 10)
    ] + [Binding("q,0", "request_exit", "Exit")]

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="page"):
            with Vertical(classes="body"):
                yield Branding()
                yield OptionList(
                    *(Option(f"[{int(m.key):02}] {m.title}", id=m.key) for m in MODULES),
                    Option("[00] EXIT", id="0"), id="menu",
                )
                yield Static(
                    f"APPLICATION: REBEL SECURITY  |  VERSION: {__version__}\n"
                    f"MODE: OFFLINE  |  PLATFORM: {platform_name()}  |  STATUS: READY",
                    classes="status", markup=False,
                )
                yield Static('"Security begins with understanding."', classes="quote")
        yield Footer()

    def on_mount(self) -> None:
        # Keep the artwork at the top even when the dashboard needs scrolling.
        self.query_one(OptionList).focus(scroll_visible=False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool:
        # Future text fields must consume their own number and Q keys.
        return not isinstance(self.focused, (Input, TextArea))

    @on(OptionList.OptionSelected)
    def selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "0":
            self.action_request_exit()
        elif event.option.id:
            self.action_open_module(event.option.id)

    def action_open_module(self, key: str) -> None:
        module = next((item for item in MODULES if item.key == key), None)
        if module is not None:
            from rebel_security.ui.password_screens import (
                AdvisorScreen, AnalyzerScreen, GeneratorScreen,
            )
            from rebel_security.ui.hash_screens import AuditorScreen, InspectorScreen
            screen_type = {
                "1": AuditorScreen, "7": InspectorScreen,
                "2": GeneratorScreen, "3": AdvisorScreen, "4": AnalyzerScreen,
                "9": SettingsScreen,
            }.get(key, ModuleScreen)
            screen = screen_type(module)
            self.app.push_screen(screen)

    def action_request_exit(self) -> None:
        self.app.request_exit()


class ModuleScreen(Screen):
    BINDINGS = [Binding("escape", "back", "Back to dashboard")]

    def __init__(self, module: Module) -> None:
        super().__init__()
        self.module = module

    def content(self) -> ComposeResult:
        yield Static(
            "Module implementation scheduled for a future milestone.",
            classes="notice",
        )

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="page"):
            with Vertical(classes="body"):
                yield Branding()
                yield Static(self.module.title, classes="title")
                yield Static(self.module.description, classes="description")
                yield from self.content()
                yield Button("Back [Esc]", id="back")
        yield Footer()

    @on(Button.Pressed, "#back")
    def action_back(self) -> None:
        self.app.pop_screen()


class SettingsScreen(ModuleScreen):
    def content(self) -> ComposeResult:
        settings = self.app.settings
        yield Static("Theme")
        yield Select(
            [(label, name) for name, label in THEMES.items()],
            value=settings.theme, allow_blank=False, id="theme-select",
        )
        yield Static("Reduced motion")
        yield Switch(settings.reduced_motion, id="reduced-motion")
        yield Static("Confirm before exit")
        yield Switch(settings.confirm_exit, id="confirm-exit")
        yield Button("Save settings", id="save", variant="primary")
        yield Button("Reset to defaults", id="reset")
        yield Static(
            "Save applies and persists preferences. Back discards unsaved changes.",
            classes="hint",
        )
        yield Static(f"Local settings: {self.app.settings_path}", classes="hint", markup=False)
        yield Static("", id="settings-result", markup=False)

    def persist(self, settings: Settings) -> None:
        if self.app.persist_settings(settings):
            self.query_one("#settings-result", Static).update("Settings saved locally.")
        else:
            self.query_one("#settings-result", Static).update(
                "Could not save settings. Check the configuration folder permissions. "
                "Active preferences are unchanged."
            )

    @on(Button.Pressed, "#save")
    def save(self) -> None:
        self.persist(Settings(
            theme=str(self.query_one("#theme-select", Select).value),
            reduced_motion=self.query_one("#reduced-motion", Switch).value,
            confirm_exit=self.query_one("#confirm-exit", Switch).value,
        ))

    @on(Button.Pressed, "#reset")
    def reset(self) -> None:
        defaults = Settings()
        self.persist(defaults)
        if self.app.settings == defaults:
            self.query_one("#theme-select", Select).value = defaults.theme
            self.query_one("#reduced-motion", Switch).value = defaults.reduced_motion
            self.query_one("#confirm-exit", Switch).value = defaults.confirm_exit


class ExitDialog(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="exit-dialog"):
            yield Static("Exit REBEL SECURITY?", classes="title")
            yield Button("Stay", id="stay", variant="primary")
            yield Button("Exit", id="exit")

    def on_mount(self) -> None:
        self.query_one("#stay", Button).focus()

    @on(Button.Pressed)
    def decide(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "exit")

    def action_cancel(self) -> None:
        self.dismiss(False)
