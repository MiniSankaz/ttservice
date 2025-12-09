#!/bin/bash
#
# Transcriptor Pipeline Pilot - Setup Script
# This script sets up the environment and starts the web service
#
# Usage:
#   ./setup.sh          # Full setup + start web service
#   ./setup.sh --setup  # Setup only (no start)
#   ./setup.sh --start  # Start web service only
#   ./setup.sh --stop   # Stop web service
#   ./setup.sh --status # Check status
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv"
PID_FILE="$PROJECT_DIR/.streamlit.pid"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Transcriptor Pipeline Pilot Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if running on macOS with Apple Silicon
check_system() {
    echo -e "\n${BLUE}Checking system...${NC}"

    if [[ "$(uname)" != "Darwin" ]]; then
        print_warning "This script is optimized for macOS"
    else
        print_status "macOS detected"
    fi

    if [[ "$(uname -m)" == "arm64" ]]; then
        print_status "Apple Silicon (M1/M2/M3/M4) detected"
    else
        print_warning "Non-Apple Silicon detected. MLX may not work optimally."
    fi
}

# Check Python version
check_python() {
    echo -e "\n${BLUE}Checking Python...${NC}"

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        print_status "Python $PYTHON_VERSION found"

        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
            print_status "Python version is compatible (>= 3.10)"
        else
            print_error "Python 3.10+ is required"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi
}

# Check FFmpeg
check_ffmpeg() {
    echo -e "\n${BLUE}Checking FFmpeg...${NC}"

    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f3)
        print_status "FFmpeg $FFMPEG_VERSION found"
    else
        print_warning "FFmpeg not found. Installing via Homebrew..."
        if command -v brew &> /dev/null; then
            brew install ffmpeg
            print_status "FFmpeg installed"
        else
            print_error "FFmpeg not found and Homebrew not available. Please install FFmpeg manually."
            exit 1
        fi
    fi
}

# Setup virtual environment
setup_venv() {
    echo -e "\n${BLUE}Setting up virtual environment...${NC}"

    if [[ -d "$VENV_DIR" ]]; then
        print_status "Virtual environment exists"
    else
        print_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        print_status "Virtual environment created"
    fi

    # Activate venv
    source "$VENV_DIR/bin/activate"
    print_status "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    echo -e "\n${BLUE}Installing dependencies...${NC}"

    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip -q
    print_status "pip upgraded"

    # Install requirements
    if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        pip install -r "$PROJECT_DIR/requirements.txt" -q
        print_status "Requirements installed"
    else
        print_warning "requirements.txt not found, installing essential packages..."
        pip install streamlit mlx mlx-whisper huggingface_hub pydub librosa soundfile noisereduce -q
        print_status "Essential packages installed"
    fi
}

# Create directories
create_directories() {
    echo -e "\n${BLUE}Creating directories...${NC}"

    mkdir -p "$PROJECT_DIR/uploads"
    mkdir -p "$PROJECT_DIR/outputs"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/models"
    mkdir -p "$PROJECT_DIR/logs"

    print_status "Directories created"
}

# Initialize database
init_database() {
    echo -e "\n${BLUE}Initializing database...${NC}"

    source "$VENV_DIR/bin/activate"

    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from web_app import init_database
init_database()
print('Database initialized')
"
    print_status "Database ready"
}

# Download default model
download_model() {
    echo -e "\n${BLUE}Checking models...${NC}"

    source "$VENV_DIR/bin/activate"

    if [[ -d "$PROJECT_DIR/models/whisper-medium-mlx" ]] || [[ -d "$PROJECT_DIR/models/distill-thonburian-whisper-large-v3-mlx" ]]; then
        MODELS=$(ls -d "$PROJECT_DIR/models"/*/ 2>/dev/null | wc -l | tr -d ' ')
        print_status "$MODELS model(s) found"
    else
        print_info "No models found. Downloading default model (Whisper Medium)..."
        python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='mlx-community/whisper-medium-mlx',
    local_dir='$PROJECT_DIR/models/whisper-medium-mlx',
    local_dir_use_symlinks=False
)
"
        print_status "Default model downloaded"
    fi
}

# Start web service
start_service() {
    echo -e "\n${BLUE}Starting web service...${NC}"

    source "$VENV_DIR/bin/activate"

    # Check if already running
    if [[ -f "$PID_FILE" ]]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            print_warning "Service already running (PID: $OLD_PID)"
            echo -e "\n${GREEN}Access the web interface at: http://localhost:8501${NC}"
            return
        fi
    fi

    # Start Streamlit in background
    cd "$PROJECT_DIR"
    nohup streamlit run web_app.py --server.port 8501 --server.headless true > "$PROJECT_DIR/logs/streamlit.log" 2>&1 &
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"

    # Wait for startup
    sleep 3

    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        print_status "Web service started (PID: $NEW_PID)"
        echo -e "\n${GREEN}========================================${NC}"
        echo -e "${GREEN}  Transcriptor is ready!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "\n${BLUE}Access the web interface at:${NC}"
        echo -e "  ${GREEN}http://localhost:8501${NC}"
        echo -e "\n${BLUE}To stop the service:${NC}"
        echo -e "  ${YELLOW}./setup.sh --stop${NC}"
        echo -e "\n${BLUE}View logs:${NC}"
        echo -e "  ${YELLOW}tail -f logs/streamlit.log${NC}"
    else
        print_error "Failed to start web service. Check logs/streamlit.log for details."
        exit 1
    fi
}

# Stop web service
stop_service() {
    echo -e "\n${BLUE}Stopping web service...${NC}"

    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            rm "$PID_FILE"
            print_status "Service stopped (PID: $PID)"
        else
            print_warning "Service not running"
            rm "$PID_FILE"
        fi
    else
        # Try to find and kill any streamlit process
        pkill -f "streamlit run web_app.py" 2>/dev/null && print_status "Service stopped" || print_warning "Service not running"
    fi
}

# Check status
check_status() {
    echo -e "\n${BLUE}Checking status...${NC}"

    # Check Python
    if command -v python3 &> /dev/null; then
        print_status "Python: $(python3 --version)"
    else
        print_error "Python: Not found"
    fi

    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        print_status "FFmpeg: $(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f3)"
    else
        print_error "FFmpeg: Not found"
    fi

    # Check venv
    if [[ -d "$VENV_DIR" ]]; then
        print_status "Virtual Environment: Ready"
    else
        print_error "Virtual Environment: Not created"
    fi

    # Check MLX
    source "$VENV_DIR/bin/activate" 2>/dev/null
    if python3 -c "import mlx" 2>/dev/null; then
        print_status "MLX: Installed"
    else
        print_error "MLX: Not installed"
    fi

    # Check MLX Whisper
    if python3 -c "import mlx_whisper" 2>/dev/null; then
        print_status "MLX Whisper: Installed"
    else
        print_error "MLX Whisper: Not installed"
    fi

    # Check models
    if [[ -d "$PROJECT_DIR/models" ]]; then
        MODELS=$(ls -d "$PROJECT_DIR/models"/*/ 2>/dev/null | wc -l | tr -d ' ')
        print_status "Models: $MODELS installed"
    else
        print_error "Models: Directory not found"
    fi

    # Check database
    if [[ -f "$PROJECT_DIR/data/transcriptor.db" ]]; then
        print_status "Database: Ready"
    else
        print_warning "Database: Not initialized"
    fi

    # Check service
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_status "Web Service: Running (PID: $PID)"
            echo -e "\n${GREEN}Access at: http://localhost:8501${NC}"
        else
            print_warning "Web Service: Not running (stale PID file)"
        fi
    else
        print_warning "Web Service: Not running"
    fi
}

# Full setup
full_setup() {
    check_system
    check_python
    check_ffmpeg
    setup_venv
    install_dependencies
    create_directories
    init_database
    download_model
}

# Main
case "${1:-}" in
    --setup)
        full_setup
        echo -e "\n${GREEN}Setup complete!${NC}"
        echo -e "Run ${YELLOW}./setup.sh --start${NC} to start the web service."
        ;;
    --start)
        start_service
        ;;
    --stop)
        stop_service
        ;;
    --status)
        check_status
        ;;
    --help|-h)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (no option)  Full setup + start web service"
        echo "  --setup      Setup only (no start)"
        echo "  --start      Start web service only"
        echo "  --stop       Stop web service"
        echo "  --status     Check status"
        echo "  --help       Show this help"
        ;;
    *)
        full_setup
        start_service
        ;;
esac
