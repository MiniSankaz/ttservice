"""
Model Management Module - lib/models.py

Functions for MLX Whisper model management.

Impact Analysis:
===============
- get_available_models(): Used by transcribe page (model dropdown) and settings page

Dependencies:
============
- lib/config.py (PROJECT_ROOT, MODELS_DIR, STANDARD_MODELS)

Used By:
========
- lib/pages/transcribe.py (model selection)
- lib/pages/settings.py (model management)
- web_app.py

External Dependencies:
====================
- huggingface_hub for model downloads

Functions:
=========
- get_available_models() -> List[Dict]
- download_model(repo_id: str, local_name: str) -> bool
- delete_model(model_name: str) -> bool
"""

import shutil
from pathlib import Path
from typing import List, Dict, Optional

from .config import PROJECT_ROOT, MODELS_DIR, STANDARD_MODELS


def get_available_models() -> List[Dict]:
    """
    Get list of available models from models directory.
    
    Returns:
        List[Dict]: List of model info dictionaries with keys:
            - name: Directory name
            - display_name: Human-readable name
            - short_name: Short identifier for CLI
            - path: Full path to model directory
            - installed: Whether model files exist
            - size_gb: Model size in GB (if installed)
            - is_custom: Whether it's a custom (non-standard) model
            
    Impact:
        - Populates model dropdown in Transcribe page
        - Shows installed models in Settings page
        - Determines which models are available for transcription
        
    Supports:
        - weights.npz format (older MLX models)
        - weights.safetensors format (newer models like Thonburian)
        
    Example:
        >>> models = get_available_models()
        >>> installed = [m for m in models if m['installed']]
        >>> print(f"{len(installed)} models installed")
    """
    models = []
    
    # Standard models
    for model_name, info in STANDARD_MODELS.items():
        model_path = MODELS_DIR / model_name / "weights.npz"
        safetensors_path = MODELS_DIR / model_name / "weights.safetensors"
        
        # Check both formats
        weights_path = safetensors_path if safetensors_path.exists() else model_path
        
        models.append({
            'name': model_name,
            'display_name': info['display_name'],
            'short_name': info['short_name'],
            'path': str(MODELS_DIR / model_name),
            'installed': weights_path.exists(),
            'size_gb': weights_path.stat().st_size / (1024**3) if weights_path.exists() else 0,
            'is_custom': False
        })
    
    # Scan for custom models
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir() and model_dir.name not in STANDARD_MODELS:
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


def download_model(repo_id: str, local_name: Optional[str] = None) -> Dict:
    """
    Download a model from HuggingFace Hub.
    
    Args:
        repo_id: HuggingFace repository ID (e.g., 'mlx-community/whisper-medium-mlx')
        local_name: Optional local directory name (defaults to repo name)
        
    Returns:
        dict: {
            'success': bool,
            'path': str or None,
            'error': str or None
        }
        
    Dependencies:
        - huggingface_hub package
        
    Impact:
        - Downloads model to MODELS_DIR
        - Makes model available for transcription
        
    Example:
        >>> result = download_model('mlx-community/whisper-medium-mlx')
        >>> if result['success']:
        ...     print(f"Downloaded to {result['path']}")
    """
    try:
        from huggingface_hub import snapshot_download
        
        # Determine local name
        if not local_name:
            local_name = repo_id.split('/')[-1]
        
        model_path = MODELS_DIR / local_name
        
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(model_path),
            local_dir_use_symlinks=False
        )
        
        return {
            'success': True,
            'path': str(model_path),
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'path': None,
            'error': str(e)
        }


def delete_model(model_name: str) -> Dict:
    """
    Delete a model from the models directory.
    
    Args:
        model_name: Name of the model directory to delete
        
    Returns:
        dict: {
            'success': bool,
            'error': str or None
        }
        
    Safety:
        - Only deletes from MODELS_DIR
        - Won't delete standard models by default
        
    Impact:
        - Removes model files from disk
        - Model will no longer be available for transcription
        
    Example:
        >>> result = delete_model('my-custom-model')
        >>> if result['success']:
        ...     print("Model deleted")
    """
    try:
        model_path = MODELS_DIR / model_name
        
        if not model_path.exists():
            return {
                'success': False,
                'error': 'Model not found'
            }
        
        # Safety check - only delete if inside MODELS_DIR
        if not str(model_path.resolve()).startswith(str(MODELS_DIR.resolve())):
            return {
                'success': False,
                'error': 'Invalid model path'
            }
        
        shutil.rmtree(model_path)
        
        return {
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_model_info(model_name: str) -> Optional[Dict]:
    """
    Get detailed information about a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        dict or None: Model information if found
        
    Example:
        >>> info = get_model_info('whisper-medium-mlx')
        >>> print(f"Size: {info['size_gb']:.2f} GB")
    """
    models = get_available_models()
    for model in models:
        if model['name'] == model_name or model['short_name'] == model_name:
            return model
    return None
