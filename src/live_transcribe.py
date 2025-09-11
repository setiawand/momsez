#!/usr/bin/env python3
import argparse
import json
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime

import numpy as np
import sounddevice as sd


def list_devices_and_exit():
    print(sd.query_devices())
    sys.exit(0)


def record_chunk(seconds: float, sample_rate: int, device_index: int | None) -> np.ndarray:
    channels = 1
    dtype = 'int16'
    frames = int(seconds * sample_rate)
    recording = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype=dtype, device=device_index)
    sd.wait()
    return recording.reshape(-1)


def write_wav_int16(path: str, audio: np.ndarray, sample_rate: int):
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


def run_whisper(whisper_bin: str, model: str, wav_path: str, language: str, threads: int) -> tuple[int, str, str]:
    # Use whisper.cpp main binary to generate .txt output; capture stdout for logging
    # Note: newer whisper.cpp does not support '-of'; it writes '<wav_path>.txt' by default.
    cmd = [
        whisper_bin,
        "-m", model,
        "-f", wav_path,
        "-otxt",
        "-l", language,
        "-t", str(threads),
        "-nt",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    txt_path = f"{wav_path}.txt"
    text = ""
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
        except Exception:
            text = ""
    return proc.returncode, proc.stdout, text


def append_transcript(output_path: str, chunk_index: int, chunk_start: float, chunk_end: float, text: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = f"\n--- chunk #{chunk_index} [{chunk_start:.1f}s - {chunk_end:.1f}s] @ {ts} ---\n"
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(header)
        f.write(text)
        f.write("\n")


def parse_args():
    p = argparse.ArgumentParser(description="Live meeting transcription using Python + whisper.cpp")
    p.add_argument('--mode', choices=['chunks', 'stream'], default='chunks', help='chunks: record in segments; stream: use whisper.cpp stream binary')
    p.add_argument('--whisper-bin', help='Path to whisper.cpp main binary (for chunks mode)')
    p.add_argument('--stream-bin', help='Path to whisper.cpp stream binary (for stream mode)')
    p.add_argument('--stream-args', default='', help='Extra args string passed to stream binary')
    p.add_argument('--model', help='Path to model (GGML/GGUF)')
    p.add_argument('--language', default='auto', help='Language code (e.g., auto, en, id)')
    p.add_argument('--chunk-sec', type=float, default=15.0, help='Seconds per recorded chunk')
    p.add_argument('--sample-rate', type=int, default=16000, help='Recording sample rate')
    p.add_argument('--device-index', type=int, default=None, help='Input device index (see --list-devices)')
    p.add_argument('--threads', type=int, default=max(1, os.cpu_count() or 1), help='Threads for whisper.cpp (-t)')
    p.add_argument('--output', default='output/transcript.txt', help='Output transcript file (appends)')
    p.add_argument('--list-devices', action='store_true', help='List input/output devices and exit')
    p.add_argument('--print-levels', action='store_true', help='Print RMS/peak levels per chunk (debug)')
    p.add_argument('--min-rms', type=float, default=0.0, help='Skip transcription for chunks with RMS below this threshold')
    return p.parse_args()


def load_config(path: str = 'config.json') -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def resolve_device_index(cli_value: int | None) -> int | None:
    if cli_value is not None:
        return cli_value
    env_val = os.getenv('MOM_DEVICE_INDEX')
    if env_val is not None and env_val != '':
        try:
            return int(env_val)
        except Exception:
            pass
    cfg = load_config()
    if isinstance(cfg.get('device_index'), int):
        return cfg['device_index']
    return None


def main():
    args = parse_args()
    if args.list_devices:
        list_devices_and_exit()

    if not args.model:
        print("--model is required unless using --list-devices", file=sys.stderr)
        sys.exit(2)
    model = os.path.abspath(args.model)
    if not os.path.exists(model):
        print(f"model not found: {model}", file=sys.stderr)
        sys.exit(1)

    if args.mode == 'stream':
        if not args.stream_bin:
            print("--stream-bin is required in stream mode", file=sys.stderr)
            sys.exit(1)
        stream_bin = os.path.abspath(args.stream_bin)
        if not os.path.exists(stream_bin):
            print(f"stream bin not found: {stream_bin}", file=sys.stderr)
            sys.exit(1)
        if not os.access(stream_bin, os.X_OK):
            print(f"stream bin is not executable: {stream_bin}", file=sys.stderr)
            sys.exit(1)

        # Try to display current OS default input device name for reference
        try:
            default_in = sd.query_devices(None, 'input')
            default_in_name = default_in.get('name', 'Unknown')
        except Exception:
            default_in_name = 'Unknown'

        print("Starting streaming transcription via whisper.cpp stream...")
        print(f"- Model: {model}")
        print(f"- Stream: {stream_bin}")
        print(f"- Language: {args.language}")
        print(f"- Output: {args.output}")
        print(f"- Input device (OS default): {default_in_name}")
        print("Press Ctrl+C to stop.\n")

        # Build command; pass common flags, and any user-provided extras for device selection, etc.
        cmd = [stream_bin, '-m', model, '-t', str(args.threads)]
        if args.language and args.language != 'auto':
            cmd.extend(['-l', args.language])
        extra = shlex.split(args.stream_args) if args.stream_args else []
        cmd.extend(extra)

        with open(args.output, 'a', encoding='utf-8') as fout:
            session_header = f"\n=== stream session started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            fout.write(session_header)
            fout.flush()

            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
                assert proc.stdout is not None
                for line in proc.stdout:
                    line = line.rstrip('\n')
                    if not line:
                        continue
                    print(line)
                    fout.write(line + '\n')
                    fout.flush()
            except KeyboardInterrupt:
                print("\nStopping stream...")
                try:
                    proc.terminate()
                except Exception:
                    pass
            finally:
                try:
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                print("Transcript saved to:", args.output)
    else:
        # chunks mode (default): record locally and invoke whisper.cpp main per chunk
        if not args.whisper_bin:
            print("--whisper-bin is required in chunks mode", file=sys.stderr)
            sys.exit(1)
        whisper_bin = os.path.abspath(args.whisper_bin)
        if not os.path.exists(whisper_bin):
            print(f"whisper bin not found: {whisper_bin}", file=sys.stderr)
            sys.exit(1)
        if not os.access(whisper_bin, os.X_OK):
            print(f"whisper bin is not executable: {whisper_bin}", file=sys.stderr)
            sys.exit(1)

        device_index = resolve_device_index(args.device_index)

        # Resolve and show input device name
        device_name = 'Unknown'
        try:
            if device_index is not None:
                device_name = sd.query_devices(device_index).get('name', 'Unknown')
            else:
                device_name = sd.query_devices(None, 'input').get('name', 'Unknown')
        except Exception:
            pass

        print("Starting live transcription (chunked)...")
        print(f"- Model: {model}")
        print(f"- Whisper: {whisper_bin}")
        print(f"- Language: {args.language}")
        print(f"- Chunk: {args.chunk_sec}s at {args.sample_rate} Hz")
        print(f"- Output: {args.output}")
        if device_index is not None:
            print(f"- Input device: {device_name} (index {device_index})")
        else:
            print(f"- Input device: {device_name} (default)")
        print("Press Ctrl+C to stop.\n")

        os.makedirs('output/.transient', exist_ok=True)
        total_elapsed = 0.0
        chunk_index = 0

        try:
            while True:
                chunk_index += 1
                t0 = time.time()
                audio = record_chunk(args.chunk_sec, args.sample_rate, device_index)
                t1 = time.time()
                elapsed = t1 - t0
                total_elapsed += elapsed
                # compute RMS and peak
                a = audio.astype(np.float32)
                rms = float(np.sqrt(np.mean(a*a)))
                peak = int(np.max(np.abs(audio)))
                if args.print_levels:
                    print(f"[chunk {chunk_index}] levels: RMS={rms:.1f}, peak={peak}")

                # simple VAD-like gating: skip low-RMS chunks
                if args.min_rms > 0.0 and rms < args.min_rms:
                    print(f"[chunk {chunk_index} {total_elapsed - elapsed:.1f}s-{total_elapsed:.1f}s] (skipped: low level, RMS={rms:.1f} < {args.min_rms})")
                    continue
                wav_path = os.path.join('output/.transient', f'chunk_{chunk_index:06d}.wav')
                write_wav_int16(wav_path, audio, args.sample_rate)

                rc, log, text = run_whisper(
                    whisper_bin=whisper_bin,
                    model=model,
                    wav_path=wav_path,
                    language=args.language,
                    threads=args.threads,
                )

                chunk_start = total_elapsed - elapsed
                chunk_end = total_elapsed

                if rc != 0:
                    print(f"[chunk {chunk_index}] whisper.cpp exited with code {rc}")
                    print(log)
                else:
                    print(f"\n[chunk {chunk_index} {chunk_start:.1f}s-{chunk_end:.1f}s]")
                    if text:
                        print(text)
                        append_transcript(args.output, chunk_index, chunk_start, chunk_end, text)
                    else:
                        print("(no text output)")

        except KeyboardInterrupt:
            print("\nStopping. Transcript saved to:", args.output)


if __name__ == '__main__':
    main()
