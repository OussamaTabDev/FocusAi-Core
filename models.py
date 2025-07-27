# models.py
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

@dataclass
class WindowInfo:
    """A data class to hold all information about a single window state."""
    raw_title: str
    window_id: int # Using a more descriptive name than 'id'
    timestamp: str
    
    # Core attributes from pygetwindow
    position: Tuple[int, int]
    size: Tuple[int, int]
    is_active: bool
    is_minimized: bool
    is_maximized: bool
    is_visible: bool
    z_order: int

    # Enriched data
    process_name: Optional[str] = None
    process: Optional[str] = None
    
    class_name: Optional[str] = None
    is_system_window: bool = False
    is_topmost: bool = False
    parent_window_exists: bool = False
    
    # Parsed and Classified data
    window_type: str = 'unknown'
    app: str = ""
    original_app: str = "Desktop App" # is Desktop app or web app 
    status: str = "Neutral"
    context: str = ""
    domain: str = ""
    display_title: str = ""
    # A field to hold any extra OS-specific data we might want
    extra_info: Dict = field(default_factory=dict)
    
    
# @dataclass
# class TabInfo:
#     """Enhanced tab information from browser extension"""
#     url: str
#     title: str
#     domain: str
#     timestamp: str
#     server_timestamp: str
#     tab_id: Optional[int] = None
#     window_id: Optional[int] = None
#     is_active: bool = False
#     is_pinned: bool = False
#     is_muted: bool = False
#     favicon_url: Optional[str] = None
    
#     # Productivity classification
#     status: str = "Neutral"  # Productive, Distracting, Neutral
#     category: str = "Unknown"  # Social, Work, Entertainment, etc.
    
#     # Additional metadata
#     load_time: Optional[float] = None
#     memory_usage: Optional[int] = None
#     extra_info: Dict = field(default_factory=dict)