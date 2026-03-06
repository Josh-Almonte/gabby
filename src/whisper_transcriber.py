from __future__ import annotations

from pathlib import Path
from typing import Any

import whisper


class WhisperTranscriber:
    def __init__(self) -> None:
        self._loaded_models: dict[str, Any] = {}

    def transcribe(
        self,
        audio_path: Path,
        model_name: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        model = self._loaded_models.get(model_name)
        if model is None:
            model = whisper.load_model(model_name)
            self._loaded_models[model_name] = model

        kwargs: dict[str, Any] = {"fp16": False, "verbose": False}
        if language:
            kwargs["language"] = language

        result = model.transcribe(str(audio_path), **kwargs)
        text = (result.get("text") or "").strip()
        segments = result.get("segments") or []

        return {"text": text, "segments": segments}
