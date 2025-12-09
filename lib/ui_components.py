"""
UI Components Module - lib/ui_components.py

Shared Streamlit UI components and styles.

Impact Analysis:
===============
- get_custom_css(): Applied to all pages for consistent styling
- Various UI helper functions used across pages

Dependencies:
============
- lib/config.py (APP_NAME, APP_VERSION)
- streamlit

Used By:
========
- lib/pages/*.py (all page modules)
- web_app.py

Functions:
=========
- get_custom_css() -> str
- show_header(title: str, subtitle: str)
- show_metric_card(label: str, value: str)
- show_progress_section() -> tuple
"""

import streamlit as st
from .config import APP_NAME, APP_VERSION


def get_custom_css() -> str:
    """
    Get custom CSS styles for the application.
    
    Returns:
        str: CSS string to be applied via st.markdown
        
    Impact:
        - Affects visual appearance of all pages
        - Includes drag-and-drop styling
        - Progress bar styling
        - Card styling
        
    Example:
        >>> st.markdown(get_custom_css(), unsafe_allow_html=True)
    """
    return """
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
        .history-item:hover {
            background-color: #e9ecef;
        }
        .stats-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin: 0.5rem 0;
        }
        
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
        
        /* Sidebar styling */
        .sidebar-info {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
    </style>
    """


def get_drag_drop_css() -> str:
    """
    Get CSS specifically for drag-and-drop file upload area.
    
    Returns:
        str: CSS string for file uploader styling
        
    Impact:
        - Enhances visual feedback for file upload
        - Used in Transcribe page
    """
    return """
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
    """


def show_header(title: str, subtitle: str = ""):
    """
    Display a page header with title and optional subtitle.
    
    Args:
        title: Main title text
        subtitle: Optional subtitle text
        
    Impact:
        - Used at top of each page
        - Provides consistent header styling
        
    Example:
        >>> show_header("🎙️ Transcription", "Upload audio files")
    """
    st.markdown(f'<p class="main-header">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="sub-header">{subtitle}</p>', unsafe_allow_html=True)


def show_metric_card(label: str, value: str, delta: str = None):
    """
    Display a styled metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/change indicator
        
    Impact:
        - Used for statistics display
        - Provides visual emphasis for key metrics
        
    Example:
        >>> show_metric_card("Total Files", "142", "+5 today")
    """
    st.metric(label=label, value=value, delta=delta)


def show_status_badge(status: str) -> str:
    """
    Get HTML for a status badge.
    
    Args:
        status: Status string ('completed', 'processing', 'failed', etc.)
        
    Returns:
        str: HTML string for the badge
        
    Impact:
        - Used in history page
        - Provides visual status indication
        
    Example:
        >>> badge_html = show_status_badge('completed')
        >>> st.markdown(badge_html, unsafe_allow_html=True)
    """
    colors = {
        'completed': '#28a745',
        'processing': '#ffc107',
        'failed': '#dc3545',
        'pending': '#6c757d',
    }
    color = colors.get(status.lower(), '#6c757d')
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{status}</span>'


def format_duration(minutes: float) -> str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        str: Formatted duration string
        
    Example:
        >>> format_duration(74.5)
        '1h 14m'
    """
    if minutes < 1:
        return f"{minutes * 60:.0f}s"
    elif minutes < 60:
        return f"{minutes:.1f}m"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        str: Formatted size string
        
    Example:
        >>> format_file_size(1536000)
        '1.5 MB'
    """
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024**2:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024**3:
        return f"{bytes_size / 1024**2:.1f} MB"
    else:
        return f"{bytes_size / 1024**3:.2f} GB"
