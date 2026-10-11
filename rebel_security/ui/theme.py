"""Two complete terminal palettes and shared responsive layout."""

from textual.theme import Theme

REBEL_GREEN = Theme(
    name="rebel-green", primary="#00FF88", secondary="#00AA66",
    accent="#00FF88", foreground="#D8E5DC", background="#0B0F0C",
    surface="#101A14", panel="#101A14", success="#00FF88",
    warning="#FFCC00", error="#FF5555", dark=True,
    variables={"text-muted": "#8C9B92"},
)
AMBER_TERMINAL = Theme(
    name="amber-terminal", primary="#FFCC00", secondary="#C79A30",
    accent="#FFCC00", foreground="#F1E4C4", background="#120F08",
    surface="#201A0D", panel="#201A0D", success="#B9D879",
    warning="#FFAA44", error="#FF5555", dark=True,
    variables={"text-muted": "#ABA18B"},
)

CSS = """
Screen { background: $background; color: $foreground; }
.page { width: 100%; height: 1fr; align-horizontal: center; }
.body { width: 76; max-width: 100%; height: auto; padding: 0 1; }
Branding { height: auto; margin: 0 0 1 0; color: $primary; text-align: center; }
Branding.compact { margin: 0; }
#menu { height: 12; border: round $secondary; padding: 0 1; }
OptionList:focus { border: round $primary; }
OptionList > .option-list--option-highlighted {
    background: $primary; color: $background; text-style: bold;
}
.status { height: auto; margin-top: 1; color: $text-muted; }
.quote { height: auto; color: $secondary; text-align: center; }
.title { height: auto; color: $primary; text-style: bold; margin: 1 0; }
.description { height: auto; margin-bottom: 1; }
.notice { height: auto; border-left: thick $warning; padding: 1; }
.hint { height: auto; color: $text-muted; margin: 1 0; }
.secret-output { height: auto; padding: 1; border: round $primary; color: $primary; }
#result, #time-result, #time-error, #form-error { height: auto; }
#time-result { border: round $secondary; padding: 1; margin: 1 0; }
#phrase-options, #pin-options, #custom-rate-row { height: auto; }
Checkbox { width: 100%; height: auto; }
Input:focus { border: tall $primary; }
.secret-actions { height: 4; }
.secret-actions Button { width: 1fr; min-width: 8; margin: 0 1 1 0; }
.form-error, #time-error { color: $warning; }
Button { margin: 1 0; min-width: 12; }
Button:focus { border: tall $primary; text-style: bold; }
Select { width: 100%; margin-bottom: 1; }
Switch { margin-bottom: 1; }
Footer { background: $surface; }
ExitDialog { align: center middle; background: $background 80%; }
#exit-dialog { width: 46; max-width: 100%; height: auto;
    padding: 1 2; border: round $primary; background: $surface; }
#exit-dialog Button { width: 100%; margin: 0; }
"""

CSS += """
#candidate-fields, #verify-fields, #demo-fields, #generated-fields { height: auto; }
#hash-result { height: auto; border: solid $primary; padding: 1; margin-top: 1; }
#hash-output { height: 5; width: 100%; }
"""

CSS += """
AuditorScreen Button { margin: 0; }
AuditorScreen Select { margin-bottom: 0; }
AuditorScreen #hash-result { display: none; padding: 0 1; margin: 0; }
AuditorScreen #hash-result.match { color: #00ff88; border: solid #00ff88; }
AuditorScreen #hash-result.no-match { color: #ff6666; border: solid #ff6666; }
AuditorScreen #hash-result.invalid { color: #ffd166; border: solid #ffd166; }
"""
