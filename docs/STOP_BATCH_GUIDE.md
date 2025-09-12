# 🛑 Panduan Menghentikan Batch Recording

## 🚨 Masalah: Mic Status Masih Open

Jika setelah tekan ENTER mic masih terlihat open/aktif, berikut cara menghentikannya:

## 🔧 Cara Menghentikan Recording

### 1. Cara Normal (Recommended)
```bash
# Di terminal yang menjalankan batch recording:
# Tekan ENTER untuk stop
```

### 2. Force Stop dengan Ctrl+C
```bash
# Di terminal yang menjalankan batch recording:
# Tekan Ctrl+C untuk force stop
```

### 3. Menggunakan Stop Script (Otomatis)
```bash
# Jalankan script stop otomatis:
scripts/stop_batch.sh
```

### 4. Manual Kill Process
```bash
# Cari proses yang berjalan:
ps aux | grep batch_transcribe

# Kill berdasarkan PID:
kill [PID_NUMBER]

# Atau force kill jika perlu:
kill -9 [PID_NUMBER]
```

## 🔍 Cara Cek Status Mic

### Cek Proses yang Berjalan
```bash
# Cek proses batch recording:
ps aux | grep -E '(batch_transcribe|python.*batch)' | grep -v grep

# Cek proses audio secara umum:
lsof | grep -i audio
```

### Cek Device Audio (macOS)
```bash
# List audio devices:
python3 apps/backend/src/batch_transcribe.py --list-devices

# Atau gunakan system_profiler:
system_profiler SPAudioDataType
```

## 🚀 Solusi Cepat

### One-Liner Stop All
```bash
# Stop semua proses batch sekaligus:
killall -9 python3 2>/dev/null; scripts/stop_batch.sh
```

### Restart Audio System (macOS)
```bash
# Restart audio system jika perlu:
sudo killall coreaudiod
```

## 📋 Troubleshooting Checklist

- ✅ **Cek Terminal**: Pastikan tidak ada proses yang masih berjalan
- ✅ **Cek Activity Monitor**: Lihat proses Python yang menggunakan mic
- ✅ **Restart Terminal**: Buka terminal baru jika perlu
- ✅ **Check Permissions**: System Preferences > Security & Privacy > Microphone
- ✅ **Restart Audio**: `sudo killall coreaudiod` jika perlu

## 🎯 Prevention Tips

### Selalu Gunakan Proper Stop
```bash
# GOOD: Tekan ENTER untuk stop normal
# GOOD: Tekan Ctrl+C untuk force stop
# AVOID: Menutup terminal tanpa stop recording
```

### Monitor Process
```bash
# Selalu cek status sebelum mulai recording baru:
scripts/stop_batch.sh
python3 apps/backend/src/batch_transcribe.py --config configs/hybrid_config_meeting.json
```

## 🔧 Advanced Solutions

### Script Auto-Stop dengan Timeout
```bash
# Jalankan dengan timeout otomatis (5 menit):
timeout 300 python3 apps/backend/src/batch_transcribe.py --config configs/hybrid_config_meeting.json
```

### Background Process Management
```bash
# Jalankan di background dengan control:
python3 apps/backend/src/batch_transcribe.py --config configs/hybrid_config_meeting.json &
BATCH_PID=$!

# Stop kapan saja:
kill $BATCH_PID
```

## 📞 Emergency Stop Commands

```bash
# Emergency stop - jalankan salah satu:
scripts/stop_batch.sh              # Script otomatis
killall python3                    # Kill semua Python
killall -9 batch_transcribe        # Force kill batch
sudo killall coreaudiod            # Restart audio system
```

---

## 🎉 Status Fix

✅ **Threading implementation** - ENTER sekarang bekerja dengan benar  
✅ **Ctrl+C support** - Force stop tersedia  
✅ **Auto stop script** - `scripts/stop_batch.sh` untuk cleanup  
✅ **Process monitoring** - Tools untuk cek status  
✅ **Emergency procedures** - Multiple fallback options  

**Mic status sekarang dapat dikontrol dengan benar!** 🎤
