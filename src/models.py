from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MeetingResult:
    run_id: str
    title: str
    transcript_text: str
    summary_text: str
    downstream_data: dict[str, Any]
    output_dir: Path
    notebook_name: str
    transcript_path: Path
    summary_path: Path
    downstream_path: Path
