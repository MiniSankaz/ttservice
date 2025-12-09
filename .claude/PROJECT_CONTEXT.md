# PROJECT_CONTEXT.md - Static Project Knowledge

> Last Updated: 2025-12-09
> This file contains stable project information that rarely changes.

## Project Identity

**Name:** Transcriptor Pipeline Pilot
**Purpose:** Thai audio transcription using MLX Whisper on Apple Silicon
**Repository:** https://github.com/MiniSankaz/ttservice.git
**Primary Language:** Thai (ภาษาไทย)

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Web UI                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │Transcribe│ History  │Statistics│ Settings │  About   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    lib/ Module Layer                         │
│  config.py │ system.py │ audio.py │ models.py │ ui_*.py    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│              app/services/mlx_hybrid/                        │
│  HybridMLXTranscriber (2 Processes × N Workers)             │
│  ├── Process 1: MLX Model + ThreadPool                      │
│  └── Process 2: MLX Model + ThreadPool                      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                 │
│  SQLite (history) │ Models Dir │ Uploads │ Outputs          │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Dynamic Paths (No Hardcoding)
All paths use `Path(__file__).parent` or environment variables.
See: `lib/config.py`

### 2. Dual Model Format Support
- `weights.npz` - Older MLX models
- `weights.safetensors` - Newer models (Thonburian)
See: `lib/models.py`

### 3. Hybrid Multi-Process Architecture
- 2 processes (avoid GIL bottleneck)
- N workers per process (ThreadPool)
- Better stability than single-process with many threads
See: `app/services/mlx_hybrid/transcription_hybrid.py`

### 4. Smart Chunking with Overlap
- 20s chunks (configurable 15-25s)
- 3s overlap (prevents word cutoff)
See: `app/services/mlx_hybrid/smart_chunking.py`

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `lib/config.py` | Paths, constants, environment vars |
| `lib/system.py` | CPU/memory detection, worker calculation |
| `lib/audio.py` | Transcription wrapper, subprocess management |
| `lib/models.py` | Model listing, download, delete |
| `lib/ui_components.py` | CSS, formatters, UI helpers |
| `lib/pages/settings.py` | Setup Wizard, Claude Terminal |

## Critical Files

| File | Impact | Notes |
|------|--------|-------|
| `web_app.py` | Main entry | All UI logic |
| `lib/config.py` | All modules | Path configuration |
| `app/database.py` | History/Stats | SQLite operations |
| `app/services/mlx_hybrid/transcription_hybrid.py` | Core | Transcription engine |

## Standard Models

| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| whisper-tiny-mlx | ~100MB | 10x | Testing only |
| whisper-base-mlx | ~200MB | 7x | Quick drafts |
| whisper-small-mlx | ~500MB | 5x | General use |
| whisper-medium-mlx | ~1.5GB | 3x | Production |
| whisper-large-v3-mlx | ~3GB | 1.5x | High accuracy |
| distill-thonburian-* | ~1GB | 3x | Thai optimized |

## Testing Strategy

- **RPA Tests:** Selenium WebDriver automation
- **Test File:** `tests/rpa_web_test.py`
- **Coverage:** 29 tests, 100% pass rate
- **Requires:** Running Streamlit server on port 8501

## Environment Setup

```bash
# Quick start
./setup.sh --setup   # Create venv, install deps, init DB
./setup.sh --start   # Start Streamlit server

# Manual
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run web_app.py
```

## Common Workflows

### Add New Feature
1. Create/modify in `lib/` if reusable
2. Update `web_app.py` for UI
3. Add RPA test in `tests/rpa_web_test.py`
4. Update `CLAUDE.md` if significant

### Fix Bug
1. Reproduce with RPA test if possible
2. Fix in appropriate module
3. Run full test suite
4. Update `KNOWN_ISSUES.md` if applicable

### Add New Model Support
1. Ensure model has `weights.npz` or `weights.safetensors`
2. Model will auto-detect in `lib/models.py`
3. Test with transcription
