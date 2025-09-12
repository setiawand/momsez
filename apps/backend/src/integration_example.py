#!/usr/bin/env python3
"""
Contoh Integrasi Hybrid Transcription dengan Aplikasi Existing

Script ini menunjukkan bagaimana mengintegrasikan hybrid transcription
ke dalam aplikasi yang sudah ada.
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
from hybrid_transcribe import HybridTranscriber

class TranscriptionService:
    """
    Service wrapper untuk hybrid transcription yang dapat diintegrasikan
    ke aplikasi existing.
    """
    
    def __init__(self, config_path="hybrid_config.json"):
        self.config_path = config_path
        self.transcriber = None
        self.is_active = False
        self.callbacks = {
            'on_stream_update': [],
            'on_chunk_complete': [],
            'on_session_complete': [],
            'on_error': []
        }
        
    def add_callback(self, event_type, callback_func):
        """
        Tambahkan callback untuk event tertentu.
        
        Args:
            event_type: 'on_stream_update', 'on_chunk_complete', 
                       'on_session_complete', 'on_error'
            callback_func: Function yang akan dipanggil
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback_func)
    
    def start_transcription(self, session_name=None):
        """
        Mulai sesi transkripsi.
        
        Args:
            session_name: Nama sesi (optional)
        
        Returns:
            dict: Status dan informasi sesi
        """
        try:
            if self.is_active:
                return {
                    'success': False,
                    'message': 'Transcription already active'
                }
            
            # Load config
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Update output directory dengan session name
            if session_name:
                base_dir = Path(config['output_dir'])
                config['output_dir'] = str(base_dir / session_name)
                # Ensure parent directory exists
                Path(config['output_dir']).parent.mkdir(parents=True, exist_ok=True)
            
            # Start transcriber
            self.transcriber = HybridTranscriber(config)
            self.transcriber.start()
            self.is_active = True
            
            # Start monitoring thread
            self._start_monitoring()
            
            return {
                'success': True,
                'message': 'Transcription started',
                'session_id': self.transcriber.session_id,
                'output_dir': config['output_dir']
            }
            
        except Exception as e:
            self._trigger_callbacks('on_error', {'error': str(e)})
            return {
                'success': False,
                'message': f'Failed to start: {str(e)}'
            }
    
    def stop_transcription(self):
        """
        Hentikan sesi transkripsi.
        
        Returns:
            dict: Status dan hasil akhir
        """
        try:
            if not self.is_active or not self.transcriber:
                return {
                    'success': False,
                    'message': 'No active transcription'
                }
            
            # Stop transcriber
            final_result = self.transcriber.stop_and_get_final()
            self.is_active = False
            
            # Trigger completion callback
            self._trigger_callbacks('on_session_complete', {
                'final_transcript': final_result['final_transcript'],
                'session_report': final_result['session_report']
            })
            
            return {
                'success': True,
                'message': 'Transcription stopped',
                'final_transcript': final_result['final_transcript'],
                'session_report': final_result['session_report']
            }
            
        except Exception as e:
            self._trigger_callbacks('on_error', {'error': str(e)})
            return {
                'success': False,
                'message': f'Failed to stop: {str(e)}'
            }
    
    def get_current_status(self):
        """
        Dapatkan status transkripsi saat ini.
        
        Returns:
            dict: Status dan informasi real-time
        """
        if not self.is_active or not self.transcriber:
            return {
                'active': False,
                'stream_text': '',
                'last_update': None
            }
        
        return {
            'active': True,
            'stream_text': self.transcriber.get_latest_stream_text(),
            'last_update': self.transcriber.get_last_update(),
            'session_id': self.transcriber.session_id
        }
    
    def _start_monitoring(self):
        """
        Mulai thread monitoring untuk callback real-time.
        """
        def monitor():
            last_stream_text = ""
            last_chunk_count = 0
            
            while self.is_active and self.transcriber:
                try:
                    # Check stream updates
                    current_stream = self.transcriber.get_latest_stream_text()
                    if current_stream != last_stream_text:
                        self._trigger_callbacks('on_stream_update', {
                            'text': current_stream,
                            'timestamp': datetime.now().isoformat()
                        })
                        last_stream_text = current_stream
                    
                    # Check chunk completion
                    current_chunks = self.transcriber.get_completed_chunks_count()
                    if current_chunks > last_chunk_count:
                        self._trigger_callbacks('on_chunk_complete', {
                            'chunk_number': current_chunks,
                            'timestamp': datetime.now().isoformat()
                        })
                        last_chunk_count = current_chunks
                    
                    time.sleep(1)  # Check every second
                    
                except Exception as e:
                    self._trigger_callbacks('on_error', {'error': str(e)})
                    break
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _trigger_callbacks(self, event_type, data):
        """
        Trigger semua callback untuk event tertentu.
        """
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Callback error for {event_type}: {e}")


# Contoh penggunaan dalam aplikasi
class MeetingApp:
    """
    Contoh aplikasi meeting yang menggunakan TranscriptionService.
    """
    
    def __init__(self):
        self.transcription = TranscriptionService()
        self.setup_callbacks()
        self.meeting_notes = []
    
    def setup_callbacks(self):
        """
        Setup callback untuk menangani event transkripsi.
        """
        # Real-time stream updates
        self.transcription.add_callback('on_stream_update', self.on_stream_update)
        
        # Chunk completion
        self.transcription.add_callback('on_chunk_complete', self.on_chunk_complete)
        
        # Session completion
        self.transcription.add_callback('on_session_complete', self.on_session_complete)
        
        # Error handling
        self.transcription.add_callback('on_error', self.on_error)
    
    def on_stream_update(self, data):
        """
        Handle real-time transcript updates.
        """
        print(f"[LIVE] {data['text']}")
        
        # Bisa integrate dengan UI real-time
        # self.update_live_transcript_ui(data['text'])
    
    def on_chunk_complete(self, data):
        """
        Handle chunk completion.
        """
        print(f"[CHUNK {data['chunk_number']}] Completed at {data['timestamp']}")
        
        # Bisa trigger auto-save atau processing
        # self.auto_save_progress()
    
    def on_session_complete(self, data):
        """
        Handle session completion.
        """
        print("[SESSION] Transcription completed!")
        print(f"Final transcript: {data['final_transcript'][:100]}...")
        
        # Save to meeting notes
        self.meeting_notes.append({
            'timestamp': datetime.now().isoformat(),
            'transcript': data['final_transcript'],
            'report': data['session_report']
        })
        
        # Bisa trigger post-processing
        # self.generate_meeting_summary(data['final_transcript'])
        # self.send_email_summary()
    
    def on_error(self, data):
        """
        Handle transcription errors.
        """
        print(f"[ERROR] {data['error']}")
        
        # Bisa implement retry logic atau fallback
        # self.handle_transcription_error(data['error'])
    
    def start_meeting(self, meeting_name):
        """
        Mulai meeting dengan transkripsi.
        """
        print(f"Starting meeting: {meeting_name}")
        
        result = self.transcription.start_transcription(meeting_name)
        if result['success']:
            print(f"Transcription started. Output: {result['output_dir']}")
            return True
        else:
            print(f"Failed to start transcription: {result['message']}")
            return False
    
    def end_meeting(self):
        """
        Akhiri meeting dan dapatkan hasil.
        """
        print("Ending meeting...")
        
        result = self.transcription.stop_transcription()
        if result['success']:
            print("Meeting ended successfully!")
            return result
        else:
            print(f"Failed to end meeting: {result['message']}")
            return None
    
    def get_live_status(self):
        """
        Dapatkan status live meeting.
        """
        return self.transcription.get_current_status()


# Contoh penggunaan
if __name__ == "__main__":
    # Inisialisasi aplikasi
    app = MeetingApp()
    
    print("=== Meeting App with Hybrid Transcription ===")
    print("Commands: start <name>, status, stop, quit")
    
    while True:
        try:
            command = input("\n> ").strip().split()
            
            if not command:
                continue
            
            if command[0] == "start":
                meeting_name = command[1] if len(command) > 1 else "default_meeting"
                app.start_meeting(meeting_name)
            
            elif command[0] == "status":
                status = app.get_live_status()
                if status['active']:
                    print(f"Active session: {status['session_id']}")
                    print(f"Last update: {status['last_update']}")
                    print(f"Current text: {status['stream_text'][:100]}...")
                else:
                    print("No active transcription")
            
            elif command[0] == "stop":
                result = app.end_meeting()
                if result:
                    print(f"\nFinal transcript saved!")
                    print(f"Session report: {result['session_report']}")
            
            elif command[0] == "quit":
                # Stop transcription if active
                if app.get_live_status()['active']:
                    app.end_meeting()
                print("Goodbye!")
                break
            
            else:
                print("Unknown command. Use: start <name>, status, stop, quit")
        
        except KeyboardInterrupt:
            print("\nStopping...")
            if app.get_live_status()['active']:
                app.end_meeting()
            break
        except Exception as e:
            print(f"Error: {e}")
