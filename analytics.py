# analytics.py
from collections import defaultdict
from typing import List, Dict
from models import WindowInfo

class SessionAnalytics:
    """Provides analytics based on a session's window focus history."""

    def __init__(self, history: List[WindowInfo], interval: int):
        self.history = history
        self.interval = interval

    def get_time_by_app(self) -> Dict[str, float]:
        """Calculates total time spent in each application."""
        stats = defaultdict(float)
        for record in self.history:
            app_name = record.app or "Unknown App"
            stats[app_name] += self.interval
        return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))

    def get_time_by_window_type(self) -> Dict[str, float]:
        """Calculates total time spent in each window type."""
        stats = defaultdict(float)
        for record in self.history:
            stats[record.window_type] += self.interval
        return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))

    def get_top_windows(self, n: int = 5) -> List[Dict]:
        """Finds the most frequently focused individual windows."""
        usage = defaultdict(float)
        # Use a dict to store the latest info for each unique window ID
        window_details = {} 

        for record in self.history:
            usage[record.window_id] += self.interval
            window_details[record.window_id] = {
                "display_title": record.display_title,
                "app": record.app,
                "type": record.window_type
            }

        sorted_usage = sorted(usage.items(), key=lambda item: item[1], reverse=True)

        top_windows = []
        for window_id, total_time in sorted_usage[:n]:
            details = window_details[window_id]
            details["time_seconds"] = total_time
            top_windows.append(details)
            
        return top_windows