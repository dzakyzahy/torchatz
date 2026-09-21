"""
End-to-End Loopback Integration Test for TorChatZ.
Simulates two peers on localhost verifying handshake, chat messaging, and binary file transfer.
"""

import unittest
import socket
import time
import tempfile
import os
from pathlib import Path

from torchatz.config import Config
from torchatz.file_transfer import FileTransferManager
from torchatz.network import PeerConnection
from torchatz.protocol import Protocol


class TestE2ELoopback(unittest.TestCase):
    def test_e2e_peer_chat_and_file_transfer(self):
        with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
            path_a = Path(dir_a)
            path_b = Path(dir_b)

            config_a = Config(data_dir=path_a / "data")
            config_a.username = "Alice"
            config_a.onion_address = "alice56characterslongv3hiddenonionaddress1234567890abcdef.onion"
            file_mgr_a = FileTransferManager(path_a / "downloads")

            config_b = Config(data_dir=path_b / "data")
            config_b.username = "Bob"
            config_b.onion_address = "bob56characterslongv3hiddenonionaddress1234567890abcdefg.onion"
            file_mgr_b = FileTransferManager(path_b / "downloads")

            messages_received_by_b = []
            files_completed_by_b = []

            # Create listening socket for A
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("127.0.0.1", 11088))
            server_sock.listen(1)

            # Connect client B to server A directly (loopback simulation)
            client_sock_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock_b.connect(("127.0.0.1", 11088))

            server_conn_sock, _ = server_sock.accept()

            # Initialize PeerConnection for A (inbound)
            peer_a = PeerConnection(
                sock=server_conn_sock,
                is_outbound=False,
                config=config_a,
                file_mgr=file_mgr_a,
                on_message=lambda s, u, txt, ts: None,
                on_file_start=lambda s, u, fn, sz: None,
                on_file_progress=lambda s, fn, r, t: None,
                on_file_complete=lambda s, u, p, ok, m: None,
                on_status_change=lambda o, u, st: None,
            )

            # Initialize PeerConnection for B (outbound)
            peer_b = PeerConnection(
                sock=client_sock_b,
                is_outbound=True,
                config=config_b,
                file_mgr=file_mgr_b,
                on_message=lambda s, u, txt, ts: messages_received_by_b.append((u, txt)),
                on_file_start=lambda s, u, fn, sz: None,
                on_file_progress=lambda s, fn, r, t: None,
                on_file_complete=lambda s, u, p, ok, m: files_completed_by_b.append((p, ok)),
                on_status_change=lambda o, u, st: None,
            )

            # Wait briefly for initial handshake exchange
            time.sleep(0.5)

            # 1. Test Chat: A sends chat to B
            self.assertTrue(peer_a.send_chat("Hello Bob! This is an anonymous message."))
            time.sleep(0.3)

            self.assertEqual(len(messages_received_by_b), 1)
            self.assertEqual(messages_received_by_b[0][0], "Alice")
            self.assertEqual(messages_received_by_b[0][1], "Hello Bob! This is an anonymous message.")

            # 2. Test File Transfer: A sends image file to B
            test_file = path_a / "sample_image.png"
            dummy_data = os.urandom(80 * 1024)  # 80 KB
            test_file.write_bytes(dummy_data)

            ok_send, send_msg = peer_a.send_file(test_file)
            self.assertTrue(ok_send)

            # Wait for transfer and SHA-256 verification
            time.sleep(0.5)

            self.assertEqual(len(files_completed_by_b), 1)
            saved_path, success = files_completed_by_b[0]
            self.assertTrue(success)
            self.assertTrue(Path(saved_path).exists())
            self.assertEqual(Path(saved_path).read_bytes(), dummy_data)

            # Cleanup
            peer_a.close()
            peer_b.close()
            server_sock.close()


if __name__ == "__main__":
    unittest.main()
