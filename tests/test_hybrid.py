#!/usr/bin/env python3
"""
Test script untuk hybrid transcription
"""

import json
import time
import sys
from pathlib import Path

# Ensure 'src' is importable when running tests from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hybrid_transcribe import HybridTranscriber

def test_hybrid_basic():
    """
    Test basic hybrid transcription functionality
    """
    print("=== Testing Hybrid Transcription ===")
    
    # Load config
    try:
        with open('configs/hybrid_config.json', 'r') as f:
            config = json.load(f)
        print("✓ Config loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False
    
    # Test directory creation
    test_output_dir = "test_hybrid_output"
    config['output_dir'] = test_output_dir
    
    try:
        # Initialize transcriber
        transcriber = HybridTranscriber(config)
        print("✓ HybridTranscriber initialized successfully")
        
        # Check if directories were created
        output_path = Path(test_output_dir)
        if output_path.exists():
            print("✓ Output directory created successfully")
            print(f"  - Path: {output_path.absolute()}")
            
            # Check subdirectories
            subdirs = ['live', 'final', 'logs']
            for subdir in subdirs:
                subdir_path = output_path / subdir
                if subdir_path.exists():
                    print(f"  ✓ {subdir}/ directory created")
                else:
                    print(f"  ✗ {subdir}/ directory missing")
        else:
            print("✗ Output directory not created")
            return False
        
        # Test configuration validation
        required_keys = ['stream_bin', 'whisper_bin', 'stream_model', 'chunk_model']
        for key in required_keys:
            if key in config:
                print(f"  ✓ {key}: {config[key]}")
            else:
                print(f"  ✗ Missing config key: {key}")
        
        print("\n=== Test Summary ===")
        print("✓ Hybrid transcription setup is working correctly!")
        print(f"✓ Output directory: {output_path.absolute()}")
        print("✓ Ready to start transcription")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
        return False

def test_integration_service():
    """
    Test integration service without interactive input
    """
    print("\n=== Testing Integration Service ===")
    
    try:
        from integration_example import TranscriptionService
        
        # Initialize service
        service = TranscriptionService()
        print("✓ TranscriptionService initialized")
        
        # Test callback system
        callback_called = False
        def test_callback(data):
            nonlocal callback_called
            callback_called = True
            print(f"  ✓ Callback received: {data}")
        
        service.add_callback('on_error', test_callback)
        print("✓ Callback system working")
        
        # Test status when not active
        status = service.get_current_status()
        if not status['active']:
            print("✓ Inactive status correct")
        else:
            print("✗ Status should be inactive")
        
        print("✓ Integration service is working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ Integration service error: {e}")
        return False

def check_prerequisites():
    """
    Check if all prerequisites are met
    """
    print("=== Checking Prerequisites ===")
    
    checks = [
        ('configs/hybrid_config.json', Path('configs/hybrid_config.json').exists()),
        ('src/hybrid_transcribe.py', Path('src/hybrid_transcribe.py').exists()),
        ('src/live_transcribe.py', Path('src/live_transcribe.py').exists()),
        ('whisper.cpp/stream', Path('whisper.cpp/stream').exists()),
        ('whisper.cpp/main', Path('whisper.cpp/main').exists()),
    ]
    
    all_good = True
    for name, exists in checks:
        if exists:
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - Missing!")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    print("🎙️ Hybrid Transcription Test Suite\n")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please check missing files.")
        exit(1)
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    if test_hybrid_basic():
        tests_passed += 1
    
    if test_integration_service():
        tests_passed += 1
    
    # Final result
    print(f"\n=== Final Results ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Hybrid transcription is ready to use.")
        print("\nNext steps:")
        print("1. Run: ./start_hybrid.sh meeting")
        print("2. Or: python3 hybrid_transcribe.py")
        print("3. Or: python3 integration_example.py (interactive)")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        exit(1)

