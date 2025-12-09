"""
Page Modules Package - lib/pages/__init__.py

This package contains individual page modules for the Streamlit application.

Module Structure:
================
- transcribe.py  - Audio transcription page
- history.py     - Transcription history page
- statistics.py  - Usage statistics page
- settings.py    - Application settings page
- about.py       - About page

Dependencies:
============
All page modules depend on:
- lib/config.py
- lib/ui_components.py
- app/database.py (for data persistence)

Individual dependencies are documented in each module.

Impact Analysis:
===============
- Changes to page modules only affect their respective pages
- Shared components (ui_components.py) affect all pages
- Database schema changes affect history.py and statistics.py
"""

# Page modules are imported on demand to avoid circular imports
# Use: from lib.pages.transcribe import show_transcribe_page

__all__ = [
    'transcribe',
    'history', 
    'statistics',
    'settings',
    'about',
]
