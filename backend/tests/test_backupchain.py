from pathlib import Path
import pytest
from app.database import Base
from app.models import BackupPoint
from app.services.engine import source, create_full_backup, create_incremental_backup
from app.services.hash_service import calculate_artifact_hash
from app.services.chain_service import verify_chain, find_alternate_delta
from app.services.validation_service import validate_backup
from app.services.alternate_service import verify_alternate

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
    assert delta.change_count == 0
    assert validate_backup(setup, full)["valid"]

def test_multiple_changes_are_one_delta(setup):
    create_full_backup(setup); source.modify("a", "one-new"); source.modify("b", "two-new")
    delta = create_incremental_backup(setup)
    assert delta.change_count == 2

def test_hash_detects_artifact_modification(setup):
    full = create_full_backup(setup)
    Path(full.artifact_path).write_text("tampered", encoding="utf-8")
    assert calculate_artifact_hash(full.artifact_path) != full.artifact_hash
    assert not validate_backup(setup, full)["valid"]

def test_valid_chain_and_parent(setup):
    full = create_full_backup(setup); source.modify("a", "v2"); d1 = create_incremental_backup(setup); source.modify("b", "v2"); d2 = create_incremental_backup(setup)
    assert d1.parent_id == full.id and d2.parent_id == d1.id
    assert verify_chain(setup)["chain_status"] == "VALID"

def test_missing_delta_breaks_chain(setup):
    create_full_backup(setup); source.modify("a", "v2"); d1 = create_incremental_backup(setup); source.modify("b", "v2"); d2 = create_incremental_backup(setup)
    Path(d1.artifact_path).unlink()
    result = verify_chain(setup)
    assert result["chain_status"] == "BROKEN" and result["latest_safe_recovery_point"] == "FULL-001"

def test_alternate_with_wrong_parent_rejected(setup):
    create_full_backup(setup); source.modify("a", "v2"); original = create_incremental_backup(setup); source.modify("b", "v2"); other = create_incremental_backup(setup)
    other.parent_id = "wrong"; setup.commit()
    assert not verify_alternate(setup, original, other)["accepted"]

def test_alternate_coverage_can_be_verified(setup):
    create_full_backup(setup); source.modify("a", "v2"); original = create_incremental_backup(setup)
    source.modify("b", "v2"); later = create_incremental_backup(setup)
    assert find_alternate_delta(setup, original) == []
    assert not verify_alternate(setup, original, later)["accepted"]
