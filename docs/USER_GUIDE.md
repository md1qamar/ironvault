# 📖 IronVault User Guide & Keyfile Setup

Welcome to the comprehensive user guide for **IronVault**. This guide walks you through every feature of the password manager from initial vault creation to advanced dual-factor security.

---

## 📑 Table of Contents
1. [Initial Setup & Vault Creation](#1-initial-setup--vault-creation)
2. [Dual-Factor Keyfile (Optional High-Security Layer)](#2-dual-factor-keyfile-optional-high-security-layer)
3. [Unlocking & Locking Your Vault](#3-unlocking--locking-your-vault)
4. [Managing Vault Entries](#4-managing-vault-entries)
5. [Built-in TOTP 2FA Authenticator](#5-built-in-totp-2fa-authenticator)
6. [Password & Passphrase Generator](#6-password--passphrase-generator)
7. [Security Watchdogs (Auto-Lock & Clipboard Clear)](#7-security-watchdogs-auto-lock--clipboard-clear)
8. [Exporting Backups & Portability](#8-exporting-backups--portability)

---

## 1. Initial Setup & Vault Creation

When you launch IronVault for the first time:
1. Select the **"✨ Create New Vault"** tab in the center card.
2. Choose a destination path for your vault file (default: `my_vault.ivault`).
3. Enter a strong **Master Password** (at least 12–16 characters recommended).
   - Watch the live **Entropy Strength Meter** at the bottom of the password box. It calculates real-time bits of entropy from Red (*Very Weak*) to Emerald Green (*Very Strong*).
4. Confirm your Master Password.
5. Click **"🚀 Create Encrypted Vault"**.

> [!CAUTION]
> IronVault is a **zero-knowledge** password manager. We do not store your master password on any server. If you lose your master password, **it cannot be reset or recovered**. Store it in a secure location!

---

## 2. Dual-Factor Keyfile (Optional High-Security Layer)

A **Keyfile** acts as a physical security factor (*something you have*) alongside your master password (*something you know*).

### How to Enable a Keyfile:
1. During Vault Creation, check **"Enable Dual-Factor Keyfile"**.
2. Choose where to save the generated `.key` file (e.g., on an external USB flash drive).
3. IronVault will generate a 256-bit cryptographically secure random entropy key.

### How to Unlock with a Keyfile:
- Whenever you unlock your vault, check **"Use Secondary Keyfile"** and browse to the `.key` file.
- Even if someone discovers your master password, **they cannot decrypt the vault without having physical access to your keyfile**.

---

## 3. Unlocking & Locking Your Vault

- **To Unlock**: Select your `.ivault` file, type your Master Password (and select keyfile if enabled), and press **Enter** or click **"🔓 Unlock Vault"**.
- **To Lock**: Click the red **"🔒 Lock Vault"** button in the top right header, or press **`Ctrl + L`** anytime.
- Locking immediately purges all decrypted credentials from your computer's RAM.

---

## 4. Managing Vault Entries

IronVault provides an organized 3-column desktop layout:

### Adding a New Entry:
1. Click **"➕ New Item"** on the left sidebar, or press **`Ctrl + N`**.
2. The spacious right-side editor will open:
   - **Category**: Select `Login`, `Note`, `Card`, or `API Key`.
   - **Title**: Service name (e.g. *GitHub, Google, Netflix*).
   - **Username / Email**: Your login ID.
   - **Password**: Enter manually or click the **🎲 Generator** icon to generate a strong password. Click **👁** to peek.
   - **Website URL**: Web address. Click the **🌐 Launch** icon to open directly in your default browser.
   - **TOTP Secret**: Optional 2FA secret (see below).
   - **Secure Notes**: Multi-line recovery codes, PINs, or confidential notes.
3. Click **"💾 Save & Encrypt to Vault"**.

### Quick Search:
- Press **`Ctrl + F`** to focus the search bar in the top navigation.
- Real-time search filters entries instantly by title, username, website, and tags.

---

## 5. Built-in TOTP 2FA Authenticator

IronVault serves as a full replacement for Google Authenticator or Authy.

1. When setting up 2FA on a service (e.g. GitHub, Google), copy the **Base32 secret key** (e.g. `JBSWY3DPEHPK3PXP`).
2. Paste it into the **TOTP Secret** field of that entry in IronVault and save.
3. Once saved:
   - The card in the center feed displays a live **⏱ 6-digit rolling code**.
   - A countdown timer refreshes every 30 seconds automatically.
   - Click the TOTP badge to copy the current code directly to your clipboard.

---

## 6. Password & Passphrase Generator

Click **"🎲 Password Gen"** in the sidebar to open the generator:
- **Random Characters**:
  - Slider controls length (8 to 48 characters).
  - Toggles for Uppercase (A–Z), Numbers (0–9), and Symbols (`!@#$%^&*`).
  - Automatic ambiguous character exclusion (`0`, `O`, `l`, `1`).
- **Diceware Passphrase**:
  - Generates memorable, high-entropy word combinations (e.g. `Glacier-Falcon-Orbit-Crystal`).

---

## 7. Security Watchdogs (Auto-Lock & Clipboard Clear)

IronVault runs two background security watchdogs:

1. **30-Second Clipboard Auto-Clear**:
   - Whenever you click "Copy" for a password, username, or TOTP code, a 30-second countdown begins.
   - After 30 seconds, IronVault automatically checks if the clipboard still contains the sensitive string and wipes it clean.
2. **5-Minute Inactivity Auto-Lock**:
   - If no mouse movement or keypress occurs for 5 minutes, IronVault automatically locks itself and zeros out volatile memory.

---

## 8. Exporting Backups & Portability

- Click **"💾 Export Backup"** in the left sidebar to save an encrypted copy of your `.ivault` file anywhere (USB drive, external hard drive, or cloud storage).
- Because `.ivault` files are encrypted with **AES-256-GCM**, the file is 100% safe to store in Google Drive, Dropbox, or OneDrive.
