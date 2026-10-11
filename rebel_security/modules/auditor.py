"""Controlled, application-generated fixtures only; no external audit targets."""
from dataclasses import dataclass
from threading import Event
from time import perf_counter
from typing import Callable

from rebel_security.utils.hashing import HashError, generate_hash, verify_hash

EXAMPLES = ('password', '123456', 'qwerty', 'letmein', 'welcome', 'admin')
WORDLISTS = {
    'common': ('password', '123456', 'qwerty', 'letmein', 'welcome', 'admin'),
    'short': ('test', 'guest', 'hello'),
}


@dataclass(frozen=True)
class AuditResult:
    algorithm: str
    candidates: int
    elapsed: float
    matched: bool
    cancelled: bool

    @property
    def attempts_per_second(self):
        return self.candidates / self.elapsed if self.elapsed > 0 else 0.0

    def summary(self):
        status = 'CANCELLED' if self.cancelled else 'MATCH FOUND' if self.matched else 'NOT FOUND IN DEMONSTRATION WORDLIST'
        return (f'{status}\nAlgorithm: {self.algorithm}\nCandidates tested: {self.candidates}\n'
                f'Elapsed: {self.elapsed:.6f} seconds\nMeasured attempts/second: {self.attempts_per_second:.2f}\n'
                'Measured local verification only; fixture generation is excluded. A tiny educational sample, '
                'not a benchmark or a theoretical exhaustive-search estimate.')


def run_demo(example: str, algorithm: str, wordlist: str, cancel: Event,
             progress: Callable[[int], None] = lambda count: None) -> AuditResult:
    if example not in EXAMPLES or wordlist not in WORDLISTS:
        raise HashError('Choose a built-in demonstration fixture and wordlist.')
    if cancel.is_set():
        return AuditResult(algorithm, 0, 0, False, True)
    fixture = generate_hash(example, algorithm)
    started = perf_counter()
    count, matched = 0, False
    for candidate in WORDLISTS[wordlist]:
        if cancel.is_set():
            break
        matched = verify_hash(candidate, fixture, algorithm)
        count += 1
        progress(count)
        if matched:
            break
    return AuditResult(algorithm, count, perf_counter() - started, matched, cancel.is_set())
