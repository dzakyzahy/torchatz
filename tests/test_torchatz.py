"""
Unit and Integration Tests for TorChatZ.
Validates protocol framing, privacy guarantees, file transfer chunking, and SHA-256 verification.
"""

import unittest
import json
import base64
import hashlib
import tempfile
import os
from pathlib import Path

from torchatz.protocol import Protocol, MessageType
from torchatz.file_transfer import FileTransferManager, sanitize_filename
from torchatz.config import Config


class TestTorChatZProtocol(unittest.TestCase):
    def test_frame_packing_and_unpacking(self):
        payload = {
            "type": MessageType.CHAT,
            "text": "Hello world from TorChatZ! 🧅",
            "ts": 123456789,
        }
        frame_bytes = Protocol.pack_frame(payload)
        self.assertGreaterEqual(len(frame_bytes), 4)

        # Unpack header
        header = frame_bytes[:4]
        length = Protocol.unpack_header(header)
        self.assertEqual(len(frame_bytes) - 4, length)

        # Unpack body
        body = json.loads(frame_bytes[4:].decode("utf-8"))
        self.assertEqual(body["type"], MessageType.CHAT)
        self.assertEqual(body["text"], "Hello world from TorChatZ! 🧅")

    def test_privacy_guarantee_no_os_or_ip_in_handshake(self):
        handshake = Protocol.create_handshake(
            my_onion="abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwx.onion",
            username="Alice",
            session_id="session123"
        )
        json_str = json.dumps(handshake)

        # Ensure no system information or IP patterns exist in handshake payload
        self.assertNotIn("192.168.", json_str)
        self.assertNotIn("10.", json_str)
        self.assertNotIn("Windows", json_str)
        self.assertNotIn("Linux", json_str)
        self.assertNotIn("Kali", json_str)
        self.assertNotIn("Darwin", json_str)
        self.assertIn("Alice", json_str)
        self.assertIn(".onion", json_str)

    def test_file_transfer_integrity_and_sha256(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source_file = tmppath / "test_image.png"
            # Write 150 KB of random dummy image data
            test_content = os.urandom(150 * 1024)
            source_file.write_bytes(test_content)

            downloads_dir = tmppath / "downloads"
            file_mgr = FileTransferManager(downloads_dir)

            size, sha256_hash = file_mgr.calculate_file_hash(source_file)
            self.assertEqual(size, len(test_content))
            self.assertEqual(sha256_hash, hashlib.sha256(test_content).hexdigest().lower())

            # Simulate inbound file reception
            inbound = file_mgr.start_inbound(
                file_id="fid_123",
                filename="../../danger/path/secret_photo.png",  # Directory traversal attempt
                filesize=size,
                sha256_hash=sha256_hash
            )

            # Check filename sanitization
            self.assertEqual(inbound.filename, "secret_photo.png")

            # Chunked writing simulation
            chunk_size = 64 * 1024
            for i in range(0, len(test_content), chunk_size):
                chunk = test_content[i:i + chunk_size]
                inbound.write_chunk(chunk)

            success, msg, saved_path = inbound.finalize()
            self.assertTrue(success)
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.read_bytes(), test_content)

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("test.jpg"), "test.jpg")
        self.assertEqual(sanitize_filename("../../../evil.exe"), "evil.exe")
        self.assertEqual(sanitize_filename("C:\\Windows\\System32\\cmd.exe"), "cmd.exe")
        self.assertEqual(sanitize_filename("foo/bar/baz.mp4"), "baz.mp4")

    def test_config_contacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(data_dir=Path(tmpdir))
            onion = "expyuz5wqqfdgah56789abcdefghijklmnopqrstuvwxyz12345678.onion"
            config.add_contact(onion, alias="Bob")

            resolved = config.resolve_onion("Bob")
            self.assertEqual(resolved, onion)
            self.assertEqual(config.get_alias(onion), "Bob")

            # Remove contact
            self.assertTrue(config.remove_contact("Bob"))
            self.assertIsNone(config.resolve_onion("Bob"))

    def test_inbound_peer_registration_and_status(self):
        from torchatz.network import NetworkManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(data_dir=Path(tmpdir))
            file_mgr = FileTransferManager(Path(tmpdir) / "downloads")

            statuses = []
            net_mgr = NetworkManager(
                config=config,
                file_mgr=file_mgr,
                on_message=lambda s, u, t, ts: None,
                on_file_start=lambda s, u, fn, sz: None,
                on_file_progress=lambda s, fn, r, tot: None,
                on_file_complete=lambda s, u, p, ok, m: None,
                on_status_change=lambda o, u, st: statuses.append((o, u, st)),
                on_system_log=lambda lvl, msg: None,
            )

            class MockPeer:
                def __init__(self, onion):
                    self.peer_onion = onion
                    self.is_alive = True

            mock_peer = MockPeer("testonion123456.onion")
            net_mgr._handle_peer_status(mock_peer, "testonion123456.onion", "Bob", "connected")

            self.assertTrue(net_mgr.is_peer_online("testonion123456.onion"))
            self.assertEqual(net_mgr.get_connection("testonion123456.onion"), mock_peer)
            self.assertEqual(len(statuses), 1)
            self.assertEqual(statuses[0], ("testonion123456.onion", "Bob", "connected"))

            # Disconnect
            net_mgr._handle_peer_status(mock_peer, "testonion123456.onion", "Bob", "disconnected")
            self.assertFalse(net_mgr.is_peer_online("testonion123456.onion"))
            self.assertIsNone(net_mgr.get_connection("testonion123456.onion"))


if __name__ == "__main__":
    unittest.main()
