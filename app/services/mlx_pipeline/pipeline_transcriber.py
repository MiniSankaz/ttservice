"""
Pipeline Transcriber - Overlapped Preprocessing + Transcription

This module implements a pipeline architecture that:
1. Uses CPU cores for preprocessing (noise reduction, chunking)
2. Uses GPU/Neural Engine for transcription (MLX Whisper)
3. Overlaps execution to maximize resource utilization

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    PIPELINE ORCHESTRATOR                         │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                   │
    │   [CPU Process]              [GPU Process]                       │
    │   ┌──────────────┐          ┌──────────────┐                    │
    │   │ Preprocess   │          │ Transcribe   │                    │
    │   │ Worker       │ ──Queue──│ Worker       │                    │
    │   │              │          │ (MLX)        │                    │
    │   └──────────────┘          └──────────────┘                    │
    │         │                          │                             │
    │         ▼                          ▼                             │
    │   • Audio enhance           • Load MLX model                    │
    │   • Noise reduction         • Transcribe chunks                 │
    │   • Smart chunking          • Generate output                   │
    │                                                                   │
    └─────────────────────────────────────────────────────────────────┘

Benefits:
- CPU preprocessing runs in parallel with GPU transcription
- No idle time between files in batch processing
- Better utilization of Apple Silicon's unified memory
"""

import logging
import gc
import json
import threading
import queue
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future
import multiprocessing as mp

from .audio_preprocessing import AudioPreprocessor
from .smart_chunking import SmartChunker

logger = logging.getLogger(__name__)


@dataclass
class PipelineJob:
    """Represents a single file job in the pipeline."""
    job_id: int
    input_file: Path
    output_file: Path
    status: str = "pending"  # pending, preprocessing, chunking, transcribing, completed, failed
    chunks_dir: Optional[Path] = None
    total_chunks: int = 0
    processed_chunks: int = 0
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PreprocessWorker:
    """
    CPU-bound worker for audio preprocessing and chunking.
    Runs in a separate process to utilize CPU while GPU is busy.
    """

    def __init__(
        self,
        chunk_duration: int = 20,
        overlap_duration: int = 3,
        enable_noise_reduction: bool = True,
    ):
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.enable_noise_reduction = enable_noise_reduction

    def process(
        self,
        input_file: Path,
        output_dir: Path,
        job_id: int,
    ) -> Dict[str, Any]:
        """
        Preprocess audio file and create chunks.

        Args:
            input_file: Input audio file
            output_dir: Directory for output chunks
            job_id: Job identifier for logging

        Returns:
            Dictionary with preprocessing results
        """
        import time
        start_time = time.time()

        # Setup logging for this worker
        log_file = Path("/tmp") / f"preprocess_job_{job_id}.log"
        worker_logger = self._setup_logger(job_id, log_file)

        worker_logger.info(f"=" * 50)
        worker_logger.info(f"PREPROCESS JOB {job_id} STARTED")
        worker_logger.info(f"Input: {input_file}")
        worker_logger.info(f"=" * 50)

        try:
            # Step 1: Audio preprocessing
            worker_logger.info("Step 1: Audio enhancement...")
            preprocessor = AudioPreprocessor()
            enhanced_file = output_dir / "enhanced.wav"

            preprocess_result = preprocessor.process(
                input_file=str(input_file),
                output_file=str(enhanced_file),
                save_metadata=True
            )
            worker_logger.info(f"✓ Enhanced: {preprocess_result['speed_factor']:.1f}x realtime")

            # Step 2: Smart chunking
            worker_logger.info("Step 2: Smart chunking...")
            chunker = SmartChunker(
                chunk_duration=self.chunk_duration,
                overlap_duration=self.overlap_duration
            )
            chunks_dir = output_dir / "chunks"

            chunk_result = chunker.process(
                input_file=str(enhanced_file),
                output_dir=str(chunks_dir),
                save_metadata=True
            )
            worker_logger.info(f"✓ Created {chunk_result['total_chunks']} chunks")

            total_time = time.time() - start_time
            worker_logger.info(f"=" * 50)
            worker_logger.info(f"PREPROCESS COMPLETED in {total_time:.1f}s")
            worker_logger.info(f"=" * 50)

            return {
                'success': True,
                'job_id': job_id,
                'chunks_dir': str(chunks_dir),
                'total_chunks': chunk_result['total_chunks'],
                'metadata_file': str(chunks_dir / "chunking_metadata.json"),
                'preprocess_time': total_time,
                'audio_duration': chunk_result.get('audio_duration_seconds', 0),
            }

        except Exception as e:
            worker_logger.error(f"PREPROCESS FAILED: {e}")
            return {
                'success': False,
                'job_id': job_id,
                'error': str(e),
            }

    def _setup_logger(self, job_id: int, log_file: Path) -> logging.Logger:
        """Setup a file logger for this worker."""
        logger_name = f"preprocess_worker_{job_id}"
        worker_logger = logging.getLogger(logger_name)
        worker_logger.setLevel(logging.INFO)
        worker_logger.handlers = []

        # File handler
        file_handler = logging.FileHandler(log_file, mode='w')
        formatter = logging.Formatter('%(asctime)s - [Preprocess %(job_id)s] - %(message)s', datefmt='%H:%M:%S')

        class JobFormatter(logging.Formatter):
            def __init__(self, job_id):
                super().__init__('%(asctime)s - [Preprocess Job %(job_id)s] - %(message)s', datefmt='%H:%M:%S')
                self.job_id = job_id

            def format(self, record):
                record.job_id = self.job_id
                return super().format(record)

        file_handler.setFormatter(JobFormatter(job_id))
        worker_logger.addHandler(file_handler)

        # Stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(JobFormatter(job_id))
        worker_logger.addHandler(stream_handler)

        return worker_logger


def _preprocess_worker_function(
    input_file: str,
    output_dir: str,
    job_id: int,
    chunk_duration: int,
    overlap_duration: int,
) -> Dict[str, Any]:
    """
    Standalone function for ProcessPoolExecutor.
    """
    worker = PreprocessWorker(
        chunk_duration=chunk_duration,
        overlap_duration=overlap_duration,
    )
    return worker.process(
        input_file=Path(input_file),
        output_dir=Path(output_dir),
        job_id=job_id,
    )


class TranscribeWorker:
    """
    GPU-bound worker for MLX transcription.
    Uses the existing HybridMLXTranscriber or MLXTranscriber.
    """

    def __init__(
        self,
        model: str = "mlx-community/whisper-medium-mlx",
        language: str = "th",
        num_processes: int = 2,
        workers_per_process: int = 8,
    ):
        self.model = model
        self.language = language
        self.num_processes = num_processes
        self.workers_per_process = workers_per_process
        self._transcriber = None

    def _get_transcriber(self):
        """Lazy load transcriber."""
        if self._transcriber is None:
            # Import here to avoid loading MLX until needed
            from .transcription_hybrid import HybridMLXTranscriber
            self._transcriber = HybridMLXTranscriber(
                model=self.model,
                language=self.language,
                num_processes=self.num_processes,
                workers_per_process=self.workers_per_process,
            )
        return self._transcriber

    def transcribe(
        self,
        chunks_dir: Path,
        output_file: Path,
        metadata_file: Optional[Path] = None,
        job_id: int = 0,
    ) -> Dict[str, Any]:
        """
        Transcribe chunks directory.

        Args:
            chunks_dir: Directory containing audio chunks
            output_file: Output text file path
            metadata_file: Chunking metadata file
            job_id: Job identifier for logging

        Returns:
            Dictionary with transcription results
        """
        logger.info(f"[Transcribe Job {job_id}] Starting transcription...")

        transcriber = self._get_transcriber()
        result = transcriber.transcribe_directory(
            input_dir=str(chunks_dir),
            output_file=str(output_file),
            metadata_file=str(metadata_file) if metadata_file else None,
            generate_srt=True,
            generate_json=True,
        )

        logger.info(f"[Transcribe Job {job_id}] Completed: {result['success_rate']:.1f}% success")
        return result


class PipelineTranscriber:
    """
    Pipeline orchestrator that manages overlapped preprocessing and transcription.

    Usage:
        pipeline = PipelineTranscriber(
            model="mlx-community/whisper-medium-mlx",
            language="th",
        )

        # Process multiple files with overlapped execution
        results = pipeline.process_batch([
            ("input1.mp3", "output1.txt"),
            ("input2.mp3", "output2.txt"),
            ("input3.mp3", "output3.txt"),
        ])

    Monitor progress:
        tail -f /tmp/preprocess_job_*.log
        tail -f /tmp/mlx_process_*.log
    """

    def __init__(
        self,
        model: str = "mlx-community/whisper-medium-mlx",
        language: str = "th",
        num_transcribe_processes: int = 2,
        workers_per_process: int = 8,
        chunk_duration: int = 20,
        overlap_duration: int = 3,
        max_preprocess_workers: int = 2,
    ):
        """
        Initialize Pipeline Transcriber.

        Args:
            model: MLX Whisper model name
            language: Language code
            num_transcribe_processes: Processes for transcription
            workers_per_process: Workers per transcription process
            chunk_duration: Chunk duration in seconds
            overlap_duration: Overlap duration in seconds
            max_preprocess_workers: Max concurrent preprocessing jobs
        """
        self.model = model
        self.language = language
        self.num_transcribe_processes = num_transcribe_processes
        self.workers_per_process = workers_per_process
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.max_preprocess_workers = max_preprocess_workers

        # Job tracking
        self.jobs: Dict[int, PipelineJob] = {}
        self.job_counter = 0

        # Queues
        self.preprocess_queue = queue.Queue()
        self.transcribe_queue = queue.Queue()

        logger.info("=" * 70)
        logger.info("🚀 PIPELINE TRANSCRIBER INITIALIZED")
        logger.info("=" * 70)
        logger.info(f"Model: {model}")
        logger.info(f"Transcription: {num_transcribe_processes} proc × {workers_per_process} workers")
        logger.info(f"Preprocessing: {max_preprocess_workers} parallel workers")
        logger.info(f"Chunking: {chunk_duration}s + {overlap_duration}s overlap")
        logger.info("=" * 70)

    def process_batch(
        self,
        file_pairs: List[Tuple[str, str]],
        temp_base: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files with overlapped execution.

        Args:
            file_pairs: List of (input_file, output_file) tuples
            temp_base: Base directory for temp files

        Returns:
            List of results for each file
        """
        import time
        start_time = time.time()

        logger.info(f"📋 Starting batch processing: {len(file_pairs)} files")

        # Create jobs
        jobs = []
        for input_file, output_file in file_pairs:
            job = self._create_job(Path(input_file), Path(output_file))
            jobs.append(job)
            logger.info(f"  Job {job.job_id}: {Path(input_file).name}")

        # Create temp directories
        temp_dirs = {}
        for job in jobs:
            if temp_base:
                temp_dir = Path(temp_base) / f"job_{job.job_id}"
                temp_dir.mkdir(parents=True, exist_ok=True)
            else:
                temp_dir = Path(tempfile.mkdtemp(prefix=f"pipeline_job_{job.job_id}_"))
            temp_dirs[job.job_id] = temp_dir

        results = []

        try:
            # Pipeline execution
            with ProcessPoolExecutor(max_workers=self.max_preprocess_workers) as preprocess_executor:
                # Submit all preprocessing jobs
                preprocess_futures: Dict[Future, PipelineJob] = {}
                for job in jobs:
                    future = preprocess_executor.submit(
                        _preprocess_worker_function,
                        str(job.input_file),
                        str(temp_dirs[job.job_id]),
                        job.job_id,
                        self.chunk_duration,
                        self.overlap_duration,
                    )
                    preprocess_futures[future] = job
                    job.status = "preprocessing"
                    logger.info(f"[Job {job.job_id}] Preprocessing started (CPU)")

                # Create transcribe worker (lazy load MLX)
                transcribe_worker = TranscribeWorker(
                    model=self.model,
                    language=self.language,
                    num_processes=self.num_transcribe_processes,
                    workers_per_process=self.workers_per_process,
                )

                # Process as preprocessing completes
                from concurrent.futures import as_completed
                for future in as_completed(preprocess_futures):
                    job = preprocess_futures[future]
                    preprocess_result = future.result()

                    if preprocess_result['success']:
                        job.status = "transcribing"
                        job.chunks_dir = Path(preprocess_result['chunks_dir'])
                        job.total_chunks = preprocess_result['total_chunks']

                        logger.info(f"[Job {job.job_id}] Preprocessing done, starting transcription (GPU)")

                        # Start transcription (this will use GPU)
                        transcribe_result = transcribe_worker.transcribe(
                            chunks_dir=job.chunks_dir,
                            output_file=job.output_file,
                            metadata_file=Path(preprocess_result['metadata_file']),
                            job_id=job.job_id,
                        )

                        job.status = "completed"
                        job.end_time = datetime.now()

                        results.append({
                            'job_id': job.job_id,
                            'input_file': str(job.input_file),
                            'output_file': str(job.output_file),
                            'success': True,
                            'preprocess_time': preprocess_result['preprocess_time'],
                            'transcribe_result': transcribe_result,
                        })

                        logger.info(f"[Job {job.job_id}] ✅ COMPLETED")

                    else:
                        job.status = "failed"
                        job.error = preprocess_result.get('error', 'Unknown error')
                        results.append({
                            'job_id': job.job_id,
                            'input_file': str(job.input_file),
                            'success': False,
                            'error': job.error,
                        })
                        logger.error(f"[Job {job.job_id}] ❌ FAILED: {job.error}")

        finally:
            # Cleanup temp directories
            for temp_dir in temp_dirs.values():
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)

        total_time = time.time() - start_time
        logger.info("=" * 70)
        logger.info(f"🎉 BATCH COMPLETE: {len(results)}/{len(jobs)} files in {total_time/60:.1f} min")
        logger.info("=" * 70)

        return results

    def process_single(
        self,
        input_file: str,
        output_file: str,
    ) -> Dict[str, Any]:
        """Process a single file."""
        results = self.process_batch([(input_file, output_file)])
        return results[0] if results else {'success': False, 'error': 'No results'}

    def _create_job(self, input_file: Path, output_file: Path) -> PipelineJob:
        """Create a new pipeline job."""
        self.job_counter += 1
        job = PipelineJob(
            job_id=self.job_counter,
            input_file=input_file,
            output_file=output_file,
            start_time=datetime.now(),
        )
        self.jobs[job.job_id] = job
        return job
