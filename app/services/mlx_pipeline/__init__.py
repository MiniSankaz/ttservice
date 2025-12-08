"""
MLX Pipeline Mode - Parallel Preprocessing + Transcription

Architecture:
- Uses CPU for preprocessing while GPU handles transcription
- Overlapped execution: preprocess next file while transcribing current
- Maximizes both CPU and GPU utilization

Pipeline Flow:
    [Preprocess F1] ─> [Transcribe F1] ─────────────────────>
           [Preprocess F2] ─> [Transcribe F2] ─────────────>
                  [Preprocess F3] ─> [Transcribe F3] ─────>
                         [Preprocess F4] ─> ...

Components:
- PipelineOrchestrator: Manages the overall pipeline
- PreprocessWorker: CPU-bound preprocessing (runs in separate process)
- TranscribeWorker: GPU-bound transcription (MLX)
- ChunkQueue: Thread-safe queue for passing chunks between stages
"""

from .audio_preprocessing import AudioPreprocessor
from .smart_chunking import SmartChunker

__all__ = [
    'AudioPreprocessor',
    'SmartChunker',
    'PipelineTranscriber',
]
