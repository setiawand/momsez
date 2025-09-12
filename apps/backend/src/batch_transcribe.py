#!/usr/bin/env python3
"""
Batch Transcription Mode
Merekam audio sampai selesai, kemudian memproses transkripsi sekaligus
"""

import argparse
import json
import os
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import numpy as np


class BatchTranscriber:
    def __init__(self, config, interactive=True):
        self.config = config
        self.interactive = interactive
        self.recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.output_dir = Path(config['output_dir'])
        self.output_dir.mkdir(exist_ok=True)
        self.stop_recording = False
        self.thread = None
        self.last_audio_path: Path | None = None
        
        # Create subdirectories
        (self.output_dir / 'recordings').mkdir(exist_ok=True)
        (self.output_dir / 'transcripts').mkdir(exist_ok=True)
        (self.output_dir / 'logs').mkdir(exist_ok=True)
    
    def audio_callback(self, indata, frames, time, status):
        """Callback untuk merekam audio"""
        if status:
            print(f"[WARNING] Audio status: {status}")
        
        if self.recording:
            self.audio_data.append(indata.copy())
    
    def start_recording(self):
        """Mulai merekam audio"""
        print("\n[BATCH] === BATCH RECORDING MODE ===")
        print(f"[BATCH] Output directory: {self.output_dir}")
        print(f"[BATCH] Language: {self.config['language']}")
        print(f"[BATCH] Device: {self.config.get('device_index', 'default')}")
        
        if self.interactive:
            print("\n[BATCH] Tekan ENTER untuk mulai merekam...")
            input()
        else:
            print("\n[BATCH] Starting recording automatically (API mode)...")
            time.sleep(1)  # Brief pause for setup
        
        self.recording = True
        self.audio_data = []
        self.stop_recording = False
        
        device_index = self.config.get('device_index', None)
        
        print("\n[BATCH] 🔴 RECORDING STARTED")
        print("[BATCH] Berbicara ke mikrofon...")
        
        if self.interactive:
            print("[BATCH] Tekan ENTER untuk berhenti merekam")
            
            # Create a thread to wait for user input
            def wait_for_stop():
                try:
                    # Clear any pending input
                    import sys
                    if sys.stdin.isatty():
                        # Flush input buffer
                        import termios
                        termios.tcflush(sys.stdin, termios.TCIFLUSH)
                    
                    input()
                    self.stop_recording = True
                    print("\n[BATCH] ⏹️  STOP SIGNAL RECEIVED")
                except KeyboardInterrupt:
                    print("\n[BATCH] ⏹️  FORCE STOP (Ctrl+C)")
                    self.stop_recording = True
                except Exception as e:
                    print(f"\n[BATCH] Input error: {e}")
                    self.stop_recording = True
        else:
            print("[BATCH] Recording for 30 seconds (API mode)...")
            
            # Auto-stop after specified duration for API mode
            def auto_stop():
                duration = int(self.config.get('chunk_duration', 30))
                if duration <= 0:
                    duration = 30
                time.sleep(duration)
                self.stop_recording = True
                print(f"\n[BATCH] ⏹️  AUTO STOP ({duration} seconds completed)")
        
        if self.interactive:
            stop_thread = threading.Thread(target=wait_for_stop, daemon=True)
        else:
            stop_thread = threading.Thread(target=auto_stop, daemon=True)
        stop_thread.start()
        
        # Start recording stream
        with sd.InputStream(
            callback=self.audio_callback,
            device=device_index,
            channels=1,
            samplerate=self.sample_rate,
            dtype=np.float32
        ):
            # Wait for stop signal
            while not self.stop_recording:
                time.sleep(0.1)
        
        self.recording = False
        print("[BATCH] ⏹️  RECORDING STOPPED")
        
        if not self.audio_data:
            print("[BATCH] Tidak ada audio yang direkam")
            return None
        
        # Save audio file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"recording_{timestamp}.wav"
        audio_path = self.output_dir / 'recordings' / audio_filename
        
        # Combine audio data
        audio_array = np.concatenate(self.audio_data, axis=0)
        
        # Save to WAV file
        sf.write(str(audio_path), audio_array, self.sample_rate)
        
        duration = len(audio_array) / self.sample_rate
        print(f"[BATCH] Audio disimpan: {audio_path}")
        print(f"[BATCH] Durasi: {duration:.2f} detik")
        
        return audio_path

    def _recording_loop(self):
        """Internal loop for async recording controlled by API start/stop."""
        self.recording = True
        self.audio_data = []
        self.stop_recording = False

        device_index = self.config.get('device_index', None)

        print("\n[BATCH] 🔴 RECORDING STARTED (API-controlled)")
        print(f"[BATCH] Output directory: {self.output_dir}")
        print(f"[BATCH] Language: {self.config['language']}")
        print(f"[BATCH] Device: {self.config.get('device_index', 'default')}")

        try:
            with sd.InputStream(
                callback=self.audio_callback,
                device=device_index,
                channels=1,
                samplerate=self.sample_rate,
                dtype=np.float32
            ):
                while not self.stop_recording:
                    time.sleep(0.1)

        except Exception as e:
            print(f"[BATCH] ❌ Error during recording: {e}")
        finally:
            self.recording = False
            print("[BATCH] ⏹️  RECORDING STOPPED (API)")

        if not self.audio_data:
            print("[BATCH] Tidak ada audio yang direkam")
            self.last_audio_path = None
            return

        # Save audio file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"recording_{timestamp}.wav"
        audio_path = self.output_dir / 'recordings' / audio_filename

        # Combine audio data
        audio_array = np.concatenate(self.audio_data, axis=0)

        # Save to WAV file
        sf.write(str(audio_path), audio_array, self.sample_rate)

        duration = len(audio_array) / self.sample_rate
        print(f"[BATCH] Audio disimpan: {audio_path}")
        print(f"[BATCH] Durasi: {duration:.2f} detik")

        self.last_audio_path = audio_path

    def start_recording_async(self):
        """Start recording in a background thread (API-controlled stop)."""
        if self.thread and self.thread.is_alive():
            print("[BATCH] Recording already running")
            return False
        self.thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.thread.start()
        return True
    
    def transcribe_audio(self, audio_path):
        """Proses transkripsi audio yang sudah direkam"""
        if not audio_path or not audio_path.exists():
            print("[BATCH] File audio tidak ditemukan")
            return None
        
        print("\n[BATCH] 🔄 MEMULAI TRANSKRIPSI...")
        print(f"[BATCH] Memproses: {audio_path.name}")
        
        # Prepare output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_filename = f"transcript_{timestamp}.txt"
        transcript_path = self.output_dir / 'transcripts' / transcript_filename
        log_path = self.output_dir / 'logs' / f"batch_{timestamp}.log"
        
        # Build whisper command
        # Note: whisper.cpp akan otomatis membuat output file dengan nama yang sama seperti input tapi ekstensi .txt
        cmd = [
            self.config['whisper_bin'],
            '-m', self.config['chunk_model'],
            '-l', self.config['language'],
            '--output-txt',
            '--no-timestamps',
            '-f', str(audio_path)
        ]
        
        print(f"[BATCH] Command: {' '.join(cmd)}")
        
        try:
            # Run transcription
            with open(log_path, 'w') as log_file:
                log_file.write(f"=== BATCH TRANSCRIPTION LOG ===\n")
                log_file.write(f"Timestamp: {datetime.now()}\n")
                log_file.write(f"Audio file: {audio_path}\n")
                log_file.write(f"Command: {' '.join(cmd)}\n\n")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Monitor progress
                for line in process.stdout:
                    print(f"[BATCH] {line.strip()}")
                    log_file.write(line)
                    log_file.flush()
                
                process.wait()
                
                if process.returncode == 0:
                    print(f"\n[BATCH] ✅ TRANSKRIPSI SELESAI")
                    
                    # Whisper.cpp creates output file with same name as input but adds .txt extension
                    auto_transcript_path = Path(str(audio_path) + '.txt')
                    
                    # Move to our desired location
                    if auto_transcript_path.exists():
                        import shutil
                        shutil.move(str(auto_transcript_path), str(transcript_path))
                        print(f"[BATCH] Hasil disimpan: {transcript_path}")
                    
                    # Read and display transcript
                    if transcript_path.exists():
                        with open(transcript_path, 'r', encoding='utf-8') as f:
                            transcript_content = f.read().strip()
                        
                        print("\n[BATCH] === HASIL TRANSKRIPSI ===")
                        print(transcript_content)
                        print("[BATCH] ========================\n")
                        
                        return transcript_path
                    else:
                        print(f"[BATCH] ❌ File transcript tidak ditemukan: {transcript_path}")
                        return None
                else:
                    print(f"[BATCH] ❌ Transkripsi gagal dengan exit code: {process.returncode}")
                    return None
                    
        except Exception as e:
            print(f"[BATCH] ❌ Error during transcription: {e}")
            return None
    
    def run(self):
        """Jalankan mode batch recording"""
        try:
            if self.interactive:
                # Interactive mode with loop and prompts
                while True:
                    # Record audio
                    audio_path = self.start_recording()
                    
                    if audio_path:
                        # Transcribe audio
                        transcript_path = self.transcribe_audio(audio_path)
                        
                        if transcript_path:
                            print(f"[BATCH] Transkripsi berhasil: {transcript_path}")
                        else:
                            print("[BATCH] Transkripsi gagal")
                    
                    # Ask if user wants to continue
                    print("\n[BATCH] Apakah ingin merekam lagi? (y/n): ", end="")
                    choice = input().strip().lower()
                    
                    if choice not in ['y', 'yes', 'ya']:
                        break
                
                print("[BATCH] Selesai. Terima kasih!")
            else:
                # API mode - single recording session without prompts
                audio_path = self.start_recording()
                
                if audio_path:
                    transcript_path = self.transcribe_audio(audio_path)
                    
                    if transcript_path:
                        print(f"[BATCH] Transkripsi berhasil: {transcript_path}")
                        return transcript_path
                    else:
                        print("[BATCH] Transkripsi gagal")
                        return None
                else:
                    print("[BATCH] Recording gagal")
                    return None
            
        except KeyboardInterrupt:
            print("\n[BATCH] Dihentikan oleh user")
            return None
        except Exception as e:
            print(f"[BATCH] Error: {e}")
            return None
    
    def run_single_session(self):
        """Jalankan satu sesi recording tanpa prompt (untuk API)"""
        try:
            # Record audio
            audio_path = self.start_recording()
            
            if audio_path:
                # Transcribe audio
                transcript_path = self.transcribe_audio(audio_path)
                
                if transcript_path:
                    print(f"[BATCH] Transkripsi berhasil: {transcript_path}")
                    return transcript_path
                else:
                    print("[BATCH] Transkripsi gagal")
                    return None
            else:
                print("[BATCH] Recording gagal")
                return None
                
        except KeyboardInterrupt:
            print("\n[BATCH] Dihentikan oleh user")
            return None
        except Exception as e:
            print(f"[BATCH] Error: {e}")
            return None
    
    def stop(self):
        """Stop current recording (untuk API)"""
        print("[BATCH] Stop signal received from API")
        self.stop_recording = True
        self.recording = False

    def wait_for_finish(self, timeout: float | None = None):
        """Wait for async recording to finish and return audio path."""
        if self.thread:
            self.thread.join(timeout=timeout)
        return self.last_audio_path


def load_batch_config(config_file='hybrid_config.json'):
    """Load configuration for batch mode"""
    if not os.path.exists(config_file):
        print(f"[ERROR] Configuration file not found: {config_file}")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Normalize output directory for batch mode under unified 'output/'
    # Default to 'output/batch'
    desired = 'output/batch'
    cfg_out = config.get('output_dir')
    if not cfg_out:
        config['output_dir'] = desired
    else:
        # Rebase any legacy paths to the unified output dir
        # e.g., 'hybrid_output_meeting' -> 'output/batch', 'batch_output_meeting' -> 'output/batch'
        legacy = str(cfg_out)
        if 'output/' in legacy:
            # keep as-is under output/
            config['output_dir'] = legacy
        else:
            config['output_dir'] = desired
    
    return config


def main():
    parser = argparse.ArgumentParser(description="Batch Transcription: Record then Process")
    parser.add_argument('--config', default='hybrid_config.json', help='Configuration file')
    parser.add_argument('--output-dir', help='Override output directory')
    parser.add_argument('--list-devices', action='store_true', help='List audio devices and exit')
    
    args = parser.parse_args()
    
    if args.list_devices:
        print("Available audio devices:")
        print(sd.query_devices())
        sys.exit(0)
    
    # Load configuration
    config = load_batch_config(args.config)
    
    # Override output directory if specified
    if args.output_dir:
        config['output_dir'] = args.output_dir
    
    # Validate required files
    required_files = [
        ('whisper_bin', 'Whisper binary'),
        ('chunk_model', 'Chunk model')
    ]
    
    for key, name in required_files:
        path = config[key]
        if not os.path.exists(path):
            print(f"[ERROR] {name} not found: {path}")
            print(f"[INFO] Please update {args.config} with correct paths")
            sys.exit(1)
    
    # Start batch transcription
    transcriber = BatchTranscriber(config)
    transcriber.run()


if __name__ == '__main__':
    main()
