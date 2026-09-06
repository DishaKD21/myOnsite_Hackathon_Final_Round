from pathlib import Path
import pytest
import json
from app.database import Base
from app.backup_chain import BackupChain
from app.models import BackupPoint
from app.services.engine import source, create_full_backup, create_incremental_backup
from app.services.hash_service import calculate_artifact_hash
from app.services.chain_service import verify_chain, find_alternate_delta
from app.services.validation_service import validate_backup
from app.services.alternate_service import verify_alternate
from app.services.alternate_service import create_alternate_copy

@pytest.fixture
def setup(tmp_path, monkeypatch):
    import app.database as database
    monkeypatch.setattr(database, "SOURCE_DIR", tmp_path / "source")
    monkeypatch.setattr(database, "BACKUPS_DIR", tmp_path / "backups")
    database.SOURCE_DIR.mkdir(); database.BACKUPS_DIR.mkdir()
    source.root = database.SOURCE_DIR; source.meta_path = source.root / "source.json"
    engine = database.create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session
    db = Session(engine)
    source.seed([{"file_id":"a", "filename":"a.json", "content":"one"}, {"file_id":"b", "filename":"b.json", "content":"two"}])
    yield db
    db.close()

def test_full_and_no_change(setup):
    full = create_full_backup(setup)
    assert full.type == "FULL"
    delta = create_incremental_backup(setup)
    assert delta is None
    assert setup.query(BackupPoint).count() == 1
    assert validate_backup(setup, full)["valid"]

def test_multiple_changes_are_one_delta(setup):
    create_full_backup(setup); source.modify("a", "one-new"); source.modify("b", "two-new")
    delta = create_incremental_backup(setup)
    assert delta.change_count == 2

def test_metadata_signal_still_checks_content_hash(setup):
    create_full_backup(setup); source.modify("a", "one"); delta = create_incremental_backup(setup)
    assert delta is None

def test_second_delta_contains_only_changes_after_first(setup):
    create_full_backup(setup); source.modify("a", "one-new"); first = create_incremental_backup(setup)
    source.modify("b", "two-new"); second = create_incremental_backup(setup)
    payload = json.loads(Path(second.artifact_path).with_name("artifact.json").read_text())
    assert [change["file_id"] for change in payload["changes"]] == ["b"]

def test_added_file_is_the_only_delta_change(setup):
    create_full_backup(setup); source.add("c", "c.json", "three"); delta = create_incremental_backup(setup)
    payload = json.loads(Path(delta.artifact_path).with_name("artifact.json").read_text())
    assert [change["file_id"] for change in payload["changes"]] == ["c"] and payload["changes"][0]["old"] is None

def test_deleted_file_is_the_only_delta_change(setup):
    create_full_backup(setup); source.delete("b"); delta = create_incremental_backup(setup)
    payload = json.loads(Path(delta.artifact_path).with_name("artifact.json").read_text())
    assert [change["file_id"] for change in payload["changes"]] == ["b"] and payload["changes"][0]["new"] is None

def test_mixed_delta_excludes_unchanged_files(setup):
    create_full_backup(setup); source.modify("a", "one-new"); source.add("c", "c.json", "three"); source.delete("b"); delta = create_incremental_backup(setup)
    payload = json.loads(Path(delta.artifact_path).with_name("artifact.json").read_text())
    assert [change["file_id"] for change in payload["changes"]] == ["a", "b", "c"]

def test_delta_rejects_wrong_parent_old_hash(setup):
    create_full_backup(setup); source.modify("a", "one-new"); delta = create_incremental_backup(setup)
    artifact_path = Path(delta.artifact_path).with_name("artifact.json")
    artifact = json.loads(artifact_path.read_text())
    artifact["changes"][0]["previous_content_hash"] = "wrong"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    result = validate_backup(setup, delta)
    assert not result["valid"] and any("old hash/version mismatch" in error for error in result["errors"])

def test_delta_rejects_wrong_resulting_content_hash(setup):
    create_full_backup(setup); source.modify("a", "one-new"); delta = create_incremental_backup(setup)
    artifact_path = Path(delta.artifact_path).with_name("artifact.json")
    artifact = json.loads(artifact_path.read_text())
    artifact["changes"][0]["new_content_hash"] = "wrong"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    result = validate_backup(setup, delta)
    assert not result["valid"] and any("resulting state mismatch" in error for error in result["errors"])

def test_hash_detects_artifact_modification(setup):
    full = create_full_backup(setup)
    Path(full.artifact_path).write_text("tampered", encoding="utf-8")
    assert calculate_artifact_hash(full.artifact_path) != full.artifact_hash
    assert not validate_backup(setup, full)["valid"]

def test_hash_detects_manifest_modification(setup):
    full = create_full_backup(setup)
    manifest_path = Path(full.manifest_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["file_count"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = validate_backup(setup, full)
    assert not result["valid"] and "manifest hash mismatch" in result["errors"]

def test_valid_chain_and_parent(setup):
    full = create_full_backup(setup); source.modify("a", "v2"); d1 = create_incremental_backup(setup); source.modify("b", "v2"); d2 = create_incremental_backup(setup)
    assert d1.parent_id == full.id and d2.parent_id == d1.id
    assert verify_chain(setup)["chain_status"] == "VALID"

def test_existing_backup_records_are_linked_without_losing_metadata(setup):
    full = create_full_backup(setup); source.modify("a", "v2"); d1 = create_incremental_backup(setup); source.modify("b", "v2"); d2 = create_incremental_backup(setup)
    chain = BackupChain.load(setup)
    assert chain.head is full and chain.head.next is d1 and chain.head.next.next is d2 and chain.head.next.next.next is None
    assert d1.manifest_hash and d1.artifact_hash and d1.change_count == 1

def test_missing_delta_breaks_chain(setup):
    create_full_backup(setup); source.modify("a", "v2"); d1 = create_incremental_backup(setup); source.modify("b", "v2"); d2 = create_incremental_backup(setup)
    Path(d1.artifact_path).unlink()
    result = verify_chain(setup)
    assert result["chain_status"] == "BROKEN" and result["latest_safe_recovery_point"] == "FULL-001"

def test_version_gap_breaks_chain(setup):
    create_full_backup(setup); source.modify("a", "v2"); d1 = create_incremental_backup(setup); source.modify("b", "v2"); d2 = create_incremental_backup(setup)
    d2.start_version = d1.end_version + 10
    setup.commit()
    result = verify_chain(setup)
    assert result["chain_status"] == "BROKEN" and result["earliest_problem"] == d2.id

def test_alternate_with_wrong_parent_rejected(setup):
    create_full_backup(setup); source.modify("a", "v2"); original = create_incremental_backup(setup); source.modify("b", "v2"); other = create_incremental_backup(setup)
    other.parent_id = "wrong"; setup.commit()
    assert not verify_alternate(setup, original, other)["accepted"]

def test_alternate_coverage_can_be_verified(setup):
    create_full_backup(setup); source.modify("a", "v2"); original = create_incremental_backup(setup)
    source.modify("b", "v2"); later = create_incremental_backup(setup)
    assert find_alternate_delta(setup, original) == []
    assert not verify_alternate(setup, original, later)["accepted"]

def test_alternate_can_prove_equivalence_when_original_artifact_is_missing(setup):
    create_full_backup(setup); source.modify("a", "v2"); original = create_incremental_backup(setup)
    alternate = create_alternate_copy(setup, original, "D1-ALT")
    Path(original.artifact_path).unlink()
    Path(original.artifact_path).with_name("artifact.json").unlink()
    assert verify_alternate(setup, original, alternate)["accepted"]

def test_verified_alternate_is_traversed_in_original_node_position(setup):
    create_full_backup(setup); source.modify("a", "v2"); original = create_incremental_backup(setup)
    source.modify("b", "v2"); later = create_incremental_backup(setup)
    alternate = create_alternate_copy(setup, original, "D1-ALT")
    assert verify_alternate(setup, original, alternate)["accepted"]
    Path(original.artifact_path).unlink()
    Path(original.artifact_path).with_name("artifact.json").unlink()
    chain = BackupChain.load(setup)
    assert chain.head.next.id == "D1-ALT" and chain.head.next.next.id == later.id
    result = verify_chain(setup)
    assert result["chain_status"] == "RECOVERED_WITH_ALTERNATE" and result["latest_safe_recovery_point"] == later.id
