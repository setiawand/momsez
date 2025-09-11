#!/usr/bin/env python3
"""
Test script untuk memverifikasi command whisper.cpp yang sudah diperbaiki
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

def load_config(config_file='configs/hybrid_config_meeting.json'):
    """Load configuration"""
    with open(config_file, 'r') as f:
        return json.load(f)

def test_whisper_command():
    """Test whisper command dengan file audio yang sudah ada"""
    config = load_config()
    
    # Cari file audio yang sudah ada
    recordings_dir = Path('output/batch/recordings')
    audio_files = list(recordings_dir.glob('*.wav'))
    
    if not audio_files:
        print("❌ Tidak ada file audio untuk ditest")
        return False
    
    audio_path = audio_files[0]  # Ambil file pertama
    print(f"🎵 Testing dengan file: {audio_path.name}")
    
    # Prepare output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    transcript_filename = f"test_transcript_{timestamp}.txt"
    transcript_path = Path('output/batch/transcripts') / transcript_filename
    
    # Build command (urutan yang sudah diperbaiki)
    cmd = [
        config['whisper_bin'],
        '-m', config['chunk_model'],
        '-l', config['language'],
        '--output-txt',
        '--no-timestamps',
        '-f', str(audio_path)
    ]
    
    print(f"🔧 Command: {' '.join(cmd)}")
    print("\n🔄 Menjalankan whisper...")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Monitor output
        for line in process.stdout:
            print(f"[WHISPER] {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0:
            print(f"\n✅ WHISPER BERHASIL (exit code: {process.returncode})")
            
            # Whisper.cpp creates output file with same name as input but adds .txt extension
            auto_transcript_path = Path(str(audio_path) + '.txt')
            
            # Move to our desired location
            if auto_transcript_path.exists():
                import shutil
                shutil.move(str(auto_transcript_path), str(transcript_path))
            
            # Check output file
            if transcript_path.exists():
                print(f"✅ File transcript dibuat: {transcript_path}")
                
                # Show content
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    print(f"\n📝 Isi transcript:\n{content}")
                
                return True
            else:
                print(f"❌ File transcript tidak ditemukan: {transcript_path}")
                return False
        else:
            print(f"\n❌ WHISPER GAGAL (exit code: {process.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("=== TEST WHISPER COMMAND ===")
    success = test_whisper_command()
    
    if success:
        print("\n🎉 Test BERHASIL - Command whisper.cpp sudah benar!")
    else:
        print("\n💥 Test GAGAL - Masih ada masalah dengan command")
