#!/usr/bin/env python3
"""
MLX Whisper Models Downloader

This script downloads MLX-optimized Whisper models from Hugging Face
for use with the Transcriptor pipeline on Apple Silicon.

Models:
- mlx-community/whisper-medium-mlx
- mlx-community/whisper-large-v3-mlx

Storage location: ./models/ (relative to project root)
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

try:
    from huggingface_hub import snapshot_download
    from tqdm import tqdm
except ImportError:
    print("Error: Required packages not found.")
    print("Please install: pip install huggingface-hub tqdm")
    sys.exit(1)


# Configuration - use relative path from script location
SCRIPT_DIR = Path(__file__).parent.parent  # Go up from scripts/ to project root
MODELS_DIR = SCRIPT_DIR / "models"
MODELS_TO_DOWNLOAD = [
    ("mlx-community/whisper-medium-mlx", "whisper-medium-mlx"),
    ("mlx-community/whisper-large-v3-mlx", "whisper-large-v3-mlx"),
]


def check_model_exists(model_path: Path) -> bool:
    """
    Check if model already exists in the target directory.

    Args:
        model_path: Path to the model directory

    Returns:
        True if model exists and contains files, False otherwise
    """
    if not model_path.exists():
        return False

    # Check if directory has any files (not just empty)
    files = list(model_path.glob("*"))
    return len(files) > 0


def download_model(repo_id: str, local_dir_name: str) -> Tuple[bool, str]:
    """
    Download a model from Hugging Face Hub.

    Args:
        repo_id: Hugging Face repository ID (e.g., 'mlx-community/whisper-medium-mlx')
        local_dir_name: Local directory name to store the model

    Returns:
        Tuple of (success: bool, message: str)
    """
    model_path = MODELS_DIR / local_dir_name

    # Check if model already exists
    if check_model_exists(model_path):
        return True, f"Model already exists at {model_path}"

    print(f"\n{'='*80}")
    print(f"Downloading: {repo_id}")
    print(f"Target: {model_path}")
    print(f"{'='*80}\n")

    try:
        # Create models directory if it doesn't exist
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        # Download with progress tracking
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(model_path),
            local_dir_use_symlinks=False,
            resume_download=True,
            tqdm_class=tqdm,
        )

        return True, f"Successfully downloaded to {downloaded_path}"

    except Exception as e:
        return False, f"Error downloading {repo_id}: {str(e)}"


def print_header():
    """Print script header."""
    print("\n" + "="*80)
    print("MLX Whisper Models Downloader")
    print("="*80)
    print(f"Target directory: {MODELS_DIR}")
    print(f"Models to download: {len(MODELS_TO_DOWNLOAD)}")
    print("="*80 + "\n")


def print_summary(results: List[Tuple[str, bool, str]]):
    """
    Print download summary.

    Args:
        results: List of (model_name, success, message) tuples
    """
    print("\n" + "="*80)
    print("Download Summary")
    print("="*80 + "\n")

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    for model_name, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {model_name}")
        print(f"  {message}\n")

    print(f"{'='*80}")
    print(f"Total: {success_count}/{total_count} successful")
    print(f"{'='*80}\n")

    if success_count < total_count:
        sys.exit(1)


def main():
    """Main execution function."""
    print_header()

    # Check if models directory path is valid
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error: Cannot create models directory: {e}")
        sys.exit(1)

    results = []

    # Download each model
    for repo_id, local_dir_name in MODELS_TO_DOWNLOAD:
        success, message = download_model(repo_id, local_dir_name)
        results.append((local_dir_name, success, message))

    # Print summary
    print_summary(results)

    print("All models ready for use!")
    print(f"Models location: {MODELS_DIR}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
