"""
Hashing utility to calculate file checksums (SHA-256) for auditability and lineage.
"""
import hashlib
from pathlib import Path

def calculate_file_sha256(file_path: Path) -> str:
    """
    Computes the SHA-256 checksum of a file in chunks.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
