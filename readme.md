# BackupChain

BackupChain is a deterministic FastAPI backend with a React/Vite integrity console. The frontend is intentionally thin: the backend remains the source of truth for backup validity, chain breaks, alternate equivalence, and safe recovery points.

## Run locally

Start the backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend uses `VITE_API_BASE_URL` and defaults to `http://localhost:8000`.

To use another backend:

```powershell
# frontend/.env.local
VITE_API_BASE_URL=http://localhost:8000
```

## Frontend architecture

- `src/services/api.js` centralizes every fetch request and translates network/HTTP errors into user-facing messages.
- `SourcePanel` uploads and modifies user-provided source files using the backend's actual schemas.
- `BackupChain` renders the returned catalog dynamically using `parent_id`-ordered records.
- `BackupDetails` displays hashes and invokes backend validation.
- `VerificationPanel` shows the actual `/chain/verify` decision.
- `RecoveryPanel` invokes restore and restored-state verification.
- `DemoControls` exposes safe manual backup and alternate-discovery actions; it does not invent destructive simulation APIs.

## Actual backend contract used

| UI action | Method and endpoint | Body/query |
| --- | --- | --- |
| Read source | `GET /source/state` | none |
| Upload source files | `POST /source/files` | multipart file upload |
| Modify file | `POST /source/modify` | `{ file_id, content }` |
| Create full | `POST /backup/full` | none |
| Create incremental | `POST /backup/incremental` | none |
| List points | `GET /backups` | none |
| Point details | `GET /backups/{backup_id}` | none |
| Validate point | `POST /backups/{backup_id}/validate` | none |
| Verify chain | `GET /chain/verify` | none |
| Find alternate | `POST /backups/{backup_id}/find-alternate` | none |
| Verify alternate | `POST /backups/{backup_id}/verify-alternate?alternate_id=...` | query parameter |
| Restore | `POST /restore` | `{ recovery_point_id }` |
| Verify restore | `POST /restore/verify` | `{ recovery_point_id }` |

CORS is enabled in `backend/app/main.py` for `localhost:5173` and `127.0.0.1:5173`. No backend business logic or demo-only destructive endpoint was added.

## Docker

From `backend/`, the existing Compose file now runs both services:

```powershell
docker compose up --build
```

The API is on port `8000`; the production frontend is served on port `5173`.

## Demo workflow

1. Open the frontend and click `Seed Source`.
2. Click `Create Full Backup`.
3. Modify a tracked file and click `Create Incremental Backup`.
4. Click `Verify Chain` to see the backend decision.
5. Select a chain node to inspect hashes and validate it.
6. Use `Find alternate` on an incremental when catalog metadata contains a compatible candidate.
7. Verify the candidate through the backend before trusting a replacement.
8. Restore the latest safe point and run restored-state verification.

The frontend never decides that an alternate is equivalent and never treats a later stored backup as safe without the backend verification response.
