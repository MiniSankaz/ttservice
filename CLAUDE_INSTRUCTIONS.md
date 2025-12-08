# Claude Code Instructions - Transcriptor Pipeline Pilot

## สำหรับ Claude Code ที่เปิด Project นี้บนเครื่องอื่น

เมื่อ user เปิด project นี้และต้องการใช้งาน ให้ทำตามขั้นตอนนี้:

---

## 1. ตรวจสอบสถานะ Environment

รันคำสั่งนี้ก่อน:

```bash
cd "<PROJECT_PATH>"

# Check venv
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python -c "import mlx; import mlx_whisper; print('ENV OK')" 2>/dev/null && echo "✓ venv พร้อมใช้งาน" || echo "✗ venv ต้องสร้างใหม่"
else
    echo "✗ ไม่พบ venv - ต้องรัน setup.sh"
fi

# Check models
if [ -f "models/whisper-medium-mlx/weights.npz" ]; then
    echo "✓ models พร้อมใช้งาน"
else
    echo "✗ ไม่พบ models - ต้องรัน setup.sh"
fi
```

---

## 2. ถ้า venv ไม่พร้อม (ปกติเมื่อคัดลอกข้ามเครื่อง)

### วิธีที่ 1: รัน setup.sh (แนะนำ)

```bash
# ลบ venv เก่า (ถ้ามี)
rm -rf venv

# รัน setup
./setup.sh
```

### วิธีที่ 2: สร้าง venv เอง

```bash
# หา Python 3.11+
PYTHON_CMD=$(which python3.12 || which python3.11 || which python3.13)

# สร้าง venv
rm -rf venv
$PYTHON_CMD -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download models (ถ้ายังไม่มี)
python scripts/download_models.py
```

---

## 3. ข้อกำหนดของเครื่อง

ตรวจสอบว่าเครื่องมี:

```bash
# Apple Silicon
uname -m  # ต้องเป็น arm64

# Python 3.11+
python3 --version  # ต้อง >= 3.11

# FFmpeg
ffmpeg -version

# ถ้าไม่มี ติดตั้งด้วย:
# brew install python@3.12 ffmpeg
```

---

## 4. การใช้งาน

หลังจาก environment พร้อม:

```bash
# Activate
source venv/bin/activate

# Interactive wizard (แนะนำ)
python transcribe_wizard.py --interactive

# Auto mode
python transcribe_wizard.py --input audio.mp3 --mode auto

# Manual mode (2 processes × 8 workers)
python transcribe_wizard.py --input audio.mp3 --mode manual --processes 2 --workers 8

# Batch folder
python transcribe_wizard.py --input ./audios/ --output-dir ./outputs --mode auto

# Large-v3 model (แม่นยำสูงสุด)
python transcribe_wizard.py --input audio.mp3 --model large-v3 --mode auto
```

---

## 5. Troubleshooting

### ปัญหา: "No module named 'mlx'"
```bash
rm -rf venv && ./setup.sh
```

### ปัญหา: "Python 3.11+ not found"
```bash
brew install python@3.12
```

### ปัญหา: Models ไม่พบ
```bash
source venv/bin/activate
python scripts/download_models.py
```

### ปัญหา: Permission denied
```bash
chmod +x setup.sh transcribe_wizard.py scripts/*.py
```

---

## 6. โครงสร้าง Project

```
transcriptor-pipeline-pilot/
├── app/services/mlx_pipeline/   # Core transcription modules
│   ├── audio_preprocessing.py   # Audio enhancement
│   ├── smart_chunking.py        # Smart audio chunking
│   ├── transcription_hybrid.py  # Hybrid MLX transcriber
│   └── pipeline_transcriber.py  # Pipeline orchestrator
├── scripts/
│   ├── transcribe_pipeline.py   # Main transcription script
│   └── download_models.py       # Model downloader
├── models/                      # MLX Whisper models (~4.3 GB)
│   ├── whisper-medium-mlx/
│   └── whisper-large-v3-mlx/
├── venv/                        # Virtual environment (~2.9 GB)
├── requirements.txt             # Dependencies
├── setup.sh                     # One-click setup
├── transcribe_wizard.py         # Interactive wizard
├── USAGE.md                     # คู่มือการใช้งาน
└── CLAUDE_INSTRUCTIONS.md       # ไฟล์นี้
```

---

## 7. Performance Reference

ทดสอบบน M2 Pro (10-core, 16GB RAM):

| Audio | Model | Config | Time | Speed |
|-------|-------|--------|------|-------|
| 10 min | medium | 1×8 | 3.5 min | 2.86x |
| 74 min | medium | 2×8 | 18.7 min | 3.98x |
| 74 min | large-v3 | 2×8 | 41.2 min | 1.80x |

---

## 8. Quick Health Check Script

ใช้ script นี้ตรวจสอบ environment:

```bash
cd "<PROJECT_PATH>" && source venv/bin/activate 2>/dev/null && python -c "
import sys
from pathlib import Path

print('=== TRANSCRIPTOR HEALTH CHECK ===')
print()

# Check Python
print(f'Python: {sys.version.split()[0]}', end=' ')
print('✓' if sys.version_info >= (3, 11) else '✗ (need 3.11+)')

# Check imports
for mod in ['mlx', 'mlx_whisper', 'librosa', 'soundfile', 'noisereduce']:
    try:
        __import__(mod)
        print(f'{mod}: ✓')
    except:
        print(f'{mod}: ✗')

# Check models
print()
for model in ['whisper-medium-mlx', 'whisper-large-v3-mlx']:
    path = Path(f'models/{model}/weights.npz')
    if path.exists():
        size = path.stat().st_size / (1024**3)
        print(f'{model}: ✓ ({size:.1f} GB)')
    else:
        print(f'{model}: ✗ (not found)')

print()
print('=== END CHECK ===')
" || echo "❌ venv ไม่พร้อม - รัน: rm -rf venv && ./setup.sh"
```

---

*สร้างโดย Claude Code - December 2024*
