from datetime import timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class ModeSettings:
    """Configuration settings for each mode"""
    def __init__(self):
        self.allowed_apps: List[str] = []
        self.blocked_apps: List[str] = []
        self.minimized_apps: List[str] = []
        self.duration: Optional[timedelta] = None
        self.notifications_enabled: bool = True
        self.notification_intensity: str = "normal"  # "gentle", "normal", "strong"
        self.screen_time_limit: Optional[timedelta] = None
        self.productivity_target: Optional[int] = None
        self.time_limit: int = None
        self.bedtime_start: str = None
        self.bedtime_end: str = None
        self.parental_override_required: bool = False
        self.screen_time_alerts: bool = False
        self.educational_time_bonus: bool = False
        self.achievement_tracking: bool = False