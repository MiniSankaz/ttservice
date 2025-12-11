# Plan: Convert whisper-th-large-v3-combined to MLX

## Overview
แปลง Full Thonburian Whisper model จาก Transformers format เป็น MLX format สำหรับใช้บน Apple Silicon

## Model Info
| Field | Value |
|-------|-------|
| Source | `biodatlab/whisper-th-large-v3-combined` |
| Target | `whisper-th-large-v3-combined-mlx` |
| Size | ~3GB |
| WER Thai | 6.59% (ดีกว่า distill 0.23%) |
| Parameters | 2B |

## Prerequisites
- [x] Clone MLX Examples repository
- [x] Install torch, transformers

## Steps

### Step 1: Run Conversion Script
```bash
source /Users/sem4pro/_git/ttservice/venv/bin/activate
cd /Users/sem4pro/_git/mlx-examples/whisper

python convert.py \
  --torch-name-or-path biodatlab/whisper-th-large-v3-combined \
  --mlx-path /Users/sem4pro/_git/ttservice/models/whisper-th-large-v3-combined-mlx
```

**เวลาโดยประมาณ**: 10-20 นาที (download ~3GB + convert)

### Step 2: Verify Output
```bash
ls -lh /Users/sem4pro/_git/ttservice/models/whisper-th-large-v3-combined-mlx/
```

**Expected files:**
- `weights.npz` หรือ `weights.safetensors` (~3GB)
- `config.json`

### Step 3: Test Model
```bash
source /Users/sem4pro/_git/ttservice/venv/bin/activate
python -c "
import mlx_whisper
result = mlx_whisper.transcribe(
    'test_audio.mp3',
    path_or_hf_repo='/Users/sem4pro/_git/ttservice/models/whisper-th-large-v3-combined-mlx',
    language='th'
)
print(result['text'][:200])
"
```

### Step 4: Use in Web App
1. Restart web service: `./setup.sh --stop && ./setup.sh --start`
2. Open http://localhost:8501
3. Select model: `whisper-th-large-v3-combined-mlx`
4. Start transcription

## Optional: Create Quantized Version (4-bit)
ลดขนาด model ~4x แต่อาจลด accuracy เล็กน้อย

```bash
python convert.py \
  --torch-name-or-path biodatlab/whisper-th-large-v3-combined \
  -q --q_bits 4 \
  --mlx-path /Users/sem4pro/_git/ttservice/models/whisper-th-large-v3-combined-mlx-4bit
```

## Comparison After Conversion

| Model | Size | WER Thai | Speed |
|-------|------|----------|-------|
| distill-thonburian-mlx (มีแล้ว) | 1.5GB | 6.82% | เร็ว |
| **whisper-th-large-v3-combined-mlx** | 3GB | **6.59%** | ปานกลาง |
| whisper-th-large-v3-combined-mlx-4bit | ~0.8GB | ~7-8%? | เร็วมาก |

## Cleanup (Optional)
```bash
# ลบ mlx-examples repo หลัง convert เสร็จ
rm -rf /Users/sem4pro/_git/mlx-examples
```

---
Created: 2025-12-11
Status: Ready to execute
