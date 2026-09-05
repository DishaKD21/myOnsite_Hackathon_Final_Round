from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .hash_service import sha256_content

class SourceService:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.meta_path = root / "source.json"

    def _read(self) -> dict[str, Any]:
        if not self.meta_path.exists():
            return {"source_id": "demo-source", "version": 0, "files": {}}
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _write(self, state: dict[str, Any]) -> dict[str, Any]:
        self.meta_path.write_text(json.dumps(state, sort_keys=True, indent=2), encoding="utf-8")
        return state

    def seed(self, files: list[dict[str, str]]) -> dict[str, Any]:
        state = {"source_id": "demo-source", "version": 1, "files": {}}
        for item in files:
            state["files"][item["file_id"]] = self._file(item["file_id"], item["filename"], item["content"], 1)
        return self._write(state)

    def _file(self, file_id: str, filename: str, content: str, version: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {"file_id": file_id, "filename": filename, "path": f"/{filename}", "version": version, "size": len(content.encode("utf-8")), "modified_timestamp": now, "content": content, "content_hash": sha256_content(content)}

    def state(self) -> dict[str, Any]:
        state = self._read()
        state["files"] = sorted(state["files"].values(), key=lambda value: value["file_id"])
        return state

    def _mutate(self, operation) -> dict[str, Any]:
        raw = self._read()
        raw["version"] += 1
        operation(raw)
        return self._write(raw)

    def modify(self, file_id: str, content: str) -> dict[str, Any]:
        def change(raw):
            if file_id not in raw["files"]:
                raise KeyError(file_id)
            old = raw["files"][file_id]
            raw["files"][file_id] = self._file(file_id, old["filename"], content, old["version"] + 1)
        return self._mutate(change)

    def add(self, file_id: str, filename: str, content: str) -> dict[str, Any]:
        def change(raw):
            if file_id in raw["files"]:
                raise ValueError(f"file already exists: {file_id}")
            raw["files"][file_id] = self._file(file_id, filename, content, 1)
        return self._mutate(change)

    def delete(self, file_id: str) -> dict[str, Any]:
        def change(raw):
            if file_id not in raw["files"]:
                raise KeyError(file_id)
            del raw["files"][file_id]
        return self._mutate(change)
