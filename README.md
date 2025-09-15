# Mom Transcript (Whisper.cpp + FastAPI + Next.js)

Mom Transcript is a full‑stack app to record meetings, upload audio, and get fast transcripts using whisper.cpp. It ships with:

- FastAPI backend (apps/backend) with sessionized recording, ingest (browser chunks), uploads, model management, and WebSocket updates
- Next.js frontend (apps/frontend) with a clean dashboard, Record in Browser, Upload & Transcribe, Sessions, and Settings (download/set models, validate)
- whisper.cpp embedded in the repo (whisper.cpp/) for on‑device transcription

## Quick Start

### Option A — Docker Compose (recommended)

1) Ensure Docker is installed

2) Start backend + frontend

```
docker compose up --build
```

This will expose:
- Backend API: http://localhost:8030
- Frontend:    http://localhost:3001

3) Open http://localhost:3001 and log in (dev token)

The app uses a minimal JWT dev login. Open “Login” and click “Login”; the token is stored in localStorage.

### Option B — Local dev (power users)

- Backend (Python 3.11+):
  - `pip install -r requirements.txt`
  - `python apps/backend/src/main.py`
- Frontend (Node 20):
  - `cd apps/frontend`
  - `npm install`
  - `npm run dev`
- Visit http://localhost:3001

## Features

### Record in Browser (/ingest)
- Creates an ingest session and records via MediaRecorder in chunks (1–5s)
- Language selector (Auto/id/en)
- Stop + Finish merges chunks → mono 16 kHz WAV → transcribes with whisper.cpp
- Shows processing spinner with estimated progress (based on audio duration broadcast by backend) and a “Selesai” toast via WebSocket before redirecting to the session page
- Start is disabled while transcribing to avoid accidental restarts

### Sessions (/sessions and /sessions/[id])
- Lists your sessions (persist across restarts)
- Session detail page shows:
  - Status, audio duration
  - Transcript inline (auto-refreshes)
  - Copy and Download buttons
- Stop/Cancel controls removed (not needed for ingest flow)

### Upload & Transcribe (/upload)
- Upload a single audio file (webm, wav, m4a, mp3, flac, ogg/opus, etc.)
- Choose language (Auto/id/en)
- Backend converts to mono 16 kHz WAV and runs whisper.cpp
- Transcript appears inline with a download link

### Settings (/settings)
- Active Model: choose which ggml-* model whisper.cpp uses (saved to configs/server_settings.json)
- Catalog + Download: fetch common models (tiny/base/small/medium/large)
  - Robust downloader: prefers Hugging Face, retries, validates size
  - Shows Downloading/Error with log snippet when issues occur
- Upload model: if server cannot access internet, upload ggml-*.bin directly via the UI
- Validate: runs whisper.cpp against samples/jfk.wav to confirm the model loads

### Persistence
- Session metadata is saved at `output/sessions/<session_id>/meta.json` and restored on backend startup
  - Includes: session_id, status, start_time, output_dir, transcript_path, audio_duration, language, chunk_count, model
- Transcripts under `output/sessions/<session_id>/transcripts/`
- Audio under `output/sessions/<session_id>/recordings/`

## Model Management and whisper.cpp

- Binary: `whisper.cpp/main` (Settings lets you validate the binary and active model)
- Models directory: `whisper.cpp/models/`
- Active model is stored in `configs/server_settings.json` (project‑relative path recommended)

If using Docker, bind‑mount the models folder so downloads persist and are visible on the host:

```
# In docker-compose.yml under the backend service:
#  - ./whisper.cpp/models:/app/whisper.cpp/models
```

Build whisper.cpp binary (optional if not included):

```
make -C whisper.cpp
```

## How It Works (Ingest)

- Browser records short chunks (webm/opus), uploads to `/sessions/{id}/ingest`
- Finish (`/sessions/{id}/finish`) merges all chunks safely:
  - For MediaRecorder WebM: binary‑concatenate and decode to a single WAV via ffmpeg
  - For other types/fallback: per‑chunk decode to WAV then merge
- Backend runs whisper.cpp with the selected model and saves transcript
- WebSocket broadcasts a `processing` event with actual audio duration first, and a `completed` event on finish

## Running the App

- Login (dev): “Login” → click the button
- Record: “Record” → Start Recording → Stop + Finish
- Upload: “Upload” → pick a file and language → Upload & Transcribe
- Sessions: “Sessions” → open a session to read or copy the transcript
- Settings: choose, download, upload, validate models; then Save

## API Overview (selected)

- Auth
  - `POST /auth/login { user_id }` → dev token
  - `GET  /auth/verify` → check token
- Health
  - `GET /health` → { status, timestamp }
- Sessions (ingest)
  - `POST /sessions/start { ingest: true, language }` → { session_id }
  - `POST /sessions/{id}/ingest` (multipart) → append chunk
  - `POST /sessions/{id}/finish` → merge + transcribe
  - `GET  /sessions` → list sessions
  - `GET  /sessions/{id}/status` → status + paths
  - WS `/ws/session?session_id=...&token=...` → events: chunk, processing, completed
- Upload transcription
  - `POST /upload/transcribe` (multipart: file, language?) → transcript
- Files
  - `GET /transcription/download/{path}` → download .txt
  - `GET /transcription/content/{path}` → { content }
- Models & Settings
  - `GET  /models/installed` → installed ggml models
  - `GET  /models/catalog` → available names
  - `POST /models/download { name }` → start download (script or curl). Status: `GET /models/downloads`
  - `POST /models/upload` (multipart: file) → place model into whisper.cpp/models
  - `POST /models/validate { path? }` → run a small validation with jfk.wav
  - `GET  /settings` / `POST /settings { chunk_model }`

## Environment & Config

- Frontend reads API base from `NEXT_PUBLIC_API_BASE` (defaults to http://localhost:8030 when served on 3000/3001)
- Backend uses:
  - `JWT_SECRET` (optional dev default provided)
  - `JWT_LEEWAY` (default 60s)
  - `ENABLE_LIVE_CHUNK_TRANSCRIBE` (default 1; dev feature)
  - `LIVE_TAIL_SEC` (default 15; dev feature)
- Server settings persisted at `configs/server_settings.json`

## Troubleshooting

- Backend offline / Health unknown
  - Ensure backend is running on http://localhost:8030
  - Set `NEXT_PUBLIC_API_BASE=http://localhost:8030` when running frontend outside Compose
- Mic prompt doesn’t show
  - Allow microphone for http://localhost:3001 in the browser site settings
- Chunk upload finishes but transcript empty
  - Input was silent (check levels) or wrong language/model; try `Auto` language and a smaller model first
- Model download errors
  - Settings shows the last lines of the download log
  - If behind a proxy/firewall, use “Upload model” to add ggml-*.bin from your machine
- “Model file does not exist” on Save
  - Ensure path under `whisper.cpp/models` exists; with Docker, bind‑mount the folder as shown above

## License & Credits

- whisper.cpp by Georgi Gerganov and contributors
- This app wraps whisper.cpp with a simple web UI and REST/WebSocket API for local transcription

