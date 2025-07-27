# analytics.py
from collections import defaultdict
from typing import Dict, List, Optional , Tuple
from datetime import datetime, timedelta
from models import WindowInfo
import logging

class SessionAnalytics:
    """Provides analytics based on window focus history using the WindowHistory class."""

    def __init__(self, window_history):
        self.window_history = window_history

    # In analytics.py, update the get_time_by_app method:
    def get_time_by_app(self, hours: Optional[int] = None) -> Dict[str, float]:
        """Calculates total time spent in each application."""
        try:
            if hours is not None:
                result = self.window_history.get_app_usage_summary(hours)
                return result if result else {}
            else:
                # Get all-time statistics
                stats = {}
                for app_name, app_stats in self.window_history.get_app_statistics().items():
                    stats[app_name] = app_stats.total_time
                return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))
        except Exception as e:
            logging.error(f"Error in get_time_by_app: {e}")
            return {}
        
    def get_time_by_window_type(self) -> Dict[str, float]:
        """Calculates total time spent in each window type."""
        stats = defaultdict(float)
        for record in self.window_history.raw_history:
            stats[record.window_type] += self.window_history.tracker.interval
        return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))

    def get_top_windows(self, n: int = 5, hours: Optional[int] = None) -> List[Dict]:
        """Finds the most frequently focused individual windows."""
        usage = defaultdict(float)
        window_details = {}
        
        # Determine which records to process
        if hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            records = [r for r in self.window_history.raw_history 
                      if datetime.fromisoformat(r.timestamp) >= cutoff]
        else:
            records = self.window_history.raw_history

        for record in records:
            usage[record.window_id] += self.window_history.tracker.interval
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

    def get_productivity_summary(self, hours: Optional[int] = None) -> Dict[str, Dict[str, float]]:
        """
        Get comprehensive productivity status summary.
        If hours is None, returns all-time statistics.
        """
        if hours is not None:
            return self.window_history.get_status_summary(hours)
        else:
            # Calculate all-time statistics
            status_times = defaultdict(float)
            status_details = {
                'Productive': defaultdict(float),
                'Neutral': defaultdict(float),
                'Distracting': defaultdict(float),
                'Blocked': defaultdict(float)
            }
            
            for session in self.window_history.app_sessions:
                if session.status_changes:
                    time_per_status = session.total_duration / len(session.status_changes)
                    for _, status in session.status_changes:
                        status_times[status] += time_per_status
                        status_details[status][session.app_name] += time_per_status
                else:
                    status_times['Neutral'] += session.total_duration
                    status_details['Neutral'][session.app_name] += session.total_duration
            
            # Include current session if exists
            if self.window_history.current_session:
                session = self.window_history.current_session
                duration = (datetime.now() - session.start_time).total_seconds()
                
                if session.status_changes:
                    time_per_status = duration / len(session.status_changes)
                    for _, status in session.status_changes:
                        status_times[status] += time_per_status
                        status_details[status][session.app_name] += time_per_status
                else:
                    status_times['Neutral'] += duration
                    status_details['Neutral'][session.app_name] += duration
            
            total_time = sum(status_times.values())
            
            # Calculate percentages
            status_percentages = {}
            for status in ['Productive', 'Neutral', 'Distracting', 'Blocked']:
                if total_time > 0:
                    status_percentages[status] = (status_times[status] / total_time) * 100
                else:
                    status_percentages[status] = 0.0
            
            return {
                'times': dict(status_times),
                'percentages': status_percentages,
                'details': {k: dict(v) for k, v in status_details.items()},
                'total_time': total_time
            }

    def get_productive_apps_ranking(self, hours: Optional[int] = None) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by productivity.
        Returns: [(app_name, productive_time, productivity_ratio), ...]
        """
        if hours is not None:
            return self.window_history.get_productive_apps_ranking(hours)
        else:
            # Calculate all-time rankings
            app_stats = defaultdict(lambda: {'productive': 0.0, 'total': 0.0})
            
            for session in self.window_history.app_sessions:
                if session.status_changes:
                    productive_time = session.total_duration * (
                        sum(1 for _, status in session.status_changes if status == 'Productive') / 
                        len(session.status_changes)
                    )
                    app_stats[session.app_name]['productive'] += productive_time
                    app_stats[session.app_name]['total'] += session.total_duration
            
            # Include current session if exists
            if self.window_history.current_session:
                session = self.window_history.current_session
                duration = (datetime.now() - session.start_time).total_seconds()
                
                if session.status_changes:
                    productive_time = duration * (
                        sum(1 for _, status in session.status_changes if status == 'Productive') / 
                        len(session.status_changes)
                    )
                    app_stats[session.app_name]['productive'] += productive_time
                    app_stats[session.app_name]['total'] += duration
            
            app_rankings = []
            for app_name, stats in app_stats.items():
                productivity_ratio = stats['productive'] / stats['total'] if stats['total'] > 0 else 0.0
                app_rankings.append((app_name, stats['productive'], productivity_ratio))
            
            # Sort by productive time (descending)
            app_rankings.sort(key=lambda x: x[1], reverse=True)
            
            return app_rankings

    # In analytics.py, add this method to the SessionAnalytics class:
    def get_distracting_apps_ranking(self, hours: Optional[int] = None) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by distraction time.
        Returns: [(app_name, distracting_time, distraction_ratio), ...]
        """
        if hours is not None:
            return self.window_history.get_distracting_apps_ranking(hours)
        else:
            # Calculate all-time rankings
            app_stats = defaultdict(lambda: {'distracting': 0.0, 'total': 0.0})
            
            for session in self.window_history.app_sessions:
                if session.status_changes:
                    distracting_time = session.total_duration * (
                        sum(1 for _, status in session.status_changes if status == 'Distracting') / 
                        len(session.status_changes)
                    )
                    app_stats[session.app_name]['distracting'] += distracting_time
                    app_stats[session.app_name]['total'] += session.total_duration
            
            # Include current session if exists
            if self.window_history.current_session:
                session = self.window_history.current_session
                duration = (datetime.now() - session.start_time).total_seconds()
                
                if session.status_changes:
                    distracting_time = duration * (
                        sum(1 for _, status in session.status_changes if status == 'Distracting') / 
                        len(session.status_changes)
                    )
                    app_stats[session.app_name]['distracting'] += distracting_time
                    app_stats[session.app_name]['total'] += duration
            
            app_rankings = []
            for app_name, stats in app_stats.items():
                distraction_ratio = stats['distracting'] / stats['total'] if stats['total'] > 0 else 0.0
                app_rankings.append((app_name, stats['distracting'], distraction_ratio))
            
            # Sort by distracting time (descending)
            app_rankings.sort(key=lambda x: x[1], reverse=True)
            
            return app_rankings
    
    def get_daily_summary(self, days: int = 7) -> List[Dict]:
        """Get daily summaries for the last N days."""
        return self.window_history.get_daily_summary_range(days)

    def get_weekly_summary(self, weeks: int = 4) -> List[Dict]:
        """Get weekly summaries for the last N weeks."""
        return self.window_history.get_weekly_summary_range(weeks)

    def get_monthly_summary(self, months: int = 6) -> List[Dict]:
        """Get monthly summaries for the last N months."""
        return self.window_history.get_monthly_summary_range(months)