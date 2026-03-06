from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from .config import AppConfig
from .notebooklm_client import NotebookLMClient
from .pipeline import MeetingPipeline
from .whisper_transcriber import WhisperTranscriber


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local Whisper + NotebookLM meeting processor"
    )
    parser.add_argument("--audio", required=True, help="Path to meeting audio file")
    parser.add_argument("--title", required=True, help="Meeting title")
    parser.add_argument("--whisper-model", default=None, help="Whisper model name")
    parser.add_argument(
        "--transcript-language",
        default=None,
        help="Language hint for Whisper transcript (e.g. en, es)",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = AppConfig.load()

    client = NotebookLMClient(
        project=config.notebooklm_project,
        location=config.notebooklm_location,
        base_url=config.notebooklm_base_url,
    )
    pipeline = MeetingPipeline(
        transcriber=WhisperTranscriber(),
        notebooklm_client=client,
        output_root=config.output_dir,
        default_language=config.notebooklm_language,
    )

    result = pipeline.process(
        audio_path=Path(args.audio).expanduser().resolve(),
        title=args.title,
        whisper_model=args.whisper_model or config.whisper_model,
        transcript_language=args.transcript_language,
    )

    payload = {
        "run_id": result.run_id,
        "title": result.title,
        "notebook_name": result.notebook_name,
        "output_dir": str(result.output_dir),
        "transcript_path": str(result.transcript_path),
        "summary_path": str(result.summary_path),
        "downstream_path": str(result.downstream_path),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
