"""
TorChatZ Protocol Specification and Frame Serialization.
Guarantees absolute anonymity: NO IP addresses, NO hostname, NO OS fingerprint.
Only Onion addresses, pseudonymous usernames, and encrypted/raw payloads.
"""

import json
import struct
import base64
import hashlib
import time
import uuid
from typing import Dict, Any, Optional, Tuple

PROTOCOL_VERSION = "2.0"
MAX_FRAME_SIZE = 16 * 1024 * 1024  # 16 MB max frame size for safety
DEFAULT_CHUNK_SIZE = 64 * 1024     # 64 KB binary chunks for smooth streaming


class MessageType:
    HANDSHAKE = "HANDSHAKE"
    HANDSHAKE_ACK = "HANDSHAKE_ACK"
    PING = "PING"
    PONG = "PONG"
    CHAT = "CHAT"
    STATUS = "STATUS"
    FILE_START = "FILE_START"
    FILE_CHUNK = "FILE_CHUNK"
    FILE_ACK = "FILE_ACK"
    DISCONNECT = "DISCONNECT"


class Protocol:
    @staticmethod
    def pack_frame(payload: Dict[str, Any]) -> bytes:
        """Packs a dictionary payload into a length-prefixed frame: [4 bytes length][JSON utf-8]"""
        raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        length = len(raw_json)
        return struct.pack("!I", length) + raw_json

    @staticmethod
    def unpack_header(header_bytes: bytes) -> int:
        """Unpacks 4-byte big-endian header to get payload length."""
        if len(header_bytes) < 4:
            raise ValueError("Header must be 4 bytes")
        return struct.unpack("!I", header_bytes)[0]

    @staticmethod
    def create_handshake(my_onion: str, username: str, session_id: str) -> Dict[str, Any]:
        return {
            "v": PROTOCOL_VERSION,
            "type": MessageType.HANDSHAKE,
            "onion": my_onion,
            "username": username,
            "session_id": session_id,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_handshake_ack(my_onion: str, username: str, session_id: str) -> Dict[str, Any]:
        return {
            "v": PROTOCOL_VERSION,
            "type": MessageType.HANDSHAKE_ACK,
            "onion": my_onion,
            "username": username,
            "session_id": session_id,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_chat(text: str) -> Dict[str, Any]:
        return {
            "type": MessageType.CHAT,
            "id": uuid.uuid4().hex[:12],
            "text": text,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_ping() -> Dict[str, Any]:
        return {
            "type": MessageType.PING,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_pong() -> Dict[str, Any]:
        return {
            "type": MessageType.PONG,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_file_start(file_id: str, filename: str, filesize: int, sha256_hash: str) -> Dict[str, Any]:
        # Strip path components for privacy and directory traversal protection
        import os
        safe_name = os.path.basename(filename)
        return {
            "type": MessageType.FILE_START,
            "file_id": file_id,
            "filename": safe_name,
            "filesize": filesize,
            "sha256": sha256_hash,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_file_chunk(file_id: str, chunk_index: int, total_chunks: int, chunk_data: bytes) -> Dict[str, Any]:
        return {
            "type": MessageType.FILE_CHUNK,
            "file_id": file_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "data_b64": base64.b64encode(chunk_data).decode("ascii"),
        }

    @staticmethod
    def create_file_ack(file_id: str, status: str, message: str = "") -> Dict[str, Any]:
        return {
            "type": MessageType.FILE_ACK,
            "file_id": file_id,
            "status": status,  # "ok", "hash_mismatch", "rejected", "error"
            "message": message,
            "ts": int(time.time()),
        }

    @staticmethod
    def create_disconnect(reason: str = "Client closed") -> Dict[str, Any]:
        return {
            "type": MessageType.DISCONNECT,
            "reason": reason,
            "ts": int(time.time()),
        }
