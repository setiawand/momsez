# Hybrid Transcription Mode

## Overview

Hybrid mode menggabungkan kelebihan **Stream Mode** (real-time) dan **Chunk Mode** (high accuracy) untuk memberikan pengalaman transkripsi terbaik.

### Keunggulan Hybrid Approach

✅ **Real-time Feedback** - Lihat transkripsi langsung saat berbicara  
✅ **High Accuracy** - Hasil akhir dengan akurasi tinggi dari chunk processing  
✅ **Redundancy** - Backup jika salah satu mode gagal  
✅ **Flexibility** - Pilih preset sesuai kebutuhan  

## Quick Start

### 1. Persiapan

```bash
# Pastikan whisper.cpp sudah di-compile
cd whisper.cpp
make
make stream
cd ..

# Install dependencies Python
pip install numpy sounddevice
```

### 2. Penggunaan Mudah dengan Preset

```bash
# Meeting formal (balance speed/accuracy)
./start_hybrid.sh meeting

# Interview (prioritas akurasi tinggi)
./start_hybrid.sh interview

# Presentasi (responsif real-time)
./start_hybrid.sh presentation
```

### 3. Penggunaan Manual

```bash
# Dengan konfigurasi default
python3 apps/backend/src/hybrid_transcribe.py

# Dengan konfigurasi custom
python3 apps/backend/src/hybrid_transcribe.py --config my_config.json

# Dengan output directory custom
python3 apps/backend/src/hybrid_transcribe.py --output-dir ./my_transcripts
```

## Konfigurasi

### File Konfigurasi (JSON)

```json
{
  "output_dir": "output/hybrid",
  "stream_bin": "./whisper.cpp/stream",
  "whisper_bin": "./whisper.cpp/main",
  "stream_model": "./whisper.cpp/models/ggml-small.bin",
  "chunk_model": "./whisper.cpp/models/ggml-medium.bin",
  "language": "id",
  "device_index": 1,
  "chunk_duration": 30,
  "stream_args": "--capture 1 --step 2000 --length 6000 --keep 200 --vad-thold 0.7"
}
```

### Parameter Penting

| Parameter | Deskripsi | Rekomendasi |
|-----------|-----------|-------------|
| `stream_model` | Model untuk real-time | `ggml-small.bin` (cepat) |
| `chunk_model` | Model untuk akurasi | `ggml-medium.bin` atau `ggml-large.bin` |
| `chunk_duration` | Durasi chunk (detik) | 20-45 detik |
| `device_index` | Index audio device | Cek dengan `--list-devices` |
| `vad-thold` | VAD threshold | 0.5-0.8 (sesuai lingkungan) |

## Preset Configurations

### 🏢 Meeting Preset
- **Use Case**: Meeting formal, diskusi tim
- **Karakteristik**: Balance antara speed dan accuracy
- **Model**: Small (stream) + Medium (chunk)
- **Chunk Duration**: 30 detik
- **VAD Threshold**: 0.6

### 🎤 Interview Preset
- **Use Case**: Wawancara, podcast, content penting
- **Karakteristik**: Prioritas akurasi maksimal
- **Model**: Small (stream) + Large (chunk)
- **Chunk Duration**: 45 detik
- **VAD Threshold**: 0.5 (lebih sensitif)

### 📊 Presentation Preset
- **Use Case**: Presentasi, demo, live streaming
- **Karakteristik**: Responsif real-time
- **Model**: Small (stream) + Medium (chunk)
- **Chunk Duration**: 20 detik
- **VAD Threshold**: 0.7

## Output Files

Hybrid mode menghasilkan beberapa file output:

```
output/hybrid/
├── stream_transcript.txt      # Real-time transcript
├── chunk_transcript.txt       # High-accuracy transcript
├── final_transcript.txt       # Merged final result
├── session_report.json        # Session statistics
├── audio_chunks/              # Recorded audio chunks
│   ├── chunk_001.wav
│   ├── chunk_002.wav
│   └── ...
└── logs/
    ├── stream.log            # Stream process logs
    └── chunk.log             # Chunk process logs
```

## Monitoring & Debugging

### Real-time Monitoring

```bash
# Monitor stream output
tail -f output/hybrid/stream_transcript.txt

# Monitor chunk processing
tail -f output/hybrid/logs/chunk.log

# Monitor session statistics
watch -n 5 'cat output/hybrid/session_report.json | jq .'
```

### Common Issues

#### 1. Stream Mode Tidak Mendeteksi Suara
```bash
# Cek audio devices
python3 apps/backend/src/hybrid_transcribe.py --list-devices

# Test dengan VAD threshold lebih rendah
# Edit config: "vad-thold": 0.4
```

#### 2. Chunk Processing Lambat
```bash
# Gunakan model lebih kecil untuk chunk
# Edit config: "chunk_model": "./whisper.cpp/models/ggml-small.bin"

# Kurangi chunk duration
# Edit config: "chunk_duration": 20
```

#### 3. Audio Device Error
```bash
# List semua devices
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# Test dengan device index berbeda
# Edit config: "device_index": 0
```

## Advanced Usage

### Custom Processing Pipeline

```python
# Contoh integrasi dengan aplikasi lain
from hybrid_transcribe import HybridTranscriber

transcriber = HybridTranscriber('my_config.json')
transcriber.start()

# Monitor real-time transcript
while transcriber.is_running():
    latest = transcriber.get_latest_stream_text()
    if latest:
        print(f"Real-time: {latest}")
    time.sleep(1)

# Get final result
final_transcript = transcriber.get_final_transcript()
print(f"Final: {final_transcript}")
```

### Integration dengan Web App

```python
# Flask example
from flask import Flask, jsonify
from hybrid_transcribe import HybridTranscriber

app = Flask(__name__)
transcriber = None

@app.route('/start', methods=['POST'])
def start_transcription():
    global transcriber
    transcriber = HybridTranscriber()
    transcriber.start()
    return jsonify({'status': 'started'})

@app.route('/stream', methods=['GET'])
def get_stream():
    if transcriber:
        return jsonify({
            'text': transcriber.get_latest_stream_text(),
            'timestamp': transcriber.get_last_update()
        })
    return jsonify({'text': '', 'timestamp': None})

@app.route('/stop', methods=['POST'])
def stop_transcription():
    if transcriber:
        final = transcriber.stop_and_get_final()
        return jsonify({'final_transcript': final})
    return jsonify({'final_transcript': ''})
```

## Performance Tips

### 1. Hardware Optimization
- **CPU**: Minimal 4 cores untuk smooth operation
- **RAM**: Minimal 8GB, recommended 16GB
- **Storage**: SSD untuk faster chunk processing

### 2. Model Selection
- **Real-time**: Gunakan `ggml-tiny.bin` atau `ggml-small.bin`
- **Accuracy**: Gunakan `ggml-medium.bin` atau `ggml-large.bin`
- **Balance**: Small (stream) + Medium (chunk)

### 3. Audio Settings
- **Sample Rate**: 16kHz (default whisper)
- **Channels**: Mono (lebih efisien)
- **Bit Depth**: 16-bit

### 4. Environment Tuning
```bash
# Set CPU affinity untuk better performance
taskset -c 0,1 python3 apps/backend/src/hybrid_transcribe.py  # Linux

# Increase process priority
nice -n -10 python3 apps/backend/src/hybrid_transcribe.py

# Set environment variables
export OMP_NUM_THREADS=4
export WHISPER_CPP_THREADS=4
```

## Troubleshooting

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `stream binary not found` | whisper.cpp belum di-compile | `cd whisper.cpp && make stream` |
| `Audio device not available` | Device index salah | `--list-devices` dan update config |
| `Model file not found` | Path model salah | Cek path di config file |
| `Permission denied` | Script tidak executable | `chmod +x start_hybrid.sh` |
| `VAD not detecting` | Threshold terlalu tinggi | Turunkan `vad-thold` ke 0.4-0.6 |

### Performance Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High CPU usage | Model terlalu besar | Gunakan model lebih kecil |
| Delayed transcription | Chunk duration terlalu besar | Kurangi `chunk_duration` |
| Memory leak | Long running session | Restart setiap 2-3 jam |
| Audio dropouts | Buffer underrun | Increase audio buffer size |

## Best Practices

1. **Start Simple**: Mulai dengan preset, lalu customize
2. **Test Audio**: Selalu test audio device sebelum session penting
3. **Monitor Resources**: Watch CPU/memory usage selama transcription
4. **Backup Strategy**: Simpan audio chunks untuk re-processing
5. **Regular Updates**: Update whisper.cpp models secara berkala

## FAQ

**Q: Apakah bisa digunakan untuk bahasa selain Indonesia?**  
A: Ya, edit parameter `language` di config file (en, es, fr, dll.)

**Q: Berapa lama delay real-time transcription?**  
A: Sekitar 2-5 detik tergantung model dan hardware.

**Q: Apakah bisa record multiple speakers?**  
A: Ya, tapi perlu audio device yang support multi-channel.

**Q: Bagaimana cara integrate dengan aplikasi existing?**  
A: Gunakan `HybridTranscriber` class sebagai library atau REST API.

**Q: Apakah support GPU acceleration?**  
A: Tergantung whisper.cpp build. Compile dengan CUDA/OpenCL support.

---

## Support

Untuk pertanyaan atau issue:
1. Cek logs di `output/hybrid/logs/`
2. Test dengan preset berbeda
3. Verify audio device dengan `--list-devices`
4. Check whisper.cpp installation

**Happy Transcribing! 🎙️✨**
