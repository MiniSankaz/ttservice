"""
Transcriptor Pipeline - Library Modules

This package contains modular components extracted from web_app.py
for better maintainability and code organization.

Module Structure:
================

lib/
├── __init__.py          # Package initialization
├── config.py            # Configuration and constants
├── system.py            # System utilities (CPU, memory)
├── audio.py             # Audio processing utilities
├── models.py            # Model management
├── ui_components.py     # Shared UI components
└── pages/               # Page-specific modules
    ├── __init__.py
    ├── transcribe.py    # Transcription page
    ├── history.py       # History page
    ├── statistics.py    # Statistics page
    ├── settings.py      # Settings page
    └── about.py         # About page

Dependencies:
============
- config.py: No internal dependencies (base module)
- system.py: Depends on config.py
- audio.py: Depends on config.py, system.py
- models.py: Depends on config.py
- ui_components.py: Depends on config.py
- pages/*: Depends on all above modules

Impact Analysis:
===============
- config.py: Changing constants affects all modules
- system.py: Affects worker calculation, resource display
- audio.py: Affects transcription, duration display
- models.py: Affects model selection, settings
- pages/*: UI changes only, isolated impact
"""

from .config import (
    PROJECT_ROOT,
    SUPPORTED_FORMATS,
    UPLOADS_DIR,
    OUTPUTS_DIR,
    DEFAULT_CHUNK_DURATION,
    DEFAULT_OVERLAP_DURATION,
)

from .system import (
    get_system_resources,
    calculate_optimal_workers,
)

from .audio import (
    get_audio_duration,
    run_transcription,
)

from .models import (
    get_available_models,
)

__all__ = [
    # Config
    'PROJECT_ROOT',
    'SUPPORTED_FORMATS',
    'UPLOADS_DIR',
    'OUTPUTS_DIR',
    'DEFAULT_CHUNK_DURATION',
    'DEFAULT_OVERLAP_DURATION',
    # System
    'get_system_resources',
    'calculate_optimal_workers',
    # Audio
    'get_audio_duration',
    'run_transcription',
    # Models
    'get_available_models',
]

__version__ = '1.2.0'
