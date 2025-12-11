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


def find_claude_cli() -> str:
    """
    Find Claude Code CLI binary path.

    Returns:
        Path to claude binary or empty string if not found.
    """
    import os
    import glob

    # Common locations to check
    possible_paths = [
        # macOS Claude App installation
        os.path.expanduser("~/Library/Application Support/Claude/claude-code/*/claude"),
        # Homebrew
        "/opt/homebrew/bin/claude",
        "/usr/local/bin/claude",
        # npm global
        "/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js",
    ]

    # Check each possible path
    for pattern in possible_paths:
        matches = glob.glob(pattern)
        if matches:
            # Sort to get latest version if multiple exist
            matches.sort(reverse=True)
            if os.path.isfile(matches[0]) and os.access(matches[0], os.X_OK):
                return matches[0]

    # Try which command
    try:
        result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return ""


def run_claude_cli(prompt: str, timeout: int = 120) -> dict:
    """
    Run Claude Code CLI with a prompt and return the response.

    Args:
        prompt: The prompt to send to Claude
        timeout: Timeout in seconds (default 120)

    Returns:
        dict with 'success', 'output', and 'error' keys
    """
    claude_path = find_claude_cli()

    if not claude_path:
        return {
            'success': False,
            'output': '',
            'error': 'Claude CLI not found. Please install Claude Code from https://claude.ai/claude-code'
        }

    try:
        # Build system prompt for context
        system_prompt = f"""You are helping with the Transcriptor Pipeline Pilot project.
Project directory: {PROJECT_ROOT}
Models directory: {MODELS_DIR}

Focus on helping with:
- Installing and managing MLX Whisper models
- Troubleshooting transcription issues
- Checking system requirements
- Audio file processing

Be concise and helpful. If asked to run commands, explain what they do first."""

        # Run claude in print mode (non-interactive)
        result = subprocess.run(
            [
                claude_path,
                '-p',  # Print mode (non-interactive)
                '--append-system-prompt', system_prompt,
                prompt
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT)
        )

        if result.returncode == 0:
            return {
                'success': True,
                'output': result.stdout.strip(),
                'error': ''
            }
        else:
            return {
                'success': False,
                'output': result.stdout.strip() if result.stdout else '',
                'error': result.stderr.strip() if result.stderr else 'Unknown error'
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': f'Request timed out after {timeout} seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e)
        }


def show_claude_terminal():
    """
    Show Claude terminal for AI-assisted interaction.

    Features:
        - Real Claude Code CLI integration
        - Interactive chat interface
        - Context-aware responses about the project

    Impact:
        - Provides AI-powered assistance
        - Helps with model management and troubleshooting
    """
    st.markdown("### 🤖 Claude Terminal")

    # Check if Claude CLI is available
    claude_path = find_claude_cli()

    if claude_path:
        st.success(f"✅ Claude CLI found: `{claude_path}`")
        st.markdown("AI-powered terminal using **Claude Code CLI**.")
    else:
        st.warning("⚠️ Claude CLI not found. Install from https://claude.ai/claude-code")
        st.markdown("Using fallback mode with limited commands.")

    st.info("""
    **How to use:**
    1. Type any question or request below
    2. Claude will respond with helpful information
    3. You can ask about models, transcription, troubleshooting, etc.

    **Example prompts:**
    - "How do I install the Thai Thonburian model?"
    - "What MLX Whisper models are available?"
    - "Why is my transcription failing?"
    - "Check if FFmpeg is installed"
    """)

    # Claude chat interface
    if 'claude_history' not in st.session_state:
        st.session_state.claude_history = []

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.claude_history[-10:]:  # Show last 10 messages
            if msg['role'] == 'user':
                st.markdown(f"**🧑 You:** {msg['content']}")
            else:
                st.markdown(f"**🤖 Claude:**")
                st.markdown(msg['content'])
                if msg.get('error'):
                    st.error(f"Error: {msg['error']}")

    st.markdown("---")

    # Input
    user_input = st.text_input(
        "Ask Claude...",
        placeholder="e.g., How do I install a new model?",
        key="claude_input"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("🚀 Send", type="primary", use_container_width=True) and user_input:
            st.session_state.claude_history.append({'role': 'user', 'content': user_input})

            response = {'role': 'assistant', 'content': '', 'error': ''}

            if claude_path:
                # Use real Claude CLI
                with st.spinner("🤔 Claude is thinking..."):
                    result = run_claude_cli(user_input)

                    if result['success']:
                        response['content'] = result['output']
                    else:
                        response['content'] = result['output'] if result['output'] else "Sorry, I couldn't process that request."
                        response['error'] = result['error']
            else:
                # Fallback mode - simple keyword matching
                user_lower = user_input.lower()

                if 'install' in user_lower and 'thonburian' in user_lower:
                    response['content'] = "To install the Thai Thonburian model, go to the **Models** tab and click the quick install button, or run:\n\n```python\nfrom huggingface_hub import snapshot_download\nsnapshot_download('tawankri/distill-thonburian-whisper-large-v3-mlx', local_dir='models/distill-thonburian-whisper-large-v3-mlx')\n```"

                elif 'list' in user_lower and 'model' in user_lower:
                    if MODELS_DIR.exists():
                        models = [d.name for d in MODELS_DIR.iterdir() if d.is_dir()]
                        response['content'] = f"**Installed models ({len(models)}):**\n" + "\n".join(f"- {m}" for m in models)
                    else:
                        response['content'] = "No models directory found. Run Setup Wizard first."

                elif 'check' in user_lower or 'status' in user_lower:
                    checks = check_system_status()
                    lines = ["**System Status:**"]
                    for name, value, ok in checks:
                        lines.append(f"- {name}: {value} {'✅' if ok else '❌'}")
                    response['content'] = "\n".join(lines)

                elif 'help' in user_lower:
                    response['content'] = """**Available in fallback mode:**
- Ask about installing models (e.g., "install thonburian")
- List installed models
- Check system status
- General help

*For full AI capabilities, install Claude Code CLI.*"""

                else:
                    response['content'] = f"*Fallback mode - Claude CLI not available*\n\nYou asked: {user_input}\n\nTry:\n- \"list models\" - Show installed models\n- \"check status\" - Check system status\n- \"help\" - Show available commands"

            st.session_state.claude_history.append(response)
            st.rerun()

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.claude_history = []
            st.rerun()
