#!/bin/bash

# Batch Transcription Starter Script
# Merekam audio sampai selesai, kemudian memproses transkripsi

echo "=== BATCH TRANSCRIPTION MODE ==="
echo "Mode: Rekam sampai selesai, baru proses transkripsi"
echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "[INFO] Mengaktifkan virtual environment..."
    source .venv/bin/activate
else
    echo "[WARNING] Virtual environment tidak ditemukan"
    echo "[INFO] Menggunakan Python system"
fi

# Check dependencies
echo "[INFO] Memeriksa dependencies..."
python3 -c "import sounddevice, numpy, soundfile" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Dependencies tidak lengkap"
    echo "[INFO] Jalankan: pip install -r requirements.txt"
    exit 1
fi

# Configuration options
echo ""
echo "Pilih konfigurasi:"
echo "1. Meeting (configs/hybrid_config_meeting.json)"
echo "2. Default (configs/hybrid_config.json)"
echo "3. Custom config file"
echo ""
read -p "Pilihan (1-3): " choice

case $choice in
    1)
        CONFIG="hybrid_config_meeting.json"
        echo "[INFO] Menggunakan konfigurasi meeting"
        ;;
    2)
        CONFIG="hybrid_config.json"
        echo "[INFO] Menggunakan konfigurasi default"
        ;;
    3)
        read -p "Masukkan path config file: " CONFIG
        if [ ! -f "$CONFIG" ]; then
            echo "[ERROR] File konfigurasi tidak ditemukan: $CONFIG"
            exit 1
        fi
        ;;
    *)
        CONFIG="hybrid_config_meeting.json"
        echo "[INFO] Menggunakan konfigurasi meeting (default)"
        ;;
esac

# Check if config file exists
if [ ! -f "$CONFIG" ]; then
    echo "[ERROR] File konfigurasi tidak ditemukan: $CONFIG"
    exit 1
fi

echo ""
echo "[INFO] Konfigurasi: $CONFIG"
echo "[INFO] Memulai batch transcription..."
echo ""

# Start batch transcription
python3 src/batch_transcribe.py --config "configs/$CONFIG"

echo ""
echo "[INFO] Batch transcription selesai"