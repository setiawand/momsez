# Mom Transcript 🎙️

Sistem transkripsi audio real-time menggunakan Whisper.cpp dengan berbagai mode operasi.

## 🚀 Quick Start dengan Docker

```bash
# Build dan setup
make setup

# Jalankan batch transcription
make run-batch

# Atau hybrid mode
make run-hybrid
```

📖 **[Panduan Docker Lengkap](DOCKER_GUIDE.md)**

## 📁 Struktur Project

```
mom-transcript/
├── src/                    # 🐍 Source code Python
├── configs/               # ⚙️ File konfigurasi
├── scripts/               # 📜 Shell scripts
├── docs/                  # 📚 Dokumentasi
├── output/                # 📤 Output transcription
├── tests/                 # ✅ Test scripts
├── Dockerfile             # 🐳 Docker image
├── docker-compose.yml     # 🐙 Multi-service config
└── Makefile              # 🔧 Development commands
```

## 🎯 Mode Operasi

A simple Python + whisper.cpp tool to transcribe meetings live from your microphone. It records audio in chunks and invokes the whisper.cpp binary on each chunk, appending the results to a transcript file and printing them to the terminal.

Bahasa Indonesia available below.

## Features

- Live, chunked transcription from default mic
- Uses whisper.cpp for fast, local inference
- Saves full transcript to a file while also printing to console
- Simple CLI with options for model, language, chunk length, and device

## Requirements

- Python 3.9+
- `sounddevice` Python package (see Installation)
- Built whisper.cpp binaries and a model file
  - whisper.cpp `main` binary path (e.g. `./whisper.cpp/main`)
  - a GGML/GGUF model (e.g. `models/ggml-small.bin` or `ggml-small.en.bin`)

Note: This project does not download or build whisper.cpp or models for you. Follow the upstream instructions to build and obtain models.

## Installation

1) Create a virtual environment (optional but recommended)

```
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```
pip install -r requirements.txt
```

If you are on macOS, the first time you access the microphone you may need to grant mic permission to your terminal/IDE.

3) Build whisper.cpp and download a model

- whisper.cpp: https://github.com/ggerganov/whisper.cpp
- Build the `main` binary following their README (e.g. `make`)
- Download a model, e.g. `ggml-small.en.bin` or `ggml-small.bin`

## Usage

```
# Chunked mode (default):
python apps/backend/src/live_transcribe.py --mode chunks \
  --whisper-bin /path/to/whisper.cpp/main \
  --model /path/to/model.bin \
  --language auto \
  --chunk-sec 15 \
  --output transcript.txt

# Streaming mode (more live):
python apps/backend/src/live_transcribe.py --mode stream \
  --stream-bin /path/to/whisper.cpp/examples/stream/stream \
  --model /path/to/model.bin \
  --language auto \
  --output transcript.txt \
  --stream-args "<extra args for device, vad, etc>"
```

Options:

- `--mode`: `chunks` uses `main` per audio chunk; `stream` uses the streaming binary
- `--whisper-bin`: Path to whisper.cpp `main` executable
- `--stream-bin`: Path to whisper.cpp `stream` executable
- `--model`: Path to GGML/GGUF model file
- `--language`: Language code (e.g. `auto`, `en`, `id`)
- `--chunk-sec`: Chunk duration to record and transcribe each iteration
- `--device-index`: Optional input device index (see `--list-devices`)
- `--sample-rate`: Sample rate for capture (default 16000)
- `--threads`: Number of threads for whisper.cpp (`-t`)
- `--output`: Output transcript file (appends)
- `--list-devices`: List available input devices and exit
- `--stream-args`: Extra flags forwarded directly to the `stream` binary (e.g. device selection, VAD)

Tips:

- For Bahasa Indonesia, set `--language id`
- For English-only model (e.g. `ggml-small.en.bin`), set `--language en`

## How it works

The script records the microphone for N seconds (chunk) at 16 kHz mono, writes a temporary WAV, calls whisper.cpp on that WAV, then appends the recognized text to your transcript. This repeats until you Ctrl+C to stop.

This is a simple, robust approach. It is not a fully streaming, token-by-token transcription, but gives near-live results every chunk. If you need true streaming, consider compiling and using whisper.cpp's `stream` example and wrapping/parsing its stdout.

## API Authentication (JWT)

For web multi-user scenarios, session endpoints require a Bearer JWT. The server reads `JWT_SECRET` from the environment; set it in production. A simple dev login is provided:

```
# Dev login (issues a JWT for the provided user_id/username)
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"alice","exp_minutes":60}'

# Verify token
curl http://localhost:8000/auth/verify \
  -H "Authorization: Bearer $JWT"
```

Use the token in `Authorization: Bearer <JWT>` header for all session endpoints. For WebSocket per session, you may pass the token via header or `?token=` query param.

## Session APIs (Recording & Ingest)

The backend supports both device-capture sessions (server mic) and ingest sessions (browser uploads chunks). All session responses are scoped to the authenticated user.

### Device-Capture Session

```
# Start (uses server microphone; restricts one session per device)
curl -X POST http://localhost:8000/sessions/start \
  -H "Authorization: Bearer $JWT" \
  -H 'Content-Type: application/json' \
  -d '{"language":"id","device_index":0}'

# Status
curl http://localhost:8000/sessions/$SID/status \
  -H "Authorization: Bearer $JWT"

# Stop + transcribe
curl -X POST http://localhost:8000/sessions/$SID/stop \
  -H "Authorization: Bearer $JWT"
```

### Ingest Session (Browser Upload)

```
# Start ingest session
curl -X POST http://localhost:8000/sessions/start \
  -H "Authorization: Bearer $JWT" \
  -H 'Content-Type: application/json' \
  -d '{"ingest":true, "language":"id"}'

# Upload chunk(s)
curl -X POST http://localhost:8000/sessions/$SID/ingest \
  -H "Authorization: Bearer $JWT" \
  -F 'file=@/path/to/chunk1.wav'

# Finish (merge + transcribe)
curl -X POST http://localhost:8000/sessions/$SID/finish \
  -H "Authorization: Bearer $JWT"
```

### Session Management

```
# List user's sessions
curl http://localhost:8000/sessions -H "Authorization: Bearer $JWT"

# Cancel an active session (no transcription)
curl -X POST http://localhost:8000/sessions/$SID/cancel -H "Authorization: Bearer $JWT"

# Delete a session (and optionally purge files)
curl -X DELETE 'http://localhost:8000/sessions/$SID?purge=true' \
  -H "Authorization: Bearer $JWT"
```

### WebSocket Per Session

```
# Receive session events (started, chunk, completed)
ws://localhost:8000/ws/session?session_id=$SID&token=$JWT
```

Events are JSON messages with fields like `type`, `session_id`, and additional data.

## Bahasa Indonesia

### Ringkasan

Program Python ini melakukan transkripsi secara langsung dari mikrofon saat meeting berlangsung. Audio direkam per potongan waktu (chunk), lalu setiap potongan diproses oleh whisper.cpp. Hasil transkripsi akan tampil di terminal dan disimpan ke file.

### Persyaratan

- Python 3.9+
- Paket Python `sounddevice`
- Biner whisper.cpp (`main`) dan file model (GGML/GGUF)

### Instalasi

1. (Opsional) Buat virtual env dan aktifkan

```
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```
pip install -r requirements.txt
```

3. Build whisper.cpp dan unduh model sesuai panduan repo whisper.cpp

### Cara Menjalankan

```
# Mode chunk (default):
python apps/backend/src/live_transcribe.py --mode chunks \
  --whisper-bin /path/ke/whisper.cpp/main \
  --model /path/ke/model.bin \
  --language id \
  --chunk-sec 15 \
  --output transcript.txt

# Mode streaming (lebih "live"):
python apps/backend/src/live_transcribe.py --mode stream \
  --stream-bin /path/ke/whisper.cpp/examples/stream/stream \
  --model /path/ke/model.bin \
  --language id \
  --output transcript.txt \
  --stream-args "<opsi tambahan perangkat / VAD>"
```

Gunakan `--list-devices` untuk melihat daftar input device dan tentukan `--device-index` bila perlu.

### Catatan

- Program ini tidak mengunduh atau membangun whisper.cpp dan model secara otomatis.
- Untuk output yang lebih cepat, gunakan model yang lebih kecil (mis. `tiny`, `base`, `small`).
