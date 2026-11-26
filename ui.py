"""
IronVault Modern Desktop GUI (v2.0 Redesign)
Designed with a sleek, modern cyber/slate aesthetic:
- View Mode & Edit Mode with rich detail cards
- Category Avatars with distinct accent color coding
- Real-time live TOTP 2FA ticker with progress countdown bar
- Live item counter badges in sidebar (e.g. Logins: 4)
- Floating status toast with automatic dismissal
- Quick keyboard shortcuts (Ctrl+F for search, Ctrl+L to lock, Ctrl+N for new)
- High-contrast visual hierarchy with Segoe UI & Consolas fonts
"""

import os
import sys
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from crypto import (
    encrypt_vault, decrypt_vault, generate_secure_keyfile,
    check_password_strength, InvalidPasswordOrKeyfileError, CryptoError
)
from vault import (
    VaultManager, VaultItem, generate_random_password, generate_passphrase
)
from security_manager import SecurityManager

# Modern Color Palette (Deep Slate / Cyber Vibe)
C_CANVAS = "#080c14"        # Deepest dark background
C_SURFACE = "#0f172a"       # Main panels & sidebar
C_SURFACE_LIGHT = "#151f33" # Elevated panel
C_CARD = "#19243a"          # Individual item cards
C_CARD_HOVER = "#22314e"    # Card hover state
C_CARD_ACTIVE = "#1e2e4f"   # Selected item background
C_BORDER = "#253450"        # Subtle container borders
C_BORDER_FOCUS = "#38bdf8"  # Neon cyan / accent focus

# Accent Colors
C_PRIMARY = "#3b82f6"       # Electric Blue
C_PRIMARY_HOVER = "#2563eb"
C_CYAN = "#06b6d4"
C_EMERALD = "#10b981"       # Success / Green
C_EMERALD_HOVER = "#059669"
C_AMBER = "#f59e0b"         # Warning / Star
C_ROSE = "#ef4444"          # Danger / Lock
C_ROSE_HOVER = "#dc2626"
C_PURPLE = "#a855f7"        # Card / API Key

# Typography Colors
C_TEXT = "#f8fafc"
C_MUTED = "#64748b"
C_SUBTEXT = "#94a3b8"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class IronVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("IronVault – Zero-Knowledge Offline Password Manager")
        self.geometry("1280x820")
        self.minsize(1080, 680)
        self.configure(fg_color=C_CANVAS)

        # Core State
        self.vault_mgr = VaultManager()
        self.current_vault_path = None
        self.current_keyfile_path = None
        self.active_category = "All"
        self.active_item: VaultItem = None
        self.is_editing_item = False
        self.totp_timer_id = None
        self.toast_timer_id = None

        # Security manager (auto-lock after 5m idle, clipboard auto-clear in 30s)
        self.sec_mgr = SecurityManager(
            self,
            on_auto_lock_callback=self.on_auto_lock_triggered,
            auto_lock_timeout_secs=300
        )

        # Container frames
        self.auth_frame = None
        self.dashboard_frame = None

        # Global Hotkeys
        self.bind("<Control-l>", lambda e: self.lock_vault() if self.vault_mgr.is_unlocked else None)
        self.bind("<Control-L>", lambda e: self.lock_vault() if self.vault_mgr.is_unlocked else None)
        self.bind("<Control-n>", lambda e: self._on_click_new_item() if self.vault_mgr.is_unlocked else None)
        self.bind("<Control-N>", lambda e: self._on_click_new_item() if self.vault_mgr.is_unlocked else None)
        self.bind("<Control-f>", lambda e: self._focus_search() if self.vault_mgr.is_unlocked else None)
        self.bind("<Control-F>", lambda e: self._focus_search() if self.vault_mgr.is_unlocked else None)

        # Start at Welcome / Unlock view
        self.show_auth_view()

    # ==========================================================
    # AUTH VIEW (Unlock / Create Vault)
    # ==========================================================
    def show_auth_view(self):
        if self.dashboard_frame:
            self.dashboard_frame.destroy()
            self.dashboard_frame = None

        if self.totp_timer_id:
            self.after_cancel(self.totp_timer_id)
            self.totp_timer_id = None

        self.auth_frame = ctk.CTkFrame(self, fg_color=C_CANVAS, corner_radius=0)
        self.auth_frame.pack(fill="both", expand=True)

        # Elegant Centered Auth Card
        card = ctk.CTkFrame(
            self.auth_frame,
            fg_color=C_SURFACE,
            corner_radius=20,
            border_width=1,
            border_color=C_BORDER,
            width=540
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Top Badge / Logo
        badge = ctk.CTkLabel(
            card,
            text="🛡️",
            font=ctk.CTkFont(size=44)
        )
        badge.pack(pady=(35, 6))

        app_title = ctk.CTkLabel(
            card,
            text="IRONVAULT",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=C_TEXT
        )
        app_title.pack()

        subtitle = ctk.CTkLabel(
            card,
            text="Zero-Knowledge AES-256-GCM & Argon2id Security",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=C_SUBTEXT
        )
        subtitle.pack(pady=(2, 24))

        # Mode Tab Pills
        self.auth_tab = ctk.CTkSegmentedButton(
            card,
            values=["🔓  Unlock Vault", "✨  Create New Vault"],
            command=self._on_auth_tab_change,
            selected_color=C_PRIMARY,
            selected_hover_color=C_PRIMARY_HOVER,
            unselected_color=C_CARD,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.auth_tab.set("🔓  Unlock Vault")
        self.auth_tab.pack(padx=42, fill="x", pady=(0, 20))

        self.auth_form_container = ctk.CTkFrame(card, fg_color="transparent")
        self.auth_form_container.pack(fill="both", expand=True, padx=42, pady=(0, 35))

        self._render_unlock_form()

    def _on_auth_tab_change(self, selected):
        for widget in self.auth_form_container.winfo_children():
            widget.destroy()

        if "Unlock" in selected:
            self._render_unlock_form()
        else:
            self._render_create_form()

    def _render_unlock_form(self):
        # Vault File Picker
        lbl_vault = ctk.CTkLabel(self.auth_form_container, text="VAULT FILE LOCATION", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED, anchor="w")
        lbl_vault.pack(fill="x", pady=(0, 5))

        vault_box = ctk.CTkFrame(self.auth_form_container, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER)
        vault_box.pack(fill="x", pady=(0, 16))

        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_vault.ivault")
        self.ent_vault_path = ctk.CTkEntry(
            vault_box,
            placeholder_text="Choose .ivault file...",
            height=40,
            border_width=0,
            fg_color="transparent",
            text_color=C_TEXT
        )
        self.ent_vault_path.pack(side="left", fill="x", expand=True, padx=(10, 6))
        if os.path.exists(default_path):
            self.ent_vault_path.insert(0, default_path)

        btn_browse_v = ctk.CTkButton(
            vault_box, text="Browse", width=75, height=30,
            fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._browse_vault_file
        )
        btn_browse_v.pack(side="right", padx=6)

        # Master Password
        lbl_pwd = ctk.CTkLabel(self.auth_form_container, text="MASTER PASSWORD", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED, anchor="w")
        lbl_pwd.pack(fill="x", pady=(0, 5))

        pwd_box = ctk.CTkFrame(self.auth_form_container, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER)
        pwd_box.pack(fill="x", pady=(0, 16))

        self.ent_master_pwd = ctk.CTkEntry(
            pwd_box,
            placeholder_text="Enter your master password...",
            show="●",
            height=40,
            border_width=0,
            fg_color="transparent",
            text_color=C_TEXT,
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.ent_master_pwd.pack(side="left", fill="x", expand=True, padx=(10, 6))
        self.ent_master_pwd.bind("<Return>", lambda e: self._handle_unlock())

        self.btn_show_pwd = ctk.CTkButton(
            pwd_box, text="👁", width=36, height=30,
            fg_color="transparent", hover_color=C_CARD_HOVER,
            font=ctk.CTkFont(size=14),
            command=self._toggle_pwd_visibility
        )
        self.btn_show_pwd.pack(side="right", padx=6)

        # Keyfile toggle
        self.chk_use_keyfile = ctk.CTkCheckBox(
            self.auth_form_container,
            text="Use Secondary Keyfile (Dual-Factor Authentication)",
            command=self._toggle_keyfile_row,
            fg_color=C_PRIMARY, hover_color=C_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12),
            text_color=C_SUBTEXT
        )
        self.chk_use_keyfile.pack(anchor="w", pady=(0, 8))

        self.keyfile_row = ctk.CTkFrame(self.auth_form_container, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER)
        self.ent_keyfile_path = ctk.CTkEntry(
            self.keyfile_row,
            placeholder_text="Select your .key file...",
            height=40,
            border_width=0,
            fg_color="transparent"
        )
        self.ent_keyfile_path.pack(side="left", fill="x", expand=True, padx=(10, 6))
        btn_browse_kf = ctk.CTkButton(
            self.keyfile_row, text="Browse", width=75, height=30,
            fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
            corner_radius=8,
            command=self._browse_keyfile
        )
        btn_browse_kf.pack(side="right", padx=6)

        # Status text
        self.lbl_auth_status = ctk.CTkLabel(self.auth_form_container, text="", text_color=C_ROSE, font=ctk.CTkFont(size=12))
        self.lbl_auth_status.pack(pady=(4, 6))

        # Unlock Button
        btn_unlock = ctk.CTkButton(
            self.auth_form_container,
            text="🔓  Unlock IronVault",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOVER,
            command=self._handle_unlock
        )
        btn_unlock.pack(fill="x", pady=(8, 0))

    def _render_create_form(self):
        # Vault Location
        lbl_vault = ctk.CTkLabel(self.auth_form_container, text="SAVE NEW VAULT AS", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED, anchor="w")
        lbl_vault.pack(fill="x", pady=(0, 4))

        vbox = ctk.CTkFrame(self.auth_form_container, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER)
        vbox.pack(fill="x", pady=(0, 12))

        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_vault.ivault")
        self.ent_new_vault_path = ctk.CTkEntry(vbox, height=38, border_width=0, fg_color="transparent")
        self.ent_new_vault_path.insert(0, default_path)
        self.ent_new_vault_path.pack(side="left", fill="x", expand=True, padx=(10, 6))

        btn_browse = ctk.CTkButton(
            vbox, text="Save As", width=75, height=30,
            fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
            corner_radius=8,
            command=self._browse_new_vault_save
        )
        btn_browse.pack(side="right", padx=6)

        # Password
        lbl_pwd = ctk.CTkLabel(self.auth_form_container, text="CREATE MASTER PASSWORD", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED, anchor="w")
        lbl_pwd.pack(fill="x", pady=(0, 4))

        self.ent_new_pwd = ctk.CTkEntry(
            self.auth_form_container,
            placeholder_text="Enter a memorable, high-entropy password...",
            show="●",
            height=40,
            fg_color=C_CARD,
            border_color=C_BORDER,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.ent_new_pwd.pack(fill="x", pady=(0, 6))
        self.ent_new_pwd.bind("<KeyRelease>", self._on_password_typing)

        # Dynamic Password Strength Meter
        strength_row = ctk.CTkFrame(self.auth_form_container, fg_color="transparent")
        strength_row.pack(fill="x", pady=(0, 10))
        self.bar_strength = ctk.CTkProgressBar(strength_row, height=6, fg_color=C_CARD, corner_radius=3)
        self.bar_strength.set(0)
        self.bar_strength.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl_strength = ctk.CTkLabel(strength_row, text="Strength: Empty", text_color=C_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_strength.pack(side="right")

        # Confirm Password
        lbl_conf = ctk.CTkLabel(self.auth_form_container, text="CONFIRM MASTER PASSWORD", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED, anchor="w")
        lbl_conf.pack(fill="x", pady=(0, 4))
        self.ent_conf_pwd = ctk.CTkEntry(
            self.auth_form_container,
            placeholder_text="Repeat master password...",
            show="●",
            height=40,
            fg_color=C_CARD,
            border_color=C_BORDER,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.ent_conf_pwd.pack(fill="x", pady=(0, 12))

        # Keyfile Option
        self.chk_new_keyfile = ctk.CTkCheckBox(
            self.auth_form_container,
            text="Generate Dual-Factor Keyfile (Store on USB drive)",
            command=self._toggle_new_keyfile_options,
            fg_color=C_PRIMARY, hover_color=C_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12),
            text_color=C_SUBTEXT
        )
        self.chk_new_keyfile.pack(anchor="w", pady=(0, 8))

        self.new_keyfile_box = ctk.CTkFrame(self.auth_form_container, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER)
        self.ent_new_keyfile_path = ctk.CTkEntry(self.new_keyfile_box, height=38, border_width=0, fg_color="transparent")
        self.ent_new_keyfile_path.pack(side="left", fill="x", expand=True, padx=(10, 6))
        btn_gen_kf = ctk.CTkButton(
            self.new_keyfile_box, text="Set Keyfile", width=90, height=30,
            fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
            corner_radius=8,
            command=self._browse_new_keyfile_path
        )
        btn_gen_kf.pack(side="right", padx=6)

        # Status
        self.lbl_create_status = ctk.CTkLabel(self.auth_form_container, text="", text_color=C_ROSE, font=ctk.CTkFont(size=12))
        self.lbl_create_status.pack(pady=(4, 6))

        btn_create = ctk.CTkButton(
            self.auth_form_container,
            text="🚀  Create & Initialize Vault",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOVER,
            command=self._handle_create_vault
        )
        btn_create.pack(fill="x", pady=(8, 0))

    def _toggle_pwd_visibility(self):
        if self.ent_master_pwd.cget("show") == "●":
            self.ent_master_pwd.configure(show="")
            self.btn_show_pwd.configure(text="🔒")
        else:
            self.ent_master_pwd.configure(show="●")
            self.btn_show_pwd.configure(text="👁")

    def _toggle_keyfile_row(self):
        if self.chk_use_keyfile.get():
            self.keyfile_row.pack(fill="x", pady=(0, 15))
        else:
            self.keyfile_row.pack_forget()

    def _toggle_new_keyfile_options(self):
        if self.chk_new_keyfile.get():
            self.new_keyfile_box.pack(fill="x", pady=(0, 12))
            def_kf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault_key.key")
            self.ent_new_keyfile_path.delete(0, "end")
            self.ent_new_keyfile_path.insert(0, def_kf)
        else:
            self.new_keyfile_box.pack_forget()

    def _on_password_typing(self, event=None):
        pwd = self.ent_new_pwd.get()
        res = check_password_strength(pwd)
        score = res["score"] / 5.0
        self.bar_strength.set(score)
        self.bar_strength.configure(progress_color=res["color"])
        self.lbl_strength.configure(text=f"{res['label']} ({res['entropy']} bits)", text_color=res["color"])

    def _browse_vault_file(self):
        path = filedialog.askopenfilename(
            title="Select IronVault File",
            filetypes=[("IronVault Files", "*.ivault"), ("All Files", "*.*")]
        )
        if path:
            self.ent_vault_path.delete(0, "end")
            self.ent_vault_path.insert(0, path)

    def _browse_keyfile(self):
        path = filedialog.askopenfilename(
            title="Select Keyfile",
            filetypes=[("Key Files", "*.key"), ("All Files", "*.*")]
        )
        if path:
            self.ent_keyfile_path.delete(0, "end")
            self.ent_keyfile_path.insert(0, path)

    def _browse_new_vault_save(self):
        path = filedialog.asksaveasfilename(
            title="Choose Vault Destination",
            defaultextension=".ivault",
            filetypes=[("IronVault Files", "*.ivault")]
        )
        if path:
            self.ent_new_vault_path.delete(0, "end")
            self.ent_new_vault_path.insert(0, path)

    def _browse_new_keyfile_path(self):
        path = filedialog.asksaveasfilename(
            title="Set Keyfile Destination",
            defaultextension=".key",
            filetypes=[("Key Files", "*.key")]
        )
        if path:
            self.ent_new_keyfile_path.delete(0, "end")
            self.ent_new_keyfile_path.insert(0, path)

    def _handle_unlock(self):
        vault_path = self.ent_vault_path.get().strip()
        pwd = self.ent_master_pwd.get()
        use_keyfile = self.chk_use_keyfile.get()
        keyfile_path = self.ent_keyfile_path.get().strip() if use_keyfile else None

        if not vault_path or not os.path.exists(vault_path):
            self.lbl_auth_status.configure(text="Vault file not found! Select an existing .ivault file.")
            return

        if not pwd:
            self.lbl_auth_status.configure(text="Master password is required.")
            return

        keyfile_bytes = None
        if use_keyfile:
            if not keyfile_path or not os.path.exists(keyfile_path):
                self.lbl_auth_status.configure(text="Keyfile was not found at specified path.")
                return
            with open(keyfile_path, "rb") as kf:
                keyfile_bytes = kf.read()

        self.lbl_auth_status.configure(text="⚡ Deriving key with Argon2id (64MB RAM)...", text_color=C_CYAN)
        self.update()

        try:
            with open(vault_path, "rb") as f:
                blob = f.read()

            raw_json = decrypt_vault(blob, pwd, keyfile_bytes)
            self.vault_mgr.load_from_json(raw_json)
            self.current_vault_path = vault_path
            self.current_keyfile_path = keyfile_path
            self.master_pwd_cache = pwd

            self.show_dashboard_view()
        except InvalidPasswordOrKeyfileError as e:
            self.lbl_auth_status.configure(text=f"Authentication failed: {e}", text_color=C_ROSE)
        except Exception as e:
            self.lbl_auth_status.configure(text=f"Error unlocking vault: {str(e)}", text_color=C_ROSE)

    def _handle_create_vault(self):
        vault_path = self.ent_new_vault_path.get().strip()
        pwd = self.ent_new_pwd.get()
        conf = self.ent_conf_pwd.get()
        use_keyfile = self.chk_new_keyfile.get()
        keyfile_path = self.ent_new_keyfile_path.get().strip() if use_keyfile else None

        if not vault_path:
            self.lbl_create_status.configure(text="Specify destination for the vault.")
            return

        if not pwd:
            self.lbl_create_status.configure(text="Master password cannot be empty.")
            return

        if pwd != conf:
            self.lbl_create_status.configure(text="Passwords do not match.")
            return

        if len(pwd) < 8:
            self.lbl_create_status.configure(text="Password must be at least 8 characters.")
            return

        keyfile_bytes = None
        if use_keyfile:
            if not keyfile_path:
                self.lbl_create_status.configure(text="Choose a destination for the keyfile.")
                return
            try:
                generate_secure_keyfile(keyfile_path)
                with open(keyfile_path, "rb") as kf:
                    keyfile_bytes = kf.read()
            except Exception as e:
                self.lbl_create_status.configure(text=f"Keyfile error: {e}")
                return

        self.lbl_create_status.configure(text="⚡ Encrypting vault with Argon2id + AES-256-GCM...", text_color=C_CYAN)
        self.update()

        try:
            self.vault_mgr.new_vault()
            json_bytes = self.vault_mgr.to_json_bytes()
            encrypted_blob = encrypt_vault(json_bytes, pwd, keyfile_bytes)

            with open(vault_path, "wb") as f:
                f.write(encrypted_blob)

            self.current_vault_path = vault_path
            self.current_keyfile_path = keyfile_path
            self.master_pwd_cache = pwd

            self.show_dashboard_view()
            self.show_toast("✨ High-security vault initialized successfully!")
        except Exception as e:
            self.lbl_create_status.configure(text=f"Failed to create vault: {e}")

    # ==========================================================
    # MAIN DASHBOARD VIEW
    # ==========================================================
    def show_dashboard_view(self):
        if self.auth_frame:
            self.auth_frame.destroy()
            self.auth_frame = None

        self.dashboard_frame = ctk.CTkFrame(self, fg_color=C_CANVAS, corner_radius=0)
        self.dashboard_frame.pack(fill="both", expand=True)

        # 1. Sleek Navigation Header
        self._build_header_bar()

        # 2. Main 3-Column Body (Sidebar + Item Cards + Detail View)
        body = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(10, 14))

        self._build_sidebar(body)
        self._build_items_feed(body)
        self._build_detail_inspector(body)

        # Initial populate
        self._refresh_sidebar_counts()
        self._refresh_items_list()

        # Select first item if exists
        if self.vault_mgr.items:
            self._select_item(self.vault_mgr.items[0])

        # Start live TOTP ticker loop (1s resolution)
        self._totp_tick_loop()

    def _build_header_bar(self):
        top_bar = ctk.CTkFrame(self.dashboard_frame, fg_color=C_SURFACE, height=60, corner_radius=0)
        top_bar.pack(fill="x", side="top")

        # Brand Title
        brand_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        brand_box.pack(side="left", padx=(20, 16))

        ctk.CTkLabel(brand_box, text="🛡️", font=ctk.CTkFont(size=20)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            brand_box,
            text="IRONVAULT",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=C_TEXT
        ).pack(side="left")

        # Security Status Pill
        sec_badge = ctk.CTkFrame(top_bar, fg_color="#064e3b", corner_radius=12)
        sec_badge.pack(side="left", padx=5)

        ctk.CTkLabel(
            sec_badge,
            text="●  E2EE OFFLINE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#6ee7b7",
            padx=10,
            pady=3
        ).pack()

        # Modern Search Input
        search_box = ctk.CTkFrame(top_bar, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER, width=340)
        search_box.pack(side="left", padx=25)

        ctk.CTkLabel(search_box, text="🔍", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10, 2))
        self.search_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="Search passwords, tags, notes... (Ctrl+F)",
            width=260,
            height=34,
            border_width=0,
            fg_color="transparent"
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(2, 6))
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_items_list())

        # Header Right Actions
        right_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_box.pack(side="right", padx=20)

        # Lock Button
        btn_lock = ctk.CTkButton(
            right_box,
            text="🔒 Lock (Ctrl+L)",
            width=110,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#33141e",
            text_color="#fca5a5",
            hover_color=C_ROSE,
            command=self.lock_vault
        )
        btn_lock.pack(side="right")

    def _build_sidebar(self, parent):
        self.sidebar = ctk.CTkFrame(parent, fg_color=C_SURFACE, width=240, corner_radius=14, border_width=1, border_color=C_BORDER)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))

        # Categories Section
        lbl_head = ctk.CTkLabel(self.sidebar, text="VAULT CATEGORIES", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_MUTED)
        lbl_head.pack(anchor="w", padx=18, pady=(18, 6))

        self.cat_buttons = {}
        self.cat_counts = {}
        categories = [
            ("All", "📁  All Entries"),
            ("Favorites", "⭐  Favorites"),
            ("Login", "🔑  Logins"),
            ("Note", "📝  Secure Notes"),
            ("Card", "💳  Credit Cards"),
            ("API Key", "⚡  API Keys"),
        ]

        for cat_id, cat_name in categories:
            btn_row = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=38)
            btn_row.pack(fill="x", padx=10, pady=2)

            btn = ctk.CTkButton(
                btn_row,
                text=cat_name,
                anchor="w",
                fg_color=C_PRIMARY if cat_id == "All" else "transparent",
                hover_color=C_CARD_HOVER,
                corner_radius=8,
                height=36,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=lambda c=cat_id: self._on_select_category(c)
            )
            btn.pack(side="left", fill="x", expand=True)

            cnt_lbl = ctk.CTkLabel(
                btn_row,
                text="0",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=C_MUTED,
                width=24
            )
            cnt_lbl.pack(side="right", padx=(2, 6))

            self.cat_buttons[cat_id] = btn
            self.cat_counts[cat_id] = cnt_lbl

        # Divider
        div = ctk.CTkFrame(self.sidebar, fg_color=C_BORDER, height=1)
        div.pack(fill="x", padx=14, pady=16)

        # Bottom Utilities Section
        lbl_actions = ctk.CTkLabel(self.sidebar, text="QUICK ACTIONS", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_MUTED)
        lbl_actions.pack(anchor="w", padx=18, pady=(0, 6))

        btn_new = ctk.CTkButton(
            self.sidebar,
            text="➕ New Item (Ctrl+N)",
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOVER,
            corner_radius=10,
            height=46,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._on_click_new_item
        )
        btn_new.pack(fill="x", padx=10, pady=(4, 8))

        btn_gen = ctk.CTkButton(
            self.sidebar,
            text="🎲 Password Generator",
            fg_color=C_CARD,
            hover_color=C_CARD_HOVER,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self.open_password_generator_dialog
        )
        btn_gen.pack(fill="x", padx=10, pady=3)

        btn_backup = ctk.CTkButton(
            self.sidebar,
            text="💾 Export Backup",
            fg_color=C_CARD,
            hover_color=C_CARD_HOVER,
            corner_radius=8,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self._export_backup
        )
        btn_backup.pack(fill="x", padx=10, pady=3)

        # Bottom Auto-Lock Indicator
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        lbl_autolock = ctk.CTkLabel(
            self.sidebar,
            text="⏱ Auto-lock: 5m idle",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED
        )
        lbl_autolock.pack(side="bottom", pady=12)

    def _build_items_feed(self, parent):
        self.feed_container = ctk.CTkFrame(parent, fg_color=C_SURFACE, width=380, corner_radius=14, border_width=1, border_color=C_BORDER)
        self.feed_container.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # Feed Header
        header_row = ctk.CTkFrame(self.feed_container, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(16, 8))

        self.feed_title = ctk.CTkLabel(
            header_row,
            text="All Vault Entries",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=C_TEXT
        )
        self.feed_title.pack(side="left")

        self.feed_count_pill = ctk.CTkLabel(
            header_row,
            text="0 items",
            font=ctk.CTkFont(size=11),
            text_color=C_SUBTEXT,
            fg_color=C_CARD,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.feed_count_pill.pack(side="right")

        # Scrollable Feed
        self.scroll_feed = ctk.CTkScrollableFrame(self.feed_container, fg_color="transparent")
        self.scroll_feed.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _build_detail_inspector(self, parent):
        self.detail_container = ctk.CTkFrame(parent, fg_color=C_SURFACE, width=540, corner_radius=14, border_width=1, border_color=C_BORDER)
        self.detail_container.pack(side="right", fill="both")

        self.scroll_detail = ctk.CTkScrollableFrame(self.detail_container, fg_color="transparent")
        self.scroll_detail.pack(fill="both", expand=True, padx=20, pady=20)

        self._render_empty_detail()

    # ==========================================================
    # ITEM LIST FEED LOGIC
    # ==========================================================
    def _on_select_category(self, cat_id):
        self.active_category = cat_id
        for c_id, btn in self.cat_buttons.items():
            btn.configure(fg_color=C_PRIMARY if c_id == cat_id else "transparent")
        self.feed_title.configure(text=f"{cat_id} Entries")
        self._refresh_items_list()

    def _refresh_sidebar_counts(self):
        items = self.vault_mgr.items
        counts = {
            "All": len(items),
            "Favorites": len([i for i in items if i.favorite]),
            "Login": len([i for i in items if i.category == "Login"]),
            "Note": len([i for i in items if i.category == "Note"]),
            "Card": len([i for i in items if i.category == "Card"]),
            "API Key": len([i for i in items if i.category == "API Key"]),
        }
        for cat_id, cnt in counts.items():
            if cat_id in self.cat_counts:
                self.cat_counts[cat_id].configure(text=str(cnt))

    def _refresh_items_list(self):
        for w in self.scroll_feed.winfo_children():
            w.destroy()

        query = self.search_entry.get()
        items = self.vault_mgr.search_items(query, self.active_category)
        self.feed_count_pill.configure(text=f"{len(items)} items")

        if not items:
            empty_box = ctk.CTkFrame(self.scroll_feed, fg_color="transparent")
            empty_box.pack(pady=60)
            ctk.CTkLabel(empty_box, text="🔍", font=ctk.CTkFont(size=32)).pack(pady=4)
            ctk.CTkLabel(
                empty_box,
                text="No entries match your search",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=C_SUBTEXT
            ).pack()
            return

        for item in items:
            self._render_item_card(item)

    def _render_item_card(self, item: VaultItem):
        is_active = (self.active_item and self.active_item.id == item.id)

        card = ctk.CTkFrame(
            self.scroll_feed,
            fg_color=C_CARD_ACTIVE if is_active else C_CARD,
            corner_radius=10,
            border_width=1 if is_active else 0,
            border_color=C_PRIMARY if is_active else "transparent"
        )
        card.pack(fill="x", pady=4)
        card.bind("<Button-1>", lambda e, it=item: self._select_item(it))

        # Avatar Badge (Colored circle with category icon)
        category_meta = {
            "Login": ("🔑", "#1e3a8a", "#60a5fa"),
            "Note": ("📝", "#78350f", "#fcd34d"),
            "Card": ("💳", "#581c87", "#c084fc"),
            "API Key": ("⚡", "#064e3b", "#34d399"),
        }
        icon, bg_color, fg_color = category_meta.get(item.category, ("🔐", "#334155", "#cbd5e1"))

        avatar = ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=16),
            width=36,
            height=36,
            fg_color=bg_color,
            text_color=fg_color,
            corner_radius=18
        )
        avatar.pack(side="left", padx=(10, 10), pady=10)
        avatar.bind("<Button-1>", lambda e, it=item: self._select_item(it))

        # Info column
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=8)
        info.bind("<Button-1>", lambda e, it=item: self._select_item(it))

        title_text = item.title or "Untitled"
        title_box = ctk.CTkFrame(info, fg_color="transparent")
        title_box.pack(fill="x")
        title_box.bind("<Button-1>", lambda e, it=item: self._select_item(it))

        lbl_title = ctk.CTkLabel(
            title_box,
            text=title_text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=C_TEXT,
            anchor="w"
        )
        lbl_title.pack(side="left")
        lbl_title.bind("<Button-1>", lambda e, it=item: self._select_item(it))

        if item.favorite:
            ctk.CTkLabel(title_box, text="⭐", font=ctk.CTkFont(size=11), text_color=C_AMBER).pack(side="left", padx=4)

        sub_text = item.username or item.url or "(no details)"
        lbl_sub = ctk.CTkLabel(
            info,
            text=sub_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=C_MUTED,
            anchor="w"
        )
        lbl_sub.pack(fill="x")
        lbl_sub.bind("<Button-1>", lambda e, it=item: self._select_item(it))

        # Actions on Card
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=(4, 10))

        # Live TOTP ticker pill on card if secret exists
        if item.totp_secret:
            code, remaining = item.get_current_totp()
            if code and code != "INVALID":
                btn_totp = ctk.CTkButton(
                    actions,
                    text=f"⏱ {code}",
                    width=75,
                    height=28,
                    corner_radius=6,
                    fg_color="#1e1b4b",
                    hover_color="#312e81",
                    text_color="#a5b4fc",
                    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                    command=lambda it=item: self._copy_totp(it)
                )
                btn_totp.pack(side="left", padx=3)

        if item.password:
            btn_copy_pwd = ctk.CTkButton(
                actions,
                text="📋 Copy",
                width=60,
                height=28,
                corner_radius=6,
                fg_color=C_SURFACE_LIGHT,
                hover_color=C_PRIMARY,
                text_color=C_TEXT,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda it=item: self._copy_data(it.password, "Password")
            )
            btn_copy_pwd.pack(side="left", padx=3)

    def _select_item(self, item: VaultItem):
        self.active_item = item
        self.is_editing_item = False
        self._refresh_items_list()
        self._render_item_view_mode(item)

    def _render_empty_detail(self):
        for w in self.scroll_detail.winfo_children():
            w.destroy()

        box = ctk.CTkFrame(self.scroll_detail, fg_color="transparent")
        box.pack(expand=True, pady=120)

        ctk.CTkLabel(box, text="🔐", font=ctk.CTkFont(size=44)).pack(pady=4)
        ctk.CTkLabel(box, text="No Item Selected", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXT).pack()
        ctk.CTkLabel(
            box,
            text="Select an entry from the list to view secure details\nor create a new item to encrypt.",
            text_color=C_MUTED,
            justify="center",
            font=ctk.CTkFont(size=12)
        ).pack(pady=6)

    # ==========================================================
    # ITEM DETAIL: VIEW MODE (Modern Card Inspection)
    # ==========================================================
    def _render_item_view_mode(self, item: VaultItem):
        for w in self.scroll_detail.winfo_children():
            w.destroy()

        # 1. Top Header Banner
        top_hero = ctk.CTkFrame(self.scroll_detail, fg_color=C_CARD, corner_radius=12)
        top_hero.pack(fill="x", pady=(0, 14), padx=2)

        hero_left = ctk.CTkFrame(top_hero, fg_color="transparent")
        hero_left.pack(side="left", padx=16, pady=14)

        title_lbl = ctk.CTkLabel(
            hero_left,
            text=item.title or "Untitled",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT
        )
        title_lbl.pack(anchor="w")

        # Category Pill
        cat_badge = ctk.CTkLabel(
            hero_left,
            text=f"📂 {item.category.upper()}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=C_CYAN,
            fg_color=C_SURFACE,
            corner_radius=6,
            padx=8,
            pady=2
        )
        cat_badge.pack(anchor="w", pady=(4, 0))

        # Star toggle & Edit Button
        hero_right = ctk.CTkFrame(top_hero, fg_color="transparent")
        hero_right.pack(side="right", padx=16, pady=14)

        btn_fav = ctk.CTkButton(
            hero_right,
            text="⭐" if item.favorite else "☆",
            width=36,
            height=34,
            corner_radius=8,
            fg_color=C_SURFACE_LIGHT,
            hover_color=C_CARD_HOVER,
            font=ctk.CTkFont(size=15),
            command=lambda it=item: self._toggle_favorite(it)
        )
        btn_fav.pack(side="left", padx=(0, 6))

        btn_edit = ctk.CTkButton(
            hero_right,
            text="✏️ Edit",
            width=70,
            height=34,
            corner_radius=8,
            fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda it=item: self._render_item_edit_mode(it)
        )
        btn_edit.pack(side="left")

        # 2. TOTP 2FA HERO CARD (If TOTP Secret exists)
        if item.totp_secret:
            code, remaining = item.get_current_totp()
            totp_card = ctk.CTkFrame(self.scroll_detail, fg_color="#171e38", corner_radius=12, border_width=1, border_color="#3730a3")
            totp_card.pack(fill="x", pady=(0, 14), padx=2)

            t_top = ctk.CTkFrame(totp_card, fg_color="transparent")
            t_top.pack(fill="x", padx=16, pady=(12, 4))

            ctk.CTkLabel(t_top, text="⏱ TWO-FACTOR AUTHENTICATOR (TOTP)", font=ctk.CTkFont(size=10, weight="bold"), text_color="#a5b4fc").pack(side="left")
            self.lbl_totp_rem = ctk.CTkLabel(t_top, text=f"{remaining}s", font=ctk.CTkFont(size=11, weight="bold"), text_color="#c7d2fe")
            self.lbl_totp_rem.pack(side="right")

            # Formatted OTP code
            formatted_code = f"{code[:3]}  {code[3:]}" if len(code) == 6 else code
            otp_box = ctk.CTkFrame(totp_card, fg_color="transparent")
            otp_box.pack(fill="x", padx=16, pady=(2, 6))

            self.lbl_totp_val = ctk.CTkLabel(
                otp_box,
                text=formatted_code,
                font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
                text_color="#e0e7ff"
            )
            self.lbl_totp_val.pack(side="left")

            btn_copy_otp = ctk.CTkButton(
                otp_box,
                text="Copy Code",
                width=80,
                height=30,
                corner_radius=6,
                fg_color="#4338ca",
                hover_color="#4f46e5",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda it=item: self._copy_totp(it)
            )
            btn_copy_otp.pack(side="right")

            # Animated Progress Bar
            self.totp_progress = ctk.CTkProgressBar(totp_card, height=4, fg_color="#1e1b4b", progress_color="#818cf8")
            self.totp_progress.set(remaining / 30.0)
            self.totp_progress.pack(fill="x", padx=16, pady=(0, 12))

        # 3. Username / Email Field Card
        if item.username:
            self._render_view_field(
                label="USERNAME / EMAIL",
                value=item.username,
                on_copy=lambda: self._copy_data(item.username, "Username")
            )

        # 4. Password Field Card
        self._render_view_password_field(item)

        # 5. Website URL Field Card
        if item.url:
            self._render_view_field(
                label="WEBSITE URL",
                value=item.url,
                on_copy=lambda: self._copy_data(item.url, "URL"),
                on_launch=lambda: webbrowser.open(item.url)
            )

        # 6. Secure Notes Field Card
        if item.notes:
            notes_card = ctk.CTkFrame(self.scroll_detail, fg_color=C_CARD, corner_radius=10)
            notes_card.pack(fill="x", pady=5, padx=2)

            ctk.CTkLabel(notes_card, text="SECURE NOTES", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_MUTED).pack(anchor="w", padx=14, pady=(10, 4))
            txt_box = ctk.CTkTextbox(notes_card, height=80, fg_color=C_SURFACE_LIGHT, border_width=0, font=ctk.CTkFont(family="Consolas", size=12))
            txt_box.insert("1.0", item.notes)
            txt_box.configure(state="disabled")
            txt_box.pack(fill="x", padx=12, pady=(0, 12))

        # 7. Metadata & Timestamps
        meta_box = ctk.CTkFrame(self.scroll_detail, fg_color="transparent")
        meta_box.pack(fill="x", pady=(14, 0))

        updated_str = item.updated_at[:19].replace("T", " ") if item.updated_at else "Just now"
        ctk.CTkLabel(
            meta_box,
            text=f"Last updated: {updated_str}",
            font=ctk.CTkFont(size=11),
            text_color=C_MUTED
        ).pack(side="left")

    def _render_view_field(self, label: str, value: str, on_copy=None, on_launch=None):
        card = ctk.CTkFrame(self.scroll_detail, fg_color=C_CARD, corner_radius=10)
        card.pack(fill="x", pady=4, padx=2)

        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=C_MUTED).pack(anchor="w", padx=14, pady=(8, 2))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))

        lbl_val = ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=C_TEXT,
            anchor="w"
        )
        lbl_val.pack(side="left", fill="x", expand=True)

        if on_launch:
            btn_launch = ctk.CTkButton(
                row, text="🌐 Launch", width=70, height=28,
                corner_radius=6,
                fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
                font=ctk.CTkFont(size=11),
                command=on_launch
            )
            btn_launch.pack(side="right", padx=(4, 0))

        if on_copy:
            btn_copy = ctk.CTkButton(
                row, text="📋 Copy", width=60, height=28,
                corner_radius=6,
                fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
                font=ctk.CTkFont(size=11),
                command=on_copy
            )
            btn_copy.pack(side="right")

    def _render_view_password_field(self, item: VaultItem):
        card = ctk.CTkFrame(self.scroll_detail, fg_color=C_CARD, corner_radius=10)
        card.pack(fill="x", pady=4, padx=2)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(8, 2))

        ctk.CTkLabel(top, text="PASSWORD / SECRET", font=ctk.CTkFont(size=10, weight="bold"), text_color=C_MUTED).pack(side="left")

        # Password strength badge
        p_info = check_password_strength(item.password)
        badge = ctk.CTkLabel(
            top,
            text=f"{p_info['label']} ({p_info['entropy']} bits)",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=p_info["color"]
        )
        badge.pack(side="right")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(2, 10))

        self.lbl_view_pwd = ctk.CTkLabel(
            row,
            text="●●●●●●●●●●●●",
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=C_TEXT,
            anchor="w"
        )
        self.lbl_view_pwd.pack(side="left", fill="x", expand=True)
        self.is_view_pwd_revealed = False

        def _toggle_peek():
            if self.is_view_pwd_revealed:
                self.lbl_view_pwd.configure(text="●●●●●●●●●●●●")
                btn_eye.configure(text="👁 Reveal")
                self.is_view_pwd_revealed = False
            else:
                self.lbl_view_pwd.configure(text=item.password or "(empty)")
                btn_eye.configure(text="🔒 Hide")
                self.is_view_pwd_revealed = True

        btn_eye = ctk.CTkButton(
            row, text="👁 Reveal", width=70, height=28,
            corner_radius=6,
            fg_color=C_SURFACE_LIGHT, hover_color=C_CARD_HOVER,
            font=ctk.CTkFont(size=11),
            command=_toggle_peek
        )
        btn_eye.pack(side="right", padx=(4, 0))

        btn_copy = ctk.CTkButton(
            row, text="📋 Copy", width=60, height=28,
            corner_radius=6,
            fg_color=C_PRIMARY, hover_color=C_PRIMARY_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._copy_data(item.password, "Password")
        )
        btn_copy.pack(side="right")

    # ==========================================================
    # ITEM DETAIL: EDIT / ADD MODE
    # ==========================================================
    def _on_click_new_item(self):
        new_item = VaultItem(category="Login")
        self.active_item = new_item
        self._render_item_edit_mode(new_item, is_new=True)

    def _render_item_edit_mode(self, item: VaultItem, is_new: bool = False):
        self.is_editing_item = True
        for w in self.scroll_detail.winfo_children():
            w.destroy()

        header_row = ctk.CTkFrame(self.scroll_detail, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header_row,
            text="✨ Add New Entry" if is_new else "✏️ Edit Entry",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_TEXT
        ).pack(side="left")

        # Category Menu
        ctk.CTkLabel(self.scroll_detail, text="CATEGORY", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(4, 4))
        self.opt_category = ctk.CTkOptionMenu(
            self.scroll_detail,
            values=["Login", "Note", "Card", "API Key"],
            fg_color=C_CARD,
            button_color=C_PRIMARY,
            corner_radius=8,
            height=42,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.opt_category.set(item.category)
        self.opt_category.pack(fill="x", pady=(0, 12))

        # Title
        ctk.CTkLabel(self.scroll_detail, text="TITLE / SERVICE NAME", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.ent_title = ctk.CTkEntry(self.scroll_detail, placeholder_text="e.g. Google, GitHub, Netflix...", height=42, fg_color=C_CARD, border_color=C_BORDER, corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.ent_title.insert(0, item.title)
        self.ent_title.pack(fill="x", pady=(0, 12))

        # Username
        ctk.CTkLabel(self.scroll_detail, text="USERNAME / EMAIL", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.ent_username = ctk.CTkEntry(self.scroll_detail, placeholder_text="e.g. alex@company.com", height=42, fg_color=C_CARD, border_color=C_BORDER, corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.ent_username.insert(0, item.username)
        self.ent_username.pack(fill="x", pady=(0, 12))

        # Password
        ctk.CTkLabel(self.scroll_detail, text="PASSWORD", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(0, 4))
        pwd_box = ctk.CTkFrame(self.scroll_detail, fg_color=C_CARD, corner_radius=8, border_width=1, border_color=C_BORDER, height=44)
        pwd_box.pack(fill="x", pady=(0, 12))

        self.ent_password = ctk.CTkEntry(
            pwd_box, show="●", height=42, border_width=0, fg_color="transparent", font=ctk.CTkFont(family="Consolas", size=14)
        )
        self.ent_password.insert(0, item.password)
        self.ent_password.pack(side="left", fill="x", expand=True, padx=(12, 6))

        btn_peek = ctk.CTkButton(
            pwd_box, text="👁", width=38, height=34, fg_color="transparent", hover_color=C_CARD_HOVER,
            command=self._toggle_edit_pwd_peek
        )
        btn_peek.pack(side="left", padx=2)

        btn_gen = ctk.CTkButton(
            pwd_box, text="🎲", width=38, height=34, fg_color=C_PRIMARY, hover_color=C_PRIMARY_HOVER,
            command=self._fill_generated_password
        )
        btn_gen.pack(side="left", padx=(2, 8))

        # Website URL
        ctk.CTkLabel(self.scroll_detail, text="WEBSITE URL", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.ent_url = ctk.CTkEntry(self.scroll_detail, placeholder_text="https://...", height=42, fg_color=C_CARD, border_color=C_BORDER, corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.ent_url.insert(0, item.url)
        self.ent_url.pack(fill="x", pady=(0, 12))

        # TOTP Secret
        ctk.CTkLabel(self.scroll_detail, text="TOTP SECRET KEY (OPTIONAL 2FA)", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.ent_totp = ctk.CTkEntry(self.scroll_detail, placeholder_text="e.g. JBSWY3DPEHPK3PXP", height=42, fg_color=C_CARD, border_color=C_BORDER, corner_radius=8, font=ctk.CTkFont(family="Consolas", size=13))
        self.ent_totp.insert(0, item.totp_secret)
        self.ent_totp.pack(fill="x", pady=(0, 12))

        # Secure Notes
        ctk.CTkLabel(self.scroll_detail, text="SECURE NOTES / RECOVERY KEYS", font=ctk.CTkFont(size=11, weight="bold"), text_color=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.txt_notes = ctk.CTkTextbox(self.scroll_detail, height=120, fg_color=C_CARD, border_width=1, border_color=C_BORDER, corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.txt_notes.insert("1.0", item.notes)
        self.txt_notes.pack(fill="x", pady=(0, 18))

        # Action Buttons
        btn_save = ctk.CTkButton(
            self.scroll_detail,
            text="💾  Save & Encrypt to Vault",
            height=48,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=C_EMERALD,
            hover_color=C_EMERALD_HOVER,
            command=lambda it=item, is_new_flag=is_new: self._save_item(it, is_new_flag)
        )
        btn_save.pack(fill="x", pady=(0, 8))

        cancel_row = ctk.CTkFrame(self.scroll_detail, fg_color="transparent")
        cancel_row.pack(fill="x")

        btn_cancel = ctk.CTkButton(
            cancel_row,
            text="Cancel",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=C_CARD,
            hover_color=C_CARD_HOVER,
            command=lambda: self._render_item_view_mode(item) if not is_new else self._render_empty_detail()
        )
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 6))

        if not is_new:
            btn_del = ctk.CTkButton(
                cancel_row,
                text="🗑️ Delete",
                height=38,
                corner_radius=8,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#3b111a",
                text_color="#fca5a5",
                hover_color=C_ROSE,
                command=lambda it=item: self._delete_item(it)
            )
            btn_del.pack(side="right", padx=(4, 0))

    def _toggle_edit_pwd_peek(self):
        if self.ent_password.cget("show") == "●":
            self.ent_password.configure(show="")
        else:
            self.ent_password.configure(show="●")

    def _fill_generated_password(self):
        pwd = generate_random_password(length=20)
        self.ent_password.delete(0, "end")
        self.ent_password.insert(0, pwd)
        self.show_toast("🎲 High-entropy 20-character password generated!")

    def _save_item(self, item: VaultItem, is_new: bool):
        item.title = self.ent_title.get().strip() or "Untitled"
        item.category = self.opt_category.get()
        item.username = self.ent_username.get().strip()
        item.password = self.ent_password.get()
        item.url = self.ent_url.get().strip()
        item.totp_secret = self.ent_totp.get().strip()
        item.notes = self.txt_notes.get("1.0", "end-1c").strip()

        if is_new:
            self.vault_mgr.add_item(item)
        else:
            self.vault_mgr.update_item(item)

        self._persist_vault_to_disk()
        self.show_toast(f"🔒 '{item.title}' encrypted and saved.")
        self._refresh_sidebar_counts()
        self._refresh_items_list()
        self._render_item_view_mode(item)

    def _delete_item(self, item: VaultItem):
        if messagebox.askyesno("Confirm Deletion", f"Permanently remove '{item.title}' from the encrypted vault?"):
            self.vault_mgr.delete_item(item.id)
            self._persist_vault_to_disk()
            self.active_item = None
            self._render_empty_detail()
            self._refresh_sidebar_counts()
            self._refresh_items_list()
            self.show_toast("Item permanently removed.")

    def _toggle_favorite(self, item: VaultItem):
        item.favorite = not item.favorite
        self.vault_mgr.update_item(item)
        self._persist_vault_to_disk()
        self._refresh_sidebar_counts()
        self._refresh_items_list()
        self._render_item_view_mode(item)

    def _persist_vault_to_disk(self):
        if not self.current_vault_path or not self.master_pwd_cache:
            return

        keyfile_bytes = None
        if self.current_keyfile_path and os.path.exists(self.current_keyfile_path):
            with open(self.current_keyfile_path, "rb") as kf:
                keyfile_bytes = kf.read()

        json_bytes = self.vault_mgr.to_json_bytes()
        encrypted_blob = encrypt_vault(json_bytes, self.master_pwd_cache, keyfile_bytes)

        tmp_path = self.current_vault_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(encrypted_blob)
        os.replace(tmp_path, self.current_vault_path)

    def _copy_data(self, text: str, label: str = "Data"):
        if not text:
            return
        self.sec_mgr.copy_sensitive_data(
            text,
            clear_after_secs=30,
            on_clear_cb=lambda: self.show_toast(f"🛡️ Clipboard cleared for security ({label}).")
        )
        self.show_toast(f"📋 Copied {label} to clipboard! (Auto-clears in 30s)")

    def _copy_totp(self, item: VaultItem):
        code, _ = item.get_current_totp()
        if code and code != "INVALID":
            self._copy_data(code, f"2FA Code for {item.title}")

    def _focus_search(self):
        if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
            self.search_entry.focus()
            self.search_entry.select_range(0, "end")

    # ==========================================================
    # TOAST NOTIFICATION SYSTEM
    # ==========================================================
    def show_toast(self, message: str, duration_ms: int = 3500):
        if hasattr(self, "toast_label") and self.toast_label.winfo_exists():
            self.toast_label.destroy()

        self.toast_label = ctk.CTkLabel(
            self.dashboard_frame if self.dashboard_frame else self,
            text=message,
            fg_color="#1e293b",
            text_color="#f8fafc",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            padx=16,
            pady=8
        )
        self.toast_label.place(relx=0.5, rely=0.94, anchor="center")

        if self.toast_timer_id:
            self.after_cancel(self.toast_timer_id)

        def _dismiss():
            if hasattr(self, "toast_label") and self.toast_label.winfo_exists():
                self.toast_label.destroy()

        self.toast_timer_id = self.after(duration_ms, _dismiss)

    # ==========================================================
    # TOTP LIVE TICK LOOP
    # ==========================================================
    def _totp_tick_loop(self):
        if not self.vault_mgr.is_unlocked:
            return

        # If viewing an item with TOTP, update remaining counter & progress smoothly
        if self.active_item and self.active_item.totp_secret and not self.is_editing_item:
            code, remaining = self.active_item.get_current_totp()
            if hasattr(self, "lbl_totp_rem") and self.lbl_totp_rem.winfo_exists():
                self.lbl_totp_rem.configure(text=f"{remaining}s")
            if hasattr(self, "totp_progress") and self.totp_progress.winfo_exists():
                self.totp_progress.set(remaining / 30.0)
            if hasattr(self, "lbl_totp_val") and self.lbl_totp_val.winfo_exists():
                formatted_code = f"{code[:3]}  {code[3:]}" if len(code) == 6 else code
                self.lbl_totp_val.configure(text=formatted_code)

        self.totp_timer_id = self.after(1000, self._totp_tick_loop)

    def lock_vault(self):
        self.vault_mgr.lock()
        self.master_pwd_cache = None
        self.active_item = None
        self.show_auth_view()

    def on_auto_lock_triggered(self):
        if self.vault_mgr.is_unlocked:
            self.lock_vault()
            messagebox.showinfo("Vault Auto-Locked", "IronVault was automatically locked due to inactivity.")

    def _export_backup(self):
        dest = filedialog.asksaveasfilename(
            title="Export Encrypted Vault Backup",
            defaultextension=".ivault",
            filetypes=[("IronVault Files", "*.ivault")]
        )
        if dest:
            self._persist_vault_to_disk()
            with open(self.current_vault_path, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            self.show_toast(f"💾 Encrypted backup saved to: {os.path.basename(dest)}")

    # ==========================================================
    # PASSWORD GENERATOR MODAL DIALOG
    # ==========================================================
    def open_password_generator_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("🎲 Cryptographic Password Generator")
        dlg.geometry("520x480")
        dlg.configure(fg_color=C_CANVAS)
        dlg.transient(self)
        dlg.grab_set()

        lbl_top = ctk.CTkLabel(dlg, text="Cryptographic Password Generator", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=C_TEXT)
        lbl_top.pack(pady=(22, 10))

        # Output Card
        res_card = ctk.CTkFrame(dlg, fg_color=C_SURFACE, corner_radius=12, border_width=1, border_color=C_BORDER)
        res_card.pack(fill="x", padx=30, pady=10)

        ent_generated = ctk.CTkEntry(
            res_card,
            font=ctk.CTkFont(family="Consolas", size=15),
            height=44,
            justify="center",
            border_width=0,
            fg_color="transparent",
            text_color=C_TEXT
        )
        ent_generated.pack(fill="x", padx=12, pady=12)

        # Mode Tab
        seg_mode = ctk.CTkSegmentedButton(
            dlg,
            values=["Random Characters", "Diceware Passphrase"],
            selected_color=C_PRIMARY,
            selected_hover_color=C_PRIMARY_HOVER,
            corner_radius=8
        )
        seg_mode.set("Random Characters")
        seg_mode.pack(fill="x", padx=30, pady=5)

        opt_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        opt_frame.pack(fill="x", padx=30, pady=10)

        lbl_len = ctk.CTkLabel(opt_frame, text="Length: 20 characters", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_SUBTEXT)
        lbl_len.pack(anchor="w")

        slider_len = ctk.CTkSlider(opt_frame, from_=8, to=48, number_of_steps=40, progress_color=C_PRIMARY)
        slider_len.set(20)
        slider_len.pack(fill="x", pady=(4, 12))

        chk_upper = ctk.CTkCheckBox(opt_frame, text="Uppercase Letters (A-Z)", fg_color=C_PRIMARY)
        chk_upper.select()
        chk_upper.pack(anchor="w", pady=2)

        chk_digits = ctk.CTkCheckBox(opt_frame, text="Numbers (0-9)", fg_color=C_PRIMARY)
        chk_digits.select()
        chk_digits.pack(anchor="w", pady=2)

        chk_sym = ctk.CTkCheckBox(opt_frame, text="Symbols (!@#$%^&*)", fg_color=C_PRIMARY)
        chk_sym.select()
        chk_sym.pack(anchor="w", pady=2)

        def _generate():
            mode = seg_mode.get()
            length = int(slider_len.get())
            if mode == "Diceware Passphrase":
                words_count = max(3, min(8, int(length // 4)))
                lbl_len.configure(text=f"Passphrase: {words_count} Diceware words")
                pwd = generate_passphrase(word_count=words_count)
            else:
                lbl_len.configure(text=f"Length: {length} characters")
                pwd = generate_random_password(
                    length=length,
                    use_upper=bool(chk_upper.get()),
                    use_digits=bool(chk_digits.get()),
                    use_symbols=bool(chk_sym.get()),
                    avoid_ambiguous=True
                )
            ent_generated.delete(0, "end")
            ent_generated.insert(0, pwd)

        slider_len.configure(command=lambda v: _generate())
        seg_mode.configure(command=lambda v: _generate())
        _generate()

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=30, pady=16)

        btn_refresh = ctk.CTkButton(
            btn_row, text="🔄 Regenerate", fg_color=C_SURFACE, hover_color=C_CARD_HOVER, corner_radius=8, command=_generate
        )
        btn_refresh.pack(side="left", expand=True, fill="x", padx=(0, 6))

        def _copy_and_close():
            text = ent_generated.get()
            self._copy_data(text, "Generated Password")
            dlg.destroy()

        btn_copy = ctk.CTkButton(
            btn_row, text="📋 Copy & Close", fg_color=C_PRIMARY, hover_color=C_PRIMARY_HOVER, corner_radius=8, command=_copy_and_close
        )
        btn_copy.pack(side="right", expand=True, fill="x", padx=(6, 0))


if __name__ == "__main__":
    app = IronVaultApp()
    app.mainloop()
