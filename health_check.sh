#!/bin/bash
# ============================================================
# Transcriptor Pipeline Pilot - Health Check Script
# ============================================================
# รัน script นี้เพื่อตรวจสอบว่า environment พร้อมใช้งานหรือไม่
# ============================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}"
echo "============================================================"
echo "   🔍 Transcriptor Pipeline - Health Check"
echo "============================================================"
echo -e "${NC}"

READY=true

# 1. Check Apple Silicon
echo -e "${BLUE}[1/6] Checking Apple Silicon...${NC}"
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo -e "${GREEN}  ✓ Apple Silicon ($ARCH)${NC}"
else
    echo -e "${RED}  ✗ Not Apple Silicon ($ARCH) - MLX requires Apple Silicon${NC}"
    READY=false
fi

# 2. Check Python 3.11+
echo -e "${BLUE}[2/6] Checking Python...${NC}"
PYTHON_OK=false
for py in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.13 python3.12 python3.11 python3.13; do
    if command -v $py &> /dev/null; then
        PY_VER=$($py -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "${GREEN}  ✓ Python $PY_VER found ($py)${NC}"
        PYTHON_OK=true
        break
    fi
done
if [ "$PYTHON_OK" = false ]; then
    echo -e "${RED}  ✗ Python 3.11+ not found${NC}"
    echo -e "${YELLOW}    Fix: brew install python@3.12${NC}"
    READY=false
fi

# 3. Check FFmpeg
echo -e "${BLUE}[3/6] Checking FFmpeg...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VER=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    echo -e "${GREEN}  ✓ FFmpeg $FFMPEG_VER${NC}"
else
    echo -e "${RED}  ✗ FFmpeg not found${NC}"
    echo -e "${YELLOW}    Fix: brew install ffmpeg${NC}"
    READY=false
fi

# 4. Check venv
echo -e "${BLUE}[4/6] Checking Virtual Environment...${NC}"
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate 2>/dev/null
    if python -c "import mlx; import mlx_whisper" 2>/dev/null; then
        echo -e "${GREEN}  ✓ venv is ready${NC}"
    else
        echo -e "${RED}  ✗ venv exists but packages missing${NC}"
        echo -e "${YELLOW}    Fix: rm -rf venv && ./setup.sh${NC}"
        READY=false
    fi
else
    echo -e "${RED}  ✗ venv not found${NC}"
    echo -e "${YELLOW}    Fix: ./setup.sh${NC}"
    READY=false
fi

# 5. Check Models
echo -e "${BLUE}[5/6] Checking Models...${NC}"
MODELS_OK=true
for model in whisper-medium-mlx whisper-large-v3-mlx; do
    if [ -f "models/$model/weights.npz" ]; then
        SIZE=$(du -sh "models/$model" | cut -f1)
        echo -e "${GREEN}  ✓ $model ($SIZE)${NC}"
    else
        echo -e "${RED}  ✗ $model not found${NC}"
        MODELS_OK=false
    fi
done
if [ "$MODELS_OK" = false ]; then
    echo -e "${YELLOW}    Fix: source venv/bin/activate && python scripts/download_models.py${NC}"
    READY=false
fi

# 6. Check Local Modules
echo -e "${BLUE}[6/6] Checking Local Modules...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null
    MODULES_OK=$(python -c "
import sys
sys.path.insert(0, '.')
try:
    from app.services.mlx_pipeline import audio_preprocessing
    from app.services.mlx_pipeline import smart_chunking
    from app.services.mlx_pipeline import transcription_hybrid
    from app.services.mlx_pipeline import pipeline_transcriber
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1)
    if [ "$MODULES_OK" = "OK" ]; then
        echo -e "${GREEN}  ✓ All local modules OK${NC}"
    else
        echo -e "${RED}  ✗ Module error: $MODULES_OK${NC}"
        READY=false
    fi
else
    echo -e "${YELLOW}  ⚠ Skipped (no venv)${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}============================================================${NC}"
if [ "$READY" = true ]; then
    echo -e "${GREEN}   ✅ ENVIRONMENT READY!${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo "  source venv/bin/activate"
    echo "  python transcribe_wizard.py --interactive"
    echo ""
else
    echo -e "${RED}   ❌ ENVIRONMENT NOT READY${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    echo -e "${YELLOW}To fix, run:${NC}"
    echo "  rm -rf venv"
    echo "  ./setup.sh"
    echo ""
fi
