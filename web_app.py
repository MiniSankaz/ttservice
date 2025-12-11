#!/usr/bin/env python3
"""
Transcriptor Pipeline - Streamlit Web UI

A web-based interface for Thai audio transcription using MLX Whisper.

Features:
- Upload audio files (MP3, WAV, M4A, FLAC)
- Real-time progress tracking
- History management with SQLite
- Export to multiple formats (TXT, JSON, SRT)
"""

import streamlit as st
import os
import sys
import json
import time
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import database module
from app.database import (
    init_database,
    create_job,
    update_job_status,
    complete_job,
    fail_job,
    get_job,
    get_jobs,
    get_recent_jobs,
    delete_job,
    clear_all_jobs,
    get_statistics,
    get_setting,
    set_setting,
    migrate_from_json
)

# Initialize database
init_database()

# Page config
st.set_page_config(
    page_title="Transcriptor - Thai Audio Transcription",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm']
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Migrate old JSON history if exists
old_history_file = PROJECT_ROOT / "data" / "history.json"
if old_history_file.exists():
    migrated = migrate_from_json(old_history_file)
    if migrated > 0:
        # Rename old file
        old_history_file.rename(old_history_file.with_suffix('.json.bak'))


def get_system_resources():
    """Get system CPU and memory info."""
    try:
        cpu_result = subprocess.run(['sysctl', '-n', 'hw.ncpu'], capture_output=True, text=True)
        cpu_cores = int(cpu_result.stdout.strip())

        mem_result = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
        memory_gb = int(mem_result.stdout.strip()) / (1024**3)

        return cpu_cores, memory_gb
    except:
        return 10, 16.0


def calculate_optimal_workers(model: str) -> tuple:
    """Calculate optimal processes and workers."""
    cpu_cores, memory_gb = get_system_resources()

    model_memory = {'medium': 0.5, 'large-v3': 1.5}
    mem_per_model = model_memory.get(model, 0.5)

    usable_cores = int(cpu_cores * 0.8)
    usable_memory = memory_gb * 0.8

    max_workers_by_memory = int(usable_memory / mem_per_model)
    total_workers = min(usable_cores, max_workers_by_memory)
    total_workers = max(8, total_workers)

    if total_workers >= 16:
        processes = 2
        workers = total_workers // 2
    else:
        processes = 1
        workers = total_workers

    return processes, workers


def get_audio_duration(file_path: str) -> float:
    """Get audio duration in minutes."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip()) / 60
    except:
        return 0.0


def run_transcription(
    input_path: str,
    output_path: str,
    model: str,
    processes: int,
    workers: int,
    progress_callback=None,
    chunk_duration: int = 20,
    overlap_duration: int = 3,
    job_id: int = None
) -> Dict:
    """Run transcription and return result."""
    from lib.process_manager import get_process_manager

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
    pm = get_process_manager()

    # Use ProcessManager if job_id provided
    if job_id:
        process = pm.start_process(
            job_id=job_id,
            cmd=cmd,
            progress_callback=progress_callback
        )

        # Wait for process to complete
        logs = []
        while process.poll() is None:
            # Check for cancellation via session state
            if 'cancel_job' in st.session_state and st.session_state.cancel_job == job_id:
                pm.stop_process(job_id)
                st.session_state.cancel_job = None
                return {
                    'success': False,
                    'elapsed_seconds': time.time() - start_time,
                    'logs': pm.get_logs(job_id),
                    'cancelled': True
                }

            # Get logs from process manager
            time.sleep(0.5)

        logs = pm.get_logs(job_id)
        elapsed = time.time() - start_time
        success = process.returncode == 0

    else:
        # Fallback to original behavior
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        logs = []
        for line in process.stdout:
            logs.append(line.strip())
            if progress_callback:
                progress_callback(line.strip())

        process.wait()
        elapsed = time.time() - start_time
        success = process.returncode == 0

    return {
        'success': success,
        'elapsed_seconds': elapsed,
        'logs': logs
    }


# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .history-item {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .status-pending { color: #ffc107; }
    .status-processing { color: #17a2b8; }
    .status-completed { color: #28a745; }
    .status-failed { color: #dc3545; }
</style>
""", unsafe_allow_html=True)


def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/microphone.png", width=60)
        st.title("Transcriptor")
        st.markdown("Thai Audio Transcription")
        st.markdown("---")

        # Navigation
        page = st.radio(
            "Navigation",
            ["🎙️ Transcribe", "📜 History", "📊 Statistics", "⚙️ Settings", "ℹ️ About"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # System info
        cpu_cores, memory_gb = get_system_resources()
        st.markdown("**System Info**")
        st.text(f"CPU Cores: {cpu_cores}")
        st.text(f"Memory: {memory_gb:.1f} GB")

        # Database info
        stats = get_statistics()
        st.markdown("---")
        st.markdown("**Database**")
        st.text(f"Total Jobs: {stats['total_jobs']}")

    # Main content based on page
    if page == "🎙️ Transcribe":
        show_transcribe_page()
    elif page == "📜 History":
        show_history_page()
    elif page == "📊 Statistics":
        show_statistics_page()
    elif page == "⚙️ Settings":
        show_settings_page()
    elif page == "ℹ️ About":
        show_about_page()


def show_transcribe_page():
    """Show transcription page."""
    st.markdown('<p class="main-header">🎙️ Audio Transcription</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload audio files and transcribe to text using MLX Whisper</p>', unsafe_allow_html=True)

    # Upload section with enhanced drag & drop
    st.markdown("""
    <style>
    /* Enhanced drag & drop styling */
    [data-testid="stFileUploader"] {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #667eea;
        background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
    }
    [data-testid="stFileUploader"] section {
        padding: 10px;
    }
    [data-testid="stFileUploader"] section > div {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**🎵 Drag & Drop or Click to Upload**")
        uploaded_file = st.file_uploader(
            "Upload Audio File",
            type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'webm'],
            help="📁 Drag and drop your audio file here, or click to browse. Supported: MP3, WAV, M4A, FLAC, OGG, WEBM",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**Model Selection**")

        # Get installed models
        installed_models = [m for m in get_available_models() if m['installed']]

        if installed_models:
            model_options = [m['short_name'] for m in installed_models]
            model_labels = [f"{m['display_name']} ({m['size_gb']:.1f}GB)" for m in installed_models]

            model = st.selectbox(
                "Whisper Model",
                options=model_options,
                format_func=lambda x: next((m['display_name'] for m in installed_models if m['short_name'] == x), x),
                index=0,
                help="Select a model for transcription"
            )
        else:
            st.warning("No models installed! Go to Settings to download.")
            model = 'medium'

        # Auto calculate workers
        auto_proc, auto_workers = calculate_optimal_workers(model)

        mode = st.radio("Worker Mode", ["Auto", "Manual"], horizontal=True)

        if mode == "Auto":
            processes = auto_proc
            workers = auto_workers
            st.info(f"Auto: {processes} proc × {workers} workers")
        else:
            processes = st.number_input("Processes", min_value=1, max_value=8, value=2)
            workers = st.number_input("Workers/Process", min_value=4, max_value=16, value=8)

    # Chunk duration config (outside col2 to be accessible later)
    st.markdown("**⚙️ Chunk Settings**")
    with st.expander("Advanced Chunking Options", expanded=False):
        chunk_col1, chunk_col2 = st.columns(2)
        with chunk_col1:
            chunk_duration = st.slider(
                "Chunk Duration (seconds)",
                min_value=15,
                max_value=25,
                value=20,
                step=1,
                help="Audio is split into chunks for parallel processing. Default: 20s (±5s range)"
            )
        with chunk_col2:
            overlap_duration = st.slider(
                "Overlap Duration (seconds)",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                help="Overlap between chunks to preserve context. Default: 3s"
            )
        st.caption(f"📊 Effective chunk: {chunk_duration}s with {overlap_duration}s overlap")

    # Process button
    if uploaded_file is not None:
        # Show file info
        st.markdown("---")
        st.markdown("**File Information**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Filename", uploaded_file.name)
        col2.metric("Size", f"{uploaded_file.size / (1024*1024):.1f} MB")
        col3.metric("Type", uploaded_file.type.split('/')[-1].upper())

        # Save uploaded file
        temp_input = UPLOADS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
        with open(temp_input, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        # Get duration
        duration = get_audio_duration(str(temp_input))
        if duration > 0:
            st.metric("Duration", f"{duration:.1f} minutes")

        # Transcribe button
        if st.button("🚀 Start Transcription", type="primary", use_container_width=True):
            # Create job in database
            job_id = create_job(
                filename=uploaded_file.name,
                original_path=str(temp_input),
                duration_minutes=duration,
                model=model,
                processes=processes,
                workers=workers
            )

            # Output path
            output_name = temp_input.stem
            output_path = OUTPUTS_DIR / f"{output_name}.txt"

            # Update job status
            update_job_status(job_id, 'processing')

            # Progress container with Real-time logs
            progress_container = st.container()

            with progress_container:
                st.markdown("### 🔄 Processing...")

                # Progress section
                col_progress, col_stats = st.columns([3, 1])
                with col_progress:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                with col_stats:
                    chunks_text = st.empty()
                    speed_text = st.empty()

                # Real-time log section - always visible
                st.markdown("### 📋 Real-time Logs")
                log_container = st.container()
                log_area = log_container.empty()

                logs = []
                current_phase = "initializing"
                chunks_done = 0
                total_chunks = 0
                process_progress = {}  # Track progress per process
                transcription_start = None
                audio_duration_sec = duration * 60  # Convert minutes to seconds

                def update_progress(line: str):
                    nonlocal current_phase, chunks_done, total_chunks, logs
                    nonlocal process_progress, transcription_start

                    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")

                    # Keep last 30 lines and display with syntax highlighting
                    display_logs = logs[-30:]
                    log_text = '\n'.join(display_logs)
                    log_area.code(log_text, language='bash')

                    # Parse different phases and progress
                    line_lower = line.lower()

                    # Phase detection
                    if "loading" in line_lower or "initializing" in line_lower:
                        current_phase = "loading"
                        status_text.markdown("⏳ **Loading model...**")
                        progress_bar.progress(2)
                    elif "preprocessing" in line_lower or "enhancement" in line_lower:
                        current_phase = "preprocessing"
                        status_text.markdown("🔧 **Preprocessing audio...**")
                        progress_bar.progress(5)
                    elif "chunking" in line_lower or "splitting" in line_lower:
                        current_phase = "chunking"
                        status_text.markdown("✂️ **Splitting audio into chunks...**")
                        progress_bar.progress(10)
                        # Try to extract total chunks
                        match = re.search(r'(\d+)\s*chunks?', line)
                        if match:
                            total_chunks = int(match.group(1))
                            chunks_text.metric("Chunks", f"0/{total_chunks}")
                    elif "transcrib" in line_lower:
                        current_phase = "transcribing"
                        if transcription_start is None:
                            transcription_start = time.time()

                    # Progress percentage parsing - track per process
                    if "%" in line:
                        try:
                            # Look for process ID and percentage patterns
                            # Format: [Process-0] ... 45.2% or Process 1: 45.2%
                            proc_match = re.search(r'[Pp]rocess[- ]?(\d+)', line)
                            pct_match = re.search(r'(\d+\.?\d*)%', line)

                            if pct_match:
                                pct = float(pct_match.group(1))
                                proc_id = proc_match.group(1) if proc_match else "0"
                                process_progress[proc_id] = pct

                                # Calculate average progress from all processes
                                if process_progress:
                                    avg_pct = sum(process_progress.values()) / len(process_progress)
                                else:
                                    avg_pct = pct

                                # Map to 10-95% range for transcription phase
                                display_pct = 10 + (avg_pct * 0.85)
                                progress_bar.progress(int(min(display_pct, 95)))

                                # Calculate realtime speed
                                if transcription_start and audio_duration_sec > 0:
                                    elapsed_sec = time.time() - transcription_start
                                    if elapsed_sec > 0 and avg_pct > 0:
                                        # Estimate total time and calculate speed
                                        processed_audio = (avg_pct / 100) * audio_duration_sec
                                        current_speed = processed_audio / elapsed_sec
                                        speed_text.metric("Speed", f"{current_speed:.2f}x")

                                # Show progress with process count
                                proc_info = f" ({len(process_progress)} proc)" if len(process_progress) > 1 else ""
                                status_text.markdown(f"🎤 **Transcribing... {avg_pct:.1f}%{proc_info}**")
                                update_job_status(job_id, 'processing', progress=avg_pct)
                        except:
                            pass

                    # Chunk completion parsing
                    if "chunk" in line_lower and ("done" in line_lower or "completed" in line_lower or "✓" in line):
                        chunks_done += 1
                        if total_chunks > 0:
                            chunks_text.metric("Chunks", f"{chunks_done}/{total_chunks}")
                            chunk_pct = (chunks_done / total_chunks) * 100
                            speed_text.metric("Progress", f"{chunk_pct:.0f}%")

                    # Speed parsing
                    if "speed" in line_lower or "realtime" in line_lower:
                        match = re.search(r'(\d+\.?\d*)x', line)
                        if match:
                            speed_text.metric("Speed", f"{match.group(1)}x")

                    # Completion detection
                    if "completed" in line_lower or "finished" in line_lower or "success" in line_lower:
                        progress_bar.progress(100)
                        status_text.markdown("✅ **Completed!**")

                # Run transcription with process tracking
                start_time = time.time()
                result = run_transcription(
                    str(temp_input),
                    str(output_path),
                    model,
                    processes,
                    workers,
                    update_progress,
                    chunk_duration,
                    overlap_duration,
                    job_id=job_id
                )
                elapsed = time.time() - start_time

                progress_bar.progress(100)

            # Show result
            st.markdown("---")

            if result['success']:
                st.success(f"✅ Transcription completed in {elapsed/60:.1f} minutes!")

                # Speed calculation
                speed = duration / (elapsed / 60) if duration > 0 else 0
                if duration > 0:
                    st.metric("Speed", f"{speed:.2f}x realtime")

                # Read transcript
                transcript = ""
                if output_path.exists():
                    with open(output_path, 'r', encoding='utf-8') as f:
                        transcript = f.read()

                # Complete job in database
                complete_job(
                    job_id=job_id,
                    output_path=str(output_path),
                    transcript=transcript[:5000],  # Store first 5000 chars
                    elapsed_seconds=elapsed,
                    speed=speed
                )

                # Read output files
                txt_path = output_path
                json_path = output_path.with_suffix('.json')
                srt_path = output_path.with_suffix('.srt')

                # Display transcript
                if txt_path.exists():
                    st.markdown("### 📝 Transcript")
                    st.text_area("", transcript, height=300, label_visibility="collapsed")

                    # Download buttons
                    st.markdown("### 📥 Download")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.download_button(
                            "📄 Download TXT",
                            transcript,
                            file_name=f"{output_name}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                    with col2:
                        if json_path.exists():
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_content = f.read()
                            st.download_button(
                                "📋 Download JSON",
                                json_content,
                                file_name=f"{output_name}.json",
                                mime="application/json",
                                use_container_width=True
                            )

                    with col3:
                        if srt_path.exists():
                            with open(srt_path, 'r', encoding='utf-8') as f:
                                srt_content = f.read()
                            st.download_button(
                                "🎬 Download SRT",
                                srt_content,
                                file_name=f"{output_name}.srt",
                                mime="text/plain",
                                use_container_width=True
                            )

            else:
                st.error("❌ Transcription failed!")
                st.code('\n'.join(result['logs'][-30:]))

                # Fail job in database
                fail_job(job_id, '\n'.join(result['logs'][-5:]))


def show_history_page():
    """Show history page."""
    st.markdown('<p class="main-header">📜 Transcription History</p>', unsafe_allow_html=True)

    # Check if viewing specific job details
    if 'view_job_id' in st.session_state and st.session_state.view_job_id:
        show_job_details(st.session_state.view_job_id)
        return

    # Get jobs from database
    jobs = get_jobs(limit=50)

    if not jobs:
        st.info("No transcription history yet. Start by transcribing an audio file!")
        return

    # Filter options
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=['All', 'completed', 'failed', 'processing', 'pending', 'cancelled'],
            index=0
        )
    with col3:
        # Cleanup orphaned jobs button
        if st.button("🧹 Cleanup Stale", help="Clean up orphaned/stale jobs"):
            from app.database import cleanup_stale_jobs
            cleaned = cleanup_stale_jobs()
            if cleaned > 0:
                st.success(f"Cleaned up {cleaned} stale jobs")
                st.rerun()
            else:
                st.info("No stale jobs found")

    if status_filter != 'All':
        jobs = [j for j in jobs if j['status'] == status_filter]

    st.markdown("---")

    # History list
    for job in jobs:
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])

            with col1:
                status_icons = {
                    'completed': '✅',
                    'failed': '❌',
                    'processing': '⏳',
                    'pending': '🕐',
                    'cancelled': '🛑'
                }
                status_icon = status_icons.get(job['status'], '❓')
                st.markdown(f"**{status_icon} {job['filename']}**")

                if job['created_at']:
                    st.caption(job['created_at'][:16].replace('T', ' '))

            with col2:
                st.metric("Duration", f"{job['duration_minutes']:.1f} min", label_visibility="collapsed")

            with col3:
                st.metric("Model", job['model'], label_visibility="collapsed")

            with col4:
                if job['status'] == 'completed' and job.get('speed'):
                    st.metric("Speed", f"{job['speed']:.1f}x", label_visibility="collapsed")
                elif job['status'] == 'processing':
                    progress = job.get('progress') or 0
                    st.metric("Progress", f"{progress:.0f}%", label_visibility="collapsed")
                else:
                    st.caption(job['status'])

            with col5:
                # View Details button - available for all statuses
                view_label = "👁️ View" if job['status'] == 'completed' else "👁️ Monitor" if job['status'] == 'processing' else "👁️ View"
                if st.button(view_label, key=f"view_{job['id']}"):
                    st.session_state.view_job_id = job['id']
                    st.rerun()

            with col6:
                # Stop button for processing jobs
                if job['status'] == 'processing':
                    if st.button("🛑", key=f"stop_{job['id']}", help="Stop this job"):
                        import os
                        import signal
                        from app.database import cancel_job

                        # Kill process using PID from database
                        pid = job.get('pid')
                        if pid:
                            try:
                                os.kill(pid, signal.SIGTERM)
                                time.sleep(0.5)
                                # Force kill if still running
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            except ProcessLookupError:
                                pass  # Process already dead
                            except Exception as e:
                                st.warning(f"Could not kill process: {e}")

                        cancel_job(job['id'], "Cancelled by user")
                        st.success(f"Job {job['id']} cancelled")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    # Delete button
                    if st.button("🗑️", key=f"delete_{job['id']}"):
                        delete_job(job['id'])
                        st.rerun()

            st.markdown("---")

    # Clear all button
    if st.button("🗑️ Clear All History", type="secondary"):
        clear_all_jobs()
        st.rerun()


def convert_srt_to_txt(srt_content: str) -> str:
    """Convert SRT format to plain text with timestamps."""
    lines = []
    current_timestamp = ""

    for line in srt_content.split('\n'):
        line = line.strip()
        # Skip sequence numbers
        if line.isdigit():
            continue
        # Capture timestamp
        if '-->' in line:
            # Extract start time
            start_time = line.split('-->')[0].strip()
            current_timestamp = start_time
        elif line:
            # This is subtitle text
            lines.append(f"[{current_timestamp}] {line}")

    return '\n'.join(lines)


def show_job_details(job_id: int):
    """Show detailed view of a specific job."""
    job = get_job(job_id)

    if not job:
        st.error("Job not found!")
        if st.button("← Back to History"):
            st.session_state.view_job_id = None
            st.rerun()
        return

    # Back button
    if st.button("← Back to History"):
        st.session_state.view_job_id = None
        st.rerun()

    st.markdown("---")

    # Job info header
    status_icons = {
        'completed': '✅',
        'failed': '❌',
        'processing': '⏳',
        'pending': '🕐',
        'cancelled': '🛑'
    }
    status_icon = status_icons.get(job['status'], '❓')

    st.markdown(f"## {status_icon} {job['filename']}")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Duration", f"{job['duration_minutes']:.1f} min")
    col2.metric("Model", job['model'])
    col3.metric("Config", f"{job['processes']}P × {job['workers']}W")
    if job['speed']:
        col4.metric("Speed", f"{job['speed']:.2f}x")

    # Timestamps
    st.caption(f"Created: {job['created_at'][:19].replace('T', ' ') if job['created_at'] else 'N/A'}")
    if job['completed_at']:
        st.caption(f"Completed: {job['completed_at'][:19].replace('T', ' ')}")

    st.markdown("---")

    # For processing jobs, show live progress with logs
    if job['status'] == 'processing':
        st.markdown("### ⏳ Processing in Progress")

        # Stop button
        col_stop, col_info = st.columns([1, 3])
        with col_stop:
            if st.button("🛑 Stop Job", type="primary", use_container_width=True):
                import os
                import signal
                from app.database import cancel_job

                # Kill process using PID from database
                pid = job.get('pid')
                if pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(0.5)
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except ProcessLookupError:
                        pass
                    except Exception as e:
                        st.warning(f"Could not kill process: {e}")

                cancel_job(job['id'], "Cancelled by user")
                st.warning("Job cancelled!")
                time.sleep(1)
                st.rerun()

        with col_info:
            # PID info
            if job.get('pid'):
                st.caption(f"🔧 PID: {job['pid']}")

        # Progress bar
        progress = job.get('progress', 0) or 0
        st.progress(progress / 100)
        st.markdown(f"**Progress:** {progress:.1f}%")

        # Show estimated time if we have duration
        if job['duration_minutes'] and progress > 0:
            elapsed = job.get('elapsed_seconds', 0) or 0
            if elapsed > 0:
                estimated_total = elapsed / (progress / 100)
                remaining = estimated_total - elapsed
                st.caption(f"⏱️ Elapsed: {elapsed/60:.1f} min | Estimated remaining: {remaining/60:.1f} min")

        # Live log viewer
        st.markdown("### 📋 Live Logs")
        from lib.process_manager import get_process_manager
        pm = get_process_manager()

        # Get logs from process manager or log file
        logs = pm.get_logs(job['id'], last_n=50)
        if not logs and job.get('log_file'):
            # Try reading from log file
            log_file = Path(job['log_file'])
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        logs = [line.rstrip('\n') for line in lines[-50:]]
                except Exception:
                    pass

        if logs:
            log_text = '\n'.join(logs)
            st.code(log_text, language='bash')
        else:
            st.info("Waiting for logs...")

        # Auto-refresh hint
        st.info("🔄 Auto-refresh every 2 seconds. Click 'Back to History' to return.")

        # Auto-refresh every 2 seconds
        time.sleep(2)
        st.rerun()
        return

    # For pending jobs
    if job['status'] == 'pending':
        st.markdown("### 🕐 Pending")
        st.info("This job is waiting to be processed.")
        return

    # For failed jobs
    if job['status'] == 'failed':
        st.markdown("### ❌ Failed")
        if job.get('error_message'):
            st.error(job['error_message'])
        else:
            st.error("Transcription failed. Check logs for details.")

        # Show logs if available
        if job.get('log_file'):
            log_file = Path(job['log_file'])
            if log_file.exists():
                with st.expander("📋 View Logs"):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        st.code(log_content[-5000:] if len(log_content) > 5000 else log_content, language='bash')
                    except Exception as e:
                        st.warning(f"Could not read log file: {e}")
        return

    # For cancelled jobs
    if job['status'] == 'cancelled':
        st.markdown("### 🛑 Cancelled")
        if job.get('error_message'):
            st.warning(job['error_message'])
        else:
            st.warning("This job was cancelled.")

        # Show logs if available
        if job.get('log_file'):
            log_file = Path(job['log_file'])
            if log_file.exists():
                with st.expander("📋 View Logs"):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        st.code(log_content[-5000:] if len(log_content) > 5000 else log_content, language='bash')
                    except Exception as e:
                        st.warning(f"Could not read log file: {e}")
        return

    # Output files (for completed jobs)
    if job['output_path']:
        output_path = Path(job['output_path'])
        txt_path = output_path
        json_path = output_path.with_suffix('.json')
        srt_path = output_path.with_suffix('.srt')

        # Transcript display
        st.markdown("### 📝 Transcript")

        if txt_path.exists():
            with open(txt_path, 'r', encoding='utf-8') as f:
                transcript = f.read()
            st.text_area("", transcript, height=400, label_visibility="collapsed")
        elif job['transcript']:
            st.text_area("", job['transcript'], height=400, label_visibility="collapsed")
            st.caption("(Showing stored preview - full file may not be available)")

        st.markdown("---")

        # Download section with multiple options
        st.markdown("### 📥 Download Options")

        col1, col2, col3, col4 = st.columns(4)

        # TXT Download
        with col1:
            if txt_path.exists():
                with open(txt_path, 'r', encoding='utf-8') as f:
                    txt_content = f.read()
                st.download_button(
                    "📄 TXT",
                    txt_content,
                    file_name=txt_path.name,
                    mime="text/plain",
                    use_container_width=True,
                    help="Plain text transcript"
                )
            else:
                st.button("📄 TXT", disabled=True, use_container_width=True)

        # JSON Download
        with col2:
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_content = f.read()
                st.download_button(
                    "📋 JSON",
                    json_content,
                    file_name=json_path.name,
                    mime="application/json",
                    use_container_width=True,
                    help="JSON with segments and metadata"
                )
            else:
                st.button("📋 JSON", disabled=True, use_container_width=True)

        # SRT Download
        with col3:
            if srt_path.exists():
                with open(srt_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                st.download_button(
                    "🎬 SRT",
                    srt_content,
                    file_name=srt_path.name,
                    mime="text/plain",
                    use_container_width=True,
                    help="Subtitle format (SRT)"
                )
            else:
                st.button("🎬 SRT", disabled=True, use_container_width=True)

        # SRT to TXT (with timestamps)
        with col4:
            if srt_path.exists():
                with open(srt_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                srt_as_txt = convert_srt_to_txt(srt_content)
                st.download_button(
                    "⏱️ SRT→TXT",
                    srt_as_txt,
                    file_name=f"{output_path.stem}_timestamped.txt",
                    mime="text/plain",
                    use_container_width=True,
                    help="Text with timestamps from SRT"
                )
            else:
                st.button("⏱️ SRT→TXT", disabled=True, use_container_width=True)

        # File info
        st.markdown("---")
        st.markdown("### 📁 Output Files")

        files_info = []
        for path, label in [(txt_path, "TXT"), (json_path, "JSON"), (srt_path, "SRT")]:
            if path.exists():
                size_kb = path.stat().st_size / 1024
                files_info.append(f"✅ {label}: {path.name} ({size_kb:.1f} KB)")
            else:
                files_info.append(f"❌ {label}: Not available")

        for info in files_info:
            st.text(info)

    elif job['status'] == 'failed':
        st.error("Transcription failed")
        if job['error_message']:
            st.code(job['error_message'])


def show_statistics_page():
    """Show statistics page."""
    st.markdown('<p class="main-header">📊 Statistics</p>', unsafe_allow_html=True)

    stats = get_statistics()

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Jobs", stats['total_jobs'])
    col2.metric("Success Rate", f"{stats['success_rate']:.0f}%")
    col3.metric("Total Audio", f"{stats['total_audio_minutes']:.0f} min")
    col4.metric("Avg Speed", f"{stats['average_speed']:.1f}x")

    st.markdown("---")

    # Detailed stats
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Job Status")
        st.metric("✅ Completed", stats['successful_jobs'])
        st.metric("❌ Failed", stats['failed_jobs'])
        st.metric("⏳ Pending/Processing", stats['pending_jobs'])

    with col2:
        st.markdown("### Processing Time")
        st.metric("Total Processing", f"{stats['total_processing_minutes']:.1f} min")

        if stats['total_audio_minutes'] > 0 and stats['total_processing_minutes'] > 0:
            efficiency = stats['total_audio_minutes'] / stats['total_processing_minutes']
            st.metric("Overall Efficiency", f"{efficiency:.2f}x")

    st.markdown("---")

    # Recent jobs chart (if any)
    recent_jobs = get_recent_jobs(10)
    if recent_jobs:
        st.markdown("### Recent Jobs Performance")

        # Simple bar chart data
        chart_data = []
        for job in reversed(recent_jobs):
            if job['status'] == 'completed' and job['speed']:
                chart_data.append({
                    'File': job['filename'][:20],
                    'Speed': job['speed']
                })

        if chart_data:
            import pandas as pd
            df = pd.DataFrame(chart_data)
            st.bar_chart(df.set_index('File'))


def get_available_models() -> List[Dict]:
    """Get list of available models from models directory."""
    models_dir = PROJECT_ROOT / "models"
    models = []

    # Standard models
    standard_models = {
        'whisper-medium-mlx': {'display_name': 'Medium', 'short_name': 'medium'},
        'whisper-large-v3-mlx': {'display_name': 'Large-v3', 'short_name': 'large-v3'},
    }

    for model_name, info in standard_models.items():
        model_path = models_dir / model_name / "weights.npz"
        models.append({
            'name': model_name,
            'display_name': info['display_name'],
            'short_name': info['short_name'],
            'path': str(models_dir / model_name),
            'installed': model_path.exists(),
            'size_gb': model_path.stat().st_size / (1024**3) if model_path.exists() else 0,
            'is_custom': False
        })

    # Scan for custom models
    if models_dir.exists():
        for model_dir in models_dir.iterdir():
            if model_dir.is_dir() and model_dir.name not in standard_models:
                # Support both .npz and .safetensors formats
                weights_npz = model_dir / "weights.npz"
                weights_safetensors = model_dir / "weights.safetensors"
                weights_path = weights_safetensors if weights_safetensors.exists() else weights_npz
                config_path = model_dir / "config.json"
                if weights_path.exists() or config_path.exists():
                    models.append({
                        'name': model_dir.name,
                        'display_name': model_dir.name,
                        'short_name': model_dir.name,
                        'path': str(model_dir),
                        'installed': weights_path.exists(),
                        'size_gb': weights_path.stat().st_size / (1024**3) if weights_path.exists() else 0,
                        'is_custom': True
                    })

    return models


def show_settings_page():
    """Show settings page."""
    st.markdown('<p class="main-header">⚙️ Settings</p>', unsafe_allow_html=True)

    # Tabs for different settings sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 Models", "⚡ Performance", "💾 Storage", "🔧 Setup Wizard", "🤖 Claude Terminal"])

    with tab1:
        show_model_settings()

    with tab2:
        show_performance_settings()

    with tab3:
        show_storage_settings()

    with tab4:
        show_setup_wizard()

    with tab5:
        show_claude_terminal()


def show_model_settings():
    """Show model management settings."""
    st.markdown("### Installed Models")

    models = get_available_models()
    models_dir = PROJECT_ROOT / "models"

    # Display installed models
    for model in models:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            if model['installed']:
                badge = "🟢" if not model['is_custom'] else "🔵"
                st.markdown(f"{badge} **{model['display_name']}**")
                st.caption(f"`{model['name']}` ({model['size_gb']:.1f} GB)")
            else:
                st.markdown(f"⚪ **{model['display_name']}** (not installed)")

        with col2:
            if model['installed']:
                st.success("Ready")
            else:
                if st.button("📥 Install", key=f"install_{model['name']}"):
                    with st.spinner(f"Downloading {model['display_name']}..."):
                        result = subprocess.run(
                            [sys.executable, str(PROJECT_ROOT / "scripts" / "download_models.py"),
                             "--model", model['short_name']],
                            capture_output=True, text=True
                        )
                        if result.returncode == 0:
                            st.success("Downloaded!")
                            st.rerun()
                        else:
                            st.error(f"Failed: {result.stderr[:100]}")

        with col3:
            if model['is_custom'] and model['installed']:
                if st.button("🗑️", key=f"delete_model_{model['name']}"):
                    shutil.rmtree(model['path'])
                    st.rerun()

    st.markdown("---")

    # Add custom model section
    st.markdown("### Add Custom Model")

    st.info("""
    **Add MLX Whisper models from HuggingFace:**
    - Models must be in MLX format (converted from OpenAI Whisper)
    - Enter the HuggingFace model ID (e.g., `mlx-community/whisper-large-v3-turbo-mlx`)
    """)

    col1, col2 = st.columns([3, 1])

    with col1:
        hf_model_id = st.text_input(
            "HuggingFace Model ID",
            placeholder="mlx-community/whisper-large-v3-turbo-mlx",
            help="Enter full HuggingFace model ID"
        )

    with col2:
        custom_name = st.text_input(
            "Local Name (optional)",
            placeholder="whisper-turbo",
            help="Name for the local folder"
        )

    # Popular models quick select
    st.markdown("**Popular MLX Models:**")

    popular_models = [
        ("tawankri/distill-thonburian-whisper-large-v3-mlx", "🇹🇭 Thai Thonburian"),
        ("mlx-community/whisper-large-v3-turbo-mlx", "Large-v3-Turbo"),
        ("mlx-community/whisper-small-mlx", "Small"),
    ]

    cols = st.columns(len(popular_models))
    for i, (model_id, label) in enumerate(popular_models):
        with cols[i]:
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                st.session_state.quick_model_id = model_id

    # Use quick select if clicked
    if 'quick_model_id' in st.session_state and st.session_state.quick_model_id:
        hf_model_id = st.session_state.quick_model_id
        st.session_state.quick_model_id = None

    if st.button("📥 Download Model", type="primary", disabled=not hf_model_id):
        if hf_model_id:
            # Determine local name
            local_name = custom_name if custom_name else hf_model_id.split('/')[-1]
            model_path = models_dir / local_name

            with st.spinner(f"Downloading {hf_model_id}..."):
                st.info("This may take a few minutes depending on model size...")

                # Use huggingface_hub to download
                try:
                    from huggingface_hub import snapshot_download

                    snapshot_download(
                        repo_id=hf_model_id,
                        local_dir=str(model_path),
                        local_dir_use_symlinks=False
                    )

                    st.success(f"✅ Model downloaded to: {local_name}")
                    st.info("The model will be available in the Transcribe page model selection.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Download failed: {str(e)}")

    st.markdown("---")

    # Download standard models button
    if st.button("📥 Download All Standard Models"):
        with st.spinner("Downloading models..."):
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "download_models.py")],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                st.success("Models downloaded successfully!")
                st.rerun()
            else:
                st.error(f"Download failed: {result.stderr}")


def show_performance_settings():
    """Show performance settings."""
    st.markdown("### Worker Configuration")

    cpu_cores, memory_gb = get_system_resources()

    st.info(f"System: {cpu_cores} CPU cores, {memory_gb:.1f} GB RAM")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Medium Model**")
        proc, workers = calculate_optimal_workers('medium')
        st.text(f"Recommended: {proc} processes × {workers} workers")

    with col2:
        st.markdown("**Large-v3 Model**")
        proc, workers = calculate_optimal_workers('large-v3')
        st.text(f"Recommended: {proc} processes × {workers} workers")

    st.markdown("---")

    st.markdown("### Custom Worker Presets")
    st.caption("These presets can be used when selecting 'Manual' mode in Transcribe page")

    presets = [
        ("Conservative", "1P × 4W", "Lower memory usage, stable"),
        ("Balanced", "2P × 8W", "Good balance for most files"),
        ("Aggressive", "3P × 8W", "Faster, needs more memory"),
        ("Maximum", "4P × 8W", "Maximum speed, high memory"),
    ]

    for name, config, desc in presets:
        col1, col2, col3 = st.columns([2, 1, 3])
        col1.markdown(f"**{name}**")
        col2.code(config)
        col3.caption(desc)


def show_storage_settings():
    """Show storage settings."""

    uploads_size = sum(f.stat().st_size for f in UPLOADS_DIR.glob('*') if f.is_file()) / (1024**2)
    outputs_size = sum(f.stat().st_size for f in OUTPUTS_DIR.glob('*') if f.is_file()) / (1024**2)

    # Database size
    db_path = PROJECT_ROOT / "data" / "transcriptor.db"
    db_size = db_path.stat().st_size / (1024**2) if db_path.exists() else 0

    # Models size
    models_dir = PROJECT_ROOT / "models"
    models_size = 0
    if models_dir.exists():
        for f in models_dir.rglob('*'):
            if f.is_file():
                models_size += f.stat().st_size
    models_size = models_size / (1024**3)  # Convert to GB

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Uploads", f"{uploads_size:.1f} MB")
    col2.metric("Outputs", f"{outputs_size:.1f} MB")
    col3.metric("Database", f"{db_size:.2f} MB")
    col4.metric("Models", f"{models_size:.1f} GB")

    st.markdown("---")

    st.markdown("### Clean Up")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear Uploaded Files", use_container_width=True):
            shutil.rmtree(UPLOADS_DIR)
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            st.success("Uploads cleared!")
            st.rerun()

    with col2:
        if st.button("🗑️ Clear Output Files", use_container_width=True):
            shutil.rmtree(OUTPUTS_DIR)
            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
            st.success("Outputs cleared!")
            st.rerun()


def show_setup_wizard():
    """Show setup wizard for initial configuration."""
    st.markdown("### 🔧 Setup Wizard")
    st.markdown("Configure your Transcriptor environment with one click.")

    # Check system status
    st.markdown("---")
    st.markdown("### 📊 System Status")

    if st.button("🔍 Check Status", type="primary", use_container_width=True):
        status_checks = []

        # Check Python version
        import sys
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        status_checks.append(("Python", py_version, sys.version_info >= (3, 10)))

        # Check FFmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            ffmpeg_ok = result.returncode == 0
            ffmpeg_version = result.stdout.split('\n')[0] if ffmpeg_ok else "Not found"
        except:
            ffmpeg_ok = False
            ffmpeg_version = "Not installed"
        status_checks.append(("FFmpeg", ffmpeg_version[:50], ffmpeg_ok))

        # Check MLX
        try:
            import mlx
            mlx_version = mlx.__version__ if hasattr(mlx, '__version__') else "Installed"
            mlx_ok = True
        except:
            mlx_version = "Not installed"
            mlx_ok = False
        status_checks.append(("MLX", mlx_version, mlx_ok))

        # Check mlx_whisper
        try:
            import mlx_whisper
            mlx_whisper_ok = True
            mlx_whisper_version = "Installed"
        except:
            mlx_whisper_ok = False
            mlx_whisper_version = "Not installed"
        status_checks.append(("MLX Whisper", mlx_whisper_version, mlx_whisper_ok))

        # Check models directory
        models_dir = PROJECT_ROOT / "models"
        installed_models = [d.name for d in models_dir.iterdir() if d.is_dir()] if models_dir.exists() else []
        models_ok = len(installed_models) > 0
        status_checks.append(("Models", f"{len(installed_models)} installed", models_ok))

        # Check database
        db_path = PROJECT_ROOT / "data" / "transcriptor.db"
        db_ok = db_path.exists()
        status_checks.append(("Database", "Ready" if db_ok else "Not initialized", db_ok))

        # Check directories
        dirs_ok = all([UPLOADS_DIR.exists(), OUTPUTS_DIR.exists()])
        status_checks.append(("Directories", "Ready" if dirs_ok else "Missing", dirs_ok))

        # Display results
        for name, value, ok in status_checks:
            col1, col2, col3 = st.columns([2, 3, 1])
            col1.markdown(f"**{name}**")
            col2.code(value)
            col3.markdown("✅" if ok else "❌")

        # Overall status
        all_ok = all(ok for _, _, ok in status_checks)
        st.markdown("---")
        if all_ok:
            st.success("✅ All systems ready!")
        else:
            st.warning("⚠️ Some components need attention. Run the wizard to fix.")

    st.markdown("---")
    st.markdown("### 🚀 Quick Setup")

    st.info("""
    The Setup Wizard will:
    1. Create necessary directories (uploads, outputs, data)
    2. Initialize the SQLite database
    3. Download a default Whisper model (Medium)
    4. Verify all dependencies
    """)

    if st.button("🔧 Run Setup Wizard", type="primary", use_container_width=True):
        progress = st.progress(0)
        status = st.empty()

        # Step 1: Create directories
        status.markdown("📁 Creating directories...")
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "models").mkdir(parents=True, exist_ok=True)
        progress.progress(20)

        # Step 2: Initialize database
        status.markdown("💾 Initializing database...")
        try:
            init_database()
            progress.progress(40)
        except Exception as e:
            st.error(f"Database initialization failed: {e}")

        # Step 3: Check for models
        status.markdown("🤖 Checking models...")
        models_dir = PROJECT_ROOT / "models"
        installed_models = [d.name for d in models_dir.iterdir() if d.is_dir()] if models_dir.exists() else []
        progress.progress(60)

        if not installed_models:
            status.markdown("📥 Downloading default model (Medium)...")
            try:
                from huggingface_hub import snapshot_download
                snapshot_download(
                    repo_id="mlx-community/whisper-medium-mlx",
                    local_dir=str(models_dir / "whisper-medium-mlx"),
                    local_dir_use_symlinks=False
                )
                progress.progress(90)
            except Exception as e:
                st.warning(f"Model download failed: {e}")
                st.info("You can download models manually from the Models tab.")
        else:
            progress.progress(90)
            status.markdown(f"✅ Found {len(installed_models)} model(s)")

        # Step 4: Complete
        progress.progress(100)
        status.markdown("✅ **Setup Complete!**")

        st.success("🎉 Transcriptor is ready to use!")
        st.balloons()


def show_claude_terminal():
    """Show Claude terminal for AI-assisted model installation."""
    st.markdown("### 🤖 Claude Terminal")
    st.markdown("AI-assisted terminal for installing and managing models.")

    st.info("""
    **How to use:**
    1. Type a command or question below
    2. Claude will help you install models or troubleshoot issues
    3. Commands are executed in the project directory

    **Example prompts:**
    - "Install the Thai Thonburian model"
    - "List all available MLX Whisper models"
    - "Check system requirements"
    """)

    # Claude chat interface
    if 'claude_history' not in st.session_state:
        st.session_state.claude_history = []

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.claude_history[-10:]:  # Show last 10 messages
            if msg['role'] == 'user':
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**Claude:** {msg['content']}")
                if 'command' in msg:
                    st.code(msg['command'], language='bash')
                if 'output' in msg:
                    with st.expander("Command Output"):
                        st.code(msg['output'])

    st.markdown("---")

    # Input
    user_input = st.text_input(
        "Ask Claude...",
        placeholder="e.g., Install the Thai Thonburian model",
        key="claude_input"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("🚀 Send", type="primary", use_container_width=True) and user_input:
            st.session_state.claude_history.append({'role': 'user', 'content': user_input})

            # Simple command parsing for common tasks
            response = {'role': 'assistant', 'content': ''}

            user_lower = user_input.lower()

            if 'install' in user_lower and 'thonburian' in user_lower:
                response['content'] = "Installing Thai Thonburian model..."
                response['command'] = "python -c \"from huggingface_hub import snapshot_download; snapshot_download('tawankri/distill-thonburian-whisper-large-v3-mlx', local_dir='models/distill-thonburian-whisper-large-v3-mlx')\""

                with st.spinner("Downloading model..."):
                    try:
                        from huggingface_hub import snapshot_download
                        snapshot_download(
                            repo_id='tawankri/distill-thonburian-whisper-large-v3-mlx',
                            local_dir=str(PROJECT_ROOT / 'models' / 'distill-thonburian-whisper-large-v3-mlx'),
                            local_dir_use_symlinks=False
                        )
                        response['output'] = "✅ Model installed successfully!"
                    except Exception as e:
                        response['output'] = f"❌ Error: {e}"

            elif 'list' in user_lower and 'model' in user_lower:
                response['content'] = "Listing installed models..."
                models_dir = PROJECT_ROOT / "models"
                if models_dir.exists():
                    models = [d.name for d in models_dir.iterdir() if d.is_dir()]
                    response['output'] = f"Installed models ({len(models)}):\n" + "\n".join(f"  - {m}" for m in models)
                else:
                    response['output'] = "No models directory found."

            elif 'check' in user_lower or 'status' in user_lower:
                response['content'] = "Checking system status..."
                checks = []
                try:
                    import mlx
                    checks.append("✅ MLX installed")
                except:
                    checks.append("❌ MLX not installed")
                try:
                    import mlx_whisper
                    checks.append("✅ MLX Whisper installed")
                except:
                    checks.append("❌ MLX Whisper not installed")
                response['output'] = "\n".join(checks)

            elif 'help' in user_lower:
                response['content'] = """Available commands:
- **install thonburian** - Install Thai Thonburian model
- **install medium** - Install Whisper Medium model
- **list models** - Show installed models
- **check status** - Check system status
- **help** - Show this help"""

            elif 'install' in user_lower and 'medium' in user_lower:
                response['content'] = "Installing Whisper Medium model..."
                with st.spinner("Downloading model..."):
                    try:
                        from huggingface_hub import snapshot_download
                        snapshot_download(
                            repo_id='mlx-community/whisper-medium-mlx',
                            local_dir=str(PROJECT_ROOT / 'models' / 'whisper-medium-mlx'),
                            local_dir_use_symlinks=False
                        )
                        response['output'] = "✅ Model installed successfully!"
                    except Exception as e:
                        response['output'] = f"❌ Error: {e}"

            else:
                response['content'] = f"I understand you want to: {user_input}\n\nFor now, I can help with:\n- **install thonburian** - Install Thai Thonburian model\n- **install medium** - Install Whisper Medium model\n- **list models** - Show installed models\n- **check status** - Check system status\n- **help** - Show available commands"

            st.session_state.claude_history.append(response)
            st.rerun()

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.claude_history = []
            st.rerun()


def show_about_page():
    """Show about page."""
    st.markdown('<p class="main-header">ℹ️ About</p>', unsafe_allow_html=True)

    st.markdown("""
    ### Transcriptor Pipeline Pilot

    **Version:** 1.1.0

    Thai audio transcription service using MLX Whisper on Apple Silicon.

    ---

    ### Features

    - 🎙️ **Audio Transcription** - Support MP3, WAV, M4A, FLAC, OGG, WEBM
    - 🚀 **MLX Whisper** - Optimized for Apple Silicon (M1/M2/M3/M4)
    - 📊 **Real-time Progress** - Track transcription progress
    - 📜 **History** - View past transcriptions (SQLite database)
    - 📥 **Export** - Download as TXT, JSON, or SRT
    - 📈 **Statistics** - Track performance metrics

    ---

    ### Database

    Using **SQLite** for persistent storage:
    - Transcription job history
    - Performance statistics
    - User settings

    ---

    ### Models

    | Model | Size | Speed | Accuracy |
    |-------|------|-------|----------|
    | medium | 1.4 GB | ~4x realtime | Good |
    | large-v3 | 2.9 GB | ~1.8x realtime | Best |

    ---

    ### Performance (M2 Pro)

    | Audio | Model | Time | Speed |
    |-------|-------|------|-------|
    | 10 min | medium | 3.5 min | 2.86x |
    | 74 min | medium | 18.7 min | 3.98x |
    | 74 min | large-v3 | 41.2 min | 1.80x |

    ---

    ### Requirements

    - Apple Silicon Mac (M1/M2/M3/M4)
    - macOS 12.0+
    - Python 3.11+
    - FFmpeg

    ---

    ### Credits

    - [MLX](https://github.com/ml-explore/mlx) - Apple's ML framework
    - [MLX Whisper](https://github.com/ml-explore/mlx-examples) - Whisper implementation
    - [Streamlit](https://streamlit.io) - Web UI framework

    ---

    *Built with ❤️ for Thai audio transcription*
    """)


if __name__ == "__main__":
    main()
