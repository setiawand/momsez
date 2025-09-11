#!/bin/bash

# Script untuk menghentikan batch recording yang masih berjalan

echo "🔍 Mencari proses batch recording..."

# Cari proses batch_transcribe
BATCH_PIDS=$(ps aux | grep -E '(batch_transcribe|python.*batch)' | grep -v grep | awk '{print $2}')

if [ -z "$BATCH_PIDS" ]; then
    echo "✅ Tidak ada proses batch recording yang berjalan"
    exit 0
fi

echo "📋 Proses yang ditemukan:"
ps aux | grep -E '(batch_transcribe|python.*batch)' | grep -v grep

echo ""
echo "⏹️  Menghentikan proses batch recording..."

for PID in $BATCH_PIDS; do
    echo "Stopping PID: $PID"
    kill $PID
    sleep 1
    
    # Check if process still running
    if kill -0 $PID 2>/dev/null; then
        echo "Force killing PID: $PID"
        kill -9 $PID
    fi
done

echo "✅ Semua proses batch recording telah dihentikan"
echo ""
echo "💡 Tips:"
echo "   - Gunakan ENTER untuk stop normal"
echo "   - Gunakan Ctrl+C untuk force stop"
echo "   - Jalankan script ini jika proses masih berjalan"