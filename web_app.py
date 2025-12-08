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
    progress_callback=None
) -> Dict:
    """Run transcription and return result."""

    script_path = PROJECT_ROOT / "scripts" / "transcribe_pipeline.py"

    cmd = [
        sys.executable,
        str(script_path),
        input_path,
        output_path,
        '--model', model,
        '--transcribe-processes', str(processes),
        '--transcribe-workers', str(workers),
        '--preprocess-workers', '2'
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

    # Upload section
    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload Audio File",
            type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'webm'],
            help="Supported formats: MP3, WAV, M4A, FLAC, OGG, WEBM"
        )

    with col2:
        st.markdown("**Model Selection**")
        model = st.selectbox(
            "Whisper Model",
            options=['medium', 'large-v3'],
            index=0,
            help="medium: faster, large-v3: more accurate"
        )

        # Auto calculate workers
        auto_proc, auto_workers = calculate_optimal_workers(model)

        mode = st.radio("Worker Mode", ["Auto", "Manual"], horizontal=True)

        if mode == "Auto":
            processes = auto_proc
            workers = auto_workers
            st.info(f"Auto: {processes} proc × {workers} workers")
        else:
            processes = st.number_input("Processes", min_value=1, max_value=4, value=2)
            workers = st.number_input("Workers/Process", min_value=4, max_value=16, value=8)

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

            # Progress container
            progress_container = st.container()

            with progress_container:
                st.markdown("### Processing...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_expander = st.expander("View Logs", expanded=False)
                log_area = log_expander.empty()

                logs = []

                def update_progress(line: str):
                    logs.append(line)
                    log_area.code('\n'.join(logs[-20:]), language='text')

                    # Parse progress from log
                    if "%" in line and "Process" in line:
                        try:
                            match = re.search(r'\((\d+\.?\d*)%\)', line)
                            if match:
                                pct = float(match.group(1))
                                progress_bar.progress(int(pct))
                                status_text.text(f"Transcribing... {pct:.1f}%")
                                # Update job progress
                                update_job_status(job_id, 'processing', progress=pct)
                        except:
                            pass
                    elif "Preprocessing" in line or "enhancement" in line.lower():
                        status_text.text("Preprocessing audio...")
                        progress_bar.progress(5)
                    elif "COMPLETED" in line:
                        progress_bar.progress(100)
                        status_text.text("Completed!")

                # Run transcription
                start_time = time.time()
                result = run_transcription(
                    str(temp_input),
                    str(output_path),
                    model,
                    processes,
                    workers,
                    update_progress
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

    # Get jobs from database
    jobs = get_jobs(limit=50)

    if not jobs:
        st.info("No transcription history yet. Start by transcribing an audio file!")
        return

    # Filter options
    col1, col2 = st.columns([3, 1])
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=['All', 'completed', 'failed', 'processing', 'pending'],
            index=0
        )

    if status_filter != 'All':
        jobs = [j for j in jobs if j['status'] == status_filter]

    st.markdown("---")

    # History list
    for job in jobs:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

            with col1:
                status_icons = {
                    'completed': '✅',
                    'failed': '❌',
                    'processing': '⏳',
                    'pending': '🕐'
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
                if job['status'] == 'completed' and job['speed']:
                    st.metric("Speed", f"{job['speed']:.1f}x", label_visibility="collapsed")
                elif job['status'] == 'processing':
                    st.metric("Progress", f"{job['progress']:.0f}%", label_visibility="collapsed")
                else:
                    st.caption(job['status'])

            with col5:
                # Download button if output exists
                if job['output_path'] and Path(job['output_path']).exists():
                    with open(job['output_path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.download_button(
                        "📥",
                        content,
                        file_name=Path(job['output_path']).name,
                        key=f"download_{job['id']}"
                    )

                # Delete button
                if st.button("🗑️", key=f"delete_{job['id']}"):
                    delete_job(job['id'])
                    st.rerun()

            st.markdown("---")

    # Clear all button
    if st.button("🗑️ Clear All History", type="secondary"):
        clear_all_jobs()
        st.rerun()


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


def show_settings_page():
    """Show settings page."""
    st.markdown('<p class="main-header">⚙️ Settings</p>', unsafe_allow_html=True)

    # Model settings
    st.markdown("### Model Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Available Models**")

        models_dir = PROJECT_ROOT / "models"
        for model in ['whisper-medium-mlx', 'whisper-large-v3-mlx']:
            model_path = models_dir / model / "weights.npz"
            if model_path.exists():
                size = model_path.stat().st_size / (1024**3)
                st.success(f"✅ {model} ({size:.1f} GB)")
            else:
                st.warning(f"⚠️ {model} (not downloaded)")

    with col2:
        st.markdown("**Download Models**")
        if st.button("📥 Download Missing Models"):
            with st.spinner("Downloading models..."):
                result = subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / "scripts" / "download_models.py")],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("Models downloaded successfully!")
                else:
                    st.error(f"Download failed: {result.stderr}")

    st.markdown("---")

    # Worker settings
    st.markdown("### Default Worker Configuration")

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

    # Storage
    st.markdown("### Storage")

    uploads_size = sum(f.stat().st_size for f in UPLOADS_DIR.glob('*') if f.is_file()) / (1024**2)
    outputs_size = sum(f.stat().st_size for f in OUTPUTS_DIR.glob('*') if f.is_file()) / (1024**2)

    # Database size
    db_path = PROJECT_ROOT / "data" / "transcriptor.db"
    db_size = db_path.stat().st_size / (1024**2) if db_path.exists() else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Uploads", f"{uploads_size:.1f} MB")
    col2.metric("Outputs", f"{outputs_size:.1f} MB")
    col3.metric("Database", f"{db_size:.2f} MB")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear Uploaded Files"):
            shutil.rmtree(UPLOADS_DIR)
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            st.success("Uploads cleared!")
            st.rerun()

    with col2:
        if st.button("🗑️ Clear Output Files"):
            shutil.rmtree(OUTPUTS_DIR)
            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
            st.success("Outputs cleared!")
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
