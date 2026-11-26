# 🔒 IronVault Cryptographic & Security Deep-Dive

This document details the exact cryptographic standards, key derivation functions, file formatting, memory protections, and threat model employed by **IronVault**.

---

## 📑 Security Overview

IronVault is built on a **Zero-Knowledge, Local-First** architecture. 
- All cryptographic operations happen exclusively on the client machine.
- No plaintext passwords, derived keys, or salts are ever transmitted over a network.
- The cipher design follows OWASP, NIST, and RFC 9106 standards.

---

## 1. Key Derivation Function: Argon2id

Passwords are not used directly as encryption keys. Instead, they are transformed into 256-bit cryptographic keys using **Argon2id**.

```text
Password + [Optional Keyfile Hash] + 32-Byte Salt ──▶ [Argon2id KDF] ──▶ 256-Bit AES Key
```

### Parameters:
- **Algorithm**: Argon2id (`argon2.low_level.Type.ID`)
- **Memory Cost**: `65,536 KB` (64 MB of dedicated RAM per derivation)
- **Time Cost (Iterations)**: `3` passes
- **Parallelism**: `4` threads
- **Salt**: 32 bytes (256 bits) of cryptographically secure randomness generated via OS entropy source (`os.urandom(32)`)
- **Output Key Length**: 32 bytes (256 bits)

### Why Argon2id?
Standard hashing algorithms like MD5, SHA-256, or PBKDF2 can be brute-forced at millions of guesses per second using modern GPUs or specialized ASICs. 
Argon2id is a **memory-hard** function: each single guess forces the attacker's hardware to allocate 64 MB of high-speed memory. This eliminates GPU parallelization advantages and makes offline brute-force attacks mathematically and economically infeasible.

---

## 2. Authenticated Encryption: AES-256-GCM (AEAD)

Vault data is encrypted using **AES-256-GCM** (Galois/Counter Mode).

- **Key Size**: 256 bits
- **Nonce Size**: 96 bits (12 bytes) uniquely generated per encryption pass (`os.urandom(12)`)
- **Authentication Tag**: 128 bits (16 bytes)
- **Associated Authenticated Data (AAD)**: The binary header, format version, flags, and Argon2 salt are cryptographically bound to the ciphertext as AAD.

### Tamper Resistance:
GCM is an **Authenticated Encryption with Associated Data (AEAD)** cipher. If an attacker modifies even a single bit in the file header, salt, or ciphertext, decryption will immediately fail with an `InvalidTag` exception. It is impossible to alter or inject data into a vault without detection.

---

## 3. Dual-Factor Authentication: Physical Keyfile

When dual-factor protection is enabled:
1. A 32-byte (256-bit) cryptographically secure random entropy key is generated and stored in a standalone `.key` file.
2. During key derivation, the SHA-256 hash of the master password is concatenated with the SHA-256 hash of the keyfile:
   $$\text{Secret Material} = \text{SHA256}(\text{MasterPassword}) \parallel \text{SHA256}(\text{KeyfileBytes})$$
3. This combined secret material is passed into Argon2id.
4. Without the physical `.key` file, the derived key cannot be produced, even if the master password is known.

---

## 4. Binary File Format (`.ivault`)

An `.ivault` file is structured as follows:

| Offset | Length | Field | Description |
|---|---|---|---|
| `0x00` | 4 Bytes | Magic Header | `b"IVLT"` identifier |
| `0x04` | 1 Byte | Format Version | `0x01` (Version 1) |
| `0x05` | 1 Byte | Flags | `0x01` if keyfile required, else `0x00` |
| `0x06` | 32 Bytes | Argon2 Salt | Cryptographic salt for key derivation |
| `0x26` | 12 Bytes | AES-GCM Nonce | Unique 96-bit initialization vector |
| `0x32` | Variable | Ciphertext + Tag | Encrypted JSON payload + 16-byte GCM authentication tag |

---

## 5. Memory Security & Zeroization

- **Volatile RAM Only**: Unlocked credentials and decrypted items exist exclusively in volatile system memory (RAM).
- **Zeroization on Lock**: When the vault is locked or idle for 5 minutes, in-memory structures are cleared and garbage-collected.
- **Atomic Disk Writes**: When saving updates, IronVault writes the newly encrypted payload to a temporary file (`.tmp`) and atomically replaces the original file (`os.replace`) to prevent file corruption during power loss.

---

## 6. Threat Model & Security Guarantees

| Attack Vector | IronVault Defense |
|---|---|
| **Stolen Vault File (`.ivault`)** | Fully protected by AES-256-GCM. Decryption is impossible without the master password. |
| **GPU / ASIC Dictionary Attacks** | Mitigated by Argon2id's 64 MB memory-hard requirement. |
| **Tampered / Corrupted Vault File** | Detected by GCM's 128-bit authentication tag and AAD verification. |
| **Memory Scraping after Lock** | Memory is purged and references cleared upon locking. |
| **Clipboard Snooping** | Clipboard auto-clears 30 seconds after any copy action. |
| **Cloud Surveillance** | Zero network calls. Offline-first architecture. |
