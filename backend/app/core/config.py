from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    api_title: str = "BackupChain"
    api_version: str = "1.0.0"
    frontend_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    data_dir: str = os.getenv("BACKUPCHAIN_DATA_DIR", "data")

settings = Settings()
