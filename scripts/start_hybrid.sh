#!/bin/bash

# Hybrid Transcription Starter Script
# Memudahkan penggunaan hybrid mode dengan berbagai preset

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== HYBRID TRANSCRIPTION STARTER ===${NC}"
echo -e "${BLUE}Menggabungkan Stream (Real-time) + Chunk (High Accuracy)${NC}\n"

# Function to show usage
show_usage() {
    echo "Usage: $0 [PRESET] [OPTIONS]"
    echo ""
    echo "PRESETS:"
    echo "  meeting     - Meeting formal (balance speed/accuracy)"
    echo "  interview   - Interview (prioritas akurasi tinggi)"
    echo "  presentation- Presentasi (responsif real-time)"
    echo "  custom      - Gunakan konfigurasi manual"
    echo ""
    echo "OPTIONS:"
    echo "  --config FILE    - Custom config file"
    echo "  --output-dir DIR - Custom output directory"
    echo "  --list-devices   - List audio devices"
    echo "  --help          - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 meeting"
    echo "  $0 interview --output-dir ./interview_transcript"
    echo "  $0 custom --config my_config.json"
}

# Function to create preset config
create_preset_config() {
    local preset=$1
    local config_file="configs/hybrid_config_${preset}.json"
    
    case $preset in
        "meeting")
            cat > "$config_file" << EOF
{
  "output_dir": "hybrid_output_meeting",
  "stream_bin": "./whisper.cpp/stream",
  "whisper_bin": "./whisper.cpp/main",
  "stream_model": "./whisper.cpp/models/ggml-small.bin",
  "chunk_model": "./whisper.cpp/models/ggml-small.bin",
  "language": "id",
  "device_index": 1,
  "chunk_duration": 30,
  "stream_args": "--capture 1 --step 3000 --length 8000 --keep 300 --vad-thold 0.6"
}
EOF
            echo -e "${GREEN}✓ Created meeting preset config${NC}" >&2
            ;;
        "interview")
            cat > "$config_file" << EOF
{
  "output_dir": "hybrid_output_interview",
  "stream_bin": "./whisper.cpp/stream",
  "whisper_bin": "./whisper.cpp/main",
  "stream_model": "./whisper.cpp/models/ggml-small.bin",
  "chunk_model": "./whisper.cpp/models/ggml-small.bin",
  "language": "id",
  "device_index": 1,
  "chunk_duration": 45,
  "stream_args": "--capture 1 --step 5000 --length 12000 --keep 500 --vad-thold 0.5"
}
EOF
            echo -e "${GREEN}✓ Created interview preset config (high accuracy)${NC}" >&2
            ;;
        "presentation")
            cat > "$config_file" << EOF
{
  "output_dir": "hybrid_output_presentation",
  "stream_bin": "./whisper.cpp/stream",
  "whisper_bin": "./whisper.cpp/main",
  "stream_model": "./whisper.cpp/models/ggml-small.bin",
  "chunk_model": "./whisper.cpp/models/ggml-small.bin",
  "language": "id",
  "device_index": 1,
  "chunk_duration": 20,
  "stream_args": "--capture 1 --step 2000 --length 6000 --keep 200 --vad-thold 0.7"
}
EOF
            echo -e "${GREEN}✓ Created presentation preset config (fast response)${NC}" >&2
            ;;
        *)
            echo -e "${RED}✗ Unknown preset: $preset${NC}"
            return 1
            ;;
    esac
    
    echo "$config_file"
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python3 not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python3 found${NC}"
    
    # Check live_transcribe.py
    if [ ! -f "live_transcribe.py" ]; then
        echo -e "${RED}✗ live_transcribe.py not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ live_transcribe.py found${NC}"
    
    # Check hybrid_transcribe.py
    if [ ! -f "hybrid_transcribe.py" ]; then
        echo -e "${RED}✗ hybrid_transcribe.py not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ hybrid_transcribe.py found${NC}"
    
    # Check whisper.cpp binaries
    if [ ! -f "./whisper.cpp/stream" ]; then
        echo -e "${RED}✗ whisper.cpp stream binary not found${NC}"
        echo -e "${YELLOW}Run: cd whisper.cpp && make stream${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Stream binary found${NC}"
    
    if [ ! -f "./whisper.cpp/main" ]; then
        echo -e "${RED}✗ whisper.cpp main binary not found${NC}"
        echo -e "${YELLOW}Run: cd whisper.cpp && make${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Main binary found${NC}"
    
    echo -e "${GREEN}✓ All prerequisites met${NC}\n"
}

# Parse arguments
PRESET=""
CONFIG_FILE=""
OUTPUT_DIR=""
LIST_DEVICES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        meeting|interview|presentation|custom)
            PRESET="$1"
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --list-devices)
            LIST_DEVICES=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Handle list devices
if [ "$LIST_DEVICES" = true ]; then
    echo -e "${BLUE}Available audio devices:${NC}"
    python3 src/hybrid_transcribe.py --list-devices
    exit 0
fi

# Check if preset is provided
if [ -z "$PRESET" ]; then
    echo -e "${RED}✗ No preset specified${NC}"
    show_usage
    exit 1
fi

# Check prerequisites
check_prerequisites

# Handle preset configurations
if [ "$PRESET" != "custom" ]; then
    echo -e "${YELLOW}Setting up $PRESET preset...${NC}"
    CONFIG_FILE=$(create_preset_config "$PRESET")
fi

# Use default config if none specified
if [ -z "$CONFIG_FILE" ]; then
    CONFIG_FILE="hybrid_config.json"
fi

# Build command
CMD="python3 src/hybrid_transcribe.py --config $CONFIG_FILE"

if [ -n "$OUTPUT_DIR" ]; then
    CMD="$CMD --output-dir $OUTPUT_DIR"
fi

# Show configuration
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Preset: ${GREEN}$PRESET${NC}"
echo -e "  Config: ${GREEN}$CONFIG_FILE${NC}"
if [ -n "$OUTPUT_DIR" ]; then
    echo -e "  Output: ${GREEN}$OUTPUT_DIR${NC}"
fi
echo ""

# Confirm start
echo -e "${YELLOW}Ready to start hybrid transcription!${NC}"
echo -e "${YELLOW}This will run both stream (real-time) and chunk (high-accuracy) modes.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop gracefully.${NC}\n"

read -p "Start transcription? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}Cancelled by user${NC}"
    exit 0
fi

# Start hybrid transcription
echo -e "${GREEN}Starting hybrid transcription...${NC}\n"
exec $CMD