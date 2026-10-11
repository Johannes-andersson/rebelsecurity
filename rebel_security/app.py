"""Application lifecycle and preference integration."""

import argparse
import sys
import traceback
from pathlib import Path

from textual.app import App
from textual import constants
from textual.binding import Binding

from rebel_security.config import Settings, load_settings, save_settings
from rebel_security.ui.components import Dashboard, ExitDialog
from rebel_security.ui.theme import AMBER_TERMINAL, CSS, REBEL_GREEN
from rebel_security.utils.helpers import config_path


class RebelSecurityApp(App[None]):
    TITLE = "REBEL SECURITY"
    SUB_TITLE = "POWERED BY REBEL BITS"
    CSS = CSS
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [Binding("ctrl+c", "request_exit", "Exit", priority=True, show=False)]

    def __init__(self, settings_path: Path | None = None, *, debug: bool = False) -> None:
        super().__init__()
        # Textual debug logs include Input.Changed values. Disable all framework
        # logging/devtools transports before mounting any secret-bearing screen.
        constants.LOG_FILE = None
        self.devtools = None
        self._devtools_redirector = None
        self.show_diagnostics = debug
        self._safe_failure = ''
        self.settings_path = settings_path if settings_path is not None else config_path()
        self.settings, self.settings_warning = load_settings(self.settings_path)
        self.register_theme(REBEL_GREEN)
        self.register_theme(AMBER_TERMINAL)
        self.apply_settings()

    def apply_settings(self) -> None:
        self.theme = self.settings.theme
        self.animation_level = "none" if self.settings.reduced_motion else "basic"

    def on_mount(self) -> None:
        self.push_screen(Dashboard())
        if self.settings_warning:
            self.notify(
                self.settings_warning, title="Settings recovery",
                severity="warning", timeout=10,
            )

    def persist_settings(self, settings: Settings) -> bool:
        try:
            save_settings(self.settings_path, settings)
        except OSError:
            return False
        self.settings = settings
        self.apply_settings()
        self.refresh(layout=True)
        return True

    def request_exit(self) -> None:
        if isinstance(self.screen, ExitDialog):
            return
        if self.settings.confirm_exit:
            self.push_screen(ExitDialog(), self.finish_exit)
        else:
            self.exit()

    def action_request_exit(self) -> None:
        self.request_exit()

    def finish_exit(self, confirmed: bool | None) -> None:
        if confirmed:
            self.exit()

    def _handle_exception(self, error: Exception) -> None:
        """Never construct Rich tracebacks containing secrets or local variables."""
        self._safe_failure = safe_diagnostic(error, self.show_diagnostics)
        self._return_code = 1
        self._exception = RuntimeError(self._safe_failure)
        self._exception_event.set()
        for screen in self.screen_stack:
            clear = getattr(screen, 'clear_sensitive', None)
            if clear is not None:
                clear()
        self._close_messages_no_wait()

    def _print_error_renderables(self) -> None:
        self._exit_renderables.clear()
        if self._safe_failure:
            print(self._safe_failure, file=sys.stderr)


def safe_diagnostic(error: Exception, debug: bool) -> str:
    message = 'REBEL SECURITY encountered an unexpected error.'
    if debug:
        # Code location only: no exception messages, source text, or local values.
        frames = traceback.walk_tb(error.__traceback__)
        message += '\n' + '\n'.join(
            f'{Path(frame.f_code.co_filename).name}:{line} in {frame.f_code.co_name}'
            for frame, line in frames
        )
    else:
        message += ' Run with --debug for safe code-location diagnostics.'
    return message


def main() -> None:
    parser = argparse.ArgumentParser(description="REBEL SECURITY — offline terminal toolkit")
    parser.add_argument("--debug", action="store_true", help="Show development diagnostics")
    parser.add_argument("--config", type=Path, help="Use an alternate local settings file")
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.exit(2, "REBEL SECURITY requires an interactive terminal.\n")
    try:
        app = RebelSecurityApp(args.config, debug=args.debug)
        app.run()
        if app.return_code:
            raise SystemExit(app.return_code)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(safe_diagnostic(error, args.debug), file=sys.stderr)
        raise SystemExit(1)
