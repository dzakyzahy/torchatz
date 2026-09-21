"""
Network subsystem for TorChatZ.
Implements SOCKS5 outbound routing over Tor and localhost inbound listening.
Provides strictly zero-knowledge networking: all peers connect via .onion only.
"""

import socket
import threading
import time
import base64
import os
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple

from .protocol import Protocol, MessageType, DEFAULT_CHUNK_SIZE, MAX_FRAME_SIZE
from .file_transfer import FileTransferManager, InboundTransfer, sanitize_filename
from .config import Config

try:
    import socks
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False


class PeerConnection:
    """Represents an active connection with a peer over Tor."""
    def __init__(
        self,
        sock: socket.socket,
        is_outbound: bool,
        config: Config,
        file_mgr: FileTransferManager,
        on_message: Callable[[str, str, str, int], None],
        on_file_start: Callable[[str, str, str, int], None],
        on_file_progress: Callable[[str, str, int, int], None],
        on_file_complete: Callable[[str, str, str, bool, str], None],
        on_status_change: Callable[[str, str, str], None],
        target_onion: Optional[str] = None
    ):
        self.sock = sock
        self.is_outbound = is_outbound
        self.config = config
        self.file_mgr = file_mgr

        self.on_message = on_message
        self.on_file_start = on_file_start
        self.on_file_progress = on_file_progress
        self.on_file_complete = on_file_complete
        self.on_status_change = on_status_change

        self.peer_onion: Optional[str] = target_onion
        self.peer_username: str = "Anonymous"
        self.is_authenticated = False
        self.is_alive = True
        self.session_id = secrets.token_hex(8)

        self._send_lock = threading.Lock()
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # Send initial handshake if this is an outbound connection
        if self.is_outbound and self.config.onion_address:
            self.send_frame(Protocol.create_handshake(
                my_onion=self.config.onion_address,
                username=self.config.username,
                session_id=self.session_id
            ))

    def send_frame(self, payload: Dict[str, Any]) -> bool:
        """Packs and sends a frame over the TCP stream."""
        if not self.is_alive:
            return False
        try:
            data = Protocol.pack_frame(payload)
            with self._send_lock:
                self.sock.sendall(data)
            return True
        except Exception:
            self.close()
            return False

    def send_chat(self, text: str) -> bool:
        return self.send_frame(Protocol.create_chat(text))

    def send_file(self, filepath: Path, progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[bool, str]:
        """Reads and transmits a file in binary chunks over the Tor circuit."""
        if not filepath.exists() or not filepath.is_file():
            return False, f"File not found: {filepath}"

        file_id = secrets.token_hex(6)
        safe_name = sanitize_filename(filepath.name)
        filesize, sha256_hash = self.file_mgr.calculate_file_hash(filepath)

        # 1. Send file start announcement
        if not self.send_frame(Protocol.create_file_start(file_id, safe_name, filesize, sha256_hash)):
            return False, "Failed to send file start frame"

        # 2. Transmit chunks
        total_chunks = (filesize + DEFAULT_CHUNK_SIZE - 1) // DEFAULT_CHUNK_SIZE if filesize > 0 else 1
        sent_bytes = 0

        try:
            with open(filepath, "rb") as f:
                for chunk_idx in range(total_chunks):
                    if not self.is_alive:
                        return False, "Connection dropped during file transfer"

                    chunk_data = f.read(DEFAULT_CHUNK_SIZE)
                    if not self.send_frame(Protocol.create_file_chunk(
                        file_id=file_id,
                        chunk_index=chunk_idx,
                        total_chunks=total_chunks,
                        chunk_data=chunk_data
                    )):
                        return False, "Failed sending chunk"

                    sent_bytes += len(chunk_data)
                    if progress_callback:
                        progress_callback(sent_bytes, filesize)

            return True, f"File '{safe_name}' sent ({filesize} bytes), awaiting peer confirmation."
        except Exception as e:
            return False, f"File transfer error: {str(e)}"

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Helper to receive exactly n bytes from the socket."""
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except Exception:
                return None
        return bytes(data)

    def _read_loop(self) -> None:
        """Continuously reads framed messages from the socket."""
        import json
        while self.is_alive:
            header = self._recv_exact(4)
            if not header:
                break

            try:
                length = Protocol.unpack_header(header)
                if length <= 0 or length > MAX_FRAME_SIZE:
                    break

                body = self._recv_exact(length)
                if not body:
                    break

                payload = json.loads(body.decode("utf-8"))
                self._dispatch_payload(payload)

            except Exception:
                break

        self.close()

    def _dispatch_payload(self, payload: Dict[str, Any]) -> None:
        msg_type = payload.get("type")

        if msg_type == MessageType.HANDSHAKE:
            peer_onion = payload.get("onion", "").strip().lower()
            peer_username = payload.get("username", "Anonymous")
            self.peer_onion = peer_onion
            self.peer_username = peer_username
            self.is_authenticated = True

            # Reply with HANDSHAKE_ACK
            if self.config.onion_address:
                self.send_frame(Protocol.create_handshake_ack(
                    my_onion=self.config.onion_address,
                    username=self.config.username,
                    session_id=self.session_id
                ))
            self.on_status_change(self.peer_onion or "unknown", self.peer_username, "connected")

        elif msg_type == MessageType.HANDSHAKE_ACK:
            peer_onion = payload.get("onion", "").strip().lower()
            peer_username = payload.get("username", "Anonymous")
            if peer_onion:
                self.peer_onion = peer_onion
            self.peer_username = peer_username
            self.is_authenticated = True
            self.on_status_change(self.peer_onion or "unknown", self.peer_username, "connected")

        elif msg_type == MessageType.PING:
            self.send_frame(Protocol.create_pong())

        elif msg_type == MessageType.PONG:
            pass

        elif msg_type == MessageType.CHAT:
            text = payload.get("text", "")
            ts = payload.get("ts", int(time.time()))
            sender = self.peer_onion or "unknown.onion"
            self.on_message(sender, self.peer_username, text, ts)

        elif msg_type == MessageType.FILE_START:
            file_id = payload.get("file_id", "")
            filename = payload.get("filename", "unknown.bin")
            filesize = payload.get("filesize", 0)
            sha256 = payload.get("sha256", "")
            sender = self.peer_onion or "unknown.onion"

            self.file_mgr.start_inbound(file_id, filename, filesize, sha256)
            self.on_file_start(sender, self.peer_username, filename, filesize)

        elif msg_type == MessageType.FILE_CHUNK:
            file_id = payload.get("file_id", "")
            data_b64 = payload.get("data_b64", "")
            sender = self.peer_onion or "unknown.onion"

            inbound = self.file_mgr.get_inbound(file_id)
            if inbound:
                try:
                    raw_chunk = base64.b64decode(data_b64)
                    inbound.write_chunk(raw_chunk)
                    self.on_file_progress(sender, inbound.filename, inbound.received_bytes, inbound.filesize)

                    # If all bytes received, finalize
                    if inbound.received_bytes >= inbound.filesize:
                        success, message, saved_path = inbound.finalize()
                        status = "ok" if success else "hash_mismatch"
                        self.send_frame(Protocol.create_file_ack(file_id, status, message))
                        self.on_file_complete(sender, self.peer_username, str(saved_path), success, message)
                        self.file_mgr.remove_inbound(file_id)
                except Exception as e:
                    inbound.abort()
                    self.send_frame(Protocol.create_file_ack(file_id, "error", str(e)))
                    self.file_mgr.remove_inbound(file_id)

        elif msg_type == MessageType.FILE_ACK:
            status = payload.get("status", "")
            msg = payload.get("message", "")
            sender = self.peer_onion or "unknown.onion"
            self.on_file_complete(sender, self.peer_username, "", status == "ok", f"Peer ack: {status} ({msg})")

        elif msg_type == MessageType.DISCONNECT:
            self.close()

    def close(self) -> None:
        if self.is_alive:
            self.is_alive = False
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            if self.peer_onion:
                self.on_status_change(self.peer_onion, self.peer_username, "disconnected")


class NetworkManager:
    """Coordinates local inbound listener and outbound SOCKS5 connections."""
    def __init__(
        self,
        config: Config,
        file_mgr: FileTransferManager,
        on_message: Callable[[str, str, str, int], None],
        on_file_start: Callable[[str, str, str, int], None],
        on_file_progress: Callable[[str, str, int, int], None],
        on_file_complete: Callable[[str, str, str, bool, str], None],
        on_status_change: Callable[[str, str, str], None],
        on_system_log: Callable[[str, str], None],
    ):
        self.config = config
        self.file_mgr = file_mgr
        self.on_message = on_message
        self.on_file_start = on_file_start
        self.on_file_progress = on_file_progress
        self.on_file_complete = on_file_complete
        self.on_status_change = on_status_change
        self.on_system_log = on_system_log

        self.connections: Dict[str, PeerConnection] = {}
        self._lock = threading.Lock()
        self._listener_sock: Optional[socket.socket] = None
        self._is_running = True

    def start_listener(self) -> Tuple[bool, str]:
        """Binds TCP server socket to 127.0.0.1:<listen_port> for Tor Hidden Service forwarding."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", self.config.listen_port))
            sock.listen(10)
            self._listener_sock = sock

            thread = threading.Thread(target=self._listener_loop, daemon=True)
            thread.start()
            return True, f"Listener active on 127.0.0.1:{self.config.listen_port}"
        except Exception as e:
            return False, f"Failed to start local listener: {str(e)}"

    def _listener_loop(self) -> None:
        while self._is_running and self._listener_sock:
            try:
                client_sock, _ = self._listener_sock.accept()
                peer = PeerConnection(
                    sock=client_sock,
                    is_outbound=False,
                    config=self.config,
                    file_mgr=self.file_mgr,
                    on_message=self.on_message,
                    on_file_start=self.on_file_start,
                    on_file_progress=self.on_file_progress,
                    on_file_complete=self.on_file_complete,
                    on_status_change=self._handle_peer_status,
                )
            except Exception:
                break

    def connect_to_peer(self, peer_onion: str, port: int = 11009) -> Tuple[bool, str]:
        """Initiates an outbound SOCKS5 connection to <peer>.onion:<port> through Tor."""
        if not SOCKS_AVAILABLE:
            return False, "PySocks is not installed. Please run: pip install PySocks"

        peer_onion = peer_onion.strip().lower()
        if not peer_onion.endswith(".onion"):
            peer_onion += ".onion"

        with self._lock:
            if peer_onion in self.connections and self.connections[peer_onion].is_alive:
                return True, f"Already connected to {peer_onion}"

        def _worker():
            self.on_system_log("info", f"Building Tor circuit to {peer_onion[:12]}...onion:{port}")
            try:
                sock = socks.socksocket()
                sock.set_proxy(
                    socks.SOCKS5,
                    self.config.settings.get("socks_host", "127.0.0.1"),
                    self.config.socks_port,
                    rdns=True
                )
                sock.settimeout(60.0)  # Onion circuits can take up to 30-45s on first handshake
                sock.connect((peer_onion, port))
                sock.settimeout(None)

                peer = PeerConnection(
                    sock=sock,
                    is_outbound=True,
                    config=self.config,
                    file_mgr=self.file_mgr,
                    on_message=self.on_message,
                    on_file_start=self.on_file_start,
                    on_file_progress=self.on_file_progress,
                    on_file_complete=self.on_file_complete,
                    on_status_change=self._handle_peer_status,
                    target_onion=peer_onion
                )

                with self._lock:
                    self.connections[peer_onion] = peer

                self.on_system_log("success", f"Connected to {self.config.get_alias(peer_onion)} ({peer_onion[:12]}...onion)")

            except Exception as e:
                err_msg = str(e)
                alias = self.config.get_alias(peer_onion)
                hint = ""
                if "0x05" in err_msg or "0x04" in err_msg or "timed out" in err_msg or "refused" in err_msg:
                    hint = " (Note: Tor v3 takes 30-60s to publish descriptors across the Tor network after startup. Both laptops should /add each other, wait ~30s, and retry with /connect)"
                self.on_system_log("error", f"Connection failed to {alias}: {err_msg}{hint}")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True, f"Connecting to {peer_onion} in background..."

    def _handle_peer_status(self, onion: str, username: str, status: str) -> None:
        with self._lock:
            if status == "connected" and onion:
                # Find and register
                for p in list(self.connections.values()):
                    if p.peer_onion == onion:
                        self.connections[onion] = p
            elif status == "disconnected":
                if onion in self.connections:
                    del self.connections[onion]

        self.on_status_change(onion, username, status)

    def get_connection(self, onion: str) -> Optional[PeerConnection]:
        with self._lock:
            return self.connections.get(onion)

    def is_peer_online(self, onion: str) -> bool:
        with self._lock:
            conn = self.connections.get(onion)
            return conn is not None and conn.is_alive

    def shutdown(self) -> None:
        self._is_running = False
        if self._listener_sock:
            try:
                self._listener_sock.close()
            except Exception:
                pass
        with self._lock:
            for conn in list(self.connections.values()):
                conn.close()
            self.connections.clear()
