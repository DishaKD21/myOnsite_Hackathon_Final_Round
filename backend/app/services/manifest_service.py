from __future__ import annotations
from typing import Any
from .hash_service import canonical_bytes, sha256_bytes

def manifest_hash(manifest: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(manifest))

def sorted_changes(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(changes, key=lambda change: change["file_id"])
