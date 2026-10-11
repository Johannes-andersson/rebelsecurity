"""Preserve logo whitespace using Rich Text and a responsive compact form."""

from rich.text import Text
from textual.widgets import Static

from rebel_security import __version__

LOGO = "\n".join([
    "██████╗ ███████╗██████╗ ███████╗██╗",
    "██╔══██╗██╔════╝██╔══██╗██╔════╝██║",
    "██████╔╝█████╗  ██████╔╝█████╗  ██║",
    "██╔══██╗██╔══╝  ██╔══██╗██╔══╝  ██║",
    "██║  ██║███████╗██████╔╝███████╗███████╗",
    "╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚══════╝",
])

FULL_LOGO_MIN_COLUMNS = 65
COMPACT_LINES = ("REBEL SECURITY", "Powered by Rebel Bits")


class Branding(Static):
    """Render literal artwork, selecting its form by terminal width only."""

    def render(self) -> Text:
        compact = self.app.size.width < FULL_LOGO_MIN_COLUMNS
        primary = self.app.current_theme.primary
        muted = self.app.current_theme.secondary
        if compact:
            # Equal cell widths keep both borders aligned. On very small
            # terminals, omit the box and allow the labels to wrap normally.
            inner_width = max(map(len, COMPACT_LINES)) + 2
            result = Text(style=primary, justify="center")
            if self.size.width >= inner_width + 2:
                result.append("╔" + "═" * inner_width + "╗\n")
                for index, line in enumerate(COMPACT_LINES):
                    result.append("║")
                    result.append(
                        line.center(inner_width),
                        style=primary if index == 0 else muted,
                    )
                    result.append("║\n")
                result.append("╚" + "═" * inner_width + "╝\n")
            else:
                result.append("REBEL SECURITY\n")
                result.append("Powered by Rebel Bits\n", style=muted)
        else:
            # Pad to equal widths so centering preserves relative alignment.
            width = max(map(len, LOGO.splitlines()))
            art = "\n".join(line.ljust(width) for line in LOGO.splitlines())
            result = Text(art + "\n\n", style=primary, justify="center", no_wrap=True)
            result.append("S E C U R I T Y\n", style=primary)
            result.append("POWERED BY REBEL BITS\n", style=muted)
        result.append(f"v{__version__}", style=muted)
        return result

    def on_resize(self) -> None:
        self.set_class(
            self.app.size.width < FULL_LOGO_MIN_COLUMNS, "compact"
        )
        self.refresh(layout=True)
