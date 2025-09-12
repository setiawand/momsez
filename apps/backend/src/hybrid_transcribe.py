#!/usr/bin/env python3
"""
Hybrid Transcription Mode
Menggabungkan mode stream (real-time) dan chunk (high accuracy) secara bersamaan
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


class HybridTranscriber:
    def __init__(self, config):
        self.config = config
        self.stream_process = None
        self.chunk_process = None
        self.running = False
        self.output_dir = Path(config['output_dir'])
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / 'live').mkdir(exist_ok=True)
        (self.output_dir / 'final').mkdir(exist_ok=True)
        (self.output_dir / 'logs').mkdir(exist_ok=True)
    
    def start_stream_mode(self):
        """Start real-time stream transcription"""
        print("[HYBRID] Starting stream mode for real-time monitoring...")
        
        stream_output = self.output_dir / 'live' / 'transcript.txt'
        log_file = self.output_dir / 'logs' / 'stream.log'
        
        cmd = [
            'python', 'src/live_transcribe.py',
            '--mode', 'stream',
            '--stream-bin', self.config['stream_bin'],
            '--model', self.config['stream_model'],
            '--language', self.config['language'],
            '--output', str(stream_output),
            '--stream-args', self.config['stream_args']
        ]
        
        try:
            with open(log_file, 'w') as log:
                self.stream_process = subprocess.Popen(
                    cmd, 
                    stdout=log, 
                    stderr=subprocess.STDOUT,
                    text=True
                )
            print(f"[STREAM] Started with PID: {self.stream_process.pid}")
            print(f"[STREAM] Output: {stream_output}")
            print(f"[STREAM] Log: {log_file}")
        except Exception as e:
            print(f"[ERROR] Failed to start stream mode: {e}")
    
    def start_chunk_mode(self):
        """Start high-accuracy chunk transcription"""
        print("[HYBRID] Starting chunk mode for high accuracy...")
        
        chunk_output = self.output_dir / 'final' / 'transcript.txt'
        log_file = self.output_dir / 'logs' / 'chunk.log'
        
        cmd = [
            'python', 'src/live_transcribe.py',
            '--mode', 'chunks',
            '--whisper-bin', self.config['whisper_bin'],
            '--model', self.config['chunk_model'],
            '--language', self.config['language'],
            '--output', str(chunk_output),
            '--chunk-sec', str(self.config['chunk_duration'])
        ]
        # Add device-index only when explicitly provided (including index 0)
        if 'device_index' in self.config and self.config['device_index'] is not None:
            cmd.extend(['--device-index', str(self.config['device_index'])])
        
        try:
            with open(log_file, 'w') as log:
                self.chunk_process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            print(f"[CHUNK] Started with PID: {self.chunk_process.pid}")
            print(f"[CHUNK] Output: {chunk_output}")
            print(f"[CHUNK] Log: {log_file}")
        except Exception as e:
            print(f"[ERROR] Failed to start chunk mode: {e}")
    
    def monitor_processes(self):
        """Monitor both processes and handle failures"""
        while self.running:
            time.sleep(5)
            
            # Check stream process
            if self.stream_process and self.stream_process.poll() is not None:
                print(f"[WARNING] Stream process ended with code: {self.stream_process.returncode}")
                if self.running:  # Restart if still supposed to be running
                    print("[HYBRID] Restarting stream mode...")
                    time.sleep(2)
                    self.start_stream_mode()
            
            # Check chunk process
            if self.chunk_process and self.chunk_process.poll() is not None:
                print(f"[WARNING] Chunk process ended with code: {self.chunk_process.returncode}")
                if self.running:  # Restart if still supposed to be running
                    print("[HYBRID] Restarting chunk mode...")
                    time.sleep(2)
                    self.start_chunk_mode()
    
    def start(self):
        """Start hybrid transcription"""
        print("\n=== HYBRID TRANSCRIPTION STARTED ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output Directory: {self.output_dir}")
        print("\nStarting both modes...\n")
        
        self.running = True
        
        # Start both modes
        self.start_stream_mode()
        time.sleep(2)  # Small delay between starts
        self.start_chunk_mode()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        
        print("\n[HYBRID] Both modes started successfully!")
        print("[INFO] Press Ctrl+C to stop gracefully")
        print("\n--- REAL-TIME MONITORING ---")
        
        # Monitor live transcript
        self.monitor_live_output()
    
    def monitor_live_output(self):
        """Monitor and display live transcript updates"""
        live_file = self.output_dir / 'live' / 'transcript.txt'
        last_size = 0
        
        try:
            while self.running:
                if live_file.exists():
                    current_size = live_file.stat().st_size
                    if current_size > last_size:
                        # Read new content
                        with open(live_file, 'r', encoding='utf-8') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            if new_content.strip():
                                print(f"[LIVE] {new_content.strip()}")
                        last_size = current_size
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop hybrid transcription gracefully"""
        print("\n\n[HYBRID] Stopping transcription...")
        self.running = False
        
        # Stop stream process
        if self.stream_process:
            try:
                self.stream_process.terminate()
                self.stream_process.wait(timeout=5)
                print("[STREAM] Stopped gracefully")
            except subprocess.TimeoutExpired:
                self.stream_process.kill()
                print("[STREAM] Force killed")
            except Exception as e:
                print(f"[STREAM] Error stopping: {e}")
        
        # Stop chunk process
        if self.chunk_process:
            try:
                self.chunk_process.terminate()
                self.chunk_process.wait(timeout=5)
                print("[CHUNK] Stopped gracefully")
            except subprocess.TimeoutExpired:
                self.chunk_process.kill()
                print("[CHUNK] Force killed")
            except Exception as e:
                print(f"[CHUNK] Error stopping: {e}")
        
        # Generate final report
        self.generate_report()
        
        print(f"\n[HYBRID] Transcription completed!")
        print(f"[INFO] Check outputs in: {self.output_dir}")
    
    def generate_report(self):
        """Generate combined report from both modes"""
        print("[HYBRID] Generating final report...")
        
        report_file = self.output_dir / f"hybrid_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        live_file = self.output_dir / 'live' / 'transcript.txt'
        final_file = self.output_dir / 'final' / 'transcript.txt'
        
        try:
            with open(report_file, 'w', encoding='utf-8') as report:
                report.write("=== HYBRID TRANSCRIPTION REPORT ===\n")
                report.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Live transcript section
                if live_file.exists():
                    report.write("--- REAL-TIME TRANSCRIPT (Stream Mode) ---\n")
                    report.write("Purpose: Live monitoring and immediate feedback\n")
                    report.write("Accuracy: ~85-90%\n\n")
                    
                    with open(live_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            report.write(content)
                        else:
                            report.write("(No content generated)")
                    report.write("\n\n")
                
                # Final transcript section
                if final_file.exists():
                    report.write("--- HIGH-ACCURACY TRANSCRIPT (Chunk Mode) ---\n")
                    report.write("Purpose: Final documentation and archival\n")
                    report.write("Accuracy: ~92-97%\n\n")
                    
                    with open(final_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            report.write(content)
                        else:
                            report.write("(No content generated)")
                    report.write("\n\n")
                
                # Statistics
                report.write("--- STATISTICS ---\n")
                live_words = len(live_file.read_text(encoding='utf-8').split()) if live_file.exists() else 0
                final_words = len(final_file.read_text(encoding='utf-8').split()) if final_file.exists() else 0
                
                report.write(f"Live transcript words: {live_words}\n")
                report.write(f"Final transcript words: {final_words}\n")
                report.write(f"Word difference: {abs(final_words - live_words)}\n")
                
            print(f"[REPORT] Generated: {report_file}")
        
        except Exception as e:
            print(f"[ERROR] Failed to generate report: {e}")


def load_hybrid_config(config_file='hybrid_config.json'):
    """Load hybrid configuration"""
    default_config = {
        'output_dir': 'output/hybrid',
        'stream_bin': './whisper.cpp/stream',
        'whisper_bin': './whisper.cpp/main',
        'stream_model': './whisper.cpp/models/ggml-small.bin',
        'chunk_model': './whisper.cpp/models/ggml-medium.bin',
        'language': 'id',
        'device_index': 1,
        'chunk_duration': 30,
        'stream_args': '--capture 1 --step 2000 --length 6000 --keep 200 --vad-thold 0.7'
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                print(f"[CONFIG] Loaded from {config_file}")
        except Exception as e:
            print(f"[WARNING] Failed to load {config_file}: {e}")
            print("[CONFIG] Using default configuration")
    else:
        # Create default config file
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            print(f"[CONFIG] Created default config: {config_file}")
        except Exception as e:
            print(f"[WARNING] Failed to create config file: {e}")
    
    return default_config


def main():
    parser = argparse.ArgumentParser(description="Hybrid Transcription: Stream + Chunk modes")
    parser.add_argument('--config', default='hybrid_config.json', help='Configuration file')
    parser.add_argument('--output-dir', help='Override output directory')
    parser.add_argument('--list-devices', action='store_true', help='List audio devices and exit')
    
    args = parser.parse_args()
    
    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        sys.exit(0)
    
    # Load configuration
    config = load_hybrid_config(args.config)
    
    # Override output directory if specified
    if args.output_dir:
        config['output_dir'] = args.output_dir
    
    # Validate required files
    required_files = [
        ('stream_bin', 'Stream binary'),
        ('whisper_bin', 'Whisper binary'),
        ('stream_model', 'Stream model'),
        ('chunk_model', 'Chunk model')
    ]
    
    for key, name in required_files:
        path = config[key]
        if not os.path.exists(path):
            print(f"[ERROR] {name} not found: {path}")
            print(f"[INFO] Please update {args.config} with correct paths")
            sys.exit(1)
    
    # Start hybrid transcription
    transcriber = HybridTranscriber(config)
    
    try:
        transcriber.start()
    except KeyboardInterrupt:
        transcriber.stop()
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        transcriber.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
