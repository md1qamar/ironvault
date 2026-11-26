# ❓ IronVault FAQ & Troubleshooting

Frequently asked questions and troubleshooting tips for **IronVault**.

---

## 📑 General Questions

### Q1: Is my data safe if I store my `.ivault` file on Google Drive or Dropbox?
**Yes, 100% safe.**  
Your `.ivault` file is already encrypted on your local computer using **AES-256-GCM** before it ever leaves your machine. Cloud storage providers (Google, Microsoft, Dropbox) only see scrambled binary noise. Without your Master Password, neither cloud providers nor any unauthorized party can read your data.

### Q2: Can AI or supercomputers decrypt my `.ivault` file?
**No.**  
AES-256 has $2^{256}$ possible key combinations (more than the estimated number of atoms in the observable universe). AI models search for patterns, but AES-256 ciphertext is indistinguishable from true mathematical randomness. Even with all the world's supercomputers running for billions of years, AES-256 cannot be brute-forced.

### Q3: What happens if I forget my Master Password?
Because IronVault is a **zero-knowledge** password manager, we do not store your master password anywhere. There are no backdoor recovery keys or "Forgot Password" links. If you lose your master password, your vault data **cannot be recovered**. We recommend writing down your master password and storing it in a physical safe.

### Q4: Does IronVault send any data to external servers?
**No.**  
IronVault has zero network connections. It does not contain telemetry, analytics, tracking, or remote API calls. It runs completely offline and air-gapped on your computer.

---

## ⏱️ TOTP Authenticator Questions

### Q5: How do I migrate 2FA from Google Authenticator to IronVault?
1. Log into your account (e.g. GitHub, Google, Amazon).
2. Go to **Security > Two-Factor Authentication**.
3. Choose "Set up new authenticator app".
4. When shown a QR code, click **"Can't scan QR code?"** or **"Show text secret key"**.
5. Copy the 16 or 32-character Base32 text key and paste it into IronVault's **TOTP Secret** field.
6. IronVault will immediately start generating the correct 6-digit rolling codes.

### Q6: Why does my TOTP 2FA code say "INVALID"?
Make sure your computer's system clock is accurate. TOTP codes (RFC 6238) are time-synchronized with global UTC time. If your computer clock is skewed by more than 30–60 seconds, generated codes may be rejected by websites.

---

## 🛠️ Troubleshooting

### Issue 1: "Decryption failed. Incorrect master password or invalid keyfile."
- Verify that **Caps Lock** is off.
- If you enabled a **Keyfile** when creating the vault, ensure the "Use Secondary Keyfile" checkbox is checked and you have selected the exact same `.key` file.
- Check that you selected the correct `.ivault` file.

### Issue 2: App does not open when double-clicking `launch.bat`
1. Ensure Python 3.10 or higher is installed and added to your system `PATH`.
2. Open PowerShell in the project directory and run:
   ```powershell
   python main.py
   ```
   This will print any missing dependency or error message directly to the console.
3. Install required packages:
   ```powershell
   pip install -r requirements.txt
   ```

### Issue 3: "This vault requires a Keyfile to unlock."
You attempted to unlock a vault that was created with dual-factor keyfile protection without specifying a keyfile. Check the **"Use Secondary Keyfile"** box and browse to your `.key` file.

---

## 💡 Best Practices

1. **Keep Regular Backups**: Use the "💾 Export Backup" button to save a copy of your `.ivault` file onto a USB drive once a month.
2. **Keep Your Keyfile Separate**: If using a keyfile, do not store it in the exact same directory as your vault file. Keep your keyfile on a dedicated USB flash drive.
3. **Use Long Passphrases**: A 4 or 5-word Diceware passphrase (e.g. `Summit-Lagoon-Orbit-Falcon-Crystal`) is easier to remember than random symbols and offers over 65+ bits of entropy.
