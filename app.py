from __future__ import annotations

import json

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from src.config import AppConfig
from src.notebooklm_client import NotebookLMClient, NotebookLMClientError
from src.pipeline import MeetingPipeline
from src.whisper_transcriber import WhisperTranscriber


load_dotenv()
config = AppConfig.load()

app = Flask(__name__)
app.secret_key = config.secret_key

_transcriber = WhisperTranscriber()


def build_pipeline() -> MeetingPipeline:
    client = NotebookLMClient(
        project=config.notebooklm_project,
        location=config.notebooklm_location,
        base_url=config.notebooklm_base_url,
    )
    return MeetingPipeline(
        transcriber=_transcriber,
        notebooklm_client=client,
        output_root=config.output_dir,
        default_language=config.notebooklm_language,
    )


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        default_model=config.whisper_model,
    )


@app.post("/process")
def process_meeting():
    title = (request.form.get("title") or "").strip() or "Untitled Meeting"
    whisper_model = (request.form.get("whisper_model") or config.whisper_model).strip()
    transcript_language = (request.form.get("transcript_language") or "").strip() or None
    upload = request.files.get("audio_file")

    if upload is None or not upload.filename:
        flash("Please upload an audio file.")
        return redirect(url_for("index"))

    upload_name = secure_filename(upload.filename)
    safe_title = secure_filename(title) or "untitled_meeting"
    upload_dir = config.upload_dir / safe_title
    upload_dir.mkdir(parents=True, exist_ok=True)
    audio_path = upload_dir / upload_name
    upload.save(audio_path)

    try:
        result = build_pipeline().process(
            audio_path=audio_path,
            title=title,
            whisper_model=whisper_model,
            transcript_language=transcript_language,
        )
    except (NotebookLMClientError, RuntimeError, ValueError) as exc:
        flash(f"Pipeline failed: {exc}")
        return redirect(url_for("index"))
    except Exception as exc:  # pragma: no cover - defensive UI guard
        flash(f"Pipeline failed: {exc}")
        return redirect(url_for("index"))

    return render_template(
        "result.html",
        run_id=result.run_id,
        title=result.title,
        notebook_name=result.notebook_name,
        transcript_text=result.transcript_text,
        summary_text=result.summary_text,
        downstream_json=json.dumps(result.downstream_data, indent=2, ensure_ascii=False),
    )


@app.get("/download/<run_id>/<asset>")
def download(run_id: str, asset: str):
    allowed = {
        "transcript": "transcript.txt",
        "summary": "summary.txt",
        "downstream": "downstream.json",
        "metadata": "metadata.json",
        "summary_audio": "summary_podcast.mp3",
        "downstream_audio": "downstream_podcast.mp3",
    }
    filename = allowed.get(asset)
    if filename is None:
        flash("Invalid asset requested.")
        return redirect(url_for("index"))

    path = config.output_dir / run_id / filename
    if not path.exists():
        flash("Requested file does not exist.")
        return redirect(url_for("index"))
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=True)
