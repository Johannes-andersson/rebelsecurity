# REBEL SECURITY

**POWERED BY REBEL BITS · v1.0.0-alpha**

A local, offline Python terminal toolkit for password-security auditing and
cybersecurity education. Milestones 1–3 provide a responsive Textual
dashboard, ASCII branding, persistent preferences, secure password/passphrase
generation, local pattern-aware password analysis, hash inspection, verification,
and controlled local audit demonstrations.

## Current status and roadmap

Implemented through Milestone 3.1:

- Full REBEL logo at terminal widths of 65 columns or more, regardless of height.
  Narrower terminals use aligned compact branding.
- Dashboard with real OS detection, version, offline mode, and readiness.
- Working Password Generator, Smart Password Advisor, Password Strength Analyzer,
  Password Auditor, Hash Inspector, and Settings; three modules remain placeholders.
- REBEL GREEN (default) and AMBER TERMINAL themes.
- Reduced motion, optional exit confirmation, and reset to defaults.
- Validated local configuration, atomic saves, and readable failure messages.
- Automated pytest and Textual Pilot regression tests.

Future milestones (not implemented or assigned dates here):

| Module | Planned capability |
| --- | --- |
| Attack Simulator | Controlled local demonstrations of guessing techniques |
| Security Lab | Hash comparisons, benchmarks, and experiments |
| Report Center | Local report generation and export |

The advanced Attack Simulator, Security Lab, and Report Center remain unimplemented.
Audit statistics are measured from actual local verification attempts.

## Requirements and installation

Python **3.12 or newer** and a Unicode-capable interactive terminal with a
monospace font. Dependencies are Textual 6.x (6.12+), Rich 14.x, zxcvbn 4.5.x,
pyperclip 1.x (1.9+), bcrypt 5.x, and argon2-cffi 25.1.x; compatible ranges are in `pyproject.toml`. Installing dependencies normally needs internet access;
running the installed application does not. There are no runtime network calls,
external services, telemetry, or browser components in application code.

macOS, from this workspace:

```sh
cd "/Users/johannes/Documents/Rebel Security"
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python main.py
```

Linux, from the project directory (use a Python 3.12+ interpreter):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python main.py
```

Windows PowerShell, from the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe main.py
```

After installation, `rebel-security` is also available while the environment
is activated. In VS Code, select `.venv` as the Python interpreter and launch
from the integrated terminal, rather than the noninteractive output panel.

The intended terminals are macOS Terminal, iTerm2, VS Code's integrated
terminal, Linux terminals, and modern Windows Terminal. Validation for this
milestone was performed on macOS with Python 3.12; other operating systems and
terminal emulators still need native smoke testing. Platform path rules are
covered by automated tests. Short windows scroll to reach the lower menu entries
and status information while retaining the full logo at widths of 65 columns or
more. Narrower windows use a compact box, with plain compact labels when even
the box cannot fit. A Unicode monospace font is needed for the full block logo.

## Controls

| Key or action | Behavior |
| --- | --- |
| Up / Down, Home / End | Select a dashboard entry |
| Enter or mouse click | Open selected entry |
| 1–9 | Open a module directly from the dashboard |
| Q or 0 | Request exit from the dashboard |
| Escape or Back button | Return from a module; discard unsaved settings |
| Tab / Shift+Tab | Move between focusable controls |
| Space | Toggle the focused switch or activate a button |
| Ctrl+C | Request exit from any screen, respecting confirmation |
| Escape in exit dialog | Cancel exit |

Menu labels are padded as `[01]`–`[09]`; shortcuts are single digits, not
two-digit sequences. Unassigned dashboard keys are ignored. Q and digits do
not trigger dashboard actions while a text input has focus. Exit confirmation
defaults to enabled, and the dialog initially focuses **Stay**.

## Password Auditor — [01]

The Auditor opens in **Verify password** mode: select the algorithm, paste the
hash, enter a candidate password, and choose **Verify password**. The result
appears directly below the action button and scrolls into view without leaving
the screen. Green means a match, red means no match, and yellow indicates invalid
hash/input. Verification preserves both entered fields until Clear, a mode change
(password only), or leaving the module. Passwords are case-sensitive.

Choose **Generate hash** in the mode selector, enter a demonstration password in the masked field,
select an algorithm, and click **Generate hash**. The generated hash is in a
scrollable field; use **Inspect generated hash** for its format and parameters,
or explicitly copy it. Switch to **Verify password** to reuse that hash, or paste
an authorized test hash, select the matching algorithm, enter a candidate, and
click **Verify password**. Generation and demonstration controls are hidden in
Verify mode. `MATCH FOUND` is shown only after real cryptographic
verification; `NO MATCH` means the supplied candidate failed verification.
Empty passwords are supported for education, not recommended for use.

| Algorithm | Generated format / settings |
| --- | --- |
| MD5, SHA-1, SHA-256, SHA-512 | Lowercase hexadecimal digest of UTF-8 bytes; no salt |
| bcrypt | Standard `$2b$` format; random 16-byte salt; cost 12 |
| Argon2id | PHC `$argon2id$v=19$…`; random 16-byte salt; 64 MiB, 3 passes, 4 lanes, 32-byte output |
| PBKDF2-SHA256 | Django `pbkdf2_sha256$iterations$salt$base64digest`; 600,000 iterations; 128 random salt bits encoded as ASCII hex; 32-byte output |

Verification supports bcrypt `$2a$`, `$2b$`, and `$2y$`; Argon2id versions 16 and
19; and the documented Django PBKDF2 format with alphanumeric ASCII salts.
Other PBKDF2 encodings are not inferred or converted. No Unicode normalization
is applied. bcrypt rejects inputs above 72 UTF-8 **bytes**, never truncating them;
other algorithms have a local input limit of 4096 UTF-8 bytes. Hash inputs are
limited to 1024 characters.

**Local audit demonstration** creates a fresh application-generated fixture
using the chosen built-in example and algorithm, then tests the selected tiny
wordlist. The `common` list is password, 123456, qwerty, letmein, welcome, admin;
`short` is test, guest, hello. These public teaching examples are embedded in
`modules/auditor.py`; arbitrary hashes, passwords, and external wordlists cannot
be audit targets. Results show actual candidates tested, elapsed verification
time, and measured attempts per second. Fixture generation is excluded from
the timing. A match stops the search; a miss only means the tiny wordlist failed.
This is a demonstration, not a reliable hardware benchmark.

Hashing runs on background workers. **Cancel** stops after any current bounded
hash operation finishes. Leaving or clearing a screen cancels pending work and
prevents late results from repopulating it. Only one expensive operation runs
at a time, including when navigating away and back. External verification is
limited to bcrypt cost 14, Argon2id 128 MiB / 10 passes / 8 lanes, and PBKDF2
2,000,000 iterations. Higher settings can be inspected but are rejected for
execution to bound local resource consumption. Cancellation cannot interrupt
a native KDF already running. Its input remains in memory until that call ends;
Python and native libraries cannot guarantee secure erasure.

## Hash Inspector — [07]

Paste a hash and select **Inspect hash**. The output reports length, encoding,
possible algorithm or structured format, salt presence, work parameters, and
recommendations. **Copy inspection** copies only the descriptive report;
**Clear** removes input and results. Hexadecimal digests are explicitly ambiguous:
length alone cannot prove MD5, SHA-1, SHA-256, or SHA-512, determine an external
salt, or establish password strength. Structured recognition validates syntax
but does not prove a hash was produced by a particular application.

Hashing is a one-way derivation, not encryption or decryption. Verification
recomputes the derivation using the encoded salt and parameters. A unique random
salt prevents equal passwords from routinely having equal stored hashes and
reduces reuse of precomputed work; it is public, not a password. Work factors
make each guess expensive. Argon2id also requires memory. Fast general-purpose
hashes (including SHA-256 and SHA-512) are unsuitable for direct modern password
storage, even though included here for education and legacy compatibility.

Defaults follow the [Argon2 RFC 9106 low-memory profile](https://argon2-cffi.readthedocs.io/en/stable/parameters.html)
and [OWASP password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
PBKDF2 uses the [documented Django format](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/).
Choose and benchmark production parameters for your own environment; recognition
alone does not establish adequate security. Theoretical guessing-time inputs in
modules 02–04 remain assumptions, separate from the measured local demo rates.

## Password Forge — [02]

Choose a length from 8–128 (default 24), enable at least one category, and select
**Generate password** or **Regenerate**. Uppercase, lowercase, digits, and ASCII
punctuation are enabled by default. Each enabled category is guaranteed present;
disabled categories cannot appear. Exclude ambiguous characters removes
`0 O o 1 l I`. Results are literal text, so brackets and other symbols cannot
be interpreted as markup. Copy happens only when you press the Copy button.

## Smart Password Advisor — [03]

- **Memorable passphrase:** six independent random word selections by default.
- **Maximum security:** a 48-character password using all four categories.
- **PIN / numeric password:** 6–20 independent random digits, default 8; leading
  zeroes are preserved. Short PINs depend heavily on rate limiting and context.
- **Custom passphrase:** configure 4–10 words, capitalization, a separator, and
  0–10 appended random digits. Memorable mode exposes the same safe controls.

Separators must contain 1–8 ASCII punctuation characters or spaces. Empty or
letter/digit separators are rejected to preserve unambiguous word boundaries.
Repeated words are possible and intentional: selection is with replacement.
Capitalization is formatting, not additional randomness.

The bundled [EFF Long Wordlist](https://www.eff.org/dice), created by Joseph
Bonneau / Electronic Frontier Foundation, contains 7,776 entries. The source
file is unchanged. Selection excludes its four hyphenated entries so separators
remain unambiguous; **7,772 unique alphabetic entries** are actually used.
Entropy always uses this reduced count. Under [EFF's current copyright
policy](https://www.eff.org/copyright), the material is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
See `rebel_security/data/WORDLIST-LICENSE.md` for source, license, and changes.
No runtime downloads are needed and no EFF endorsement is implied.

## Password Strength Analyzer — [04]

Type or paste a password into the masked field, optionally toggle **Show
password**, then select **Analyze password**. Inputs of 1–128 characters are
supported; longer inputs are rejected rather than silently truncated. Analysis
runs locally with [zxcvbn-python](https://github.com/dwolfhub/zxcvbn-python).
Results include length, category diversity, a pattern-aware rating, recognized
patterns, and recommendations. Common passwords, dictionaries, repetition,
sequences, keyboard patterns, substitutions, and dates inform the estimate.
Changing the input clears stale results. No character-set entropy is assigned
to user-entered passwords. The model may miss languages, personal information,
new attacks, and breached credentials; no breach lookup is performed.

## Entropy and guessing-time methodology

All three forms show **ESTIMATED OFFLINE GUESSING TIME**. Select 10, 1,000,
1 million, or 1 billion guesses per second, or a positive custom rate. Rates
are illustrative offline assumptions, not measured or universal hardware
benchmarks. Custom rates accept decimals/scientific notation from 1e-12 to
1e100; nonfinite values, zero, negatives, and out-of-range values are rejected.

For Forge, `secrets.choice` independently draws every position from the combined
alphabet. A whole candidate is rejected if it misses a required category.
This is uniform sampling conditioned on the category constraints; no predictable
shuffle or modulo-biased indexing is used. For disjoint category sizes `n_i`,
combined size `N`, and length `L`, inclusion-exclusion computes the exact valid
string count:

`S = sum over category subsets A of (-1)^|A| * (N - sum(n_i in A))^L`.

The entropy is `log2(S)` bits (displayed rounded), rather than blindly claiming
`L * log2(N)`. For passphrases with `w` words and `d` additional random digits,
`S = 7772^w * 10^d`. Fixed separators and capitalization add zero bits. For a
numeric password of length `L`, `S = 10^L`.

For a uniformly generated target and exhaustive search without replacement:

- Expected guess count: `(S + 1) / 2`; expected time: `(S + 1) / (2 * rate)`.
- Maximum guess count: `S`; maximum time: `S / rate`.

For user-entered passwords, the displayed time is **zxcvbn's estimated guess
count / rate**. It is neither an exhaustive maximum nor a guaranteed mean time.
We do not halve this count or replace it with a character-set search space.
Integers retain exact search-space counts; Decimal arithmetic avoids floating
point overflow. Display values use at most two decimals, with named year units
from thousand through decillion. At 10^36 years and beyond, ASCII scientific
notation (for example, `3.72e42 years`) avoids reliance on superscript font
support. Rounding promotes values at unit boundaries; only display values are
rounded. Attack rates and estimated guess counts are abbreviated too.

Estimates assume a specified offline guessing rate and do not guarantee
real-world resistance. Actual results depend on password selection, hashing
algorithms, hardware, and attack methods. Entropy describes the random
selection process, not immunity to phishing, malware, reuse, or disclosure.

## Secret and clipboard privacy

Secrets are not written to settings, databases, history, logs, crash reports,
or analytics. No password history exists. Leaving a secret screen clears its
inputs, output, and associated state; normal shutdown and fatal UI errors also
clear them. Python strings and terminal/OS buffers cannot be reliably securely
erased, so this is lifetime reduction, not a secure-memory guarantee. Avoid
screenshots, terminal recording, or external debugging when using real secrets.

Copy uses pyperclip's local OS provider only on an explicit Copy click. macOS
uses its native clipboard utility, Windows uses native clipboard support, and
Linux requires a working provider such as xclip, xsel, or a supported Wayland
clipboard service. If unavailable, the UI reports failure without echoing the
secret. Clipboard contents can be read by other applications, retained by
clipboard managers, or synced by OS features. The application makes no network
requests but cannot control OS clipboard synchronization. There is no automatic
clipboard clearing, and leaving a screen does not clear the system clipboard.

## Settings

Open **[09] SETTINGS**, change preferences, and choose **Save settings** to
apply them and persist them. **Reset to defaults** immediately saves the default
preferences. Back leaves unsaved changes unapplied. Reduced motion disables
Textual animations; normal mode permits basic widget transitions.

Configuration is a small JSON file containing only `theme`, `reduced_motion`,
and `confirm_exit`:

- macOS: `~/Library/Application Support/rebel-security/settings.json`
- Linux: `$XDG_CONFIG_HOME/rebel-security/settings.json`, or
  `~/.config/rebel-security/settings.json` if unset or not absolute.
- Windows: `%APPDATA%\rebel-security\settings.json`, falling back to
  `~\AppData\Roaming\rebel-security\settings.json`.

Missing files use defaults. Invalid or unreadable files produce a warning and
use defaults without overwriting the file. A later explicit Save or Reset
replaces it. Failed writes leave active preferences and the previous saved file
unchanged. The file is created only on Save or Reset.

Use an alternate path for isolated testing:

```sh
python main.py --config /tmp/rebel-security-demo/settings.json
```

## Development and tests

```sh
python -m pytest -q
python main.py --debug
```

Tests use temporary configuration directories and never alter personal
preferences. They exercise startup, menu entries, all nine routes, back
navigation, mouse and keyboard controls, resize behavior, both themes,
persistence across launches, invalid configuration recovery, write failures,
and exit behavior, plus generation constraints, exact search-space calculations,
huge durations, pattern detection, clipboard failures, and secret cleanup.
`--debug` reports code locations only, never exception messages, source text,
local variables, or plaintext. Textual file logging and devtools transports are
disabled to prevent input-event logging.

## Project layout

`main.py` launches `rebel_security/app.py`. `config.py` handles preferences.
`ui/branding.py`, `menus.py`, `theme.py`, and `components.py` define presentation
and screens. `ui/password_screens.py` contains the three security forms.
`modules/generator.py`, `advisor.py`, and `analyzer.py` are UI-independent.
`utils/` handles platform paths, estimates, wordlist loading, and clipboard
access. `utils/hashing.py` implements standard hash formats;
`modules/auditor.py` contains controlled demonstrations and `modules/hash_inspector.py`
exposes inspection. `ui/hash_screens.py` contains the two new screens and background
workers. `data/` contains the bundled passphrase wordlist and attribution. Three
module files remain placeholders. Tests are in `tests/`.

## Security and authorized use

Use hash generation and verification only with explicitly authorized, local
test material. Audit demonstrations accept only the built-in public fixtures. The project is intended for education and defensive
security. Security-sensitive processing must remain local, and passwords,
secrets, and plaintext credentials must never be logged. Estimates are
educational and cannot guarantee real-world security. This educational toolkit does not offer arbitrary-target cracking, remote login
attempts, or production credential management.
