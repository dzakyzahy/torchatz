"""
Tor Manager for TorChatZ.
Provides 100% autonomous Tor daemon management and v3 Onion Service creation.
Automatically starts Tor daemon on Windows and Linux (Kali) without manual user intervention.
"""

import socket
import sys
import os
import time
import shutil
import subprocess
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
        self.tor_process: Optional[subprocess.Popen] = None
        self.is_self_spawned: bool = False

    def check_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Helper to quickly check if a TCP port is open."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.error, OSError):
            return False

    def auto_detect_tor(self) -> Dict[str, Any]:
        """Auto-detects active Tor SOCKS5 and Control ports."""
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

    def start_tor_daemon(self) -> Tuple[bool, str]:
        """
        Autonomously starts Tor daemon in the background on Windows and Linux.
        Does not require external browser or manual setup.
        """
        detection = self.auto_detect_tor()
        if detection["socks_found"] and detection["control_found"]:
            return True, "Tor daemon is already running."

        project_root = Path(__file__).resolve().parent.parent
        tor_data_dir = project_root / "data" / "tor_data"
        tor_data_dir.mkdir(parents=True, exist_ok=True)

        is_windows = sys.platform == "win32"

        if is_windows:
            bin_tor = project_root / "bin" / "tor" / "tor" / "tor.exe"
            torrc_path = project_root / "bin" / "tor" / "torrc"

            # Check if Tor CLI exists or needs download
            if not bin_tor.exists():
                tor_in_path = shutil.which("tor.exe") or shutil.which("tor")
                if tor_in_path:
                    bin_tor = Path(tor_in_path)
                else:
                    # Run install script or download directly
                    install_bat = project_root / "scripts" / "install_tor_windows.bat"
                    if install_bat.exists():
                        try:
                            subprocess.run(["cmd.exe", "/c", str(install_bat)], check=True, cwd=str(project_root))
                        except Exception as e:
                            return False, f"Failed to download Tor Expert Bundle: {str(e)}"

            if not bin_tor.exists():
                return False, "Tor executable not found. Please run scripts\\install_tor_windows.bat"

            # Ensure torrc is configured
            if not torrc_path.exists():
                torrc_path.parent.mkdir(parents=True, exist_ok=True)
                torrc_content = (
                    "# TorChatZ Auto Configuration\n"
                    "SocksPort 9050\n"
                    "ControlPort 9051\n"
                    "CookieAuthentication 1\n"
                    f"DataDirectory {tor_data_dir.as_posix()}\n"
                    f"Log notice file {(project_root / 'data' / 'tor.log').as_posix()}\n"
                )
                torrc_path.write_text(torrc_content, encoding="utf-8")

            # Spawn Tor process detached without window
            DETACHED_PROCESS = 0x00000008
            CREATE_NO_WINDOW = 0x08000000
            try:
                self.tor_process = subprocess.Popen(
                    [str(bin_tor), "-f", str(torrc_path)],
                    creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(project_root)
                )
                self.is_self_spawned = True
            except Exception as e:
                return False, f"Failed to spawn tor.exe process: {str(e)}"

        else:
            # Linux (Kali / Debian / Ubuntu)
            tor_bin = shutil.which("tor")
            if not tor_bin:
                # Try installing via apt if on Kali/Debian
                try:
                    subprocess.run(["sudo", "apt", "update"], check=True)
                    subprocess.run(["sudo", "apt", "install", "-y", "tor"], check=True)
                    tor_bin = shutil.which("tor")
                except Exception:
                    pass

            if not tor_bin:
                return False, "Tor is not installed. Please run: sudo apt install -y tor"

            # Try starting systemd service first
            started_via_systemd = False
            try:
                res = subprocess.run(["sudo", "systemctl", "start", "tor"], capture_output=True, timeout=5)
                if res.returncode == 0:
                    started_via_systemd = True
            except Exception:
                pass

            if not started_via_systemd:
                # Spawn tor directly
                try:
                    self.tor_process = subprocess.Popen(
                        [
                            tor_bin,
                            "--SocksPort", "9050",
                            "--ControlPort", "9051",
                            "--CookieAuthentication", "1",
                            "--DataDirectory", str(tor_data_dir)
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        cwd=str(project_root)
                    )
                    self.is_self_spawned = True
                except Exception as e:
                    return False, f"Failed to start tor daemon: {str(e)}"

        # Wait for Tor ports to open (up to 25 seconds)
        for _ in range(25):
            time.sleep(1)
            detection = self.auto_detect_tor()
            if detection["socks_found"] and detection["control_found"]:
                return True, "Tor daemon started successfully!"

        return False, "Tor daemon started, but ports 9050/9051 did not respond in time."

    def setup_onion_service(self, local_port: int = 11009) -> Tuple[bool, str]:
        """
        Autonomously starts Tor daemon if needed, then creates or restores
        the Tor v3 Onion Service.
        """
        detection = self.auto_detect_tor()
        if not detection["socks_found"] or not detection["control_found"]:
            ok_start, start_msg = self.start_tor_daemon()
            if not ok_start:
                return False, start_msg
            detection = self.auto_detect_tor()

        # Connect to Tor Control Port via stem
        if detection["control_found"] and STEM_AVAILABLE:
            try:
                controller = Controller.from_port(port=self.active_control_port)
                # Try cookie / null auth
                try:
                    controller.authenticate(password=self.config.settings.get("control_password", ""))
                except stem.connection.AuthenticationFailure:
                    # Try explicit cookie file if in local data
                    project_root = Path(__file__).resolve().parent.parent
                    cookie_path = project_root / "data" / "tor_data" / "control_auth_cookie"
                    if cookie_path.exists():
                        controller.authenticate(chroot_path=str(cookie_path.parent))
                    else:
                        controller.authenticate()

                self.controller = controller

                if self.config.private_key:
                    key_type = "ED25519-V3"
                    key_content = self.config.private_key
                else:
                    key_type = "NEW"
                    key_content = "ED25519-V3"

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

                return (True, f"Tor Onion v3 Service online: {self.onion_address}")

            except Exception as e:
                pass

        # Static fallback
        if self.config.onion_address:
            self.onion_address = self.config.onion_address
            return (True, f"Using static Onion address: {self.onion_address}")

        return False, "Failed to authenticate with Tor Control Port 9051."

    def shutdown(self) -> None:
        """Cleans up ephemeral onion service and terminates self-spawned Tor process."""
        if self.controller and self._service_id:
            try:
                self.controller.remove_ephemeral_hidden_service(self._service_id)
            except Exception:
                pass
            try:
                self.controller.close()
            except Exception:
                pass

        if self.is_self_spawned and self.tor_process:
            try:
                self.tor_process.terminate()
                self.tor_process.wait(timeout=2)
            except Exception:
                pass
