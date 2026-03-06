from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import MeetingResult
from .notebooklm_client import NotebookLMClient
from .text_utils import extract_json_object, fallback_downstream_from_summary
from .whisper_transcriber import WhisperTranscriber


SUMMARY_FOCUS_PROMPT = (
    "Summarize this meeting with: agenda, key discussion points, decisions, blockers, "
    "and concrete next steps. Keep it concise and information-dense."
)

DOWNSTREAM_FOCUS_PROMPT = (
    "Read out only a valid JSON object with keys overview, decisions, action_items, "
    "risks, open_questions, follow_ups. Action items must include owner, task, due_date."
)
MAX_PODCAST_CONTEXT_CHARS = 150_000


class MeetingPipeline:
    def __init__(
        self,
        transcriber: WhisperTranscriber,
        notebooklm_client: NotebookLMClient,
        output_root: Path,
        default_language: str,
    ) -> None:
        self.transcriber = transcriber
        self.notebooklm_client = notebooklm_client
        self.output_root = output_root
        self.default_language = default_language

    def process(
        self,
        audio_path: Path,
        title: str,
        whisper_model: str,
        transcript_language: str | None = None,
    ) -> MeetingResult:
        run_id = self._new_run_id()
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        transcript = self.transcriber.transcribe(
            audio_path=audio_path,
            model_name=whisper_model,
            language=transcript_language or None,
        )
        transcript_text = transcript["text"]
        if not transcript_text:
            raise RuntimeError("Whisper produced an empty transcript.")
        transcript_path = run_dir / "transcript.txt"
        transcript_path.write_text(transcript_text, encoding="utf-8")

        podcast_context = transcript_text[:MAX_PODCAST_CONTEXT_CHARS]

        notebook = self.notebooklm_client.create_notebook(title=title)
        notebook_name = notebook["name"]
        self.notebooklm_client.add_text_source(
            notebook_name=notebook_name,
            source_name=f"{title} transcript",
            text_content=transcript_text,
        )

        summary_podcast_operation = self.notebooklm_client.create_podcast(
            context_text=podcast_context,
            title=f"{title} summary",
            focus=SUMMARY_FOCUS_PROMPT,
            language_code=self.default_language,
            description="Auto-generated meeting summary podcast.",
        )
        self.notebooklm_client.wait_for_operation(summary_podcast_operation)
        summary_audio_path = run_dir / "summary_podcast.mp3"
        self.notebooklm_client.download_operation_media(
            summary_podcast_operation, summary_audio_path
        )

        summary_transcription = self.transcriber.transcribe(
            audio_path=summary_audio_path,
            model_name=whisper_model,
            language=self.default_language,
        )
        summary_text = summary_transcription["text"]
        summary_path = run_dir / "summary.txt"
        summary_path.write_text(summary_text, encoding="utf-8")

        downstream_operation = self.notebooklm_client.create_podcast(
            context_text=podcast_context,
            title=f"{title} downstream data",
            focus=DOWNSTREAM_FOCUS_PROMPT,
            language_code=self.default_language,
            description="Auto-generated meeting downstream podcast.",
        )
        self.notebooklm_client.wait_for_operation(downstream_operation)
        downstream_audio_path = run_dir / "downstream_podcast.mp3"
        self.notebooklm_client.download_operation_media(
            downstream_operation, downstream_audio_path
        )

        downstream_transcription = self.transcriber.transcribe(
            audio_path=downstream_audio_path,
            model_name=whisper_model,
            language=self.default_language,
        )
        downstream_text = downstream_transcription["text"]
        parsed = extract_json_object(downstream_text)
        downstream_data: dict[str, Any]
        if parsed is None:
            downstream_data = fallback_downstream_from_summary(summary_text)
            downstream_data["raw_transcribed_output"] = downstream_text
        else:
            downstream_data = parsed

        downstream_path = run_dir / "downstream.json"
        downstream_path.write_text(
            json.dumps(downstream_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        metadata = {
            "run_id": run_id,
            "title": title,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "audio_path": str(audio_path),
            "whisper_model": whisper_model,
            "notebook_name": notebook_name,
            "podcast_context_truncated": len(transcript_text) > MAX_PODCAST_CONTEXT_CHARS,
            "summary_podcast_operation": summary_podcast_operation,
            "downstream_podcast_operation": downstream_operation,
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        return MeetingResult(
            run_id=run_id,
            title=title,
            transcript_text=transcript_text,
            summary_text=summary_text,
            downstream_data=downstream_data,
            output_dir=run_dir,
            notebook_name=notebook_name,
            transcript_path=transcript_path,
            summary_path=summary_path,
            downstream_path=downstream_path,
        )

    @staticmethod
    def _new_run_id() -> str:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return f"{stamp}_{suffix}"
