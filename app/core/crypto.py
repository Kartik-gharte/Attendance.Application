"""Authenticated encryption for the backup files.

A backup holds the face embeddings and the attendance records. Without
encryption, a stolen backup directory exposes both in plaintext.

This module wraps AES-256-GCM from the ``cryptography`` package:

- the key is derived from a passphrase with scrypt, which is memory hard
  and therefore expensive to attack;
- every file gets a fresh random nonce;
- the file name is bound to the ciphertext as associated data, so an
  encrypted file cannot be swapped for another one;
- GCM authenticates the ciphertext, so a modified file fails to decrypt
  rather than producing garbage.

The passphrase is never accepted as a command line argument, because
process arguments are visible to other users on the machine. It comes
from an environment variable or from an interactive prompt.
"""

import getpass
import os
import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


ENCRYPTED_SUFFIX = ".enc"

# scrypt parameters. The cost is the number of iterations.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LENGTH = 32
SALT_LENGTH = 16
NONCE_LENGTH = 12


class EncryptionError(RuntimeError):
    """Raised when a value cannot be encrypted or decrypted."""


def generate_salt() -> bytes:
    """Return a fresh random salt."""

    return secrets.token_bytes(SALT_LENGTH)


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive the encryption key from a passphrase and a salt.

    Raises:
        EncryptionError: When the passphrase is empty.
    """

    if not passphrase:
        raise EncryptionError("A passphrase is required")

    return Scrypt(
        salt=salt,
        length=SCRYPT_LENGTH,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    ).derive(passphrase.encode("utf-8"))


def encrypt_bytes(key: bytes, plaintext: bytes, associated_data: bytes) -> bytes:
    """Encrypt the plaintext and return the nonce followed by the
    ciphertext."""

    nonce = secrets.token_bytes(NONCE_LENGTH)

    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data)

    return nonce + ciphertext


def decrypt_bytes(key: bytes, blob: bytes, associated_data: bytes) -> bytes:
    """Decrypt the nonce and ciphertext and return the plaintext.

    Raises:
        EncryptionError: When the value is malformed, or when the
            passphrase is wrong, or when the data was modified.
    """

    if len(blob) <= NONCE_LENGTH:
        raise EncryptionError("The encrypted value is truncated")

    nonce = blob[:NONCE_LENGTH]
    ciphertext = blob[NONCE_LENGTH:]

    try:
        return AESGCM(key).decrypt(nonce, ciphertext, associated_data)

    except InvalidTag:
        raise EncryptionError(
            "The value could not be decrypted. The passphrase is wrong, or "
            "the data was modified."
        ) from None


def encrypt_file(
    key: bytes,
    source: Path,
    destination: Path,
    associated_data: bytes,
) -> None:
    """Encrypt a file into the destination path."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    plaintext = Path(source).read_bytes()

    destination.write_bytes(
        encrypt_bytes(key, plaintext, associated_data)
    )


def decrypt_file(
    key: bytes,
    source: Path,
    destination: Path,
    associated_data: bytes,
) -> None:
    """Decrypt a file into the destination path."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    plaintext = decrypt_bytes(
        key,
        Path(source).read_bytes(),
        associated_data,
    )

    destination.write_bytes(plaintext)


def encrypted_name(name: str) -> str:
    """Return the stored name of an encrypted file."""

    return f"{name}{ENCRYPTED_SUFFIX}"


def is_encrypted_name(name: str) -> bool:
    """Return whether a stored file name is an encrypted one."""

    return name.endswith(ENCRYPTED_SUFFIX)


def resolve_passphrase(
    passphrase: str | None = None,
    prompt: bool = True,
) -> str | None:
    """Return the passphrase to use.

    The order is: the explicit argument, then the ``BACKUP_PASSPHRASE``
    environment variable, then an interactive prompt.

    The passphrase is never read from a command line argument.
    """

    if passphrase:
        return passphrase

    configured = os.getenv("BACKUP_PASSPHRASE")

    if configured:
        return configured

    if prompt and _stdin_is_a_terminal():
        return getpass.getpass("Backup passphrase: ")

    return None


def _stdin_is_a_terminal() -> bool:
    import sys

    try:
        return sys.stdin.isatty()

    except Exception:
        return False


def describe_parameters() -> dict:
    """Return the key derivation parameters, for the manifest."""

    return {
        "kdf": "scrypt",
        "n": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "salt": "",
    }
