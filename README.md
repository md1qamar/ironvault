# 🛡️ IronVault – High-Security Offline Password Manager

**IronVault** ek military-grade, 100% offline, zero-knowledge desktop password manager hai jise maximum privacy aur security ke liye design kiya gaya hai. Isme internet ka koi access nahi hota, iska matlab zero remote attack surface!

---

## 🔒 Cryptographic Architecture & Specifications

| Component | Standard / Algorithm | Parameters / Description |
|---|---|---|
| **Key Derivation Function (KDF)** | **Argon2id** (RFC 9106 / OWASP recommended) | Time Cost: 3 iterations<br>Memory Cost: 64 MB RAM<br>Parallelism: 4 threads<br>Salt: 32 bytes (256-bit cryptographically secure) |
| **Authenticated Encryption** | **AES-256-GCM** (AEAD) | Key: 256-bit derived key<br>Nonce: 96-bit unique random per encryption<br>Auth Tag: 128-bit authentication tag preventing tampering |
| **Tamper Resistance** | Header AAD Binding | Magic header, version, and salt are cryptographically bound to the ciphertext via Associated Authenticated Data. |
| **Dual-Factor Authentication** | Master Password + Optional Keyfile | 256-bit keyfile (USB or external file) combined with master password before KDF derivation. |
| **Memory Security** | Zero-Knowledge In-Memory Model | Vault data decrypt hota hai sirf RAM ke andar. App close ya lock hote hi memory zeroize ho jaati hai. |

---

## ✨ Features

- 🖥️ **Modern Dark-Mode Desktop GUI**: Clean, responsive UI with custom cyber-security dark theme.
- 🔐 **Zero-Knowledge 100% Offline Vault**: Koi cloud nahi, koi tracking nahi, koi internet connection nahi chahiye.
- 🔑 **Dual-Factor Keyfile Support**: Master password ke sath ek secret `.key` file ka option (e.g. on a USB drive). Keyfile ke bina vault khul hi nahi sakta.
- ⏱️ **Built-in TOTP Authenticator (2FA)**: Google Authenticator / Authy ki tarah 6-digit rolling 2FA codes directly app me generate hote hain live countdown ke sath.
- 📋 **Secure Clipboard Auto-Clear**: Password copy karne par timer start hota hai aur 30 seconds baad clipboard automatically wipe ho jata hai.
- 🔒 **Inactivity Auto-Lock**: Agar app 5 minute tak idle rahe, toh vault automatically lock ho jata hai aur memory purge ho jaati hai.
- 🎲 **Cryptographic Password & Passphrase Generator**:
  - High-entropy random passwords (symbols, numbers, uppercase, lowercase, avoid ambiguous).
  - Diceware multi-word passphrases (easy to remember, hard to crack).
- 🔍 **Instant Search & Categorization**: Logins, Secure Notes, Credit Cards, API Keys, and Favorites.
- 💾 **Encrypted Backup & Portability**: Single `.ivault` file jise aap aasani se backup ya carry kar sakte hain.

---

## 🚀 How to Run

### Option 1: Quick Launch
Double-click karein:
```
launch.bat
```

### Option 2: Command Line
```powershell
cd C:\Users\AC\.gemini\antigravity\scratch\ironvault
python main.py
```

### Run Automated Security Tests:
```powershell
python test_ironvault.py
```

---

## 📁 File Structure

```
ironvault/
├── crypto.py            # Argon2id, AES-256-GCM, Keyfile derivation, and entropy analyzer
├── vault.py             # Vault data model, CRUD, pyotp TOTP, password generator
├── security_manager.py  # Clipboard auto-clear and inactivity auto-lock watchdog
├── ui.py                # Modern CustomTkinter dark GUI application
├── main.py              # Main application launcher
├── test_ironvault.py    # Automated cryptographic and functional test suite
├── launch.bat           # 1-click double-click launcher for Windows
└── README.md            # Documentation
```
