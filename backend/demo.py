import shutil
from app.database import DATA_DIR, BACKUPS_DIR, SOURCE_DIR, get_db, init_db
from app.services.engine import source, create_full_backup, create_incremental_backup
from app.services.chain_service import verify_chain, find_alternate_delta
from app.services.alternate_service import create_alternate_copy, verify_alternate
from pathlib import Path

if DATA_DIR.exists():
	shutil.rmtree(DATA_DIR)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DIR.mkdir(parents=True, exist_ok=True)
init_db(); db = get_db()
source.seed([{"file_id": "a", "filename": "a.json", "content": "alpha"}, {"file_id": "b", "filename": "b.json", "content": "bravo"}])
full = create_full_backup(db)
source.modify("a", "alpha-v2"); source.modify("b", "bravo-v2")
d1 = create_incremental_backup(db)
source.modify("a", "alpha-v3")
d2 = create_incremental_backup(db)
source.modify("b", "bravo-v3")
d3 = create_incremental_backup(db)
alternate = create_alternate_copy(db, d2, "D2-ALT")
Path(d2.artifact_path).unlink()
print("broken chain:", verify_chain(db))
print("alternate candidates:", [item.id for item in find_alternate_delta(db, d2)])
print("alternate verification:", verify_alternate(db, d2, alternate))
print("recovered chain:", verify_chain(db))
print("full:", full.id, "deltas:", d1.id, d2.id, d3.id)
