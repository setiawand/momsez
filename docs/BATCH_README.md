# Batch Transcription Mode

Mode transkripsi batch memungkinkan Anda merekam audio sampai selesai, kemudian memproses transkripsi sekaligus. Berbeda dengan mode hybrid yang melakukan transkripsi real-time.

## Fitur Utama

- 🎙️ **Rekam sampai selesai**: Kontrol penuh kapan mulai dan berhenti merekam
- 🔄 **Proses sekaligus**: Transkripsi dilakukan setelah recording selesai
- 📁 **Organisasi file**: Audio dan transcript tersimpan terpisah dengan timestamp
- 🎯 **Akurasi tinggi**: Menggunakan model chunk untuk hasil terbaik
- 🔁 **Multi-session**: Dapat merekam beberapa sesi berturut-turut

## Cara Penggunaan

### 1. Menggunakan Script Otomatis (Recommended)

```bash
./start_batch.sh
```

Script akan memandu Anda memilih konfigurasi dan memulai recording.

### 2. Menggunakan Python Langsung

```bash
# Dengan konfigurasi meeting
python3 apps/backend/src/batch_transcribe.py --config configs/hybrid_config_meeting.json

# Dengan konfigurasi default
python3 apps/backend/src/batch_transcribe.py --config configs/hybrid_config.json

# Dengan output directory custom
python3 apps/backend/src/batch_transcribe.py --config configs/hybrid_config_meeting.json --output-dir output/my_recordings
```

### 3. Melihat Perangkat Audio

```bash
python3 apps/backend/src/batch_transcribe.py --list-devices
```

## Alur Kerja

1. **Persiapan**: Sistem memuat konfigurasi dan menyiapkan direktori output
2. **Mulai Recording**: Tekan ENTER untuk mulai merekam
3. **Recording**: Berbicara ke mikrofon (durasi bebas)
4. **Stop Recording**: Tekan ENTER untuk berhenti merekam
5. **Simpan Audio**: File audio disimpan dalam format WAV
6. **Proses Transkripsi**: Whisper memproses audio yang sudah direkam
7. **Hasil**: Transcript ditampilkan dan disimpan ke file
8. **Repeat**: Pilihan untuk merekam sesi berikutnya

## Struktur Output

```
output/batch/
├── recordings/
│   ├── recording_20250909_143000.wav
│   └── recording_20250909_144500.wav
├── transcripts/
│   ├── transcript_20250909_143000.txt
│   └── transcript_20250909_144500.txt
└── logs/
    ├── batch_20250909_143000.log
    └── batch_20250909_144500.log
```

## Konfigurasi

Mode batch menggunakan konfigurasi yang sama dengan mode hybrid, tetapi hanya memerlukan:

- `whisper_bin`: Path ke binary whisper
- `chunk_model`: Model untuk transkripsi (akurasi tinggi)
- `language`: Bahasa untuk transkripsi
- `device_index`: Index perangkat audio (opsional)
- `output_dir`: Direktori output (akan diubah ke batch_output_*)

## Keunggulan vs Mode Hybrid

| Aspek | Batch Mode | Hybrid Mode |
|-------|------------|-------------|
| **Kontrol Recording** | ✅ Manual start/stop | ❌ Otomatis continuous |
| **Akurasi** | ✅ Tinggi (chunk model) | ⚖️ Balanced (stream + chunk) |
| **Real-time** | ❌ Tidak | ✅ Ya |
| **Resource Usage** | ✅ Rendah saat idle | ❌ Tinggi continuous |
| **File Management** | ✅ Terorganisir per sesi | ⚖️ Continuous files |
| **Use Case** | 📝 Interview, Presentation | 🎤 Meeting, Live monitoring |

## Tips Penggunaan

1. **Persiapan Lingkungan**:
   - Pastikan mikrofon berfungsi dengan baik
   - Pilih lokasi dengan noise minimal
   - Test audio device dengan `--list-devices`

2. **Recording Optimal**:
   - Berbicara dengan jelas dan tidak terlalu cepat
   - Jaga jarak konsisten dengan mikrofon
   - Hindari suara background yang mengganggu

3. **Manajemen File**:
   - File audio dan transcript diberi timestamp otomatis
   - Periksa direktori output untuk hasil lengkap
   - Log file berisi detail proses untuk debugging

## 🔧 Troubleshooting

### Audio Device Issues
```bash
# List available devices
python3 apps/backend/src/batch_transcribe.py --list-devices

# Test with specific device
python3 apps/backend/src/batch_transcribe.py --config configs/config.json --device 1
```

### Recording Stop Issues
**Problem**: Tekan ENTER tidak menghentikan recording

**Solusi yang telah diterapkan**:
- ✅ Threading terpisah untuk input handling
- ✅ Input buffer flushing untuk mencegah konflik
- ✅ Error handling yang lebih robust
- ✅ Stop signal yang lebih reliable

**Jika masih bermasalah**:
```bash
# Test fungsi stop secara terpisah
python3 tests/test_batch_stop.py

# Restart terminal jika input buffer bermasalah
# Atau gunakan Ctrl+C untuk force stop
```

### Permission Issues
```bash
# Make script executable
chmod +x start_batch.sh

# Check microphone permissions on macOS
# System Preferences > Security & Privacy > Microphone
```

### Error: "No module named 'soundfile'"
```bash
pip install soundfile>=0.12.1
```

### Error: "Audio device not found"
```bash
# Lihat perangkat yang tersedia
python3 apps/backend/src/batch_transcribe.py --list-devices

# Update device_index di config file
```

### Error: "Whisper binary not found"
```bash
# Pastikan whisper.cpp sudah di-compile
cd whisper.cpp
make

# Update path di config file
```

### Recording tidak terdengar
- Periksa permission mikrofon di System Preferences
- Test dengan aplikasi lain (Voice Memos, dll)
- Coba device_index yang berbeda

## Dependencies

- `sounddevice>=0.4.6`: Audio recording
- `numpy>=1.22`: Audio processing
- `soundfile>=0.12.1`: Audio file I/O
- `whisper.cpp`: Transcription engine

## Contoh Penggunaan

```bash
# 1. Mulai batch recording
./start_batch.sh

# 2. Pilih konfigurasi (1 untuk meeting)
# 3. Tekan ENTER untuk mulai recording
# 4. Berbicara: "Selamat pagi, ini adalah test recording untuk sistem transkripsi batch"
# 5. Tekan ENTER untuk stop
# 6. Tunggu proses transkripsi selesai
# 7. Lihat hasil di terminal dan file output
```

Mode batch sangat cocok untuk:
- 🎤 **Interview**: Recording terkontrol dengan kualitas tinggi
- 📚 **Lecture**: Rekam presentasi atau kuliah
- 📝 **Dictation**: Dikte dokumen atau catatan
- 🎙️ **Podcast**: Recording episode dengan transkripsi otomatis
