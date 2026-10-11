"""Dashboard entries and honest descriptions of future functionality."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    description: str


MODULES = (
    Module(
        "1", "PASSWORD AUDITOR",
        "Offline hash generation, verification, and controlled "
        "application-generated audit demonstrations.",
    ),
    Module("2", "PASSWORD GENERATOR", "Cryptographically secure password generation."),
    Module(
        "3", "SMART PASSWORD ADVISOR",
        "Memorable passphrase generation and security guidance.",
    ),
    Module(
        "4", "PASSWORD STRENGTH ANALYZER",
        "Password strength evaluation and estimated offline guessing resistance.",
    ),
    Module(
        "5", "ATTACK SIMULATOR",
        "Controlled local demonstrations of dictionary, brute-force, "
        "and rule-based guessing techniques.",
    ),
    Module(
        "6", "SECURITY LAB",
        "Hashing algorithm comparisons, benchmarks, and cybersecurity experiments.",
    ),
    Module("7", "HASH INSPECTOR", "Identification and inspection of common hash formats."),
    Module("8", "REPORT CENTER", "Generate and export local security analysis reports."),
    Module("9", "SETTINGS", "Configure application preferences and UI appearance."),
)
