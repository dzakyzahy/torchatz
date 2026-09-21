"""
Tor Manager for TorChatZ.
Manages Tor daemon detection, SOCKS5 proxy verification, and v3 Onion Service
creation using the Tor Control Port (stem) or static hidden services.
"""

import socket
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from .config import Config

try:
    from stem.control import Controller
    import stem
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False


class TorManager:
    def __init__(self, config: Config):
        self.config = config
        self.controller: Optional[Any] = None
        self.onion_address: Optional[str] = self.config.onion_address
        self.active_socks_port: int = self.config.socks_port
        self.active_control_port: int = self.config.control_port
        self._service_id: Optional[str] = None

    def check_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Helper to quickly check if a TCP port is open."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.error, OSError):
            return False

    def auto_detect_tor(self) -> Dict[str, Any]:
        """
        Auto-detects active Tor SOCKS5 and Control ports.
        Common ports:
          SOCKS5: 9050 (Tor Daemon / Kali / Linux), 9150 (Tor Browser / Windows)
          Control: 9051 (Tor Daemon), 9151 (Tor Browser)
        """
        socks_candidates = [self.config.socks_port, 9050, 9150]
        control_candidates = [self.config.control_port, 9051, 9151]

        found_socks = None
        for p in socks_candidates:
            if self.check_port_open("127.0.0.1", p):
                found_socks = p
                break

        found_control = None
        for p in control_candidates:
            if self.check_port_open("127.0.0.1", p):
                found_control = p
                break

        if found_socks:
            self.active_socks_port = found_socks
            self.config.socks_port = found_socks

        if found_control:
            self.active_control_port = found_control
            self.config.control_port = found_control

        return {
            "socks_found": found_socks is not None,
            "socks_port": found_socks,
            "control_found": found_control is not None,
            "control_port": found_control,
        }

    def setup_onion_service(self, local_port: int = 11009) -> Tuple[bool, str]:
        """
        Creates or restores a Tor v3 Onion Service.
        First tries Tor Control Port (ephemeral hidden service), then static fallback.
        """
        detection = self.auto_detect_tor()
        if not detection["socks_found"]:
            return (
                False,
                "Tor SOCKS5 proxy not found on port 9050 or 9150.\n"
                "Please make sure Tor is running:\n"
                "  - Kali Linux: Run 'sudo systemctl start tor'\n"
                "  - Windows: Start Tor Browser or Tor Expert Bundle"
            )

        # 1. Try Control Port via stem if available
        if detection["control_found"] and STEM_AVAILABLE:
            try:
                controller = Controller.from_port(port=self.active_control_port)
                # Try cookie or null auth first, fallback to configured password
                try:
                    controller.authenticate(password=self.config.settings.get("control_password", ""))
                except stem.connection.AuthenticationFailure:
                    controller.authenticate()

                self.controller = controller

                key_type = "ED25519-V3"
                key_content = "NEW"
                if self.config.private_key:
                    key_type = "ED25519-V3"
                    key_content = self.config.private_key

                # Port mapping: remote port (11009) -> local port (11009 on 127.0.0.1)
                response = controller.create_ephemeral_hidden_service(
                    {local_port: local_port},
                    key_type=key_type,
                    key_content=key_content,
                    await_publication=False
                )

                service_id = response.service_id
                self._service_id = service_id
                self.onion_address = f"{service_id}.onion"
                self.config.onion_address = self.onion_address

                if response.private_key and not self.config.private_key:
                    self.config.private_key = response.private_key
                    self.config.save_settings()

                return (True, f"Ephemeral v3 Onion Service active: {self.onion_address}")

            except Exception as e:
                # Log error and try static fallback
                pass

        # 2. Check for manual/static Tor hidden service hostname file
        static_paths = [
            Path("data") / "hostname",
            Path("tor_hidden_service") / "hostname",
            Path("/var/lib/tor/hidden_service/hostname"),
            Path("/var/lib/tor/torchatz/hostname"),
        ]

        for p in static_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        onion = f.read().strip()
                        if onion.endswith(".onion"):
                            self.onion_address = onion
                            self.config.onion_address = onion
                            return (True, f"Static v3 Onion Service found: {self.onion_address}")
                except Exception:
                    pass

        # 3. If onion address was previously saved or manual configuration
        if self.config.onion_address:
            self.onion_address = self.config.onion_address
            return (True, f"Using configured Onion address: {self.onion_address} (Ensure Tor routes port {local_port})")

        return (
            False,
            "Connected to Tor SOCKS5, but Tor Control Port is not available or refused authentication.\n"
            "To enable automatic onion creation:\n"
            "  1. In Kali Linux /etc/tor/torrc: add 'ControlPort 9051' and 'CookieAuthentication 1'\n"
            "  2. Or configure a HiddenServiceDir in your torrc pointing to 127.0.0.1:11009"
        )

    def shutdown(self) -> None:
        """Removes ephemeral hidden service and disconnects controller."""
        if self.controller and self._service_id:
            try:
                self.controller.remove_ephemeral_hidden_service(self._service_id)
            except Exception:
                pass
            try:
                self.controller.close()
            except Exception:
                pass
