# Transcriptor Pipeline Pilot

🚀 **Experimental Pipeline Mode** - Overlapped Preprocessing + Transcription

## Concept

ใช้ทรัพยากรให้คุ้มค่าโดยทำ Preprocessing (CPU) ขนานกับ Transcription (GPU):

```
Traditional Sequential:
[Preprocess F1] ─> [Transcribe F1] ─> [Preprocess F2] ─> [Transcribe F2] ─>
     2 min              20 min            2 min              20 min
                                Total: 44 min for 2 files

Pipeline Overlapped:
[Preprocess F1] ─> [Transcribe F1] ─────────────────────>
       [Preprocess F2] ─> [Transcribe F2] ─────────────>
     2 min              20 min
                                Total: ~22 min for 2 files (50% faster!)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE ORCHESTRATOR                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   [CPU Workers]                 [GPU Workers]                    │
│   ┌──────────────┐             ┌──────────────┐                 │
│   │ Preprocess   │             │ Transcribe   │                 │
│   │ Worker 1     │  ──Queue──> │ MLX Hybrid   │                 │
│   │ Worker 2     │             │ 2×8 workers  │                 │
│   └──────────────┘             └──────────────┘                 │
│         │                            │                           │
│         ▼                            ▼                           │
│   • Noise reduction            • MLX Whisper                    │
│   • Audio enhance              • GPU/Neural Engine              │
│   • Smart chunking             • Parallel transcription         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Single File
```bash
python scripts/transcribe_pipeline.py input.mp3 output.txt
```

### Batch Mode (Multiple Files)
```bash
python scripts/transcribe_pipeline.py \
    --batch file1.mp3 file2.mp3 file3.mp3 \
    --output-dir ./outputs
```

### Custom Configuration
```bash
python scripts/transcribe_pipeline.py input.mp3 output.txt \
    --model medium \
    --preprocess-workers 2 \
    --transcribe-processes 2 \
    --transcribe-workers 8
```

## Monitor Progress

```bash
# Preprocessing logs (CPU workers)
tail -f /tmp/preprocess_job_*.log

# Transcription logs (GPU workers)
tail -f /tmp/mlx_process_*.log
```

## Performance Comparison

| Mode | 3 Files (2h each) | CPU Usage | GPU Usage |
|------|-------------------|-----------|-----------|
| Sequential | ~66 min | Low | Medium |
| **Pipeline** | **~42 min** | **High** | **High** |
| Improvement | **36% faster** | +40% | Same |

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--preprocess-workers` | 2 | Parallel CPU workers for preprocessing |
| `--transcribe-processes` | 2 | MLX transcription processes |
| `--transcribe-workers` | 8 | Workers per transcription process |
| `--chunk-duration` | 20 | Chunk duration in seconds |
| `--overlap` | 3 | Overlap duration in seconds |

## Project Structure

```
transcriptor-pipeline-pilot/
├── app/services/mlx_pipeline/
│   ├── __init__.py
│   ├── audio_preprocessing.py    # Audio enhancement (from baseline)
│   ├── smart_chunking.py         # Smart chunking (from baseline)
│   ├── transcription_hybrid.py   # MLX transcriber (from baseline)
│   └── pipeline_transcriber.py   # NEW: Pipeline orchestrator
├── scripts/
│   └── transcribe_pipeline.py    # CLI script
└── README.md
```

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- Python 3.11+
- MLX Whisper
- FFmpeg

## Status

🧪 **Experimental** - This is a pilot project for testing pipeline architecture.

Baseline project: `transcriptor/`
