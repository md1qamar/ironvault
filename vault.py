"""
IronVault In-Memory Vault Model & Core Operations
Handles CRUD, password generation, TOTP generation, and serialization.
"""

import json
import uuid
import secrets
import string
import time
from datetime import datetime
import pyotp
import pyotp.otp as _pyotp_otp

# Allow standard 16-char and 32-char Base32 authenticator secrets
try:
    _pyotp_otp.OTP.min_secret_length_bits = 0
except Exception:
    pass

# Curated wordlist for Diceware style passphrases (offline, secure, memorable)
DICEWARE_WORDS = [
    "amber", "anchor", "arrow", "badge", "breeze", "bridge", "cable", "canyon",
    "castle", "cliff", "cloud", "clover", "comet", "coral", "crystal", "delta",
    "desert", "diver", "dragon", "eagle", "ember", "falcon", "feather", "flame",
    "forest", "frost", "galaxy", "glacier", "harbor", "haven", "island", "jungle",
    "knight", "lagoon", "lantern", "lunar", "marble", "meadow", "meteor", "nebula",
    "oasis", "ocean", "orbit", "peak", "pebble", "phoenix", "planet", "quartz",
    "quiver", "radius", "raven", "reef", "ridge", "river", "rocket", "ruby",
    "sailor", "shadow", "shield", "silver", "solar", "spark", "summit", "thunder",
    "tiger", "timber", "titan", "tower", "valley", "vapor", "velvet", "vortex",
    "voyage", "walnut", "wave", "willow", "winter", "wizard", "zenith", "zephyr"
]


class VaultItem:
    def __init__(
        self,
        item_id: str = None,
        title: str = "",
        category: str = "Login",
        username: str = "",
        password: str = "",
        url: str = "",
        totp_secret: str = "",
        notes: str = "",
        favorite: bool = False,
        created_at: str = None,
        updated_at: str = None
    ):
        self.id = item_id or str(uuid.uuid4())
        self.title = title
        self.category = category  # Login, Note, Card, API Key
        self.username = username
        self.password = password
        self.url = url
        self.totp_secret = (totp_secret or "").strip().replace(" ", "").upper()
        self.notes = notes
        self.favorite = favorite
        now = datetime.now().isoformat()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "username": self.username,
            "password": self.password,
            "url": self.url,
            "totp_secret": self.totp_secret,
            "notes": self.notes,
            "favorite": self.favorite,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            item_id=data.get("id"),
            title=data.get("title", ""),
            category=data.get("category", "Login"),
            username=data.get("username", ""),
            password=data.get("password", ""),
            url=data.get("url", ""),
            totp_secret=data.get("totp_secret", ""),
            notes=data.get("notes", ""),
            favorite=data.get("favorite", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def get_current_totp(self) -> tuple[str, int]:
        """Returns (6-digit code, remaining_seconds_until_refresh) or (None, 0)"""
        if not self.totp_secret:
            return None, 0
        try:
            totp = pyotp.TOTP(self.totp_secret)
            now = time.time()
            code = totp.at(now)
            remaining = 30 - int(now % 30)
            return code, remaining
        except Exception:
            return "INVALID", 0


class VaultManager:
    """Manages the in-memory vault lifecycle."""
    def __init__(self):
        self.items: list[VaultItem] = []
        self.file_path: str = None
        self.has_keyfile: bool = False
        self.is_unlocked: bool = False

    def new_vault(self):
        self.items = []
        self.is_unlocked = True

    def load_from_json(self, raw_bytes: bytes):
        data = json.loads(raw_bytes.decode("utf-8"))
        self.items = [VaultItem.from_dict(item) for item in data.get("items", [])]
        self.is_unlocked = True

    def to_json_bytes(self) -> bytes:
        data = {
            "version": 1,
            "app": "IronVault",
            "exported_at": datetime.now().isoformat(),
            "items": [item.to_dict() for item in self.items]
        }
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    def add_item(self, item: VaultItem):
        self.items.append(item)

    def update_item(self, updated_item: VaultItem):
        for idx, item in enumerate(self.items):
            if item.id == updated_item.id:
                updated_item.updated_at = datetime.now().isoformat()
                self.items[idx] = updated_item
                return True
        return False

    def delete_item(self, item_id: str):
        self.items = [item for item in self.items if item.id != item_id]

    def get_item(self, item_id: str) -> VaultItem:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def search_items(self, query: str = "", category: str = "All") -> list[VaultItem]:
        q = (query or "").lower().strip()
        results = []
        for item in self.items:
            if category and category != "All":
                if category == "Favorites" and not item.favorite:
                    continue
                elif category != "Favorites" and item.category != category:
                    continue

            if not q:
                results.append(item)
            elif (
                q in item.title.lower()
                or q in item.username.lower()
                or q in item.url.lower()
                or q in item.notes.lower()
            ):
                results.append(item)
        
        # Sort favorites first, then alphabetically by title
        results.sort(key=lambda x: (not x.favorite, x.title.lower()))
        return results

    def lock(self):
        """Zero out vault state from memory."""
        self.items.clear()
        self.is_unlocked = False


def generate_random_password(
    length: int = 18,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    avoid_ambiguous: bool = True
) -> str:
    """Generates cryptographically secure password with guaranteed character diversity."""
    ambiguous = "0OIl1|`'\"~"
    chars = ""
    guaranteed = []

    if use_lower:
        l = "".join(c for c in string.ascii_lowercase if not (avoid_ambiguous and c in ambiguous))
        chars += l
        guaranteed.append(secrets.choice(l))
    if use_upper:
        u = "".join(c for c in string.ascii_uppercase if not (avoid_ambiguous and c in ambiguous))
        chars += u
        guaranteed.append(secrets.choice(u))
    if use_digits:
        d = "".join(c for c in string.digits if not (avoid_ambiguous and c in ambiguous))
        chars += d
        guaranteed.append(secrets.choice(d))
    if use_symbols:
        s = "!@#$%^&*()-_=+[]{}<>?"
        chars += s
        guaranteed.append(secrets.choice(s))

    if not chars:
        chars = string.ascii_letters + string.digits

    remaining_len = max(0, length - len(guaranteed))
    pwd_list = guaranteed + [secrets.choice(chars) for _ in range(remaining_len)]
    
    # Secure shuffle
    for i in range(len(pwd_list) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        pwd_list[i], pwd_list[j] = pwd_list[j], pwd_list[i]

    return "".join(pwd_list)


def generate_passphrase(word_count: int = 4, separator: str = "-") -> str:
    """Generates Diceware style passphrase."""
    chosen = [secrets.choice(DICEWARE_WORDS) for _ in range(word_count)]
    # Capitalize each word for extra readability and entropy
    return separator.join(w.capitalize() for w in chosen)
