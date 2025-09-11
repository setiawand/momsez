#!/usr/bin/env python3
"""
Test script untuk menguji fungsi stop recording pada batch mode
"""

import time
import threading
import sys
import termios

def test_stop_function():
    """Test fungsi stop dengan threading"""
    stop_recording = False
    
    def wait_for_stop():
        nonlocal stop_recording
        try:
            # Clear any pending input
            if sys.stdin.isatty():
                # Flush input buffer
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            
            print("[TEST] Menunggu input ENTER untuk stop...")
            input()
            stop_recording = True
            print("\n[TEST] ⏹️  STOP SIGNAL RECEIVED")
        except Exception as e:
            print(f"\n[TEST] Input error: {e}")
            stop_recording = True
    
    print("[TEST] === TEST STOP FUNCTION ===")
    print("[TEST] Tekan ENTER untuk mulai test...")
    input()
    
    print("\n[TEST] 🔴 TEST STARTED")
    print("[TEST] Simulasi recording...")
    print("[TEST] Tekan ENTER untuk berhenti")
    
    # Start stop thread
    stop_thread = threading.Thread(target=wait_for_stop, daemon=True)
    stop_thread.start()
    
    # Simulate recording loop
    start_time = time.time()
    while not stop_recording:
        elapsed = time.time() - start_time
        print(f"\r[TEST] Recording... {elapsed:.1f}s", end="", flush=True)
        time.sleep(0.1)
    
    print("\n[TEST] ⏹️  TEST STOPPED")
    print(f"[TEST] Total durasi: {elapsed:.1f} detik")
    print("[TEST] Test selesai!")

if __name__ == '__main__':
    test_stop_function()

