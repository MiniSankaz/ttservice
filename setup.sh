#!/bin/bash
# ============================================================
# Transcriptor Pipeline Pilot - One-Click Setup Script
# ============================================================
# This script sets up the complete environment:
# 1. Creates Python virtual environment
# 2. Installs all dependencies
# 3. Downloads MLX Whisper models
# 4. Verifies installation
# ============================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${CYAN}"
echo "============================================================"
echo "   🚀 Transcriptor Pipeline Pilot - Setup"
echo "============================================================"
echo -e "${NC}"

# Check for Python 3.11+ (required for MLX)
echo -e "${BLUE}[1/5] Checking Python version...${NC}"

# Find Python 3.11+ (prefer homebrew versions)
PYTHON_CMD=""
for py in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.13 python3.12 python3.11 python3.13; do
    if command -v $py &> /dev/null; then
        PY_VER=$($py -c 'import sys; print(sys.version_info.minor)')
        if [ "$PY_VER" -ge 11 ]; then
            PYTHON_CMD=$py
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}  ✗ Python 3.11+ not found. Please install:${NC}"
    echo -e "${RED}    brew install python@3.12${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}  ✓ Python $PYTHON_VERSION found ($PYTHON_CMD)${NC}"

# Check for FFmpeg
echo -e "${BLUE}[2/5] Checking FFmpeg...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    echo -e "${GREEN}  ✓ FFmpeg $FFMPEG_VERSION found${NC}"
else
    echo -e "${YELLOW}  ⚠ FFmpeg not found. Installing via Homebrew...${NC}"
    if command -v brew &> /dev/null; then
        brew install ffmpeg
        echo -e "${GREEN}  ✓ FFmpeg installed${NC}"
    else
        echo -e "${RED}  ✗ Homebrew not found. Please install FFmpeg manually:${NC}"
        echo -e "${RED}    brew install ffmpeg${NC}"
        exit 1
    fi
fi

# Create virtual environment with Python 3.11+
echo -e "${BLUE}[3/5] Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}  ⚠ Virtual environment already exists. Skipping...${NC}"
else
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}  ✓ Virtual environment created with Python $PYTHON_VERSION${NC}"
fi

# Activate and install dependencies
echo -e "${BLUE}[4/5] Installing dependencies...${NC}"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}  ✓ Dependencies installed${NC}"
else
    echo -e "${RED}  ✗ requirements.txt not found${NC}"
    exit 1
fi

# Download models
echo -e "${BLUE}[5/5] Downloading MLX Whisper models...${NC}"
echo -e "${YELLOW}  This may take a while depending on your internet speed...${NC}"

# Create models directory
mkdir -p models

# Download using the download script
if [ -f "scripts/download_models.py" ]; then
    python scripts/download_models.py
    echo -e "${GREEN}  ✓ Models downloaded${NC}"
else
    echo -e "${YELLOW}  ⚠ Download script not found. Downloading manually...${NC}"
    python -c "
from huggingface_hub import snapshot_download
import os

models_dir = 'models'
models = [
    'mlx-community/whisper-medium-mlx',
    'mlx-community/whisper-large-v3-mlx',
]

for model in models:
    model_name = model.split('/')[-1]
    local_dir = os.path.join(models_dir, model_name)
    print(f'Downloading {model}...')
    snapshot_download(repo_id=model, local_dir=local_dir)
    print(f'✓ {model_name} downloaded')
"
fi

# Verify installation
echo -e "${CYAN}"
echo "============================================================"
echo "   ✨ Setup Complete!"
echo "============================================================"
echo -e "${NC}"

echo -e "${GREEN}Virtual environment:${NC} ./venv"
echo -e "${GREEN}Models directory:${NC} ./models"
echo ""
echo -e "${YELLOW}To activate the environment:${NC}"
echo "  source venv/bin/activate"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo "  # Interactive wizard"
echo "  python transcribe_wizard.py --interactive"
echo ""
echo "  # Auto mode (single file)"
echo "  python transcribe_wizard.py --input audio.mp3 --mode auto"
echo ""
echo "  # Batch processing"
echo "  python transcribe_wizard.py --input ./audios/ --output-dir ./outputs --mode auto"
echo ""
echo -e "${CYAN}============================================================${NC}"
