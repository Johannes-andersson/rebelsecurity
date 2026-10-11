"""Local standard hash formats and bounded password verification."""
import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

import bcrypt
from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import VerificationError, VerifyMismatchError

ALGORITHMS = {'md5': 'MD5', 'sha1': 'SHA-1', 'sha256': 'SHA-256', 'sha512': 'SHA-512',
              'bcrypt': 'bcrypt', 'argon2id': 'Argon2id', 'pbkdf2_sha256': 'PBKDF2-SHA256'}
FAST = {'md5': 32, 'sha1': 40, 'sha256': 64, 'sha512': 128}
ARGON = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)


class HashError(ValueError):
    """A safe, user-facing validation failure (never includes input)."""


@dataclass(frozen=True)
class HashInfo:
    algorithm: str
    length: int
    encoding: str
    salt: str
    parameters: str
    recommendation: str
    ambiguous: bool = False

    def summary(self):
        label = 'Possible match' if self.ambiguous else 'Format'
        return (f'{label}: {ALGORITHMS[self.algorithm]}\nLength: {self.length} characters\n'
                f'Encoding: {self.encoding}\nSalt: {self.salt}\nParameters: {self.parameters}\n'
                f'{self.recommendation}')


def _decode(value, padded=False):
    try:
        raw = base64.b64decode(value + ('' if padded else '=' * (-len(value) % 4)), validate=True)
        canonical = base64.b64encode(raw).decode()
        if (canonical if padded else canonical.rstrip('=')) != value:
            raise ValueError
        return raw
    except (ValueError, TypeError):
        raise HashError('Malformed base64 encoding.') from None


def inspect_hash(encoded: str) -> HashInfo:
    if not encoded or len(encoded) > 1024:
        raise HashError('Enter a hash of 1–1024 characters.')
    if re.fullmatch(r'[0-9a-fA-F]+', encoded) and len(encoded) in FAST.values():
        algorithm = next(key for key, size in FAST.items() if size == len(encoded))
        return HashInfo(algorithm, len(encoded), 'hexadecimal', 'Not encoded; cannot infer external salt',
                        'Not encoded', 'Ambiguous: other algorithms or representations can have the same length. '
                        'Fast general-purpose hashes are unsuitable for direct modern password storage.', True)
    if encoded.startswith(('$2a$', '$2b$', '$2y$')):
        match = re.fullmatch(r'\$2[aby]\$(\d{2})\$([./A-Za-z0-9]{53})', encoded)
        if not match or not 4 <= int(match[1]) <= 31 or match[2][21] not in '.Oeu' or match[2][-1] not in '.CGKOSWaeimquy26':
            raise HashError('Malformed or truncated bcrypt hash.')
        return HashInfo('bcrypt', len(encoded), 'bcrypt modular crypt / bcrypt base64', 'Present (16 bytes)',
                        f'cost={int(match[1])}', 'Legacy password hashing; prefer Argon2id for new storage. '
                        'Use cost 10 or greater. bcrypt accepts at most 72 UTF-8 bytes.')
    if encoded.startswith('$argon2'):
        match = re.fullmatch(r'\$argon2id\$v=(16|19)\$m=(\d{1,10}),t=(\d{1,10}),p=(\d{1,10})\$([A-Za-z0-9+/]+)\$([A-Za-z0-9+/]+)', encoded)
        if not match:
            raise HashError('Malformed or unsupported Argon2id format.')
        salt, digest = _decode(match[5]), _decode(match[6])
        memory, passes, lanes = map(int, (match[2], match[3], match[4]))
        if not (1 <= lanes <= 16777215 and 8 * lanes <= memory <= 4294967295 and 1 <= passes <= 4294967295 and len(salt) >= 8 and len(digest) >= 4):
            raise HashError('Invalid Argon2id parameters.')
        return HashInfo('argon2id', len(encoded), 'PHC / unpadded base64', f'Present ({len(salt)} bytes)',
                        f'version={match[1]}, memory={memory} KiB, passes={passes}, parallelism={lanes}',
                        'Recommended with adequate settings. Generated hashes use 64 MiB, 3 passes, 4 lanes. '
                        'Recognition alone does not establish sufficient strength.')
    if encoded.startswith('pbkdf2_sha256$'):
        match = re.fullmatch(r'pbkdf2_sha256\$([1-9]\d{0,9})\$([A-Za-z0-9]{1,128})\$([A-Za-z0-9+/]+={0,2})', encoded)
        if not match or len(_decode(match[3], padded=True)) != 32:
            raise HashError('Malformed PBKDF2-SHA256 hash (expected Django format).')
        return HashInfo('pbkdf2_sha256', len(encoded), 'Django / base64 digest', f'Present ({len(match[2])} ASCII characters)',
                        f'iterations={int(match[1])}', 'Password hashing; use a unique random salt and at least 600,000 iterations. '
                        'Prefer Argon2id for new storage where available.')
    raise HashError('Unknown, malformed, or truncated hash. Supported raw digests must be hexadecimal.')


def _password(password, algorithm):
    if algorithm not in ALGORITHMS:
        raise HashError('Choose a supported algorithm.')
    try:
        data = password.encode('utf-8')
    except UnicodeError:
        raise HashError('Password must contain valid Unicode.') from None
    if len(data) > 4096:
        raise HashError('Password exceeds the 4096 UTF-8 byte limit.')
    if algorithm == 'bcrypt' and len(data) > 72:
        raise HashError('bcrypt accepts at most 72 UTF-8 bytes; input is never truncated.')
    return data


def generate_hash(password: str, algorithm: str) -> str:
    data = _password(password, algorithm)
    if algorithm in FAST:
        return hashlib.new(algorithm, data).hexdigest()
    if algorithm == 'bcrypt':
        return bcrypt.hashpw(data, bcrypt.gensalt(rounds=12)).decode()
    if algorithm == 'argon2id':
        return ARGON.hash(data)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', data, salt.encode(), 600000)
    return f'pbkdf2_sha256$600000${salt}${base64.b64encode(digest).decode()}'


def verify_hash(password: str, encoded: str, algorithm: str) -> bool:
    data = _password(password, algorithm)
    info = inspect_hash(encoded)
    if info.algorithm != algorithm:
        raise HashError('Selected algorithm does not match the supplied format.')
    if algorithm in FAST:
        return hmac.compare_digest(hashlib.new(algorithm, data).hexdigest(), encoded.lower())
    if algorithm == 'bcrypt':
        if int(encoded.split('$')[2]) > 14:
            raise HashError('bcrypt cost exceeds the local verification limit (14).')
        try:
            return bcrypt.checkpw(data, encoded.encode())
        except ValueError:
            raise HashError('Invalid bcrypt hash.') from None
    if algorithm == 'argon2id':
        params = extract_parameters(encoded)
        if params.memory_cost > 131072 or params.time_cost > 10 or params.parallelism > 8:
            raise HashError('Argon2id exceeds local limits (128 MiB, 10 passes, 8 lanes).')
        try:
            return ARGON.verify(encoded, data)
        except VerifyMismatchError:
            return False
        except VerificationError:
            raise HashError('Argon2id verification could not complete.') from None
    _, iterations, salt, expected = encoded.split('$')
    if int(iterations) > 2000000:
        raise HashError('PBKDF2 exceeds the local verification limit (2,000,000 iterations).')
    actual = hashlib.pbkdf2_hmac('sha256', data, salt.encode(), int(iterations))
    return hmac.compare_digest(actual, _decode(expected, padded=True))
