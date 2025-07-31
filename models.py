# models.py
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple , List
from datetime import datetime
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
    

@dataclass
class AppSession:
    """Represents a continuous session of app usage."""
    app_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: float = 0.0  # in seconds
    context_changes: List[str] = field(default_factory=list)
    titles_seen: List[str] = field(default_factory=list)
    status_changes: List[Tuple[str, str]] = field(default_factory=list)  # (timestamp, status)
    window_count: int = 0
    session_id: Optional[int] = None  # Database ID
    
    @property
    def duration_minutes(self) -> float:
        """Return duration in minutes."""
        return self.total_duration / 60.0
    
    @property
    def is_active(self) -> bool:
        """Check if this session is still active."""
        return self.end_time is None

@dataclass
class AppStatistics:
    """Statistics for a specific app."""
    app_name: str
    total_time: float = 0.0  # in seconds
    session_count: int = 0
    contexts: Dict[str, float] = field(default_factory=dict)  # context -> time spent
    statuses: Dict[str, float] = field(default_factory=dict)  # status -> time spent
    average_session_duration: float = 0.0
    longest_session: float = 0.0
    last_used: Optional[datetime] = None
    
    def update_averages(self):
        """Update calculated fields."""
        if self.session_count > 0:
            self.average_session_duration = self.total_time / self.session_count
   
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