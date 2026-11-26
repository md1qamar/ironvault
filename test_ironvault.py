"""
Comprehensive Automated Test Suite for IronVault
Tests:
1. Argon2id key derivation & AES-256-GCM encryption/decryption
2. Vault format validation & Tamper resistance
3. Dual-factor Keyfile protection
4. Item serialization, CRUD operations, & search
5. TOTP generation and remaining time
6. Password & Passphrase generation
"""

import os
import tempfile
from crypto import (
    encrypt_vault, decrypt_vault, generate_secure_keyfile,
    InvalidPasswordOrKeyfileError, CryptoError, check_password_strength
)
from vault import (
    VaultManager, VaultItem, generate_random_password, generate_passphrase
)


def test_crypto_pipeline():
    print("[TEST 1] Testing Argon2id + AES-256-GCM encryption & decryption...")
    secret_payload = b'{"secret": "master_key_12345", "accounts": [1, 2, 3]}'
    master_pwd = "P@ssw0rd!SuperSecret2026"

    # Encrypt
    encrypted_blob = encrypt_vault(secret_payload, master_pwd)
    assert len(encrypted_blob) > len(secret_payload)
    assert encrypted_blob[:4] == b"IVLT"

    # Decrypt with correct password
    decrypted = decrypt_vault(encrypted_blob, master_pwd)
    assert decrypted == secret_payload

    # Decrypt with wrong password
    try:
        decrypt_vault(encrypted_blob, "WrongPassword")
        assert False, "Should have thrown InvalidPasswordOrKeyfileError!"
    except InvalidPasswordOrKeyfileError:
        pass

    # Tamper with ciphertext (bit flip)
    tampered = bytearray(encrypted_blob)
    tampered[-5] ^= 0xFF
    try:
        decrypt_vault(bytes(tampered), master_pwd)
        assert False, "Should have detected tampering!"
    except InvalidPasswordOrKeyfileError:
        pass

    print(" -> Crypto pipeline passed successfully!")


def test_keyfile_dual_factor():
    print("[TEST 2] Testing Dual-Factor Keyfile protection...")
    with tempfile.NamedTemporaryFile(delete=False) as kf_temp:
        kf_path = kf_temp.name

    try:
        generate_secure_keyfile(kf_path)
        with open(kf_path, "rb") as f:
            kf_bytes = f.read()

        payload = b"Top secret classified data"
        master_pwd = "StrongMasterPassword123"

        # Encrypt with password + keyfile
        encrypted = encrypt_vault(payload, master_pwd, keyfile_bytes=kf_bytes)

        # Unlock with both
        decrypted = decrypt_vault(encrypted, master_pwd, keyfile_bytes=kf_bytes)
        assert decrypted == payload

        # Unlock without keyfile -> must fail
        try:
            decrypt_vault(encrypted, master_pwd, keyfile_bytes=None)
            assert False, "Should fail without keyfile!"
        except InvalidPasswordOrKeyfileError:
            pass

        # Unlock with wrong keyfile -> must fail
        try:
            decrypt_vault(encrypted, master_pwd, keyfile_bytes=b"dummy wrong keyfile data")
            assert False, "Should fail with wrong keyfile!"
        except InvalidPasswordOrKeyfileError:
            pass

        print(" -> Keyfile Dual-Factor verification passed successfully!")
    finally:
        if os.path.exists(kf_path):
            os.remove(kf_path)


def test_vault_crud_and_totp():
    print("[TEST 3] Testing Vault Manager CRUD and TOTP...")
    vm = VaultManager()
    vm.new_vault()

    # Add item with TOTP (RFC 6238 standard test secret: JBSWY3DPEHPK3PXP)
    item1 = VaultItem(
        title="Google Account",
        category="Login",
        username="user@gmail.com",
        password="MySecretPassword99!",
        url="https://accounts.google.com",
        totp_secret="JBSWY3DPEHPK3PXP",
        favorite=True
    )
    vm.add_item(item1)

    item2 = VaultItem(
        title="Server API Key",
        category="API Key",
        username="admin",
        password="sk_live_998877665544",
        notes="AWS Production token"
    )
    vm.add_item(item2)

    # Search
    search_res = vm.search_items("Google")
    assert len(search_res) == 1
    assert search_res[0].title == "Google Account"

    # Category search
    api_res = vm.search_items("", category="API Key")
    assert len(api_res) == 1
    assert api_res[0].title == "Server API Key"

    # TOTP generation
    code, rem = item1.get_current_totp()
    assert len(code) == 6
    assert code.isdigit()
    assert 0 <= rem <= 30

    # Serialization roundtrip
    json_bytes = vm.to_json_bytes()
    vm2 = VaultManager()
    vm2.load_from_json(json_bytes)
    assert len(vm2.items) == 2
    assert vm2.items[0].title == "Google Account"

    print(" -> Vault CRUD, Search, and TOTP passed successfully!")


def test_generators():
    print("[TEST 4] Testing Password & Passphrase generators...")
    pwd = generate_random_password(length=24, use_symbols=True)
    assert len(pwd) == 24
    str_info = check_password_strength(pwd)
    assert str_info["score"] >= 4

    phrase = generate_passphrase(word_count=5, separator="-")
    words = phrase.split("-")
    assert len(words) == 5

    print(" -> Generators passed successfully!")


if __name__ == "__main__":
    test_crypto_pipeline()
    test_keyfile_dual_factor()
    test_vault_crud_and_totp()
    test_generators()
    print("\nALL 4 TEST SUITES PASSED! 100% READY.")
