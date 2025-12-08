#!/usr/bin/env python3
"""
Transcription Wizard - Interactive batch processing for MLX Whisper

This wizard provides an easy-to-use interface for transcribing audio files
using the MLX Whisper pipeline with optimized worker configuration.

Features:
- Interactive wizard mode
- Auto worker configuration based on system resources
- Manual worker configuration
- Batch processing support
- Multiple audio format support
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import json


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def get_system_resources() -> Tuple[int, float]:
    """
    Get system CPU cores and memory from macOS

    Returns:
        Tuple of (cpu_cores, memory_gb)
    """
    try:
        # Get CPU cores
        cpu_result = subprocess.run(
            ['sysctl', '-n', 'hw.ncpu'],
            capture_output=True,
            text=True,
            check=True
        )
        cpu_cores = int(cpu_result.stdout.strip())

        # Get memory in bytes
        mem_result = subprocess.run(
            ['sysctl', '-n', 'hw.memsize'],
            capture_output=True,
            text=True,
            check=True
        )
        memory_bytes = int(mem_result.stdout.strip())
        memory_gb = memory_bytes / (1024 ** 3)

        return cpu_cores, memory_gb
    except Exception as e:
        print_warning(f"Could not detect system resources: {e}")
        print_info("Using default values: 10 cores, 16 GB RAM")
        return 10, 16.0


def calculate_optimal_workers(cpu_cores: int, memory_gb: float, model: str) -> Tuple[int, int]:
    """
    Calculate optimal number of processes and workers based on system resources

    Args:
        cpu_cores: Number of CPU cores
        memory_gb: Available memory in GB
        model: Model name (medium or large-v3)

    Returns:
        Tuple of (processes, workers_per_process)
    """
    # Memory requirements per model instance
    model_memory = {
        'medium': 0.5,  # GB
        'large-v3': 1.5  # GB
    }

    mem_per_model = model_memory.get(model, 0.5)

    # Calculate based on 80% of resources
    usable_cores = int(cpu_cores * 0.8)
    usable_memory = memory_gb * 0.8

    # Calculate max workers based on memory
    max_workers_by_memory = int(usable_memory / mem_per_model)

    # Calculate total workers (limited by both CPU and memory)
    total_workers = min(usable_cores, max_workers_by_memory)

    # Ensure at least 8 workers
    total_workers = max(8, total_workers)

    # Determine optimal process/worker split
    # Prefer 2 processes for better stability (as per benchmarks)
    if total_workers >= 16:
        processes = 2
        workers_per_process = total_workers // 2
    elif total_workers >= 12:
        processes = 2
        workers_per_process = total_workers // 2
    else:
        processes = 1
        workers_per_process = total_workers

    # Ensure workers per process is at least 4
    if workers_per_process < 4:
        workers_per_process = 4
        processes = 1

    return processes, workers_per_process


def find_audio_files(input_path: str) -> List[Path]:
    """
    Find all audio files in input path (file or directory)

    Args:
        input_path: Path to file or directory

    Returns:
        List of audio file paths
    """
    supported_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm']
    audio_files = []

    path = Path(input_path)

    if path.is_file():
        if path.suffix.lower() in supported_extensions:
            audio_files.append(path)
        else:
            print_warning(f"File {path} is not a supported audio format")
    elif path.is_dir():
        for ext in supported_extensions:
            audio_files.extend(path.glob(f'*{ext}'))
            audio_files.extend(path.glob(f'*{ext.upper()}'))
    else:
        print_error(f"Path {input_path} does not exist")

    return sorted(audio_files)


def validate_model(model: str) -> bool:
    """Validate model selection"""
    valid_models = ['medium', 'large-v3']
    return model in valid_models


def get_user_input(prompt: str, default: Optional[str] = None) -> str:
    """
    Get user input with optional default value

    Args:
        prompt: Prompt message
        default: Default value

    Returns:
        User input or default value
    """
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    user_input = input(prompt).strip()
    return user_input if user_input else default


def get_user_choice(prompt: str, choices: List[str]) -> str:
    """
    Get user choice from a list of options

    Args:
        prompt: Prompt message
        choices: List of valid choices

    Returns:
        Selected choice
    """
    while True:
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")

        selection = input(f"\nEnter choice (1-{len(choices)}): ").strip()

        try:
            index = int(selection) - 1
            if 0 <= index < len(choices):
                return choices[index]
            else:
                print_error(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print_error("Please enter a valid number")


def interactive_wizard() -> dict:
    """
    Run interactive wizard to collect configuration

    Returns:
        Configuration dictionary
    """
    print_header("MLX Whisper Transcription Wizard")
    print_info("This wizard will help you configure the transcription pipeline\n")

    config = {}

    # Step 1: Input selection
    print_header("Step 1: Input Selection")
    input_path = get_user_input("Enter audio file or folder path")

    while not input_path or not Path(input_path).exists():
        print_error("Path does not exist. Please try again.")
        input_path = get_user_input("Enter audio file or folder path")

    audio_files = find_audio_files(input_path)

    if not audio_files:
        print_error("No supported audio files found!")
        sys.exit(1)

    print_success(f"Found {len(audio_files)} audio file(s)")
    for i, f in enumerate(audio_files[:5], 1):
        print(f"  {i}. {f.name}")
    if len(audio_files) > 5:
        print(f"  ... and {len(audio_files) - 5} more")

    config['input_files'] = audio_files

    # Step 2: Output directory
    print_header("Step 2: Output Directory")
    default_output = str(Path(input_path).parent / "transcriptions")
    output_dir = get_user_input("Enter output directory", default_output)
    config['output_dir'] = Path(output_dir)

    # Create output directory if it doesn't exist
    config['output_dir'].mkdir(parents=True, exist_ok=True)
    print_success(f"Output directory: {config['output_dir']}")

    # Step 3: Model selection
    print_header("Step 3: Model Selection")
    print_info("Available models:")
    print("  1. medium   - Good balance (faster, ~0.5 GB memory)")
    print("  2. large-v3 - Best accuracy (slower, ~1.5 GB memory)")

    model_choice = get_user_choice("Select model", ["medium", "large-v3"])
    config['model'] = model_choice
    print_success(f"Selected model: {model_choice}")

    # Step 4: Worker configuration
    print_header("Step 4: Worker Configuration")

    # Get system resources
    cpu_cores, memory_gb = get_system_resources()
    print_info(f"System resources detected:")
    print(f"  - CPU cores: {cpu_cores}")
    print(f"  - Memory: {memory_gb:.1f} GB")

    mode = get_user_choice("Configuration mode", ["auto", "manual"])
    config['mode'] = mode

    if mode == 'auto':
        processes, workers = calculate_optimal_workers(cpu_cores, memory_gb, model_choice)
        config['processes'] = processes
        config['workers'] = workers

        print_success(f"Auto-calculated configuration:")
        print(f"  - Processes: {processes}")
        print(f"  - Workers per process: {workers}")
        print(f"  - Total workers: {processes * workers}")
        print_info(f"Using 80% of system resources")
    else:
        # Manual configuration
        print_info("Enter worker configuration manually")

        while True:
            processes_input = get_user_input("Number of processes", "2")
            try:
                processes = int(processes_input)
                if processes > 0:
                    break
                print_error("Processes must be greater than 0")
            except ValueError:
                print_error("Please enter a valid number")

        while True:
            workers_input = get_user_input("Workers per process", "8")
            try:
                workers = int(workers_input)
                if workers > 0:
                    break
                print_error("Workers must be greater than 0")
            except ValueError:
                print_error("Please enter a valid number")

        config['processes'] = processes
        config['workers'] = workers

        print_success(f"Manual configuration:")
        print(f"  - Processes: {processes}")
        print(f"  - Workers per process: {workers}")
        print(f"  - Total workers: {processes * workers}")

    # Summary
    print_header("Configuration Summary")
    print(f"Input files: {len(config['input_files'])} file(s)")
    print(f"Output directory: {config['output_dir']}")
    print(f"Model: {config['model']}")
    print(f"Mode: {config['mode']}")
    print(f"Processes: {config['processes']}")
    print(f"Workers per process: {config['workers']}")
    print(f"Total workers: {config['processes'] * config['workers']}")

    # Confirmation
    confirm = get_user_input("\nProceed with transcription? (yes/no)", "yes")
    if confirm.lower() not in ['yes', 'y']:
        print_info("Transcription cancelled")
        sys.exit(0)

    return config


def run_transcription(audio_file: Path, output_dir: Path, model: str,
                     processes: int, workers: int) -> bool:
    """
    Run transcription for a single audio file

    Args:
        audio_file: Path to audio file
        output_dir: Output directory
        model: Model name
        processes: Number of processes
        workers: Workers per process

    Returns:
        True if successful, False otherwise
    """
    # Determine output filename
    output_file = output_dir / f"{audio_file.stem}.txt"

    # Construct command - use pipeline script
    script_dir = Path(__file__).parent / "scripts"
    script_path = script_dir / "transcribe_pipeline.py"

    if not script_path.exists():
        print_error(f"Transcription script not found: {script_path}")
        return False

    cmd = [
        sys.executable,
        str(script_path),
        str(audio_file),
        str(output_file),
        '--model', model,
        '--transcribe-processes', str(processes),
        '--transcribe-workers', str(workers),
        '--preprocess-workers', '2'
    ]

    print_info(f"Transcribing: {audio_file.name}")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True)
        print_success(f"Completed: {audio_file.name}")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed: {audio_file.name}")
        print_error(f"Error: {e}")
        return False


def process_batch(config: dict):
    """
    Process batch of audio files

    Args:
        config: Configuration dictionary
    """
    audio_files = config['input_files']
    total_files = len(audio_files)

    print_header(f"Processing Batch ({total_files} files)")

    success_count = 0
    fail_count = 0

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n{Colors.BOLD}[{i}/{total_files}]{Colors.ENDC}")

        success = run_transcription(
            audio_file,
            config['output_dir'],
            config['model'],
            config['processes'],
            config['workers']
        )

        if success:
            success_count += 1
        else:
            fail_count += 1

    # Final summary
    print_header("Batch Processing Complete")
    print(f"Total files: {total_files}")
    print_success(f"Successful: {success_count}")
    if fail_count > 0:
        print_error(f"Failed: {fail_count}")

    print(f"\nOutput directory: {config['output_dir']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MLX Whisper Transcription Wizard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive wizard mode
  python transcribe_wizard.py --interactive

  # Auto mode with single file
  python transcribe_wizard.py --input audio.mp3 --mode auto

  # Auto mode with folder
  python transcribe_wizard.py --input ./audios/ --output-dir ./outputs --mode auto

  # Manual mode with custom workers
  python transcribe_wizard.py --input audio.mp3 --mode manual --processes 2 --workers 8

  # Batch processing with large-v3 model
  python transcribe_wizard.py --input ./audios/ --model large-v3 --mode auto
        """
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive wizard mode'
    )

    parser.add_argument(
        '--input',
        type=str,
        help='Input audio file or folder'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (default: input_dir/transcriptions)'
    )

    parser.add_argument(
        '--model',
        type=str,
        choices=['medium', 'large-v3'],
        default='medium',
        help='Whisper model (default: medium)'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['auto', 'manual'],
        default='auto',
        help='Worker configuration mode (default: auto)'
    )

    parser.add_argument(
        '--processes',
        type=int,
        help='Number of processes (manual mode only)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        help='Workers per process (manual mode only)'
    )

    args = parser.parse_args()

    # Interactive mode
    if args.interactive or not args.input:
        config = interactive_wizard()
    else:
        # CLI mode
        if not Path(args.input).exists():
            print_error(f"Input path does not exist: {args.input}")
            sys.exit(1)

        audio_files = find_audio_files(args.input)
        if not audio_files:
            print_error("No supported audio files found!")
            sys.exit(1)

        # Determine output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path(args.input).parent / "transcriptions"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Get system resources
        cpu_cores, memory_gb = get_system_resources()

        # Determine worker configuration
        if args.mode == 'auto':
            processes, workers = calculate_optimal_workers(cpu_cores, memory_gb, args.model)
        else:
            if not args.processes or not args.workers:
                print_error("Manual mode requires --processes and --workers arguments")
                sys.exit(1)
            processes = args.processes
            workers = args.workers

        config = {
            'input_files': audio_files,
            'output_dir': output_dir,
            'model': args.model,
            'mode': args.mode,
            'processes': processes,
            'workers': workers
        }

        # Print configuration
        print_header("Configuration")
        print(f"Input files: {len(config['input_files'])} file(s)")
        print(f"Output directory: {config['output_dir']}")
        print(f"Model: {config['model']}")
        print(f"Mode: {config['mode']}")
        print(f"Processes: {config['processes']}")
        print(f"Workers per process: {config['workers']}")
        print(f"Total workers: {config['processes'] * config['workers']}")

    # Process batch
    process_batch(config)


if __name__ == '__main__':
    main()
