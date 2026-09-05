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
        state = json.loads(self.meta_path.read_text(encoding="utf-8"))
        for item in state.get("files", {}).values():
            item.pop("content", None)
        return state

    def _write(self, state: dict[str, Any]) -> dict[str, Any]:
        persisted = json.loads(json.dumps(state))
        for item in persisted.get("files", {}).values():
            item.pop("content", None)
        self.meta_path.write_text(json.dumps(persisted, sort_keys=True, indent=2), encoding="utf-8")
        return self.state()

    def _file_path(self, filename: str) -> Path:
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("filename must stay inside the source workspace")
        return self.root / "files" / relative

    def _content(self, item: dict[str, Any]) -> str:
        path = self._file_path(item["filename"])
        if not path.exists():
            legacy_path = self.root / item["filename"]
            if legacy_path.exists():
                path = legacy_path
            else:
                return ""
        return path.read_text(encoding="utf-8")

    def seed(self, files: list[dict[str, str]]) -> dict[str, Any]:
        state = {"source_id": "demo-source", "version": 1, "files": {}}
        for item in files:
            state["files"][item["file_id"]] = self._file(item["file_id"], item["filename"], item["content"], 1)
        return self._write(state)

    def _file(self, file_id: str, filename: str, content: str, version: int) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        path = self._file_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"file_id": file_id, "filename": filename, "path": str(path.relative_to(self.root)), "version": version, "size": len(content.encode("utf-8")), "modified_timestamp": now, "content_hash": sha256_content(content)}

    def state(self) -> dict[str, Any]:
        state = self._read()
        files = []
        for item in state["files"].values():
            current = dict(item)
            current["content"] = self._content(item)
            files.append(current)
        state["files"] = sorted(files, key=lambda value: value["file_id"])
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
            self._file_path(raw["files"][file_id]["filename"]).unlink(missing_ok=True)
            del raw["files"][file_id]
        return self._mutate(change)

    def upload(self, filename: str, content: bytes, file_id: str | None = None) -> dict[str, Any]:
        safe_name = Path(filename).name if Path(filename).name == filename else filename
        raw = self._read()
        resolved_id = file_id or safe_name
        existing = raw["files"].get(resolved_id)
        text = content.decode("utf-8")

        def change(state):
            state["files"][resolved_id] = self._file(
                resolved_id,
                safe_name,
                text,
                existing["version"] + 1 if existing else 1,
            )

        return self._mutate(change)
