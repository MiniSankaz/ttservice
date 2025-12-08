"""
Smart Audio Chunking Service

Splits audio into overlapping chunks to preserve context and prevent
word/sentence breaks in transcription.

Strategy:
- Chunk size: 20 seconds (core segment)
- Overlap: 3 seconds on each side (±3s)
- Total per chunk: 26 seconds (3s + 20s + 3s)
- Prevents context loss at boundaries

Benefits:
- No mid-word/mid-sentence cuts
- Better transcription accuracy
- Easier segment merging with overlap detection
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class SmartChunker:
    """
    Intelligent audio chunking with overlap for context preservation.

    Creates overlapping audio segments that prevent context loss:
    - Each chunk: 20s core + 3s overlap on each side
    - Example timeline:
        Chunk 1: 0s  - 23s (0-20s core + 3s overlap)
        Chunk 2: 20s - 43s (3s overlap + 20-40s core + 3s overlap)
        Chunk 3: 40s - 63s (3s overlap + 40-60s core + 3s overlap)

    The overlap allows the transcription system to:
    1. Detect and remove duplicate text
    2. Maintain context between chunks
    3. Prevent mid-word cuts

    Example:
        >>> chunker = SmartChunker(chunk_duration=20, overlap_duration=3)
        >>> result = chunker.process(
        ...     input_file="long_audio.wav",
        ...     output_dir="chunks/"
        ... )
        >>> print(f"Created {result['total_chunks']} chunks")
    """

    def __init__(
        self,
        chunk_duration: int = 20,
        overlap_duration: int = 3,
    ):
        """
        Initialize smart chunker.

        Args:
            chunk_duration: Core chunk duration in seconds (default: 20)
            overlap_duration: Overlap on each side in seconds (default: 3)
        """
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.total_chunk_duration = chunk_duration + (2 * overlap_duration)

        # Check FFmpeg availability
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Verify FFmpeg is installed."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Install with: brew install ffmpeg"
            )

    def _get_audio_duration(self, audio_file: str) -> float:
        """
        Get audio duration using FFprobe.

        Args:
            audio_file: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_file
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Could not get duration: {e}")
            raise

    def process(
        self,
        input_file: str,
        output_dir: str,
        save_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Split audio into smart overlapping chunks.

        Args:
            input_file: Path to input audio file
            output_dir: Directory for output chunks
            save_metadata: Whether to save chunk metadata to JSON

        Returns:
            Dict containing:
                - total_chunks: Number of chunks created
                - chunk_files: List of chunk file paths
                - chunks: List of chunk metadata (start, end, duration, overlap)
                - total_duration: Total audio duration
                - metadata_file: Path to metadata JSON file

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If FFmpeg processing fails
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Chunking audio: {input_file}")
        start_time = datetime.now()

        # Get total duration
        total_duration = self._get_audio_duration(str(input_path))
        logger.info(f"Audio duration: {total_duration:.2f}s ({total_duration/60:.1f} min)")

        # Calculate chunks
        chunks_metadata = []
        chunk_files = []

        # Calculate number of chunks needed
        # Each chunk moves forward by chunk_duration (not total_chunk_duration)
        num_chunks = math.ceil(total_duration / self.chunk_duration)

        logger.info(
            f"Creating {num_chunks} chunks "
            f"({self.chunk_duration}s core + {self.overlap_duration}s overlap each side)"
        )

        for i in range(num_chunks):
            chunk_num = i + 1

            # Calculate timing
            start = max(0, i * self.chunk_duration - self.overlap_duration)
            end = min(
                total_duration,
                (i + 1) * self.chunk_duration + self.overlap_duration
            )
            duration = end - start

            # Core segment (without overlap)
            core_start = i * self.chunk_duration
            core_end = min(total_duration, (i + 1) * self.chunk_duration)

            # Overlap information
            has_left_overlap = i > 0
            has_right_overlap = (i + 1) * self.chunk_duration < total_duration

            # Determine output format based on input
            input_suffix = input_path.suffix.lower()
            if input_suffix in ['.wav', '.wave']:
                # Keep WAV format for WAV input
                chunk_file = output_path / f"chunk_{chunk_num:03d}.wav"
                codec_args = ["-c", "copy"]  # Copy WAV codec
            else:
                # Convert to MP3 for other formats
                chunk_file = output_path / f"chunk_{chunk_num:03d}.mp3"
                codec_args = ["-c:a", "libmp3lame", "-b:a", "128k"]  # Encode to MP3

            # Extract chunk with FFmpeg
            cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-ss", str(start),
                "-t", str(duration),
                *codec_args,
                "-y",  # Overwrite
                str(chunk_file)
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg error for chunk {chunk_num}: {result.stderr}")
                    raise RuntimeError(f"Failed to create chunk {chunk_num}")

                # Metadata for this chunk
                chunk_meta = {
                    "chunk_number": chunk_num,
                    "file": str(chunk_file),
                    "filename": chunk_file.name,
                    "start_time": round(start, 2),
                    "end_time": round(end, 2),
                    "duration": round(duration, 2),
                    "core_start": round(core_start, 2),
                    "core_end": round(core_end, 2),
                    "core_duration": round(core_end - core_start, 2),
                    "overlap": {
                        "left": self.overlap_duration if has_left_overlap else 0,
                        "right": self.overlap_duration if has_right_overlap else 0,
                    },
                    "size_bytes": chunk_file.stat().st_size,
                }

                chunks_metadata.append(chunk_meta)
                chunk_files.append(str(chunk_file))

                logger.info(
                    f"✓ Chunk {chunk_num}/{num_chunks}: "
                    f"{start:.1f}s - {end:.1f}s ({duration:.1f}s)"
                )

            except subprocess.TimeoutExpired:
                raise RuntimeError(f"Timeout creating chunk {chunk_num}")
            except Exception as e:
                logger.error(f"Error creating chunk {chunk_num}: {e}")
                raise

        # Calculate statistics
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        speed_factor = total_duration / processing_time if processing_time > 0 else 0

        # Total size of all chunks
        total_size_mb = sum(c['size_bytes'] for c in chunks_metadata) / (1024 * 1024)

        # Complete metadata
        metadata = {
            "input_file": str(input_path),
            "output_dir": str(output_path),
            "total_duration_seconds": round(total_duration, 2),
            "total_duration_minutes": round(total_duration / 60, 2),
            "chunk_duration": self.chunk_duration,
            "overlap_duration": self.overlap_duration,
            "total_chunks": num_chunks,
            "chunk_files": chunk_files,
            "chunks": chunks_metadata,
            "total_size_mb": round(total_size_mb, 2),
            "processing_time_seconds": round(processing_time, 2),
            "speed_factor": round(speed_factor, 1),
            "timestamp": datetime.now().isoformat(),
        }

        # Save metadata
        if save_metadata:
            metadata_file = output_path / "chunking_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            metadata["metadata_file"] = str(metadata_file)
            logger.info(f"Metadata saved to: {metadata_file}")

        logger.info(
            f"✅ Chunking complete: {num_chunks} chunks in {processing_time:.1f}s "
            f"({speed_factor:.1f}x realtime)"
        )

        return metadata

    def get_merge_info(self, chunks_metadata: List[Dict]) -> List[Dict]:
        """
        Generate information for merging overlapping transcriptions.

        Args:
            chunks_metadata: List of chunk metadata from process()

        Returns:
            List of merge instructions with overlap regions
        """
        merge_info = []

        for i, chunk in enumerate(chunks_metadata):
            info = {
                "chunk_number": chunk["chunk_number"],
                "core_region": {
                    "start": chunk["core_start"],
                    "end": chunk["core_end"],
                    "duration": chunk["core_duration"],
                },
            }

            # Overlap with previous chunk
            if i > 0:
                prev_chunk = chunks_metadata[i - 1]
                overlap_start = chunk["start_time"]
                overlap_end = chunk["core_start"]
                info["left_overlap"] = {
                    "start": overlap_start,
                    "end": overlap_end,
                    "duration": overlap_end - overlap_start,
                    "overlaps_with_chunk": prev_chunk["chunk_number"],
                }

            # Overlap with next chunk
            if i < len(chunks_metadata) - 1:
                next_chunk = chunks_metadata[i + 1]
                overlap_start = chunk["core_end"]
                overlap_end = chunk["end_time"]
                info["right_overlap"] = {
                    "start": overlap_start,
                    "end": overlap_end,
                    "duration": overlap_end - overlap_start,
                    "overlaps_with_chunk": next_chunk["chunk_number"],
                }

            merge_info.append(info)

        return merge_info


if __name__ == "__main__":
    # Example usage
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 3:
        print("Usage: python smart_chunking.py <input_file> <output_dir>")
        sys.exit(1)

    chunker = SmartChunker(chunk_duration=20, overlap_duration=3)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    result = chunker.process(input_file, output_dir)

    print("\n" + "="*60)
    print("Chunking Complete!")
    print("="*60)
    print(f"Total chunks: {result['total_chunks']}")
    print(f"Duration: {result['total_duration_minutes']:.1f} minutes")
    print(f"Output dir: {result['output_dir']}")
    print(f"Speed: {result['speed_factor']:.1f}x realtime")
    print("="*60)
