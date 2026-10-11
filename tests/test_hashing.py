"""Public toy fixtures only; no user passwords or external audit targets."""
import base64
import hashlib
from threading import Event

import bcrypt
import pytest
from argon2 import PasswordHasher

from rebel_security.modules.auditor import run_demo
from rebel_security.utils.hashing import ALGORITHMS, HashError, generate_hash, inspect_hash, verify_hash


@pytest.mark.parametrize('algorithm', ALGORITHMS)
@pytest.mark.parametrize('password', ['', 'public-test-ü'])
def test_generate_and_verify(algorithm, password):
    encoded = generate_hash(password, algorithm)
    assert inspect_hash(encoded).algorithm == algorithm
    assert verify_hash(password, encoded, algorithm)
    assert not verify_hash(password + 'wrong', encoded, algorithm)
    with pytest.raises(HashError):
        verify_hash(password, encoded, 'sha512' if algorithm != 'sha512' else 'md5')


@pytest.mark.parametrize('algorithm,expected', [
    ('md5', '900150983cd24fb0d6963f7d28e17f72'),
    ('sha1', 'a9993e364706816aba3e25717850c26c9cd0d89d'),
    ('sha256', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'),
    ('sha512', 'ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f'),
])
def test_known_vectors(algorithm, expected):
    assert generate_hash('abc', algorithm) == expected
    assert verify_hash('abc', expected.upper(), algorithm)
    info = inspect_hash(expected)
    assert info.ambiguous and 'Possible match' in info.summary()
    assert 'unsuitable' in info.recommendation


@pytest.mark.parametrize('algorithm', ['bcrypt', 'argon2id', 'pbkdf2_sha256'])
def test_salts_and_native_interoperability(algorithm):
    first, second = generate_hash('example', algorithm), generate_hash('example', algorithm)
    assert first != second
    assert 'Present' in inspect_hash(first).salt
    if algorithm == 'bcrypt':
        assert bcrypt.checkpw(b'example', first.encode())
        assert verify_hash('example', bcrypt.hashpw(b'example', bcrypt.gensalt(4)).decode(), algorithm)
        assert 'cost=12' in inspect_hash(first).parameters
    elif algorithm == 'argon2id':
        assert PasswordHasher().verify(first, 'example')
        external = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash('example')
        assert verify_hash('example', external, algorithm)
        assert 'memory=65536' in inspect_hash(first).parameters
    else:
        _, iterations, salt, digest = first.split('$')
        assert int(iterations) == 600000
        assert base64.b64decode(digest) == hashlib.pbkdf2_hmac('sha256', b'example', salt.encode(), 600000)
        # Independently published PBKDF2-HMAC-SHA256 password/salt one-iteration vector.
        vector = bytes.fromhex('120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b')
        assert verify_hash('password', 'pbkdf2_sha256$1$salt$' + base64.b64encode(vector).decode(), algorithm)


@pytest.mark.parametrize('value', ['', 'g'*32, 'a'*31, 'a'*63, '$2b$12$short', '$argon2id$truncated',
    'pbkdf2_sha256$0$salt$AAAA', 'pbkdf2_sha256$1$salt$!!!', 'x'*1025,
    '$argon2id$v=19$m=1,t=1,p=1$c2FsdHNhbHQ$aGFzaA',
    '$argon2id$v=19$m=8192,t=0,p=1$c2FsdHNhbHQ$aGFzaA'])
def test_malformed_hashes(value):
    with pytest.raises(HashError):
        inspect_hash(value)
    with pytest.raises(HashError):
        verify_hash('public', value, 'sha256')


@pytest.mark.parametrize('algorithm', ALGORITHMS)
def test_password_size_limits(algorithm):
    with pytest.raises(HashError):
        generate_hash('x'*4097, algorithm)


def test_bcrypt_no_silent_truncation():
    with pytest.raises(HashError, match='72'):
        generate_hash('ü'*37, 'bcrypt')


@pytest.mark.parametrize('encoded,algorithm', [
    ('$2b$31$' + '.'*53, 'bcrypt'),
    ('$argon2id$v=19$m=4294967295,t=1,p=1$c2FsdHNhbHQ$aGFzaA', 'argon2id'),
    ('pbkdf2_sha256$9999999999$salt$' + base64.b64encode(bytes(32)).decode(), 'pbkdf2_sha256'),
])
def test_expensive_external_hashes_rejected_before_work(encoded, algorithm):
    assert inspect_hash(encoded).algorithm == algorithm
    with pytest.raises(HashError, match='limit'):
        verify_hash('public', encoded, algorithm)


@pytest.mark.parametrize('algorithm', ALGORITHMS)
def test_actual_demo_match(algorithm):
    progress = []
    result = run_demo('123456', algorithm, 'common', Event(), progress.append)
    assert result.matched and not result.cancelled and result.candidates == 2
    assert progress == [1, 2]
    assert result.elapsed > 0
    assert result.attempts_per_second == result.candidates / result.elapsed


def test_demo_no_match_and_cancel():
    result = run_demo('password', 'sha256', 'short', Event())
    assert not result.matched and result.candidates == 3
    cancel = Event()
    result = run_demo('admin', 'sha256', 'common', cancel, lambda count: cancel.set())
    assert result.cancelled and result.candidates == 1
    result = run_demo('admin', 'sha256', 'common', cancel)
    assert result.cancelled and result.candidates == 0
    with pytest.raises(HashError):
        run_demo('arbitrary target', 'sha256', 'common', Event())
    with pytest.raises(HashError):
        run_demo('admin', 'sha256', '/custom/wordlist', Event())


def test_argon_operational_failure_is_not_a_mismatch():
    from unittest.mock import patch
    from argon2.exceptions import VerificationError
    encoded = generate_hash('public', 'argon2id')
    with patch('rebel_security.utils.hashing.ARGON') as library:
        library.verify.side_effect = VerificationError('untrusted library detail')
        with pytest.raises(HashError, match='could not complete'):
            verify_hash('public', encoded, 'argon2id')
