# Transcriptor Pipeline Pilot - คู่มือการใช้งาน

## สารบัญ
1. [ข้อกำหนดเบื้องต้น](#ข้อกำหนดเบื้องต้น)
2. [การติดตั้ง](#การติดตั้ง)
3. [การใช้งาน Wizard](#การใช้งาน-wizard)
4. [โหมดการทำงาน](#โหมดการทำงาน)
5. [การตั้งค่า Workers](#การตั้งค่า-workers)
6. [ตัวอย่างการใช้งาน](#ตัวอย่างการใช้งาน)
7. [การติดตาม Progress](#การติดตาม-progress)
8. [Output Files](#output-files)
9. [Performance Tips](#performance-tips)
10. [Troubleshooting](#troubleshooting)

---

## ข้อกำหนดเบื้องต้น

### Hardware
- **Apple Silicon Mac** (M1/M2/M3/M4)
- **RAM**: อย่างน้อย 8 GB (แนะนำ 16 GB สำหรับ large-v3)
- **Storage**: อย่างน้อย 5 GB สำหรับ models

### Software
- macOS 12.0+ (Monterey หรือใหม่กว่า)
- Python 3.11+ (แนะนำ 3.12)
- FFmpeg

---

## การติดตั้ง

### One-Click Setup

```bash
cd /path/to/transcriptor-pipeline-pilot
./setup.sh
```

Script จะทำการ:
1. ตรวจสอบ Python 3.11+
2. ตรวจสอบ FFmpeg
3. สร้าง Virtual Environment
4. ติดตั้ง Dependencies
5. Download MLX Whisper Models (medium, large-v3)

### Manual Setup (ถ้าต้องการ)

```bash
# สร้าง venv ด้วย Python 3.12
/opt/homebrew/bin/python3.12 -m venv venv

# Activate
source venv/bin/activate

# ติดตั้ง dependencies
pip install -r requirements.txt

# Download models
python scripts/download_models.py
```

---

## การใช้งาน Wizard

### เปิดใช้งาน Environment

```bash
cd /path/to/transcriptor-pipeline-pilot
source venv/bin/activate
```

### Command Line Options

```bash
python transcribe_wizard.py [OPTIONS]

Options:
  --interactive          โหมด Interactive Wizard (แนะนำสำหรับผู้เริ่มต้น)
  --input PATH           ไฟล์ audio หรือ folder ที่ต้องการถอดเสียง
  --output-dir PATH      โฟลเดอร์สำหรับเก็บผลลัพธ์
  --model {medium,large-v3}  โมเดล Whisper (default: medium)
  --mode {auto,manual}   โหมดการตั้งค่า workers (default: auto)
  --processes N          จำนวน processes (เฉพาะ manual mode)
  --workers N            จำนวน workers ต่อ process (เฉพาะ manual mode)
```

---

## โหมดการทำงาน

### 1. Interactive Mode (แนะนำสำหรับผู้เริ่มต้น)

```bash
python transcribe_wizard.py --interactive
```

Wizard จะถามข้อมูลทีละขั้นตอน:
1. **Input Selection**: เลือกไฟล์หรือโฟลเดอร์
2. **Output Directory**: กำหนดที่เก็บผลลัพธ์
3. **Model Selection**: เลือก medium หรือ large-v3
4. **Worker Configuration**: เลือก auto หรือ manual

### 2. Auto Mode (เร็วและสะดวก)

```bash
# ไฟล์เดียว
python transcribe_wizard.py --input audio.mp3 --mode auto

# หลายไฟล์ (folder)
python transcribe_wizard.py --input ./audios/ --output-dir ./outputs --mode auto
```

Auto mode จะ:
- ตรวจจับ CPU cores และ Memory อัตโนมัติ
- คำนวณใช้ 80% ของ resources
- กำหนด workers ที่เหมาะสมกับเครื่อง

### 3. Manual Mode (กำหนดเอง)

```bash
python transcribe_wizard.py --input audio.mp3 --mode manual --processes 2 --workers 8
```

---

## การตั้งค่า Workers

### Auto Configuration Formula

```
usable_cores = CPU_cores × 0.8
usable_memory = RAM × 0.8
max_workers = min(usable_cores, usable_memory / model_memory)

model_memory:
  - medium: 0.5 GB ต่อ instance
  - large-v3: 1.5 GB ต่อ instance
```

### แนะนำสำหรับ Apple Silicon

| Mac Model | RAM | Medium Model | Large-v3 Model |
|-----------|-----|--------------|----------------|
| M1 (8GB) | 8 GB | 1×8 workers | 1×4 workers |
| M1 Pro (16GB) | 16 GB | 2×8 workers | 1×8 workers |
| M2 Pro (16GB) | 16 GB | 2×8 workers | 2×8 workers |
| M3 Max (32GB) | 32 GB | 2×12 workers | 2×10 workers |

### Processes vs Workers

- **Processes**: จำนวน Python processes แยกกัน (หลีกเลี่ยง GIL)
- **Workers**: จำนวน threads ต่อ process (share model)

**แนะนำ**: 2 processes × 8 workers = 16 total workers
- ให้ความเสถียร 100%
- ใช้ memory ~1-2 GB
- เหมาะกับ M2 Pro ขึ้นไป

---

## ตัวอย่างการใช้งาน

### ตัวอย่าง 1: ถอดเสียงไฟล์เดียว (Auto)

```bash
python transcribe_wizard.py \
    --input "/Users/me/Downloads/meeting.mp3" \
    --mode auto
```

Output:
```
/Users/me/Downloads/transcriptions/
├── meeting.txt
├── meeting.json
└── meeting.srt
```

### ตัวอย่าง 2: ถอดเสียงทั้งโฟลเดอร์

```bash
python transcribe_wizard.py \
    --input "/Users/me/recordings/" \
    --output-dir "/Users/me/transcripts/" \
    --mode auto
```

### ตัวอย่าง 3: ใช้โมเดล Large-v3 (แม่นยำสูงสุด)

```bash
python transcribe_wizard.py \
    --input meeting.mp3 \
    --model large-v3 \
    --mode auto
```

### ตัวอย่าง 4: กำหนด Workers เอง

```bash
python transcribe_wizard.py \
    --input meeting.mp3 \
    --mode manual \
    --processes 2 \
    --workers 8
```

### ตัวอย่าง 5: Batch Processing หลายไฟล์

```bash
# สร้างโฟลเดอร์รวมไฟล์ audio
mkdir ./to_transcribe
cp *.mp3 *.wav *.m4a ./to_transcribe/

# ถอดเสียงทั้งหมด
python transcribe_wizard.py \
    --input ./to_transcribe/ \
    --output-dir ./transcripts/ \
    --model medium \
    --mode auto
```

---

## การติดตาม Progress

### Real-time Logs

เปิด terminal ใหม่และรัน:

```bash
# ดู preprocessing progress
tail -f /tmp/preprocess_job_*.log

# ดู transcription progress
tail -f /tmp/mlx_process_*.log

# ดูทั้งหมด
tail -f /tmp/preprocess_job_*.log /tmp/mlx_process_*.log
```

### Log Format

```
19:25:33 - [Process 1] - ✓ [15/31] (48.4%) - 228 chars - 2.1s
           │             │  │       │         │          │
           │             │  │       │         │          └─ เวลาที่ใช้
           │             │  │       │         └─ จำนวนตัวอักษร
           │             │  │       └─ Progress %
           │             │  └─ chunk ที่เสร็จ / ทั้งหมด
           │             └─ status
           └─ Process ID
```

---

## Output Files

ทุกการถอดเสียงจะสร้าง 3 ไฟล์:

### 1. Text File (.txt)
```
ข้อความที่ถอดออกมาทั้งหมด
แบบ plain text
```

### 2. JSON File (.json)
```json
{
  "text": "ข้อความทั้งหมด",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "ข้อความ segment แรก"
    }
  ],
  "language": "th",
  "model": "whisper-medium-mlx"
}
```

### 3. SRT Subtitle (.srt)
```srt
1
00:00:00,000 --> 00:00:05,200
ข้อความ segment แรก

2
00:00:05,200 --> 00:00:10,500
ข้อความ segment ที่สอง
```

---

## Performance Tips

### 1. เลือก Model ที่เหมาะสม

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| **medium** | ~4x realtime | Good | ทั่วไป, เร็ว |
| **large-v3** | ~1.8x realtime | Best | ต้องการความแม่นยำสูง |

### 2. Batch Processing

ถ้ามีหลายไฟล์ ใส่ในโฟลเดอร์เดียวกันแล้วรันครั้งเดียว:

```bash
python transcribe_wizard.py --input ./all_audios/ --mode auto
```

ระบบจะ:
- Preprocess ไฟล์ถัดไปขณะ transcribe ไฟล์ปัจจุบัน
- ใช้ resources ได้คุ้มค่ากว่า

### 3. ปิด Application อื่น

ปิด Chrome, Safari, หรือ app ที่ใช้ memory มาก เพื่อให้ MLX ใช้ GPU ได้เต็มที่

### 4. ใช้ไฟล์ Audio คุณภาพดี

- Sample rate: 16kHz ขึ้นไป
- Format: MP3, WAV, M4A, FLAC
- ลด noise ก่อนถ้าเป็นไปได้

---

## Troubleshooting

### ปัญหา: "Python 3.11+ not found"

**แก้ไข:**
```bash
brew install python@3.12
```

### ปัญหา: "FFmpeg not found"

**แก้ไข:**
```bash
brew install ffmpeg
```

### ปัญหา: "Out of memory"

**แก้ไข:**
1. ลด workers: `--mode manual --processes 1 --workers 4`
2. ใช้ model เล็กลง: `--model medium`
3. ปิด app อื่นที่ใช้ memory

### ปัญหา: Transcription ช้ามาก

**ตรวจสอบ:**
1. ดู Activity Monitor → GPU usage ควรสูง
2. ถ้า GPU ต่ำ อาจมี app อื่นใช้ GPU อยู่
3. ลองปิด app ที่ใช้ Metal/GPU

### ปัญหา: ผลลัพธ์ไม่ถูกต้อง

**แก้ไข:**
1. ลองใช้ `--model large-v3` เพื่อความแม่นยำสูงขึ้น
2. ตรวจสอบคุณภาพ audio ต้นฉบับ
3. Audio ที่มี noise มากอาจถอดได้ไม่ดี

### ปัญหา: Process ค้าง

**แก้ไข:**
```bash
# หยุด process ที่ค้าง
pkill -f transcribe_pipeline
pkill -f mlx_whisper

# รันใหม่
python transcribe_wizard.py --input audio.mp3 --mode auto
```

---

## Quick Reference Card

```bash
# === SETUP ===
cd /path/to/transcriptor-pipeline-pilot
source venv/bin/activate

# === BASIC USAGE ===
# Interactive (แนะนำ)
python transcribe_wizard.py --interactive

# Single file (auto)
python transcribe_wizard.py --input audio.mp3 --mode auto

# Batch folder
python transcribe_wizard.py --input ./audios/ --output-dir ./outputs --mode auto

# === ADVANCED ===
# Large-v3 model
python transcribe_wizard.py --input audio.mp3 --model large-v3 --mode auto

# Manual workers
python transcribe_wizard.py --input audio.mp3 --mode manual --processes 2 --workers 8

# === MONITORING ===
tail -f /tmp/mlx_process_*.log
```

---

## Performance Benchmarks

ทดสอบบน M2 Pro (10-core CPU, 16GB RAM):

| Audio Length | Model | Config | Time | Speed |
|-------------|-------|--------|------|-------|
| 10 min | medium | 1×8 | 3.5 min | 2.86x |
| 74 min | medium | 2×8 | 18.7 min | 3.98x |
| 74 min | large-v3 | 2×8 | 41.2 min | 1.80x |
| 120 min | medium | 2×16 | 36.1 min | 3.32x |

---

## Support

หากพบปัญหาหรือต้องการความช่วยเหลือ:
1. ตรวจสอบ logs: `tail -f /tmp/*.log`
2. ดู error message ใน terminal
3. ลองรันด้วย `--mode manual` กับ workers น้อยลง

---

*Last updated: December 2024*
*Version: 1.0.0*
