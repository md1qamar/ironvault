"""
IronVault Cryptographic Subsystem
Implements OWASP/RFC 9106 standards:
- Argon2id Key Derivation Function (Memory-hard against GPU/ASIC attacks)
- AES-256-GCM Authenticated Encryption with Associated Data (AEAD)
- Master Password + Optional Keyfile Dual-Factor Authentication
- Zero-Knowledge Offline File Format (.ivault)
"""

import os
import math
import hashlib
import argon2.low_level as al
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC_HEADER = b"IVLT"
VERSION = 1

# Argon2id parameters (High security, OWASP recommended for password hashing & KDF)
ARGON2_TIME_COST = 3          # Iterations
ARGON2_MEMORY_COST = 65536    # 64 MB RAM
ARGON2_PARALLELISM = 4        # 4 threads
ARGON2_HASH_LEN = 32         # 256-bit AES key
SALT_LENGTH = 32             # 256-bit Salt
NONCE_LENGTH = 12            # 96-bit AES-GCM standard nonce

# Flags
FLAG_NONE = 0x00
FLAG_KEYFILE = 0x01


class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


class InvalidPasswordOrKeyfileError(CryptoError):
    """Raised when authentication fails or file is corrupted."""
    pass


def derive_key(password: str, salt: bytes, keyfile_bytes: bytes = None) -> bytes:
    """
    Derives a 256-bit AES key using Argon2id.
    If a keyfile is provided, its SHA-256 hash is concatenated with
    the password's SHA-256 hash before running through Argon2id.
    """
    pwd_hash = hashlib.sha256(password.encode("utf-8")).digest()
    
    if keyfile_bytes:
        kf_hash = hashlib.sha256(keyfile_bytes).digest()
        secret_material = pwd_hash + kf_hash
    else:
        secret_material = pwd_hash

    # Run through Argon2id (Type.ID)
    derived_key = al.hash_secret_raw(
        secret=secret_material,
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=al.Type.ID
    )
    return derived_key


def encrypt_vault(data: bytes, password: str, keyfile_bytes: bytes = None) -> bytes:
    """
    Encrypts arbitrary byte payload into the IronVault binary format.
    Format:
    [4B MAGIC: 'IVLT']
    [1B VERSION: 0x01]
    [1B FLAGS: 0x01 if keyfile was used else 0x00]
    [32B Argon2 Salt]
    [12B AES-GCM Nonce]
    [Remaining: Ciphertext + 16B Auth Tag]
    """
    salt = os.urandom(SALT_LENGTH)
    nonce = os.urandom(NONCE_LENGTH)
    flags = FLAG_KEYFILE if keyfile_bytes else FLAG_NONE

    key = derive_key(password, salt, keyfile_bytes)
    aesgcm = AESGCM(key)

    # Header is used as Associated Authenticated Data (AAD)
    # This prevents tampering with magic, version, flags, or salt
    header_aad = MAGIC_HEADER + bytes([VERSION, flags]) + salt

    ciphertext_with_tag = aesgcm.encrypt(nonce, data, header_aad)

    # Assemble complete vault payload
    vault_blob = header_aad + nonce + ciphertext_with_tag
    return vault_blob


def decrypt_vault(blob: bytes, password: str, keyfile_bytes: bytes = None) -> bytes:
    """
    Decrypts an IronVault binary blob.
    Throws InvalidPasswordOrKeyfileError on wrong password, wrong keyfile, or tampered file.
    """
    min_length = 4 + 1 + 1 + SALT_LENGTH + NONCE_LENGTH + 16
    if len(blob) < min_length:
        raise CryptoError("Corrupted vault file: size is too small.")

    magic = blob[:4]
    if magic != MAGIC_HEADER:
        raise CryptoError("Invalid vault format: magic header mismatch.")

    version = blob[4]
    if version != VERSION:
        raise CryptoError(f"Unsupported vault version: {version}")

    flags = blob[5]
    has_keyfile_flag = bool(flags & FLAG_KEYFILE)

    if has_keyfile_flag and not keyfile_bytes:
        raise InvalidPasswordOrKeyfileError("This vault requires a Keyfile to unlock.")
    if not has_keyfile_flag and keyfile_bytes:
        # User provided keyfile when vault was created without one
        raise InvalidPasswordOrKeyfileError("This vault was created without a Keyfile. Please unlock with password only.")

    offset = 6
    salt = blob[offset : offset + SALT_LENGTH]
    offset += SALT_LENGTH

    header_aad = blob[:offset]

    nonce = blob[offset : offset + NONCE_LENGTH]
    offset += NONCE_LENGTH

    ciphertext_with_tag = blob[offset:]

    key = derive_key(password, salt, keyfile_bytes)
    aesgcm = AESGCM(key)

    try:
        decrypted_data = aesgcm.decrypt(nonce, ciphertext_with_tag, header_aad)
        return decrypted_data
    except Exception as e:
        raise InvalidPasswordOrKeyfileError("Decryption failed. Incorrect master password or invalid keyfile.") from e


def generate_secure_keyfile(filepath: str):
    """
    Generates a 256-bit cryptographically secure keyfile with a human-readable header.
    """
    random_entropy = os.urandom(32)
    with open(filepath, "wb") as f:
        f.write(b"--- BEGIN IRONVAULT KEYFILE ---\n")
        f.write(random_entropy)
        f.write(b"\n--- END IRONVAULT KEYFILE ---")


def check_password_strength(password: str) -> dict:
    """
    Calculates password entropy and returns strength analysis.
    """
    if not password:
        return {"score": 0, "entropy": 0.0, "label": "Empty", "color": "#ef4444"}

    pool_size = 0
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)

    if has_lower: pool_size += 26
    if has_upper: pool_size += 26
    if has_digit: pool_size += 10
    if has_symbol: pool_size += 33

    entropy = len(password) * (math.log2(pool_size) if pool_size > 0 else 0)

    if entropy < 36:
        return {"score": 1, "entropy": round(entropy, 1), "label": "Very Weak", "color": "#ef4444"}
    elif entropy < 50:
        return {"score": 2, "entropy": round(entropy, 1), "label": "Weak", "color": "#f97316"}
    elif entropy < 65:
        return {"score": 3, "entropy": round(entropy, 1), "label": "Fair", "color": "#eab308"}
    elif entropy < 80:
        return {"score": 4, "entropy": round(entropy, 1), "label": "Strong", "color": "#22c55e"}
    else:
        return {"score": 5, "entropy": round(entropy, 1), "label": "Very Strong", "color": "#10b981"}
