# Docker Guide - Mom Transcript

Panduan lengkap untuk menjalankan Mom Transcript menggunakan Docker.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Audio device yang dapat diakses oleh Docker
- Minimal 4GB RAM
- Minimal 2GB disk space

## 🚀 Quick Start

### 1. Build Image

```bash
# Build Docker image
make build

# Atau manual
docker-compose build
```

### 2. Jalankan Aplikasi

```bash
# Batch Transcription Mode
make run-batch

# Hybrid Transcription Mode
make run-hybrid

# Live Transcription Mode
make run-live

# Development Mode
make dev
```

## 🏗️ Struktur Project

```
mom-transcript/
├── src/                    # Source code Python
│   ├── batch_transcribe.py
│   ├── hybrid_transcribe.py
│   └── live_transcribe.py
├── configs/               # File konfigurasi
│   ├── config.json
│   ├── hybrid_config.json
│   └── hybrid_config_meeting.json
├── scripts/               # Shell scripts
│   ├── start_batch.sh
│   ├── start_hybrid.sh
│   └── stop_batch.sh
├── docs/                  # Dokumentasi
├── output/                # Output directory (mounted as volume)
│   ├── batch/
│   ├── hybrid/
│   └── live/
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Multi-service configuration
├── Makefile              # Development commands
└── .dockerignore         # Docker build exclusions
```

## 🐳 Docker Services

### Batch Mode
```bash
# Merekam audio sampai selesai, kemudian proses transkripsi
docker-compose --profile batch up mom-transcript-batch
```

### Hybrid Mode
```bash
# Real-time stream + high-accuracy chunk processing
docker-compose --profile hybrid up mom-transcript-hybrid
```

### Live Mode
```bash
# Real-time transcription saja
docker-compose --profile live up mom-transcript-live
```

### Development Mode
```bash
# Shell access untuk development
docker-compose --profile dev up mom-transcript-dev
```

## ⚙️ Konfigurasi

### Audio Device Setup

Untuk mengakses audio device di dalam container:

```yaml
# docker-compose.yml
volumes:
  - /dev/snd:/dev/snd
devices:
  - /dev/snd
environment:
  - PULSE_RUNTIME_PATH=/run/user/1000/pulse
  - PULSE_NATIVE=1
```

### Custom Configuration

1. Edit file di `configs/` directory
2. Restart container untuk apply changes

```bash
# Edit konfigurasi
vim configs/hybrid_config_meeting.json

# Restart service
make stop
make run-hybrid
```

## 📁 Volume Mapping

| Host Path | Container Path | Purpose |
|-----------|----------------|----------|
| `./configs` | `/app/configs` | Configuration files (read-only) |
| `./output` | `/app/output` | Transcription output |
| `/dev/snd` | `/dev/snd` | Audio device access |

## 🔧 Development

### Development Container

```bash
# Start development container
make dev

# Atau masuk ke running container
make shell
```

### Testing

```bash
# Run test scripts
make test

# Manual testing
docker-compose --profile dev run --rm mom-transcript-dev python3 tests/test_whisper_command.py
```

### Debugging

```bash
# Lihat logs
make logs

# Check container status
make status

# Health check
make health
```

## 🛠️ Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build Docker image |
| `make run-batch` | Run batch mode |
| `make run-hybrid` | Run hybrid mode |
| `make run-live` | Run live mode |
| `make dev` | Development mode |
| `make shell` | Enter container shell |
| `make test` | Run tests |
| `make logs` | Show logs |
| `make stop` | Stop containers |
| `make clean` | Clean containers/images |
| `make setup` | Initial setup |
| `make status` | Show status |
| `make health` | Health check |
| `make backup` | Backup output |

## 🚨 Troubleshooting

### Audio Issues

```bash
# Check audio devices
docker-compose --profile dev run --rm mom-transcript-dev python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Test audio access
make health
```

### Permission Issues

```bash
# Fix output directory permissions
sudo chown -R $USER:$USER output/

# Fix audio device permissions
sudo usermod -a -G audio $USER
```

### Build Issues

```bash
# Clean build
make build-no-cache

# Check Docker resources
docker system df
docker system prune -f
```

### Container Issues

```bash
# Check container logs
docker-compose logs mom-transcript-batch

# Restart services
make stop
make run-batch
```

## 📊 Performance Tuning

### Resource Limits

Edit `docker-compose.yml` untuk set resource limits:

```yaml
services:
  mom-transcript-batch:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Model Optimization

- Gunakan model `small` untuk balance speed/accuracy
- Gunakan model `base` untuk speed priority
- Gunakan model `medium` untuk accuracy priority

## 🔐 Security

### Best Practices

1. **Jangan run sebagai root** - Container menggunakan user `appuser`
2. **Limit network access** - Gunakan `network_mode: host` hanya jika diperlukan
3. **Read-only configs** - Mount configs sebagai read-only
4. **Regular updates** - Update base image secara berkala

### Production Deployment

```bash
# Production build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Run with resource limits
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## 📝 Logs & Monitoring

### Log Locations

- Container logs: `docker-compose logs`
- Application logs: `output/*/logs/`
- System logs: `/var/log/`

### Monitoring

```bash
# Real-time logs
make logs

# Container stats
docker stats

# Resource usage
docker system df
```

## 🆘 Support

Jika mengalami masalah:

1. Check logs: `make logs`
2. Check status: `make status`
3. Run health check: `make health`
4. Restart services: `make stop && make run-batch`
5. Clean rebuild: `make clean && make build`

Untuk masalah yang persisten, buat issue dengan:
- Output dari `make status`
- Output dari `make health`
- Relevant logs dari `make logs`
