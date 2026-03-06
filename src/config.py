from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    secret_key: str
    upload_dir: Path
    output_dir: Path
    whisper_model: str
    notebooklm_project: str
    notebooklm_location: str
    notebooklm_base_url: str
    notebooklm_language: str

    @classmethod
    def load(cls) -> "AppConfig":
        upload_dir = Path(os.getenv("UPLOAD_DIR", "data/uploads")).resolve()
        output_dir = Path(os.getenv("OUTPUT_DIR", "data/output")).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5050")),
            secret_key=os.getenv("SECRET_KEY", "dev-secret-key"),
            upload_dir=upload_dir,
            output_dir=output_dir,
            whisper_model=os.getenv("WHISPER_MODEL", "small"),
            notebooklm_project=os.getenv("NOTEBOOKLM_PROJECT", "").strip(),
            notebooklm_location=os.getenv("NOTEBOOKLM_LOCATION", "global"),
            notebooklm_base_url=os.getenv(
                "NOTEBOOKLM_BASE_URL", "https://discoveryengine.googleapis.com"
            ).rstrip("/"),
            notebooklm_language=os.getenv("NOTEBOOKLM_LANGUAGE", "en"),
        )
