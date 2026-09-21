"""
Configuration and Contact management for TorChatZ.
Ensures zero metadata leaks and persists user preferences locally.
"""

import json
import os
import secrets
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DOWNLOADS_DIR = Path("downloads")


class Config:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.downloads_dir = DEFAULT_DOWNLOADS_DIR
        self.config_file = self.data_dir / "settings.json"
        self.contacts_file = self.data_dir / "contacts.json"

        self._ensure_directories()
        self.settings: Dict[str, Any] = self._load_settings()
        self.contacts: Dict[str, Dict[str, Any]] = self._load_contacts()

    def _ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def _generate_default_username(self) -> str:
        # Anonymous random username without OS or system hints
        return f"Anon_{secrets.token_hex(2)}"

    def _load_settings(self) -> Dict[str, Any]:
        default_settings = {
            "username": self._generate_default_username(),
            "socks_host": "127.0.0.1",
            "socks_port": 9050,  # 9050 for Tor daemon, 9150 for Tor Browser
            "control_host": "127.0.0.1",
            "control_port": 9051,  # 9051 for Tor daemon, 9151 for Tor Browser
            "control_password": "",
            "listen_port": 11009,
            "onion_address": None,
            "private_key": None,  # Stored if ephemeral onion service key is saved
            "auto_accept_files": False,
            "max_file_size_mb": 500,
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except Exception:
                pass

        return default_settings

    def save_settings(self) -> None:
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def _load_contacts(self) -> Dict[str, Dict[str, Any]]:
        if self.contacts_file.exists():
            try:
                with open(self.contacts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_contacts(self) -> None:
        with open(self.contacts_file, "w", encoding="utf-8") as f:
            json.dump(self.contacts, f, indent=4)

    @property
    def username(self) -> str:
        return self.settings.get("username", "Anonymous")

    @username.setter
    def username(self, val: str) -> None:
        # Sanitize username (alphanumeric, underscores, dashes, spaces, max 24 chars)
        clean_name = "".join(c for c in val if c.isalnum() or c in ("_", "-", " ")).strip()[:24]
        self.settings["username"] = clean_name or "Anonymous"
        self.save_settings()

    @property
    def socks_port(self) -> int:
        return int(self.settings.get("socks_port", 9050))

    @socks_port.setter
    def socks_port(self, port: int) -> None:
        self.settings["socks_port"] = port
        self.save_settings()

    @property
    def control_port(self) -> int:
        return int(self.settings.get("control_port", 9051))

    @control_port.setter
    def control_port(self, port: int) -> None:
        self.settings["control_port"] = port
        self.save_settings()

    @property
    def listen_port(self) -> int:
        return int(self.settings.get("listen_port", 11009))

    @property
    def onion_address(self) -> Optional[str]:
        return self.settings.get("onion_address")

    @onion_address.setter
    def onion_address(self, addr: Optional[str]) -> None:
        self.settings["onion_address"] = addr
        self.save_settings()

    @property
    def private_key(self) -> Optional[str]:
        return self.settings.get("private_key")

    @private_key.setter
    def private_key(self, key_data: Optional[str]) -> None:
        self.settings["private_key"] = key_data
        self.save_settings()

    # --- Contact management ---
    def add_contact(self, onion: str, alias: Optional[str] = None, notes: str = "") -> str:
        onion = onion.strip().lower()
        if not onion.endswith(".onion"):
            onion = onion + ".onion"
        
        if not alias:
            alias = onion[:12] + "..."

        self.contacts[onion] = {
            "onion": onion,
            "alias": alias,
            "notes": notes,
        }
        self.save_contacts()
        return onion

    def remove_contact(self, identifier: str) -> bool:
        onion = self.resolve_onion(identifier)
        if onion and onion in self.contacts:
            del self.contacts[onion]
            self.save_contacts()
            return True
        return False

    def resolve_onion(self, identifier: str) -> Optional[str]:
        """Resolves alias or partial/full onion address to full onion address."""
        identifier = identifier.strip().lower()
        if identifier in self.contacts:
            return identifier
        
        if not identifier.endswith(".onion") and (identifier + ".onion") in self.contacts:
            return identifier + ".onion"

        # Check by alias
        for onion, data in self.contacts.items():
            if data.get("alias", "").lower() == identifier:
                return onion

        # If it looks like a valid onion address directly
        if identifier.endswith(".onion") and len(identifier) >= 22:
            return identifier

        return None

    def get_alias(self, onion: str) -> str:
        onion = onion.strip().lower()
        if onion in self.contacts and self.contacts[onion].get("alias"):
            return self.contacts[onion]["alias"]
        return onion[:10] + "..."
