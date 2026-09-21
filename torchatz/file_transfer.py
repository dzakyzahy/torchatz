"""
File Transfer Engine for TorChatZ.
Supports safe, chunked transfer of images, videos, audio, and documents
with SHA-256 integrity verification and path traversal protection.
"""

import os
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Tuple

from .protocol import Protocol, DEFAULT_CHUNK_SIZE, MessageType


def sanitize_filename(filename: str) -> str:
    """Removes path traversals and illegal characters from filename."""
    base = os.path.basename(filename).strip()
    # Strip any directory separators or null bytes
    base = re.sub(r'[\\/*?:"<>|\0]', "_", base)
    if not base:
        base = "downloaded_file.bin"
    return base


def get_unique_filepath(directory: Path, filename: str) -> Path:
    """Ensures a unique destination path so existing files aren't accidentally overwritten."""
    dest = directory / filename
    if not dest.exists():
        return dest
    
    stem = dest.stem
    suffix = dest.suffix
    counter = 1
    while dest.exists():
        dest = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return dest


class InboundTransfer:
    def __init__(self, file_id: str, filename: str, filesize: int, expected_sha256: str, downloads_dir: Path):
        self.file_id = file_id
        self.filename = sanitize_filename(filename)
        self.filesize = filesize
        self.expected_sha256 = expected_sha256.lower()
        self.downloads_dir = downloads_dir

        self.temp_path = downloads_dir / f".tmp_{file_id}_{self.filename}"
        self.final_path = get_unique_filepath(downloads_dir, self.filename)

        self.received_bytes = 0
        self.chunks_received = 0
        self.hasher = hashlib.sha256()
        self.file_handle = open(self.temp_path, "wb")
        self.is_completed = False
        self.is_aborted = False

    def write_chunk(self, chunk_data: bytes) -> None:
        if self.is_completed or self.is_aborted:
            return
        self.file_handle.write(chunk_data)
        self.hasher.update(chunk_data)
        self.received_bytes += len(chunk_data)
        self.chunks_received += 1

    def finalize(self) -> Tuple[bool, str, Path]:
        """Closes handle, verifies SHA-256, and renames temp file to final location."""
        self.file_handle.close()
        actual_sha256 = self.hasher.hexdigest().lower()
        
        if actual_sha256 != self.expected_sha256:
            self.is_aborted = True
            if self.temp_path.exists():
                self.temp_path.unlink()
            return False, f"Checksum mismatch! Expected {self.expected_sha256[:8]}, got {actual_sha256[:8]}", self.final_path

        # Rename to final path
        self.temp_path.rename(self.final_path)
        self.is_completed = True
        return True, "File received and verified successfully", self.final_path

    def abort(self) -> None:
        self.is_aborted = True
        try:
            self.file_handle.close()
        except Exception:
            pass
        if self.temp_path.exists():
            try:
                self.temp_path.unlink()
            except Exception:
                pass


class FileTransferManager:
    def __init__(self, downloads_dir: Path):
        self.downloads_dir = downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.inbound_transfers: Dict[str, InboundTransfer] = {}

    def calculate_file_hash(self, filepath: Path) -> Tuple[int, str]:
        """Calculates filesize and SHA-256 hash for a local file."""
        hasher = hashlib.sha256()
        size = 0
        with open(filepath, "rb") as f:
            while chunk := f.read(64 * 1024):
                hasher.update(chunk)
                size += len(chunk)
        return size, hasher.hexdigest().lower()

    def start_inbound(self, file_id: str, filename: str, filesize: int, sha256_hash: str) -> InboundTransfer:
        transfer = InboundTransfer(file_id, filename, filesize, sha256_hash, self.downloads_dir)
        self.inbound_transfers[file_id] = transfer
        return transfer

    def get_inbound(self, file_id: str) -> Optional[InboundTransfer]:
        return self.inbound_transfers.get(file_id)

    def remove_inbound(self, file_id: str) -> None:
        if file_id in self.inbound_transfers:
            del self.inbound_transfers[file_id]
