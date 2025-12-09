# CLAUDE.md - Transcriptor Pipeline Pilot

This file provides guidance to Claude Code when working with this repository.

## Resume Conversation System

**IMPORTANT:** This project uses a portable context system in `.claude/` directory.

When starting a new Claude Code session on ANY machine:
```
Say: "อ่าน .claude/ แล้วทำงานต่อ" or "Resume from .claude/"
```

### Context Files
| File | Purpose |
|------|---------|
| `.claude/PROJECT_CONTEXT.md` | Static project knowledge (architecture, decisions) |
| `.claude/CURRENT_STATE.md` | Current work state (pending tasks, recent changes) |
| `.claude/DECISIONS.md` | Technical decision log with rationale |
| `.claude/KNOWN_ISSUES.md` | Known bugs and workarounds |

### Before Ending Session
```
Say: "อัพเดต .claude/ และ commit" to save your session state
```

---

## Project Overview

**Transcriptor Pipeline Pilot** is a Streamlit-based web application for transcribing Thai audio using MLX Whisper on Apple Silicon (M1/M2/M3/M4). Features multi-process parallel transcription with real-time progress tracking.

**Version**: 1.0.0
**Primary Language**: Thai (ภาษาไทย)
**Platform**: macOS with Apple Silicon

## Technology Stack

### Core
- **Streamlit** - Web UI framework
- **MLX Whisper** - Apple Silicon optimized Whisper
- **MLX** - Apple's ML framework
- **Python 3.10+** - Runtime

### Audio Processing
- **pydub** - Audio manipulation
- **ffmpeg** - Audio conversion
- **noisereduce** - Audio enhancement

### Data
- **SQLite** - Local database for history
- **huggingface_hub** - Model downloads

### Testing
- **Selenium WebDriver** - RPA/UI testing
- **Chrome** - Browser automation

## Project Structure

```
transcriptor-pipeline-pilot/
├── web_app.py              # Main Streamlit application
├── setup.sh                # Setup and service management script
├── requirements.txt        # Python dependencies
│
├── lib/                    # Modular library components
│   ├── __init__.py         # Package init
│   ├── config.py           # Configuration & paths (dynamic, no hardcoding)
│   ├── system.py           # System resources (CPU, memory)
│   ├── audio.py            # Audio processing & transcription
│   ├── models.py           # Model management (HuggingFace)
│   ├── ui_components.py    # Shared Streamlit UI components
│   └── pages/              # Page-specific modules
│       ├── __init__.py
│       └── settings.py     # Setup Wizard & Claude Terminal
│
├── scripts/
│   └── transcribe_pipeline.py  # CLI transcription script
│
├── app/
│   ├── database.py         # SQLite database operations
│   └── services/
│       └── mlx_hybrid/     # Hybrid multi-process transcription
│           ├── transcription_hybrid.py
│           ├── audio_preprocessing.py
│           └── smart_chunking.py
│
├── models/                 # Downloaded Whisper models
│   ├── whisper-medium-mlx/
│   └── distill-thonburian-whisper-large-v3-mlx/
│
├── data/
│   ├── uploads/            # Uploaded audio files
│   ├── outputs/            # Transcription results
│   └── transcriptor.db     # SQLite database
│
├── tests/
│   ├── rpa_web_test.py     # Selenium RPA tests (29 tests)
│   └── screenshots/        # Test screenshots
│
└── docs/
    └── technical-specs/    # Architecture documentation
```

## Key Features

### 1. Web UI (Streamlit)
- **Transcribe Page**: Upload audio, select model, configure workers
- **History Page**: View past transcriptions with download options
- **Statistics Page**: Usage analytics and charts
- **Settings Page**:
  - Model management (download/delete)
  - Performance configuration
  - Setup Wizard (one-click setup)
  - Claude Terminal (AI-assisted commands)
- **About Page**: App information

### 2. Transcription Engine
- **Hybrid Multi-Process**: 2 processes × N workers for stability
- **Smart Chunking**: 20s chunks with 3s overlap
- **Audio Preprocessing**: Noise reduction, normalization
- **Real-time Progress**: Per-process progress with speed indicator
- **Auto Export**: TXT, JSON, SRT formats simultaneously

### 3. Model Support
- **Standard Models**: tiny, base, small, medium, large
- **Custom Models**: Any MLX Whisper model from HuggingFace
- **Thai Optimized**: distill-thonburian-whisper-large-v3-mlx
- **Formats**: weights.npz and weights.safetensors

### 4. UI Enhancements
- **Drag & Drop**: Enhanced file upload area
- **Chunk Settings**: Configurable duration (15-25s) and overlap (1-5s)
- **Progress Display**: Multi-process average with realtime speed (x.x times)

## Configuration

### Environment Variables (Optional)
```bash
TRANSCRIPTOR_UPLOADS_DIR    # Custom uploads directory
TRANSCRIPTOR_OUTPUTS_DIR    # Custom outputs directory
TRANSCRIPTOR_MODELS_DIR     # Custom models directory
TRANSCRIPTOR_DATA_DIR       # Custom data directory
TRANSCRIPTOR_CHUNK_DURATION # Default chunk duration (20)
TRANSCRIPTOR_OVERLAP        # Default overlap (3)
```

### Default Paths
All paths are dynamically resolved from `PROJECT_ROOT = Path(__file__).parent.parent`:
- Models: `PROJECT_ROOT/models`
- Uploads: `PROJECT_ROOT/data/uploads`
- Outputs: `PROJECT_ROOT/data/outputs`
- Database: `PROJECT_ROOT/data/transcriptor.db`

## Development Commands

### Setup
```bash
# One-click setup
./setup.sh --setup

# Or manually
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running
```bash
# Start web service
./setup.sh --start
# or
streamlit run web_app.py --server.port 8501

# Stop service
./setup.sh --stop

# Check status
./setup.sh --status
```

### Testing
```bash
# Run all RPA tests (requires running web service)
python tests/rpa_web_test.py

# Skip transcription test (faster)
python tests/rpa_web_test.py --skip-transcription

# Test specific worker config
python tests/rpa_web_test.py --custom-worker-test
```

### CLI Transcription
```bash
# Basic usage
python scripts/transcribe_pipeline.py input.mp3 output.txt

# With options
python scripts/transcribe_pipeline.py input.mp3 output.txt \
  --model medium \
  --processes 2 \
  --workers 8 \
  --chunk-duration 20 \
  --overlap 3
```

## Architecture

### Transcription Flow
```
Audio File
    ↓
AudioPreprocessor (noise reduction, normalization)
    ↓
SmartChunker (split into 20s chunks with 3s overlap)
    ↓
HybridMLXTranscriber
├── Process 1 (MLX Model Instance)
│   └── ThreadPool (N workers)
└── Process 2 (MLX Model Instance)
    └── ThreadPool (N workers)
    ↓
Merge Results (deduplicate overlaps)
    ↓
Export (TXT, JSON, SRT)
```

### Module Dependencies
```
web_app.py
├── lib/config.py (paths, constants)
├── lib/system.py (CPU, memory)
├── lib/audio.py (transcription wrapper)
├── lib/models.py (model management)
├── lib/ui_components.py (CSS, helpers)
├── lib/pages/settings.py (Setup Wizard, Claude Terminal)
└── app/database.py (SQLite operations)
```

## Performance

### Benchmarks (M2 Pro, 10-core)
| Config | Audio | Time | Speed | Memory |
|--------|-------|------|-------|--------|
| 2×8 workers | 142 min | 44 min | 3.2x | ~1-2 GB |
| Medium model | 74 min | 23 min | 3.2x | ~0.5 GB |
| Large model | 74 min | 51 min | 1.5x | ~2 GB |

### Optimal Settings
- **Development**: 1 process, 4 workers
- **Production**: 2 processes, 8 workers per process
- **Chunk Duration**: 20 seconds (15-25 range)
- **Overlap**: 3 seconds (prevents word cutoff)

## RPA Test Coverage (29 tests)

| Test | Description |
|------|-------------|
| 01-06 | Navigation (all pages) |
| 07 | Model selection |
| 08 | File upload |
| 09 | Full transcription |
| 10, 10b | Transcript view & file verification |
| 11-13 | Export (TXT, SRT, JSON) |
| 14 | Statistics display |
| 15-17 | History operations |
| 18-19 | Settings tabs & custom model |
| 20 | Manual worker mode |
| 24-25 | Setup Wizard |
| 26-27 | Claude Terminal |
| 28 | Chunk settings UI |
| 29 | Drag & Drop upload |

## Important Notes

### No Hardcoded Paths
All paths use dynamic resolution:
```python
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
```

### Model Format Support
Both formats are supported:
- `weights.npz` (older MLX models)
- `weights.safetensors` (newer models like Thonburian)

### Thai Language Optimization
For best Thai transcription results:
1. Use `distill-thonburian-whisper-large-v3-mlx` model
2. Set language to "Thai" in transcription settings
3. Use 20s chunk duration for optimal context

## Troubleshooting

### Model not detected
- Ensure model has `weights.npz` or `weights.safetensors`
- Check `config.json` exists in model directory

### Transcription fails
- Verify FFmpeg is installed: `ffmpeg -version`
- Check audio file format (MP3, WAV, M4A supported)
- Ensure sufficient memory for model

### Web UI not loading
- Check port 8501 is available
- Verify venv is activated
- Run `./setup.sh --status` to check service

## Version History

- **v1.0.0** (Current)
  - Streamlit web UI with all features
  - Hybrid multi-process transcription
  - Setup Wizard and Claude Terminal
  - Modular lib/ architecture
  - 29 RPA tests (100% pass rate)
  - Dynamic path configuration
