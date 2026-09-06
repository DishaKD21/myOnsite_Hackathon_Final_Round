from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BackupPoint, Resolution


@dataclass(frozen=True)
class FileNode:
    file_id: str
    filename: str
    path: str
    size: int
    modified_timestamp: str
    version: int
    content_hash: str
    content: str = ""
    next: "FileNode | None" = None


def _file_nodes(files: list[dict[str, Any]]) -> FileNode | None:
    head = None
    for item in reversed(sorted(files, key=lambda value: value["file_id"])):
        head = FileNode(file_id=item["file_id"], filename=item.get("filename", ""), path=item.get("path", ""), size=item.get("size", 0), modified_timestamp=item.get("modified_timestamp", ""), version=item.get("version", 0), content_hash=item.get("content_hash", ""), content=item.get("content", ""), next=head)
    return head


def _file_map(head: FileNode | None) -> dict[str, FileNode]:
    result = {}
    current = head
    while current:
        result[current.file_id] = current
        current = current.next
    return result

def _file_data(node: FileNode) -> dict[str, Any]:
    return {key: value for key, value in vars(node).items() if key != "next"}


def _artifact_payload(point: BackupPoint) -> dict[str, Any]:
    return json.loads(Path(point.artifact_path).with_name("artifact.json").read_text(encoding="utf-8"))


def _apply_delta(head: FileNode | None, point: BackupPoint) -> FileNode | None:
    files = _file_map(head)
    for change in _artifact_payload(point).get("changes", []):
        if change.get("new") is None:
            files.pop(change["file_id"], None)
        else:
            item = change["new"]
            files[change["file_id"]] = FileNode(file_id=item["file_id"], filename=item.get("filename", ""), path=item.get("path", ""), size=item.get("size", 0), modified_timestamp=item.get("modified_timestamp", ""), version=item.get("version", 0), content_hash=item.get("content_hash", ""), content=item.get("content", ""))
    return _file_nodes([{key: value for key, value in vars(item).items() if key != "next"} for item in files.values()])


class BackupChain:
    """The in-memory chain of the existing BackupPoint domain records."""

    def __init__(self) -> None:
        self.head: BackupPoint | None = None
        self.tail: BackupPoint | None = None
        self.file_head: FileNode | None = None
        self.logical_ids: dict[str, str] = {}
        self.last_comparison_steps: list[dict[str, str]] = []

    def append(self, point: BackupPoint, file_head: FileNode | None = None, logical_id: str | None = None) -> BackupPoint:
        point.next = None
        if self.head is None:
            self.head = self.tail = point
        else:
            assert self.tail is not None
            self.tail.next = point
            self.tail = point
        if file_head is not None:
            self.file_head = file_head
        self.logical_ids[point.id] = logical_id or point.id
        return point

    def compare_source(self, current_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        current = {item["file_id"]: item for item in current_files}
        changes = []
        node = self.file_head
        while node:
            item = current.pop(node.file_id, None)
            if item is None:
                changes.append({"file_id": node.file_id, "previous": _file_data(node), "current": None, "change_reason": "deleted"})
                self.last_comparison_steps.extend([
                    {"name": f"inspect_file_{node.file_id}", "status": "completed", "details": "file deleted"},
                    {"name": "compare_content_hash", "status": "failed", "details": "DELETE added to changes[]"},
                ])
            elif item.get("content_hash") != node.content_hash:
                changes.append({"file_id": node.file_id, "previous": _file_data(node), "current": item, "change_reason": "content changed"})
                self.last_comparison_steps.extend([
                    {"name": f"inspect_file_{node.file_id}", "status": "completed", "details": "file found"},
                    {"name": "compare_content_hash", "status": "failed", "details": f"{node.content_hash[:12]} -> {item.get('content_hash', '')[:12]}"},
                ])
            else:
                self.last_comparison_steps.extend([
                    {"name": f"inspect_file_{node.file_id}", "status": "completed", "details": "file found"},
                    {"name": "compare_content_hash", "status": "completed", "details": "hash matched"},
                ])
            node = node.next
        for file_id, item in sorted(current.items()):
            changes.append({"file_id": file_id, "previous": None, "current": item, "change_reason": "added"})
            self.last_comparison_steps.extend([
                {"name": f"inspect_file_{file_id}", "status": "completed", "details": "new file"},
                {"name": "compare_content_hash", "status": "failed", "details": "ADD added to changes[]"},
            ])
        self.last_comparison_steps.append({"name": "changes_array_complete", "status": "completed", "details": f"{len(changes)} changes"})
        return changes

    def __iter__(self):
        current = self.head
        while current is not None:
            yield current
            current = current.next

    @classmethod
    def load(cls, db: Session, source_id: str = "demo-source") -> "BackupChain":
        """Build only the BackupPoint linked list from database metadata."""
        chain = cls()
        full = db.execute(
            select(BackupPoint)
            .where(BackupPoint.source_id == source_id, BackupPoint.type == "FULL")
            .order_by(BackupPoint.sequence)
        ).scalars().first()
        if full is None:
            return chain

        resolutions = {item.original_id: item.replacement_id for item in db.execute(select(Resolution).where(Resolution.approved.is_(True))).scalars().all()}
        approved_replacements = set(resolutions.values())
        chain.append(full)
        current = full
        lookup_parent_id = full.id
        while True:
            child = db.execute(
                select(BackupPoint)
                .where(
                    BackupPoint.source_id == source_id,
                    BackupPoint.type == "INCREMENTAL",
                    BackupPoint.parent_id == lookup_parent_id,
                    ~BackupPoint.id.in_(approved_replacements) if approved_replacements else True,
                )
                .order_by(BackupPoint.sequence)
            ).scalars().first()
            if child is None:
                break
            original_id = child.id
            logical_child = db.get(BackupPoint, resolutions.get(original_id, original_id)) or child
            chain.append(logical_child, logical_id=original_id)
            current = logical_child
            lookup_parent_id = original_id
        return chain

    @classmethod
    def load_for_comparison(cls, db: Session, source_id: str = "demo-source") -> "BackupChain":
        """Load the linked points and materialize file state only for incremental creation."""
        chain = cls.load(db, source_id)
        if chain.head is None:
            return chain
        file_head = _file_nodes(_artifact_payload(chain.head).get("files", []))
        chain.file_head = file_head
        for point in list(chain)[1:]:
            file_head = _apply_delta(file_head, point)
            chain.file_head = file_head
        return chain
