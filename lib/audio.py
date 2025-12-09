"""
Audio Processing Module - lib/audio.py

Functions for audio file processing and transcription.

Impact Analysis:
===============
- get_audio_duration(): Used by transcribe page for duration display
- run_transcription(): Core transcription function, affects all transcription

Dependencies:
============
- lib/config.py (PROJECT_ROOT, DEFAULT_CHUNK_DURATION, DEFAULT_OVERLAP_DURATION)

Used By:
========
- lib/pages/transcribe.py
- web_app.py

External Dependencies:
====================
- ffprobe (from ffmpeg) for duration detection
- scripts/transcribe_pipeline.py for actual transcription

Functions:
=========
- get_audio_duration(file_path: str) -> float
- run_transcription(...) -> dict
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Callable, Optional

from .config import (
    PROJECT_ROOT,
    DEFAULT_CHUNK_DURATION,
    DEFAULT_OVERLAP_DURATION,
)


def get_audio_duration(file_path: str) -> float:
    """
    Get audio file duration in minutes using ffprobe.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        float: Duration in minutes, or 0.0 if detection fails
        
    Dependencies:
        - ffprobe (part of ffmpeg package)
        
    Impact:
        - Used for progress calculation
        - Used for speed calculation (x.x realtime)
        - Displayed in file info section
        
    Example:
        >>> duration = get_audio_duration("meeting.mp3")
        >>> print(f"{duration:.1f} minutes")
        74.4 minutes
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
             file_path],
            capture_output=True, 
            text=True
        )
        duration_seconds = float(result.stdout.strip())
        return duration_seconds / 60  # Convert to minutes
    except Exception:
        return 0.0


def run_transcription(
    input_path: str,
    output_path: str,
    model: str,
    processes: int,
    workers: int,
    progress_callback: Optional[Callable[[str], None]] = None,
    chunk_duration: int = DEFAULT_CHUNK_DURATION,
    overlap_duration: int = DEFAULT_OVERLAP_DURATION
) -> Dict:
    """
    Run transcription pipeline and return result.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output text file
        model: Model name (short name like 'medium' or full name)
        processes: Number of transcription processes
        workers: Number of workers per process
        progress_callback: Optional callback for progress updates
        chunk_duration: Chunk duration in seconds (default: 20)
        overlap_duration: Overlap between chunks in seconds (default: 3)
        
    Returns:
        dict: {
            'success': bool,
            'elapsed_seconds': float,
            'logs': list[str]
        }
        
    Dependencies:
        - scripts/transcribe_pipeline.py
        - MLX Whisper models
        
    Impact:
        - Main transcription function
        - Affects all transcription operations
        - Progress callback updates UI in real-time
        
    Example:
        >>> result = run_transcription(
        ...     "input.mp3", "output.txt",
        ...     model="medium",
        ...     processes=2, workers=8
        ... )
        >>> if result['success']:
        ...     print(f"Done in {result['elapsed_seconds']:.1f}s")
    """
    script_path = PROJECT_ROOT / "scripts" / "transcribe_pipeline.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        input_path,
        output_path,
        '--model', model,
        '--transcribe-processes', str(processes),
        '--transcribe-workers', str(workers),
        '--preprocess-workers', '2',
        '--chunk-duration', str(chunk_duration),
        '--overlap', str(overlap_duration)
    ]
    
    start_time = time.time()
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    logs = []
    for line in process.stdout:
        line = line.strip()
        logs.append(line)
        if progress_callback:
            progress_callback(line)
    
    process.wait()
    elapsed = time.time() - start_time
    
    success = process.returncode == 0
    
    return {
        'success': success,
        'elapsed_seconds': elapsed,
        'logs': logs
    }


def validate_audio_file(file_path: str, supported_formats: list) -> Dict:
    """
    Validate an audio file for transcription.
    
    Args:
        file_path: Path to audio file
        supported_formats: List of supported extensions (e.g., ['.mp3', '.wav'])
        
    Returns:
        dict: {
            'valid': bool,
            'error': str or None,
            'duration_minutes': float,
            'format': str
        }
        
    Impact:
        - Used before transcription to validate input
        - Prevents processing invalid files
        
    Example:
        >>> result = validate_audio_file("meeting.mp3", ['.mp3', '.wav'])
        >>> if result['valid']:
        ...     print(f"Valid {result['format']} file, {result['duration_minutes']:.1f} min")
    """
    path = Path(file_path)
    
    if not path.exists():
        return {
            'valid': False,
            'error': 'File not found',
            'duration_minutes': 0,
            'format': None
        }
    
    file_ext = path.suffix.lower()
    if file_ext not in supported_formats:
        return {
            'valid': False,
            'error': f'Unsupported format: {file_ext}',
            'duration_minutes': 0,
            'format': file_ext
        }
    
    duration = get_audio_duration(str(path))
    
    return {
        'valid': True,
        'error': None,
        'duration_minutes': duration,
        'format': file_ext
    }
