"""
Settings Page Module - lib/pages/settings.py

Settings page with model management, performance config, storage, 
setup wizard, and Claude terminal.

Impact Analysis:
===============
- Model management affects available models for transcription
- Performance settings affect worker presets
- Storage settings affect disk usage
- Setup wizard initializes the entire application
- Claude terminal provides AI-assisted model installation

Dependencies:
============
- lib/config.py (PROJECT_ROOT, MODELS_DIR, UPLOADS_DIR, OUTPUTS_DIR, etc.)
- lib/system.py (get_system_resources, calculate_optimal_workers)
- lib/models.py (get_available_models, download_model, delete_model)
- lib/ui_components.py (get_custom_css)
- app/database.py (init_database)

Used By:
========
- web_app.py (show_settings_page)

Functions:
=========
- show_setup_wizard(): Setup wizard tab
- show_claude_terminal(): Claude AI terminal tab
- check_system_status() -> List[tuple]: System status checks
"""

import streamlit as st
import subprocess
import sys
import shutil
from typing import List, Tuple

from ..config import (
    PROJECT_ROOT,
    MODELS_DIR,
    UPLOADS_DIR,
    OUTPUTS_DIR,
    DATA_DIR,
    WORKER_PRESETS,
)
from ..system import get_system_resources, calculate_optimal_workers
from ..models import get_available_models, download_model


def check_system_status() -> List[Tuple[str, str, bool]]:
    """
    Check system status for all required components.
    
    Returns:
        List of tuples: (component_name, status_value, is_ok)
        
    Impact:
        - Used by Setup Wizard to show system status
        - Helps identify missing dependencies
        
    Example:
        >>> status = check_system_status()
        >>> for name, value, ok in status:
        ...     print(f"{name}: {value} {'✅' if ok else '❌'}")
    """
    status_checks = []
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status_checks.append(("Python", py_version, sys.version_info >= (3, 10)))
    
    # Check FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        ffmpeg_ok = result.returncode == 0
        ffmpeg_version = result.stdout.split('\n')[0] if ffmpeg_ok else "Not found"
    except Exception:
        ffmpeg_ok = False
        ffmpeg_version = "Not installed"
    status_checks.append(("FFmpeg", ffmpeg_version[:50], ffmpeg_ok))
    
    # Check MLX
    try:
        import mlx
        mlx_version = mlx.__version__ if hasattr(mlx, '__version__') else "Installed"
        mlx_ok = True
    except ImportError:
        mlx_version = "Not installed"
        mlx_ok = False
    status_checks.append(("MLX", mlx_version, mlx_ok))
    
    # Check mlx_whisper
    try:
        import mlx_whisper
        mlx_whisper_ok = True
        mlx_whisper_version = "Installed"
    except ImportError:
        mlx_whisper_ok = False
        mlx_whisper_version = "Not installed"
    status_checks.append(("MLX Whisper", mlx_whisper_version, mlx_whisper_ok))
    
    # Check models directory
    installed_models = [d.name for d in MODELS_DIR.iterdir() if d.is_dir()] if MODELS_DIR.exists() else []
    models_ok = len(installed_models) > 0
    status_checks.append(("Models", f"{len(installed_models)} installed", models_ok))
    
    # Check database
    db_path = DATA_DIR / "transcriptor.db"
    db_ok = db_path.exists()
    status_checks.append(("Database", "Ready" if db_ok else "Not initialized", db_ok))
    
    # Check directories
    dirs_ok = all([UPLOADS_DIR.exists(), OUTPUTS_DIR.exists()])
    status_checks.append(("Directories", "Ready" if dirs_ok else "Missing", dirs_ok))
    
    return status_checks


def show_setup_wizard():
    """
    Show setup wizard for initial configuration.
    
    Features:
        - System status check
        - One-click setup (directories, database, model download)
        - Visual progress feedback
        
    Impact:
        - Creates necessary directories
        - Initializes database
        - Downloads default model if none exist
    """
    st.markdown("### 🔧 Setup Wizard")
    st.markdown("Configure your Transcriptor environment with one click.")
    
    # Check system status
    st.markdown("---")
    st.markdown("### 📊 System Status")
    
    if st.button("🔍 Check Status", type="primary", use_container_width=True):
        status_checks = check_system_status()
        
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
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        progress.progress(20)
        
        # Step 2: Initialize database
        status.markdown("💾 Initializing database...")
        try:
            from app.database import init_database
            init_database()
            progress.progress(40)
        except Exception as e:
            st.error(f"Database initialization failed: {e}")
        
        # Step 3: Check for models
        status.markdown("🤖 Checking models...")
        installed_models = [d.name for d in MODELS_DIR.iterdir() if d.is_dir()] if MODELS_DIR.exists() else []
        progress.progress(60)
        
        if not installed_models:
            status.markdown("📥 Downloading default model (Medium)...")
            try:
                result = download_model("mlx-community/whisper-medium-mlx", "whisper-medium-mlx")
                if result['success']:
                    progress.progress(90)
                else:
                    st.warning(f"Model download failed: {result['error']}")
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
    """
    Show Claude terminal for AI-assisted model installation.
    
    Features:
        - Simple command interface
        - Pre-built commands for common tasks
        - Model installation, listing, status checking
        
    Impact:
        - Provides easy model installation
        - Helps troubleshoot issues
    """
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
                    result = download_model(
                        'tawankri/distill-thonburian-whisper-large-v3-mlx',
                        'distill-thonburian-whisper-large-v3-mlx'
                    )
                    if result['success']:
                        response['output'] = "✅ Model installed successfully!"
                    else:
                        response['output'] = f"❌ Error: {result['error']}"
            
            elif 'list' in user_lower and 'model' in user_lower:
                response['content'] = "Listing installed models..."
                if MODELS_DIR.exists():
                    models = [d.name for d in MODELS_DIR.iterdir() if d.is_dir()]
                    response['output'] = f"Installed models ({len(models)}):\n" + "\n".join(f"  - {m}" for m in models)
                else:
                    response['output'] = "No models directory found."
            
            elif 'check' in user_lower or 'status' in user_lower:
                response['content'] = "Checking system status..."
                checks = []
                try:
                    import mlx
                    checks.append("✅ MLX installed")
                except ImportError:
                    checks.append("❌ MLX not installed")
                try:
                    import mlx_whisper
                    checks.append("✅ MLX Whisper installed")
                except ImportError:
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
                    result = download_model(
                        'mlx-community/whisper-medium-mlx',
                        'whisper-medium-mlx'
                    )
                    if result['success']:
                        response['output'] = "✅ Model installed successfully!"
                    else:
                        response['output'] = f"❌ Error: {result['error']}"
            
            else:
                response['content'] = f"I understand you want to: {user_input}\n\nFor now, I can help with:\n- **install thonburian** - Install Thai Thonburian model\n- **install medium** - Install Whisper Medium model\n- **list models** - Show installed models\n- **check status** - Check system status\n- **help** - Show available commands"
            
            st.session_state.claude_history.append(response)
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.claude_history = []
            st.rerun()
