#!/usr/bin/env python3
"""
FastAPI Backend for Mom Transcript
Provides REST API and WebSocket endpoints for transcription services
"""

import asyncio
import json
import os
import shutil
import subprocess
import uuid
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import wave
import tempfile

import sounddevice as sd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import jwt

from batch_transcribe import BatchTranscriber, load_batch_config
from hybrid_transcribe import HybridTranscriber, load_hybrid_config

# Pydantic models
class TranscriptionConfig(BaseModel):
    mode: str  # 'batch', 'live', 'hybrid'
    language: str = 'id'
    device_index: Optional[int] = None
    output_dir: Optional[str] = None
    chunk_duration: int = 30

class RecordingConfig(BaseModel):
    language: str = 'id'
    device_index: Optional[int] = None
    output_dir: Optional[str] = None
    ingest: bool = False  # if True, do not open device; expect uploaded chunks

class SessionStartResponse(BaseModel):
    session_id: str
    status: str
    device_index: Optional[int] = None
    output_dir: str
    start_time: str

class SessionStatus(BaseModel):
    session_id: str
    status: str
    device_index: Optional[int] = None
    output_dir: str
    start_time: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = None
    error_message: Optional[str] = None

# Auth models
class UserLoginRequest(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    exp_minutes: int = 60

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_at: str

class TranscriptionStatus(BaseModel):
    status: str  # 'idle', 'recording', 'processing', 'completed', 'error'
    mode: Optional[str] = None
    start_time: Optional[str] = None
    duration: Optional[float] = None
    output_files: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class DeviceInfo(BaseModel):
    index: int
    name: str
    channels: int
    sample_rate: float

# Global state
app = FastAPI(title="Mom Transcript API", version="1.0.0")
transcription_state = {
    'status': 'idle',
    'transcriber': None,
    'mode': None,
    'start_time': None,
    'output_files': [],
    'websocket_clients': set()
}

# Sessionized state structures
sessions: Dict[str, Dict] = {}
sessions_lock = threading.Lock()
active_device_sessions: Dict[str, str] = {}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allowed directories for file access (unified under output/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
ALLOWED_DIRS = [
    PROJECT_ROOT / 'output',
    PROJECT_ROOT / 'uploads',
]

def _safe_resolve(path_str: str) -> Path:
    """Resolve a user-provided path safely within allowed directories.
    Returns resolved Path if allowed, otherwise raises HTTPException.
    """
    # Support both relative-to-project and already-relative inputs
    candidate = (PROJECT_ROOT / path_str).resolve() if not Path(path_str).is_absolute() else Path(path_str).resolve()

    for base in ALLOWED_DIRS:
        try:
            base_resolved = base.resolve()
        except Exception:
            continue
        if candidate.is_file() and str(candidate).startswith(str(base_resolved)):
            return candidate
    raise HTTPException(status_code=403, detail="Access to this path is not allowed")

def _device_key(device_index: Optional[int]) -> str:
    """Return key used to gate concurrent capture on the same device."""
    return 'default' if device_index is None else str(device_index)

# --- Minimal JWT Auth (Bearer) for session endpoints ---
def _jwt_secret() -> str:
    secret = os.getenv('JWT_SECRET')
    if not secret:
        # Development fallback; for production set JWT_SECRET in env
        secret = 'dev-secret-change-me'
    return secret

def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Not authenticated')
    return authorization.split(' ', 1)[1].strip()

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    token = _extract_bearer_token(authorization)
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=['HS256'])
        if not isinstance(payload, dict):
            raise HTTPException(status_code=401, detail='Invalid token payload')
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')

def _user_id_from_payload(payload: Dict) -> str:
    return str(payload.get('sub') or payload.get('user_id') or payload.get('uid') or '')

def _ensure_session_owner(session: Dict, user_id: str):
    owner = session.get('user_id')
    if owner and owner != user_id:
        raise HTTPException(status_code=403, detail='Forbidden: session belongs to another user')
    if not owner:
        session['user_id'] = user_id

def create_access_token(user_id: str, minutes: int = 60) -> tuple[str, datetime]:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=max(1, minutes))
    payload = {
        'sub': user_id,
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm='HS256')
    return token, exp

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
class SessionWSManager:
    def __init__(self):
        self.groups: Dict[str, List[WebSocket]] = {}
        self.lock = threading.Lock()

    async def connect(self, websocket: WebSocket, session_id: Optional[str]):
        await websocket.accept()
        if not session_id:
            return
        with self.lock:
            self.groups.setdefault(session_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: Optional[str]):
        if not session_id:
            return
        with self.lock:
            conns = self.groups.get(session_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self.groups.pop(session_id, None)

    async def broadcast(self, session_id: str, message: str):
        with self.lock:
            conns = list(self.groups.get(session_id, []))
        disconnected = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except:
                disconnected.append(ws)
        if disconnected:
            with self.lock:
                for ws in disconnected:
                    if session_id in self.groups and ws in self.groups[session_id]:
                        self.groups[session_id].remove(ws)

session_ws = SessionWSManager()

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Mom Transcript API", "version": "1.0.0"}

# --- Auth endpoints (dev/demo) ---
@app.post("/auth/login", response_model=TokenResponse)
async def auth_login(req: UserLoginRequest):
    # Very basic dev login: accept any user_id or username
    user_id = (req.user_id or req.username or '').strip()
    if not user_id:
        raise HTTPException(status_code=400, detail='user_id or username is required')
    token, exp = create_access_token(user_id=user_id, minutes=req.exp_minutes)
    return TokenResponse(access_token=token, expires_at=exp.isoformat())

@app.get("/auth/verify")
async def auth_verify(user: Dict = Depends(get_current_user)):
    # Echo back decoded claims
    return {'valid': True, 'user': user}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/devices", response_model=List[DeviceInfo])
async def get_audio_devices():
    """Get available audio input devices"""
    try:
        devices = sd.query_devices()
        input_devices = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append(DeviceInfo(
                    index=i,
                    name=device['name'],
                    channels=device['max_input_channels'],
                    sample_rate=device['default_samplerate']
                ))
        
        return input_devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get devices: {str(e)}")

@app.post("/devices/test")
async def test_audio_device(request: dict):
    """Test audio device functionality"""
    try:
        device_id = request.get('device_id')
        if device_id is None:
            raise HTTPException(status_code=400, detail="device_id is required")
        
        device_index = int(device_id)
        
        # Test device by checking if it can be opened
        devices = sd.query_devices()
        if device_index >= len(devices) or device_index < 0:
            raise HTTPException(status_code=400, detail="Invalid device index")
        
        device = devices[device_index]
        if device['max_input_channels'] <= 0:
            raise HTTPException(status_code=400, detail="Device has no input channels")
        
        # Try to open the device briefly to test it
        try:
            with sd.InputStream(device=device_index, channels=1, samplerate=16000, blocksize=1024):
                pass  # Just test if we can open it
        except Exception as device_error:
            raise HTTPException(status_code=400, detail=f"Device test failed: {str(device_error)}")
        
        return {"success": True, "message": f"Device {device['name']} test successful"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid device_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device test failed: {str(e)}")

@app.get("/status", response_model=TranscriptionStatus)
async def get_status():
    """Get current transcription status"""
    output_files = []
    
    # Try to get output files from active transcriber first
    if transcription_state['transcriber'] and hasattr(transcription_state['transcriber'], 'output_dir'):
        output_dir = Path(transcription_state['transcriber'].output_dir)
        if output_dir.exists():
            # Find transcript files
            for pattern in ['*.txt', '*.json']:
                output_files.extend([str(f) for f in output_dir.rglob(pattern)])
    
    # If no files found and transcription is completed, search only in unified output directory
    if not output_files and transcription_state['status'] in ['completed', 'idle']:
        project_root = Path(__file__).parent.parent
        dir_path = project_root / 'output'
        if dir_path.exists():
            for pattern in ['*.txt', '*.json']:
                found_files = list(dir_path.rglob(pattern))
                found_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                relative_files = [str(f.relative_to(project_root)) for f in found_files[:5]]
                output_files.extend(relative_files)
    
    return TranscriptionStatus(
        status=transcription_state['status'],
        mode=transcription_state['mode'],
        start_time=transcription_state['start_time'],
        output_files=output_files
    )

@app.post("/recording/start")
async def recording_start(config: RecordingConfig | None = None):
    """Start microphone recording (user-controlled stop)."""
    if transcription_state['status'] != 'idle':
        raise HTTPException(status_code=400, detail="Another process is in progress")

    try:
        cfg = load_batch_config('configs/hybrid_config_meeting.json')
        if config:
            if config.language:
                cfg['language'] = config.language
            if config.device_index is not None:
                cfg['device_index'] = config.device_index
            if config.output_dir:
                cfg['output_dir'] = config.output_dir

        transcriber = BatchTranscriber(cfg, interactive=False)
        ok = transcriber.start_recording_async()
        if not ok:
            raise HTTPException(status_code=400, detail="Recording already running")

        transcription_state['status'] = 'recording'
        transcription_state['transcriber'] = transcriber
        transcription_state['mode'] = 'manual-record'
        transcription_state['start_time'] = datetime.now().isoformat()

        return {"message": "Recording started", "status": "recording"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {str(e)}")

@app.post("/recording/stop")
async def recording_stop():
    """Stop microphone recording, transcribe the audio, and return text."""
    if transcription_state['status'] != 'recording':
        raise HTTPException(status_code=400, detail="No active recording")

    transcriber = transcription_state['transcriber']
    if not transcriber or not hasattr(transcriber, 'stop'):
        raise HTTPException(status_code=400, detail="No transcriber available")

    try:
        # Stop capture
        transcriber.stop()
        # Wait for audio file to be written
        audio_path = transcriber.wait_for_finish(timeout=120)
        if not audio_path or not Path(audio_path).exists():
            transcription_state['status'] = 'idle'
            transcription_state['transcriber'] = None
            transcription_state['mode'] = None
            transcription_state['start_time'] = None
            raise HTTPException(status_code=500, detail="Recording stopped but no audio saved")

        # Update state to processing
        transcription_state['status'] = 'processing'

        # Transcribe synchronously
        transcript_path = transcriber.transcribe_audio(Path(audio_path))
        text_content = ""
        if transcript_path and Path(transcript_path).exists():
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except Exception:
                text_content = ""

        # Finalize state
        transcription_state['status'] = 'completed'

        # Schedule auto-reset
        def reset_to_idle():
            time.sleep(30)
            if transcription_state['status'] == 'completed':
                transcription_state['status'] = 'idle'
                transcription_state['transcriber'] = None
                transcription_state['mode'] = None
                transcription_state['start_time'] = None
                print("[API] Auto-reset status to idle after completion")
        threading.Thread(target=reset_to_idle, daemon=True).start()

        return {
            "message": "Transcription completed",
            "status": "completed",
            "audio_path": str(audio_path),
            "transcript_path": str(transcript_path) if transcript_path else None,
            "text": text_content,
        }

    except HTTPException:
        raise
    except Exception as e:
        transcription_state['status'] = 'error'
        transcription_state['error'] = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to stop and transcribe: {str(e)}")

# --- Sessionized Recording API ---
@app.post("/sessions/start", response_model=SessionStartResponse)
async def sessions_start(config: RecordingConfig, user: Dict = Depends(get_current_user)):
    """Start a sessionized microphone recording. Returns session_id."""
    try:
        cfg = load_batch_config('configs/hybrid_config_meeting.json')
        if config.language:
            cfg['language'] = config.language
        if config.device_index is not None:
            cfg['device_index'] = config.device_index

        # Output under output/sessions/<session_id>
        session_id = uuid.uuid4().hex
        session_out = PROJECT_ROOT / 'output' / 'sessions' / session_id
        if config.output_dir:
            session_out = session_out / os.path.basename(config.output_dir)
        cfg['output_dir'] = str(session_out)
        session_out.mkdir(parents=True, exist_ok=True)

        dev_key = _device_key(cfg.get('device_index'))

        with sessions_lock:
            now = datetime.now().isoformat()
            if config.ingest:
                # Ingest mode: do not open device; prepare chunks dir
                chunks_dir = session_out / 'chunks'
                chunks_dir.mkdir(parents=True, exist_ok=True)
                sessions[session_id] = {
                    'status': 'awaiting-chunks',
                    'transcriber': None,
                    'device_index': None,
                    'output_dir': str(session_out),
                    'start_time': now,
                    'audio_path': None,
                    'transcript_path': None,
                    'error': None,
                    'chunk_count': 0,
                }
                _ensure_session_owner(sessions[session_id], _user_id_from_payload(user))
            else:
                if dev_key in active_device_sessions:
                    raise HTTPException(status_code=409, detail=f"Device in use by session {active_device_sessions[dev_key]}")
                transcriber = BatchTranscriber(cfg, interactive=False)
                ok = transcriber.start_recording_async()
                if not ok:
                    raise HTTPException(status_code=400, detail="Recording already running")
                sessions[session_id] = {
                    'status': 'recording',
                    'transcriber': transcriber,
                    'device_index': cfg.get('device_index'),
                    'output_dir': str(session_out),
                    'start_time': now,
                    'audio_path': None,
                    'transcript_path': None,
                    'error': None,
                }
                active_device_sessions[dev_key] = session_id
                _ensure_session_owner(sessions[session_id], _user_id_from_payload(user))

        # Notify session channel
        try:
            await session_ws.broadcast(session_id, json.dumps({'type': 'started', 'session_id': session_id, 'status': sessions[session_id]['status'], 'timestamp': datetime.now().isoformat()}))
        except Exception:
            pass

        return SessionStartResponse(
            session_id=session_id,
            status=sessions[session_id]['status'],
            device_index=sessions[session_id].get('device_index'),
            output_dir=str(session_out.relative_to(PROJECT_ROOT)),
            start_time=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@app.post("/sessions/{session_id}/stop")
async def sessions_stop(session_id: str, user: Dict = Depends(get_current_user)):
    """Stop recording for a session, transcribe audio, and return results."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        transcriber = session.get('transcriber')
        _ensure_session_owner(session, _user_id_from_payload(user))
        if session.get('status') != 'recording' or not transcriber:
            raise HTTPException(status_code=400, detail="Session is not recording")
        session['status'] = 'processing'

    try:
        transcriber.stop()
        audio_path = transcriber.wait_for_finish(timeout=180)

        if not audio_path or not Path(audio_path).exists():
            with sessions_lock:
                session['status'] = 'error'
                session['error'] = 'Recording stopped but no audio saved'
                dev_key = _device_key(session.get('device_index'))
                active_device_sessions.pop(dev_key, None)
            raise HTTPException(status_code=500, detail="Recording stopped but no audio saved")

        transcript_path = transcriber.transcribe_audio(Path(audio_path))
        text_content = ""
        if transcript_path and Path(transcript_path).exists():
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except Exception:
                text_content = ""

        with sessions_lock:
            session['status'] = 'completed'
            session['audio_path'] = str(audio_path)
            session['transcript_path'] = str(transcript_path) if transcript_path else None
            dev_key = _device_key(session.get('device_index'))
            active_device_sessions.pop(dev_key, None)

        # Notify session channel
        try:
            await session_ws.broadcast(session_id, json.dumps({'type': 'completed', 'session_id': session_id, 'audio_path': str(audio_path), 'transcript_path': str(transcript_path) if transcript_path else None}))
        except Exception:
            pass

        return {
            'session_id': session_id,
            'status': 'completed',
            'audio_path': str(audio_path),
            'transcript_path': str(transcript_path) if transcript_path else None,
            'text': text_content,
        }
    except HTTPException:
        raise
    except Exception as e:
        with sessions_lock:
            session['status'] = 'error'
            session['error'] = str(e)
            dev_key = _device_key(session.get('device_index'))
            active_device_sessions.pop(dev_key, None)
        raise HTTPException(status_code=500, detail=f"Failed to stop session: {str(e)}")


@app.get("/sessions/{session_id}/status", response_model=SessionStatus)
async def sessions_status(session_id: str, user: Dict = Depends(get_current_user)):
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        _ensure_session_owner(session, _user_id_from_payload(user))
        return SessionStatus(
            session_id=session_id,
            status=session.get('status', 'unknown'),
            device_index=session.get('device_index'),
            output_dir=str(Path(session.get('output_dir')).relative_to(PROJECT_ROOT)) if session.get('output_dir') else '',
            start_time=session.get('start_time'),
            audio_path=session.get('audio_path'),
            transcript_path=session.get('transcript_path'),
            error_message=session.get('error'),
        )


@app.post("/sessions/{session_id}/ingest")
async def sessions_ingest(session_id: str, file: UploadFile = File(...), user: Dict = Depends(get_current_user)):
    """Ingest an audio chunk file into a session (ingest mode)."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        _ensure_session_owner(session, _user_id_from_payload(user))
        if session.get('status') not in ['awaiting-chunks', 'ingesting']:
            raise HTTPException(status_code=400, detail="Session not accepting chunks")
        out_dir = Path(session['output_dir'])
        chunks_dir = out_dir / 'chunks'
        chunks_dir.mkdir(parents=True, exist_ok=True)

    # Save chunk file with incremental index
    try:
        ext = ''.join(Path(file.filename).suffixes).lower() or '.wav'
        with sessions_lock:
            session['chunk_count'] = int(session.get('chunk_count') or 0) + 1
            idx = session['chunk_count']
            session['status'] = 'ingesting'
        chunk_path = chunks_dir / f"chunk_{idx:06d}{ext}"
        content = await file.read()
        with open(chunk_path, 'wb') as f:
            f.write(content)

        # Notify via WS
        try:
            await session_ws.broadcast(session_id, json.dumps({'type': 'chunk', 'index': idx, 'bytes': len(content)}))
        except Exception:
            pass

        return {'session_id': session_id, 'chunk_index': idx, 'path': str(chunk_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest chunk: {str(e)}")


def _convert_to_wav(src: Path, dst: Path, sample_rate: int = 16000) -> bool:
    """Try to convert arbitrary audio to mono 16k WAV via ffmpeg.
    Returns True if success.
    """
    try:
        cmd = ['ffmpeg', '-y', '-i', str(src), '-ar', str(sample_rate), '-ac', '1', str(dst)]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode == 0 and dst.exists()
    except Exception:
        return False


def _merge_wavs(wav_files: List[Path], output_path: Path) -> None:
    """Merge multiple mono WAV files with same params into one WAV."""
    if not wav_files:
        raise ValueError('no wav files to merge')
    params = None
    with wave.open(str(output_path), 'wb') as out_wav:
        for i, wf_path in enumerate(wav_files):
            with wave.open(str(wf_path), 'rb') as w:
                if i == 0:
                    nch, sampwidth, fr, nframes, comptype, compname = w.getparams()
                    params = (nch, sampwidth, fr)
                    out_wav.setnchannels(nch)
                    out_wav.setsampwidth(sampwidth)
                    out_wav.setframerate(fr)
                else:
                    # Validate params
                    nch, sampwidth, fr, *_ = w.getparams()
                    if (nch, sampwidth, fr) != params:
                        raise ValueError('inconsistent WAV parameters')
                frames = w.readframes(w.getnframes())
                out_wav.writeframes(frames)


@app.post("/sessions/{session_id}/finish")
async def sessions_finish(session_id: str, user: Dict = Depends(get_current_user)):
    """Finalize ingest session: merge/convert chunks and transcribe."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        _ensure_session_owner(session, _user_id_from_payload(user))
        if session.get('status') not in ['awaiting-chunks', 'ingesting']:
            raise HTTPException(status_code=400, detail="Session is not an ingest session or already finished")
        out_dir = Path(session['output_dir'])
        session['status'] = 'processing'

    chunks_dir = out_dir / 'chunks'
    if not chunks_dir.exists():
        raise HTTPException(status_code=400, detail="No chunks uploaded")

    # Prepare list of wav files; convert if needed
    wav_dir = out_dir / 'chunks_wav'
    wav_dir.mkdir(exist_ok=True)
    wav_files: List[Path] = []
    for p in sorted(chunks_dir.iterdir()):
        if p.is_file():
            if p.suffix.lower() == '.wav':
                wav_files.append(p)
            else:
                tmp_wav = wav_dir / (p.stem + '.wav')
                ok = _convert_to_wav(p, tmp_wav)
                if ok:
                    wav_files.append(tmp_wav)
                else:
                    with sessions_lock:
                        session['status'] = 'error'
                        session['error'] = f'Failed to convert {p.name} to WAV'
                    raise HTTPException(status_code=500, detail=f"Failed to convert {p.name} to WAV")

    # Merge
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_path = out_dir / 'recordings' / f'recording_{timestamp}.wav'
    merged_path.parent.mkdir(exist_ok=True)
    try:
        _merge_wavs(wav_files, merged_path)
    except Exception as e:
        with sessions_lock:
            session['status'] = 'error'
            session['error'] = f'Merge failed: {e}'
        raise HTTPException(status_code=500, detail=f"Failed to merge chunks: {e}")

    # Transcribe
    cfg = {
        'output_dir': str(out_dir),
        'whisper_bin': './whisper.cpp/main',
        'chunk_model': './whisper.cpp/models/ggml-small.bin',
        'language': 'id',
    }
    transcriber = BatchTranscriber(cfg, interactive=False)
    transcript_path = transcriber.transcribe_audio(merged_path)
    text = ''
    if transcript_path and Path(transcript_path).exists():
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            text = ''

    with sessions_lock:
        session['status'] = 'completed'
        session['audio_path'] = str(merged_path)
        session['transcript_path'] = str(transcript_path) if transcript_path else None

    try:
        await session_ws.broadcast(session_id, json.dumps({'type': 'completed', 'session_id': session_id, 'audio_path': str(merged_path), 'transcript_path': session['transcript_path']}))
    except Exception:
        pass

    return {
        'session_id': session_id,
        'status': 'completed',
        'audio_path': str(merged_path),
        'transcript_path': str(transcript_path) if transcript_path else None,
        'text': text,
    }

@app.get("/sessions", response_model=List[SessionStatus])
async def sessions_list(user: Dict = Depends(get_current_user)):
    """List all sessions (active and history)."""
    items: List[SessionStatus] = []
    uid = _user_id_from_payload(user)
    with sessions_lock:
        for sid, sess in sessions.items():
            # Only list sessions owned by this user
            owner = sess.get('user_id')
            if owner and owner != uid:
                continue
            items.append(SessionStatus(
                session_id=sid,
                status=sess.get('status', 'unknown'),
                device_index=sess.get('device_index'),
                output_dir=str(Path(sess.get('output_dir')).relative_to(PROJECT_ROOT)) if sess.get('output_dir') else '',
                start_time=sess.get('start_time'),
                audio_path=sess.get('audio_path'),
                transcript_path=sess.get('transcript_path'),
                error_message=sess.get('error'),
            ))
    return items

@app.post("/sessions/{session_id}/cancel")
async def sessions_cancel(session_id: str, user: Dict = Depends(get_current_user)):
    """Cancel a recording session without transcription and free device."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        _ensure_session_owner(session, _user_id_from_payload(user))
        transcriber = session.get('transcriber')
        status = session.get('status')
        session['status'] = 'cancelling'

    try:
        if status == 'recording' and transcriber:
            transcriber.stop()
            audio_path = transcriber.wait_for_finish(timeout=120)
            with sessions_lock:
                session['audio_path'] = str(audio_path) if audio_path else None
        with sessions_lock:
            session['status'] = 'cancelled'
            dev_key = _device_key(session.get('device_index'))
            active_device_sessions.pop(dev_key, None)
            audio_path = session.get('audio_path')
        try:
            await session_ws.broadcast(session_id, json.dumps({'type': 'cancelled', 'session_id': session_id, 'audio_path': audio_path}))
        except Exception:
            pass
        return {'session_id': session_id, 'status': 'cancelled', 'audio_path': audio_path}
    except Exception as e:
        with sessions_lock:
            session['status'] = 'error'
            session['error'] = str(e)
            dev_key = _device_key(session.get('device_index'))
            active_device_sessions.pop(dev_key, None)
        raise HTTPException(status_code=500, detail=f"Failed to cancel session: {str(e)}")

@app.delete("/sessions/{session_id}")
async def sessions_delete(session_id: str, purge: bool = False, user: Dict = Depends(get_current_user)):
    """Delete a session record; optionally delete files with purge=true."""
    with sessions_lock:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        _ensure_session_owner(session, _user_id_from_payload(user))
        transcriber = session.get('transcriber')
        status = session.get('status')

    if status == 'recording' and transcriber:
        try:
            transcriber.stop()
            transcriber.wait_for_finish(timeout=120)
        except Exception:
            pass
        with sessions_lock:
            dev_key = _device_key(session.get('device_index'))
            active_device_sessions.pop(dev_key, None)

    with sessions_lock:
        removed_session = sessions.pop(session_id, None)

    removed_files = False
    if purge and removed_session and removed_session.get('output_dir'):
        out_dir = Path(removed_session['output_dir'])
        try:
            out_res = out_dir.resolve()
            out_root = (PROJECT_ROOT / 'output').resolve()
            if str(out_res).startswith(str(out_root)) and out_res.exists():
                shutil.rmtree(out_res)
                removed_files = True
        except Exception:
            pass

    return {'session_id': session_id, 'deleted': True, 'purged_files': removed_files}

@app.post("/transcription/start")
async def start_transcription(config: TranscriptionConfig):
    """Start transcription with specified configuration"""
    if transcription_state['status'] != 'idle':
        raise HTTPException(status_code=400, detail="Transcription already in progress")
    
    try:
        # Load appropriate config file
        if config.mode == 'batch':
            base_config = load_batch_config('configs/hybrid_config_meeting.json')
            transcriber = BatchTranscriber(base_config, interactive=False)
        elif config.mode == 'hybrid':
            base_config = load_hybrid_config('configs/hybrid_config_meeting.json')
            transcriber = HybridTranscriber(base_config)
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'batch' or 'hybrid'")
        
        # Update config with user preferences
        if config.language:
            base_config['language'] = config.language
        if config.device_index is not None:
            base_config['device_index'] = config.device_index
        if config.output_dir:
            base_config['output_dir'] = config.output_dir
        if config.chunk_duration:
            base_config['chunk_duration'] = config.chunk_duration
        
        # Start transcription in background thread
        def run_transcription():
            try:
                transcription_state['status'] = 'recording'
                transcription_state['transcriber'] = transcriber
                transcription_state['mode'] = config.mode
                transcription_state['start_time'] = datetime.now().isoformat()
                
                if config.mode == 'batch':
                    # For batch mode, use single session without prompts
                    result = transcriber.run_single_session()
                    if result:
                        print(f"[API] Batch transcription completed: {result}")
                else:
                    # For hybrid mode
                    transcriber.start()
                
                transcription_state['status'] = 'completed'
                
                # Notify WebSocket clients (schedule in main event loop)
                try:
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast(json.dumps({
                            'type': 'status_update',
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat()
                        })), loop
                    )
                except Exception:
                    pass  # Ignore if no event loop available
                
                # Auto-reset to idle after 30 seconds to prevent stuck 'completed' status
                def reset_to_idle():
                    time.sleep(30)
                    if transcription_state['status'] == 'completed':
                        transcription_state['status'] = 'idle'
                        transcription_state['transcriber'] = None
                        transcription_state['mode'] = None
                        transcription_state['start_time'] = None
                        print("[API] Auto-reset status to idle after completion")
                
                reset_thread = threading.Thread(target=reset_to_idle, daemon=True)
                reset_thread.start()
                
            except Exception as e:
                transcription_state['status'] = 'error'
                transcription_state['error'] = str(e)
                
                # Notify WebSocket clients (schedule in main event loop)
                try:
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(
                        manager.broadcast(json.dumps({
                            'type': 'error',
                            'message': str(e),
                            'timestamp': datetime.now().isoformat()
                        })), loop
                    )
                except Exception:
                    pass  # Ignore if no event loop available
        
        # Start transcription thread
        thread = threading.Thread(target=run_transcription, daemon=True)
        thread.start()
        
        return {"message": f"Started {config.mode} transcription", "status": "recording"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start transcription: {str(e)}")

@app.post("/transcription/stop")
async def stop_transcription():
    """Stop current transcription"""
    if transcription_state['status'] == 'idle':
        raise HTTPException(status_code=400, detail="No transcription in progress")
    
    try:
        transcriber = transcription_state['transcriber']
        if transcriber and hasattr(transcriber, 'stop'):
            transcriber.stop()
        
        transcription_state['status'] = 'idle'
        transcription_state['transcriber'] = None
        transcription_state['mode'] = None
        transcription_state['start_time'] = None
        
        # Notify WebSocket clients
        await manager.broadcast(json.dumps({
            'type': 'status_update',
            'status': 'stopped',
            'timestamp': datetime.now().isoformat()
        }))
        
        return {"message": "Transcription stopped", "status": "idle"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop transcription: {str(e)}")

@app.get("/transcription/files")
async def list_transcription_files():
    """List available transcription files"""
    files = []
    
    # Scan only unified output directory
    dir_path = Path('output')
    if dir_path.exists():
        for file_path in dir_path.rglob('*.txt'):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime,
                    'type': 'transcript'
                })
        for file_path in dir_path.rglob('*.wav'):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime,
                    'type': 'audio'
                })
    
    return {'files': files}

@app.get("/transcription/download/{file_path:path}")
async def download_file(file_path: str):
    """Download a transcription file"""
    try:
        full_path = _safe_resolve(file_path)
    except HTTPException as e:
        raise e

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type='application/octet-stream'
    )

@app.get("/transcription/content/{file_path:path}")
async def get_transcript_content(file_path: str):
    """Get the content of a transcript file"""
    try:
        full_path = _safe_resolve(file_path)
    except HTTPException as e:
        raise e

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    if not full_path.suffix.lower() in ['.txt', '.json']:
        raise HTTPException(status_code=400, detail="File is not a transcript file")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'content': content,
            'filename': full_path.name,
            'path': str(full_path),
            'size': full_path.stat().st_size,
            'modified': full_path.stat().st_mtime
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@app.post("/transcription/upload")
async def upload_audio_file(file: UploadFile = File(...)):
    """Upload audio file for transcription"""
    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    # Create upload directory
    upload_dir = Path('uploads')
    upload_dir.mkdir(exist_ok=True)
    
    # Sanitize filename to prevent path traversal and collisions
    import re
    original_name = os.path.basename(file.filename)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = (Path(upload_dir) / f"{timestamp}_{safe_name}").resolve()
    # Ensure final path is within uploads
    if not str(file_path).startswith(str(upload_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    try:
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        return {
            'message': 'File uploaded successfully',
            'filename': file.filename,
            'path': str(file_path),
            'size': len(content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo back for testing
            await manager.send_personal_message(f"Echo: {data}", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/session")
async def websocket_session(websocket: WebSocket):
    # Expect query param ?session_id= and Authorization header Bearer token (or token= in query for browsers that can't set headers)
    session_id = websocket.query_params.get('session_id')
    token = None
    # Try header first
    try:
        auth_header = websocket.headers.get('authorization')
        if auth_header:
            token = _extract_bearer_token(auth_header)
    except Exception:
        token = None
    # Fallback to query param
    if not token:
        token = websocket.query_params.get('token')
    # Validate
    try:
        user = jwt.decode(token, _jwt_secret(), algorithms=['HS256']) if token else None
        if not user:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return
    await session_ws.connect(websocket, session_id)
    
    try:
        while True:
            _ = await websocket.receive_text()  # keepalive / ignore client messages
    except WebSocketDisconnect:
        session_ws.disconnect(websocket, session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
