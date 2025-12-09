"""
System Utilities Module - lib/system.py

Functions for system resource detection and worker calculation.
Optimized for Apple Silicon (M1/M2/M3/M4) but works on other platforms.

Impact Analysis:
===============
- get_system_resources(): Used by settings page for display
- calculate_optimal_workers(): Used by transcribe page for auto mode

Dependencies:
============
- lib/config.py (CPU_USAGE_RATIO, MEMORY_USAGE_RATIO, STANDARD_MODELS)

Used By:
========
- lib/pages/transcribe.py (auto worker calculation)
- lib/pages/settings.py (resource display)
- web_app.py

Functions:
=========
- get_system_resources() -> tuple[int, float]
- calculate_optimal_workers(model: str) -> tuple[int, int]
"""

import subprocess
import platform
from typing import Tuple

from .config import CPU_USAGE_RATIO, MEMORY_USAGE_RATIO, STANDARD_MODELS


def get_system_resources() -> Tuple[int, float]:
    """
    Get system CPU cores and memory information.
    
    Returns:
        Tuple[int, float]: (cpu_cores, memory_gb)
        
    Platform Support:
        - macOS: Uses sysctl commands
        - Linux: Uses /proc filesystem
        - Windows: Uses wmic (limited support)
        
    Fallback:
        Returns (10, 16.0) if detection fails
        
    Impact:
        - Affects worker auto-calculation
        - Displayed in Settings > Performance
        
    Example:
        >>> cores, memory = get_system_resources()
        >>> print(f"{cores} cores, {memory:.1f} GB RAM")
        10 cores, 16.0 GB RAM
    """
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            # Get CPU cores
            cpu_result = subprocess.run(
                ['sysctl', '-n', 'hw.ncpu'],
                capture_output=True, text=True
            )
            cpu_cores = int(cpu_result.stdout.strip())
            
            # Get memory
            mem_result = subprocess.run(
                ['sysctl', '-n', 'hw.memsize'],
                capture_output=True, text=True
            )
            memory_gb = int(mem_result.stdout.strip()) / (1024**3)
            
        elif system == "Linux":
            # Get CPU cores
            with open('/proc/cpuinfo') as f:
                cpu_cores = sum(1 for line in f if line.startswith('processor'))
            
            # Get memory
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        memory_kb = int(line.split()[1])
                        memory_gb = memory_kb / (1024**2)
                        break
                else:
                    memory_gb = 16.0
                    
        else:  # Windows or unknown
            import os
            cpu_cores = os.cpu_count() or 10
            memory_gb = 16.0  # Default assumption
            
        return cpu_cores, memory_gb
        
    except Exception:
        # Fallback values for Apple Silicon Mac
        return 10, 16.0


def calculate_optimal_workers(model: str) -> Tuple[int, int]:
    """
    Calculate optimal number of processes and workers based on model and system resources.
    
    Args:
        model: Model short name (e.g., 'medium', 'large-v3')
        
    Returns:
        Tuple[int, int]: (num_processes, workers_per_process)
        
    Algorithm:
        1. Get available CPU cores and memory
        2. Apply usage ratios (80% by default)
        3. Calculate max processes based on memory per model
        4. Allocate workers per process based on remaining cores
        
    Impact:
        - Affects transcription speed
        - Affects memory usage
        - Used by "Auto" mode in Transcribe page
        
    Example:
        >>> processes, workers = calculate_optimal_workers('medium')
        >>> print(f"{processes} proc × {workers} workers")
        2 proc × 8 workers
    """
    cpu_cores, memory_gb = get_system_resources()
    
    # Get model memory requirement
    model_info = STANDARD_MODELS.get(f'whisper-{model}-mlx', {})
    mem_per_model = model_info.get('memory_gb', 0.5)
    
    # Calculate usable resources
    usable_cores = int(cpu_cores * CPU_USAGE_RATIO)
    usable_memory = memory_gb * MEMORY_USAGE_RATIO
    
    # Calculate max processes based on memory
    max_processes_memory = int(usable_memory / mem_per_model) if mem_per_model > 0 else 4
    max_processes_memory = max(1, min(4, max_processes_memory))
    
    # Calculate workers per process
    workers_per_proc = max(4, min(16, usable_cores // max_processes_memory))
    
    # For large models, reduce processes but keep workers
    if model in ['large-v3', 'large']:
        num_processes = min(2, max_processes_memory)
        workers_per_proc = max(4, min(8, usable_cores // num_processes))
    else:
        num_processes = min(2, max_processes_memory)
        workers_per_proc = 8
        
    return num_processes, workers_per_proc


def get_apple_silicon_info() -> dict:
    """
    Get Apple Silicon chip information if available.
    
    Returns:
        dict: Chip information including name, cores, GPU cores
        
    Example:
        >>> info = get_apple_silicon_info()
        >>> print(info['chip_name'])
        'Apple M2 Pro'
    """
    try:
        result = subprocess.run(
            ['sysctl', '-n', 'machdep.cpu.brand_string'],
            capture_output=True, text=True
        )
        chip_name = result.stdout.strip()
        
        cpu_cores, memory_gb = get_system_resources()
        
        return {
            'chip_name': chip_name,
            'cpu_cores': cpu_cores,
            'memory_gb': memory_gb,
            'is_apple_silicon': 'Apple' in chip_name and 'M' in chip_name,
        }
    except Exception:
        return {
            'chip_name': 'Unknown',
            'cpu_cores': 0,
            'memory_gb': 0,
            'is_apple_silicon': False,
        }
