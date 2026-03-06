# Meeting NotebookLM App (macOS)

Local meeting app that:
1. Transcribes meeting audio locally with Whisper.
2. Uploads transcript to NotebookLM Enterprise APIs.
3. Uses NotebookLM Podcast API for summary + downstream output generation.
4. Transcribes those generated podcast outputs back to text/JSON.

## Stack

- Python + Flask (local web app)
- `openai-whisper` (local transcription)
- Google NotebookLM Enterprise APIs (Discovery Engine)

## Project layout

- `app.py`: Flask app/UI
- `src/pipeline.py`: end-to-end processing pipeline
- `src/notebooklm_client.py`: NotebookLM API client
- `src/whisper_transcriber.py`: local Whisper wrapper
- `templates/`, `static/`: UI
- `data/output/<run_id>/`: generated artifacts

## macOS setup

1. Install system dependencies:
```bash
brew install ffmpeg
```
2. Create and activate a Python env:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
3. Install Python packages:
```bash
pip install -r requirements.txt
```
If Whisper install fails due missing `torch`, install PyTorch first and retry:
```bash
pip install torch
```
4. Configure environment:
```bash
cp .env.example .env
```

Set at least:
- `NOTEBOOKLM_PROJECT`
- `NOTEBOOKLM_LOCATION` (usually `global`)

Authenticate Google Cloud (one option):
```bash
gcloud auth application-default login
```

## Run web app

```bash
python app.py
```

Open: `http://127.0.0.1:5050`

## Run CLI

```bash
python -m src.cli \
  --audio /path/to/meeting.m4a \
  --title "Weekly Product Sync" \
  --whisper-model small
```

## Outputs

Each run writes:
- `transcript.txt`
- `summary.txt`
- `downstream.json`
- `summary_podcast.mp3`
- `downstream_podcast.mp3`
- `metadata.json`

## Notes

- Whisper runs fully local for transcript steps.
- NotebookLM integration here uses officially documented notebook/source + podcast flows.
- If downstream JSON parsing fails, the app stores raw output and falls back to heuristic structure extraction.
