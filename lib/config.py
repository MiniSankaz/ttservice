"""
Configuration Module - lib/config.py

Central configuration for the Transcriptor Pipeline application.
All constants, paths, and default settings are defined here.

Impact Analysis:
===============
- PROJECT_ROOT: Used by all modules for path resolution
- SUPPORTED_FORMATS: Used by transcribe.py for file validation
- UPLOADS_DIR, OUTPUTS_DIR: Used by audio.py, transcribe.py, settings.py
- DEFAULT_CHUNK_*: Used by audio.py, transcribe.py UI

Dependencies:
============
- None (base module)

Used By:
========
- lib/system.py
- lib/audio.py
- lib/models.py
- lib/ui_components.py
- lib/pages/*.py
- web_app.py

Configuration Override:
=====================
Environment variables can override defaults:
- TRANSCRIPTOR_UPLOADS_DIR: Override uploads directory
- TRANSCRIPTOR_OUTPUTS_DIR: Override outputs directory
- TRANSCRIPTOR_CHUNK_DURATION: Override chunk duration
- TRANSCRIPTOR_OVERLAP_DURATION: Override overlap duration
"""

import os
from pathlib import Path

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Project root is determined dynamically from this file's location
# This ensures portability - no hardcoded absolute paths
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories - relative to PROJECT_ROOT for portability
# Can be overridden via environment variables
UPLOADS_DIR = Path(os.environ.get(
    'TRANSCRIPTOR_UPLOADS_DIR',
    str(PROJECT_ROOT / "data" / "uploads")
))

OUTPUTS_DIR = Path(os.environ.get(
    'TRANSCRIPTOR_OUTPUTS_DIR',
    str(PROJECT_ROOT / "data" / "outputs")
))

DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

# =============================================================================
# FILE FORMATS
# =============================================================================

# Supported audio formats for transcription
SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm']

# Export formats
EXPORT_FORMATS = ['txt', 'json', 'srt', 'vtt']

# =============================================================================
# TRANSCRIPTION DEFAULTS
# =============================================================================

# Default chunk duration in seconds (adjustable via UI: 15-25s)
DEFAULT_CHUNK_DURATION = int(os.environ.get(
    'TRANSCRIPTOR_CHUNK_DURATION', '20'
))

# Default overlap between chunks in seconds (adjustable via UI: 1-5s)
DEFAULT_OVERLAP_DURATION = int(os.environ.get(
    'TRANSCRIPTOR_OVERLAP_DURATION', '3'
))

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Standard MLX Whisper models
STANDARD_MODELS = {
    'whisper-medium-mlx': {
        'display_name': 'Medium',
        'short_name': 'medium',
        'huggingface_id': 'mlx-community/whisper-medium-mlx',
        'memory_gb': 0.5,
    },
    'whisper-large-v3-mlx': {
        'display_name': 'Large-v3',
        'short_name': 'large-v3',
        'huggingface_id': 'mlx-community/whisper-large-v3-mlx',
        'memory_gb': 1.5,
    },
}

# Popular custom models
POPULAR_MODELS = [
    {
        'id': 'tawankri/distill-thonburian-whisper-large-v3-mlx',
        'label': '🇹🇭 Thai Thonburian',
        'description': 'Thai-optimized model',
    },
    {
        'id': 'mlx-community/whisper-large-v3-turbo-mlx',
        'label': 'Large-v3-Turbo',
        'description': 'Faster large model',
    },
    {
        'id': 'mlx-community/whisper-small-mlx',
        'label': 'Small',
        'description': 'Lightweight model',
    },
]

# =============================================================================
# WORKER CONFIGURATION
# =============================================================================

# Worker presets for different usage scenarios
WORKER_PRESETS = [
    ('Conservative', '1P × 4W', 'Lower memory usage, stable', 1, 4),
    ('Balanced', '2P × 8W', 'Good balance for most files', 2, 8),
    ('Aggressive', '3P × 8W', 'Faster, needs more memory', 3, 8),
    ('Maximum', '4P × 8W', 'Maximum speed, high memory', 4, 8),
]

# Resource allocation ratios
CPU_USAGE_RATIO = 0.8  # Use 80% of available CPU cores
MEMORY_USAGE_RATIO = 0.8  # Use 80% of available memory

# =============================================================================
# UI CONFIGURATION
# =============================================================================

# Page configuration
PAGE_TITLE = "Transcriptor - Thai Audio Transcription"
PAGE_ICON = "🎙️"

# Version info
APP_VERSION = "1.2.0"
APP_NAME = "Transcriptor Pipeline Pilot"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# SQLite database path
DATABASE_PATH = DATA_DIR / "transcriptor.db"

# =============================================================================
# ENSURE DIRECTORIES EXIST
# =============================================================================

def ensure_directories():
    """Create all necessary directories if they don't exist."""
    for directory in [UPLOADS_DIR, OUTPUTS_DIR, DATA_DIR, MODELS_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# Auto-create directories on import
ensure_directories()
