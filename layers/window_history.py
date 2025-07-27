# window_history.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import threading

from models import WindowInfo
from ModeController.mode_controller import ModeController
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

class WindowHistory:
    """
    Intelligent window history manager that focuses on app usage patterns
    while preserving context and status information.
    """
    
    def __init__(self, tracker ,session_gap_seconds: int = 30 , Mode_Controller: Optional[ModeController] = None):
        self.session_gap_seconds = session_gap_seconds
        self.lock = threading.Lock()
        
        # Core data structures
        self.raw_history: List[WindowInfo] = []
        self.app_sessions: List[AppSession] = []
        self.current_session: Optional[AppSession] = None
        self.app_statistics: Dict[str, AppStatistics] = {}
        
        # Tracking state
        self.last_window_time: Optional[datetime] = None
        self.last_app: Optional[str] = None
        
        # Mode controller for enforcing modes
        self.mode_controller = Mode_Controller
        self.tracker = tracker
    def add_window_info(self, window_info: WindowInfo):
        """Add a new window info and update sessions accordingly."""
        with self.lock:
            self._add_window_info_unsafe(window_info)
    
    def _add_window_info_unsafe(self, window_info: WindowInfo):
        """Internal method - assumes lock is held."""
        # Parse timestamp
        current_time = datetime.fromisoformat(window_info.timestamp)
        
        # Add to raw history
        self.raw_history.append(window_info)
        
        # Determine if this is a new session
        is_new_session = self._should_start_new_session(
            window_info.app, current_time
        )
        
        if is_new_session:
            self._end_current_session(current_time)
            self._start_new_session(window_info, current_time)
            self.mode_controller.enforce_current_mode(window_info)
        else:
            self._update_current_session(window_info, current_time)
        
        # Update tracking state
        self.last_window_time = current_time
        self.last_app = window_info.app
    
    def _should_start_new_session(self, app_name: str, current_time: datetime) -> bool:
        """Determine if we should start a new session."""
        # First window ever
        if self.current_session is None:
            return True
        
        # Different app
        if self.current_session.app_name != app_name:
            return True
        
        # Same app but too much time passed
        if (self.last_window_time and 
            (current_time - self.last_window_time).total_seconds() > self.session_gap_seconds):
            return True
        
        return False
    
    def _end_current_session(self, end_time: datetime):
        """End the current session and calculate its duration."""
        if self.current_session is None:
            return
        
        self.current_session.end_time = end_time
        
        # Calculate duration
        duration = (end_time - self.current_session.start_time).total_seconds()
        self.current_session.total_duration = duration
        
        # Update app statistics
        self._update_app_statistics(self.current_session)
        
        # Archive the session
        self.app_sessions.append(self.current_session)
        self.current_session = None
    
    def _start_new_session(self, window_info: WindowInfo, start_time: datetime):
        """Start a new session."""
        self.current_session = AppSession(
            app_name=window_info.app,
            start_time=start_time,
            context_changes=[window_info.context] if window_info.context else [],
            titles_seen=[window_info.raw_title],
            status_changes=[(start_time.isoformat(), window_info.status)],
            window_count=1
        )
    
    def _update_current_session(self, window_info: WindowInfo, current_time: datetime):
        """Update the current session with new window info."""
        if self.current_session is None:
            return
        
        session = self.current_session
        
        # Update context if changed
        if (window_info.context and 
            window_info.context not in session.context_changes):
            session.context_changes.append(window_info.context)
        
        # Update titles (keep unique recent ones)
        if window_info.raw_title not in session.titles_seen[-10:]:  # Last 10 titles
            session.titles_seen.append(window_info.raw_title)
        
        # Update status if changed
        if (session.status_changes and 
            session.status_changes[-1][1] != window_info.status):
            session.status_changes.append((current_time.isoformat(), window_info.status))
        
        session.window_count += 1
    
    def _update_app_statistics(self, session: AppSession):
        """Update statistics for an app based on a completed session."""
        app_name = session.app_name
        
        if app_name not in self.app_statistics:
            self.app_statistics[app_name] = AppStatistics(app_name=app_name)
        
        stats = self.app_statistics[app_name]
        
        # Update basic stats
        stats.total_time += session.total_duration
        stats.session_count += 1
        stats.last_used = session.end_time or session.start_time
        
        # Update longest session
        if session.total_duration > stats.longest_session:
            stats.longest_session = session.total_duration
        
        # Update context time tracking
        if session.context_changes:
            # Distribute time evenly among contexts for now
            # Could be improved with more sophisticated tracking
            time_per_context = session.total_duration / len(session.context_changes)
            for context in session.context_changes:
                if context:
                    stats.contexts[context] = stats.contexts.get(context, 0) + time_per_context
        
        # Update status time tracking
        if session.status_changes:
            # Simple approach: distribute time evenly
            time_per_status = session.total_duration / len(session.status_changes)
            for _, status in session.status_changes:
                stats.statuses[status] = stats.statuses.get(status, 0) + time_per_status
        
        # Update calculated fields
        stats.update_averages()
    
    def force_end_current_session(self):
        """Force end the current session (useful when stopping tracking)."""
        with self.lock:
            if self.current_session and self.last_window_time:
                self._end_current_session(self.last_window_time)
    
    def get_app_statistics(self, app_name: Optional[str] = None) -> Dict[str, AppStatistics]:
        """Get statistics for specific app or all apps."""
        with self.lock:
            if app_name:
                return {app_name: self.app_statistics.get(app_name, AppStatistics(app_name))}
            return dict(self.app_statistics)
    
    def get_recent_sessions(self, hours: int = 24) -> List[AppSession]:
        """Get sessions from the last N hours."""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_sessions = []
            
            for session in self.app_sessions:
                if session.start_time >= cutoff_time:
                    recent_sessions.append(session)
            
            # Include current session if it's recent
            if (self.current_session and 
                self.current_session.start_time >= cutoff_time):
                recent_sessions.append(self.current_session)
            
            return recent_sessions
    
    def get_sessions_by_period(self, period: str = 'day', offset: int = 0) -> List[AppSession]:
        """
        Get sessions for a specific period.
        period: 'day', 'week', 'month'
        offset: 0 for current, 1 for previous, etc.
        """
        with self.lock:
            now = datetime.now()
            
            if period == 'day':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=offset)
                end_date = start_date + timedelta(days=1)
            elif period == 'week':
                # Start of week (Monday)
                days_since_monday = now.weekday()
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                    days=days_since_monday + (offset * 7)
                )
                end_date = start_date + timedelta(days=7)
            elif period == 'month':
                # Start of month
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if offset > 0:
                    for _ in range(offset):
                        start_date = start_date.replace(day=1) - timedelta(days=1)
                        start_date = start_date.replace(day=1)
                
                # End of month
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
            else:
                raise ValueError("Period must be 'day', 'week', or 'month'")
            
            sessions = []
            for session in self.app_sessions:
                if start_date <= session.start_time < end_date:
                    sessions.append(session)
            
            # Include current session if it's in the period
            if (self.current_session and 
                start_date <= self.current_session.start_time < end_date):
                sessions.append(self.current_session)
            
            return sessions
    
    def get_app_usage_summary(self, hours: int = 24) -> Dict[str, float]:
        """Get total usage time per app in the last N hours."""
        recent_sessions = self.get_recent_sessions(hours)
        usage_summary = defaultdict(float)
        
        for session in recent_sessions:
            if session.is_active:
                # For active session, calculate duration up to now
                duration = (datetime.now() - session.start_time).total_seconds()
            else:
                duration = session.total_duration
            
            usage_summary[session.app_name] += duration
        
        return dict(usage_summary)
    
    def get_app_usage_by_period(self, period: str = 'day', offset: int = 0) -> Dict[str, float]:
        """Get app usage for a specific period."""
        sessions = self.get_sessions_by_period(period, offset)
        usage_summary = defaultdict(float)
        
        for session in sessions:
            if session.is_active and offset == 0:  # Only for current period
                duration = (datetime.now() - session.start_time).total_seconds()
            else:
                duration = session.total_duration
            
            usage_summary[session.app_name] += duration
        
        return dict(usage_summary)
    
    def get_status_summary_by_period(self, period: str = 'day', offset: int = 0) -> Dict[str, Dict[str, float]]:
        """Get status summary for a specific period."""
        sessions = self.get_sessions_by_period(period, offset)
        status_times = defaultdict(float)
        status_details = {
            'Productive': defaultdict(float),
            'Neutral': defaultdict(float), 
            'Distracting': defaultdict(float)
        }
        
        total_time = 0.0
        
        for session in sessions:
            if session.is_active and offset == 0:  # Only for current period
                duration = (datetime.now() - session.start_time).total_seconds()
            else:
                duration = session.total_duration
            
            total_time += duration
            
            if session.status_changes:
                time_per_status = duration / len(session.status_changes)
                for _, status in session.status_changes:
                    status_times[status] += time_per_status
                    status_details[status][session.app_name] += time_per_status
            else:
                status_times['Neutral'] += duration
                status_details['Neutral'][session.app_name] += duration
        
        # Calculate percentages
        status_percentages = {}
        for status in ['Productive', 'Neutral', 'Distracting']:
            if total_time > 0:
                status_percentages[status] = (status_times[status] / total_time) * 100
            else:
                status_percentages[status] = 0.0
        
        return {
            'times': dict(status_times),
            'percentages': status_percentages,
            'details': {k: dict(v) for k, v in status_details.items()},
            'total_time': total_time,
            'period': period,
            'offset': offset
        }
    
    def get_daily_summary_range(self, days: int = 7) -> List[Dict]:
        """Get daily summaries for the last N days."""
        daily_summaries = []
        
        for i in range(days):
            day_summary = self.get_status_summary_by_period('day', i)
            date = datetime.now() - timedelta(days=i)
            day_summary['date'] = date.strftime('%Y-%m-%d')
            day_summary['day_name'] = date.strftime('%A')
            daily_summaries.append(day_summary)
        
        return daily_summaries
    
    def get_weekly_summary_range(self, weeks: int = 4) -> List[Dict]:
        """Get weekly summaries for the last N weeks."""
        weekly_summaries = []
        
        for i in range(weeks):
            week_summary = self.get_status_summary_by_period('week', i)
            # Calculate week start date
            now = datetime.now()
            days_since_monday = now.weekday()
            week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                days=days_since_monday + (i * 7)
            )
            week_end = week_start + timedelta(days=6)
            
            week_summary['week_start'] = week_start.strftime('%Y-%m-%d')
            week_summary['week_end'] = week_end.strftime('%Y-%m-%d')
            week_summary['week_number'] = week_start.isocalendar()[1]
            weekly_summaries.append(week_summary)
        
        return weekly_summaries
    
    def get_monthly_summary_range(self, months: int = 6) -> List[Dict]:
        """Get monthly summaries for the last N months."""
        monthly_summaries = []
        
        for i in range(months):
            month_summary = self.get_status_summary_by_period('month', i)
            # Calculate month date
            now = datetime.now()
            month_date = now.replace(day=1)
            
            for _ in range(i):
                month_date = month_date.replace(day=1) - timedelta(days=1)
                month_date = month_date.replace(day=1)
            
            month_summary['month'] = month_date.strftime('%Y-%m')
            month_summary['month_name'] = month_date.strftime('%B %Y')
            monthly_summaries.append(month_summary)
        
        return monthly_summaries
    
    def get_context_breakdown(self, app_name: str, hours: int = 24) -> Dict[str, float]:
        """Get context usage breakdown for a specific app."""
        recent_sessions = self.get_recent_sessions(hours)
        context_times = defaultdict(float)
        
        for session in recent_sessions:
            if session.app_name == app_name:
                if session.context_changes:
                    duration = session.total_duration
                    if session.is_active:
                        duration = (datetime.now() - session.start_time).total_seconds()
                    
                    time_per_context = duration / len(session.context_changes)
                    for context in session.context_changes:
                        if context:
                            context_times[context] += time_per_context
        
        return dict(context_times)
    
    def get_productivity_summary(self, hours: int = 24) -> Dict[str, float]:
        """Get productivity breakdown based on status."""
        recent_sessions = self.get_recent_sessions(hours)
        productivity_times = defaultdict(float)
        
        for session in recent_sessions:
            if session.status_changes:
                duration = session.total_duration
                if session.is_active:
                    duration = (datetime.now() - session.start_time).total_seconds()
                
                time_per_status = duration / len(session.status_changes)
                for _, status in session.status_changes:
                    productivity_times[status] += time_per_status
        
        return dict(productivity_times)
    
    def get_status_summary(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """
        Get comprehensive status summary with time breakdown.
        Returns dict with 'times', 'percentages', and 'details'.
        """
        recent_sessions = self.get_recent_sessions(hours)
        status_times = defaultdict(float)
        status_details = {
            'Productive': defaultdict(float),
            'Neutral': defaultdict(float), 
            'Distracting': defaultdict(float),
            'Blocked': defaultdict(float)
        }
        
        total_time = 0.0
        
        for session in recent_sessions:
            duration = session.total_duration
            if session.is_active:
                duration = (datetime.now() - session.start_time).total_seconds()
            
            total_time += duration
            
            if session.status_changes:
                # Distribute time among status changes
                time_per_status = duration / len(session.status_changes)
                for _, status in session.status_changes:
                    status_times[status] += time_per_status
                    # Track which apps contribute to each status
                    status_details[status][session.app_name] += time_per_status
            else:
                # Default to Neutral if no status recorded
                status_times['Neutral'] += duration
                status_details['Neutral'][session.app_name] += duration
        
        # Calculate percentages
        status_percentages = {}
        for status in ['Productive', 'Neutral', 'Distracting' , 'Blocked']:
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
    
    def get_status_by_app(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """
        Get status breakdown by app.
        Returns: {app_name: {status: time_in_seconds}}
        """
        recent_sessions = self.get_recent_sessions(hours)
        app_status_times = defaultdict(lambda: defaultdict(float))
        
        for session in recent_sessions:
            duration = session.total_duration
            if session.is_active:
                duration = (datetime.now() - session.start_time).total_seconds()
            
            if session.status_changes:
                time_per_status = duration / len(session.status_changes)
                for _, status in session.status_changes:
                    app_status_times[session.app_name][status] += time_per_status
            else:
                app_status_times[session.app_name]['Neutral'] += duration
        
        # Convert to regular dict
        result = {}
        for app_name, status_dict in app_status_times.items():
            result[app_name] = dict(status_dict)
        
        return result
    
    def get_productive_apps_ranking(self, hours: int = 24) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by productivity.
        Returns: [(app_name, productive_time, productivity_ratio), ...]
        """
        app_status_breakdown = self.get_status_by_app(hours)
        app_rankings = []
        
        for app_name, status_times in app_status_breakdown.items():
            productive_time = status_times.get('Productive', 0.0)
            total_app_time = sum(status_times.values())
            
            productivity_ratio = productive_time / total_app_time if total_app_time > 0 else 0.0
            
            app_rankings.append((app_name, productive_time, productivity_ratio))
        
        # Sort by productive time (descending)
        app_rankings.sort(key=lambda x: x[1], reverse=True)
        
        return app_rankings
    
    def get_distracting_apps_ranking(self, hours: int = 24) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by distraction time.
        Returns: [(app_name, distracting_time, distraction_ratio), ...]
        """
        app_status_breakdown = self.get_status_by_app(hours)
        app_rankings = []
        
        for app_name, status_times in app_status_breakdown.items():
            distracting_time = status_times.get('Distracting', 0.0)
            total_app_time = sum(status_times.values())
            
            distraction_ratio = distracting_time / total_app_time if total_app_time > 0 else 0.0
            
            app_rankings.append((app_name, distracting_time, distraction_ratio))
        
        # Sort by distracting time (descending)
        app_rankings.sort(key=lambda x: x[1], reverse=True)
        
        return app_rankings
    
    def cleanup_old_data(self, days: int = 30):
        """Remove data older than specified days."""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # Clean raw history
            self.raw_history = [
                w for w in self.raw_history 
                if datetime.fromisoformat(w.timestamp) >= cutoff_time
            ]
            
            # Clean sessions
            self.app_sessions = [
                s for s in self.app_sessions 
                if s.start_time >= cutoff_time
            ]
            
            # Rebuild statistics from remaining sessions
            self.app_statistics.clear()
            for session in self.app_sessions:
                if session.end_time:  # Only completed sessions
                    self._update_app_statistics(session)
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get overall statistics summary."""
        with self.lock:
            total_sessions = len(self.app_sessions)
            if self.current_session:
                total_sessions += 1
            
            total_apps = len(self.app_statistics)
            total_raw_records = len(self.raw_history)
            
            return {
                'total_sessions': total_sessions,
                'total_apps_tracked': total_apps,
                'total_raw_records': total_raw_records,
                'current_session_active': self.current_session is not None,
                'tracking_since': self.raw_history[0].timestamp if self.raw_history else None
            }