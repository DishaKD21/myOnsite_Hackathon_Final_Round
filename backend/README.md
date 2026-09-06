# BackupChain

BackupChain is a deterministic FastAPI prototype for proving whether an incremental backup chain can be safely reconstructed. It models a source dataset, stores full and interval-level delta artifacts on local storage, records coverage evidence in SQLite, and refuses to skip an unavailable or invalid delta.

## Model

- A FULL backup captures the complete source state.
- Each incremental is one batch for a backup interval. D1, D2, and D3 are not one delta per file; each contains every change detected in that interval.
- A delta points to its parent. Recovery follows `parent_id`, never filenames or sequence numbers alone.
- `latest stored backup` and `latest safe recovery point` are different: a later artifact is unusable when its required history is broken.

File identity uses stable `file_id`. Metadata changes are candidates; actual content hashes decide ordinary content changes. Additions, deletions, and version transitions are retained as explicit changes. SHA-256 is computed from UTF-8 content or actual artifact bytes, never from a concatenated metadata string.

Every point has two independent proofs:

- `manifest_hash`: hash of canonical, sorted manifest JSON describing coverage.
- `artifact_hash`: hash of the complete artifact file bytes.

## Chain recovery

Validation checks storage, both hashes, JSON structure, parent/version metadata, change counts, coverage, and whether the artifact applies to its parent state. When a delta is missing, the verifier stops at that point. It can search catalog candidates using structural metadata, but an alternate is accepted only when its source, parent, version transition, change IDs, old/new versions, old/new content hashes, and artifact integrity all agree. The original catalog record remains for auditability.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000/docs`. Data is written below `data/`. Set `BACKUPCHAIN_DATA_DIR` and `BACKUPCHAIN_DATABASE_URL` to override local storage.

Run the deterministic smoke demo:

```powershell
python demo.py
```

Run tests:

```powershell
pytest -q
```

Docker is also supported with `docker compose up --build`.

## API

Source operations:

- Upload files through `POST /source/files` to establish the source state.
- `POST /source/modify`, `/source/add`, `/source/delete`
- `GET /source/state`

Backup and evidence operations:

- `POST /backup/full`
- `POST /backup/incremental`
- `GET /backups`, `GET /backups/{backup_id}`
- `POST /backups/{backup_id}/validate`
- `GET /chain/verify`, `GET /chain/problems`, `GET /recovery-points`
- `POST /backups/{backup_id}/find-alternate`
- `POST /backups/{backup_id}/verify-alternate?alternate_id=D2-ALT`

Recovery operations:

- `POST /restore` with `{ "recovery_point_id": "D1" }`
- `POST /restore/verify` with the same body

Typical successful chain output is shaped like:

```json
{
	"chain_status": "VALID",
	"latest_safe_recovery_point": "D2",
	"earliest_problem": null,
	"replacement": null
}
```

The core functions live in `app/services`: source mutation, canonical hashing, backup creation, validation, chain verification, alternate verification, and recovery. No LLM, cloud SDK, scheduler, or external service is needed for correctness.
