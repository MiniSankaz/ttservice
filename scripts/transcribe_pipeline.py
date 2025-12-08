#!/usr/bin/env python3
"""
MLX Pipeline Transcription - Overlapped Preprocessing + Transcription

This script implements a pipeline architecture that maximizes resource utilization:
- CPU cores handle preprocessing (noise reduction, chunking)
- GPU/Neural Engine handles transcription (MLX Whisper)
- Overlapped execution: preprocess next file while transcribing current

Usage:
    # Single file
    python scripts/transcribe_pipeline.py input.mp3 output.txt

    # Batch mode (multiple files)
    python scripts/transcribe_pipeline.py --batch file1.mp3 file2.mp3 file3.mp3 --output-dir ./outputs

    # With options
    python scripts/transcribe_pipeline.py input.mp3 output.txt \
        --model medium \
        --preprocess-workers 2 \
        --transcribe-processes 2 \
        --transcribe-workers 8

Monitor Progress:
    # Preprocessing logs
    tail -f /tmp/preprocess_job_*.log

    # Transcription logs
    tail -f /tmp/mlx_process_*.log

Performance Benefits:
    - Sequential: preprocess 2min + transcribe 20min = 22min per file
    - Pipeline:   preprocess overlapped with transcribe = ~20min per file
    - Batch 3 files: Sequential 66min vs Pipeline ~42min (36% faster)
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.mlx_pipeline.pipeline_transcriber import PipelineTranscriber


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def main():
    parser = argparse.ArgumentParser(
        description='MLX Pipeline Transcription - Overlapped Preprocessing + Transcription',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file
  python scripts/transcribe_pipeline.py meeting.mp3 transcript.txt

  # Batch mode
  python scripts/transcribe_pipeline.py --batch file1.mp3 file2.mp3 --output-dir ./outputs

  # Custom configuration
  python scripts/transcribe_pipeline.py input.mp3 output.txt \\
    --model medium \\
    --preprocess-workers 2 \\
    --transcribe-processes 2 \\
    --transcribe-workers 16

Monitor Progress:
  tail -f /tmp/preprocess_job_*.log     # Preprocessing
  tail -f /tmp/mlx_process_*.log        # Transcription
        """
    )

    # Mode selection
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Input audio file (single file mode)'
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        help='Output text file (single file mode)'
    )
    parser.add_argument(
        '--batch',
        nargs='+',
        help='Batch mode: list of input files'
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for batch mode'
    )

    # Model settings
    parser.add_argument(
        '--model',
        default='medium',
        choices=['tiny', 'base', 'small', 'medium', 'large-v3'],
        help='Whisper model size (default: medium)'
    )
    parser.add_argument(
        '--language',
        default='th',
        help='Language code (default: th for Thai)'
    )

    # Pipeline settings
    parser.add_argument(
        '--preprocess-workers',
        type=int,
        default=2,
        help='Number of parallel preprocessing workers (default: 2)'
    )
    parser.add_argument(
        '--transcribe-processes',
        type=int,
        default=2,
        help='Number of transcription processes (default: 2)'
    )
    parser.add_argument(
        '--transcribe-workers',
        type=int,
        default=8,
        help='Number of workers per transcription process (default: 8)'
    )

    # Chunking settings
    parser.add_argument(
        '--chunk-duration',
        type=int,
        default=20,
        help='Chunk duration in seconds (default: 20)'
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=3,
        help='Overlap duration in seconds (default: 3)'
    )

    # Other options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Validate arguments
    if args.batch:
        # Batch mode
        if not args.output_dir:
            logger.error("Batch mode requires --output-dir")
            return 1
        input_files = [Path(f) for f in args.batch]
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        file_pairs = [
            (str(f), str(output_dir / f"{f.stem}_transcript.txt"))
            for f in input_files
        ]
    elif args.input_file and args.output_file:
        # Single file mode
        input_path = Path(args.input_file)
        if not input_path.exists():
            logger.error(f"Input file not found: {args.input_file}")
            return 1
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        file_pairs = [(str(input_path), str(output_path))]
    else:
        parser.print_help()
        return 1

    # Print configuration
    logger.info("=" * 70)
    logger.info("🚀 MLX PIPELINE TRANSCRIPTION")
    logger.info("=" * 70)
    logger.info(f"Mode: {'Batch' if args.batch else 'Single'} ({len(file_pairs)} files)")
    logger.info(f"Model: mlx-community/whisper-{args.model}-mlx")
    logger.info(f"Language: {args.language}")
    logger.info(f"Pipeline Config:")
    logger.info(f"  - Preprocessing: {args.preprocess_workers} parallel workers (CPU)")
    logger.info(f"  - Transcription: {args.transcribe_processes} proc × {args.transcribe_workers} workers (GPU)")
    logger.info(f"  - Chunking: {args.chunk_duration}s + {args.overlap}s overlap")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📋 Monitor Progress:")
    logger.info("  tail -f /tmp/preprocess_job_*.log   # Preprocessing")
    logger.info("  tail -f /tmp/mlx_process_*.log      # Transcription")
    logger.info("")

    start_time = datetime.now()

    # Create pipeline
    pipeline = PipelineTranscriber(
        model=f"mlx-community/whisper-{args.model}-mlx",
        language=args.language,
        num_transcribe_processes=args.transcribe_processes,
        workers_per_process=args.transcribe_workers,
        chunk_duration=args.chunk_duration,
        overlap_duration=args.overlap,
        max_preprocess_workers=args.preprocess_workers,
    )

    # Process files
    try:
        results = pipeline.process_batch(file_pairs)

        # Summary
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        logger.info("")
        logger.info("=" * 70)
        logger.info("✨ PIPELINE COMPLETE!")
        logger.info("=" * 70)

        successful = sum(1 for r in results if r.get('success', False))
        logger.info(f"Total time: {total_time/60:.1f} minutes")
        logger.info(f"Files processed: {successful}/{len(results)}")
        logger.info("")

        for result in results:
            if result.get('success'):
                logger.info(f"  ✓ {Path(result['output_file']).name}")
            else:
                logger.info(f"  ✗ {Path(result.get('input_file', 'unknown')).name}: {result.get('error', 'Unknown error')}")

        logger.info("=" * 70)

        return 0 if successful == len(results) else 1

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
