# Core/window_history.py (Modified version with database integration)
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import threading
import logging

from models import WindowInfo
from ModeController.mode_controller import ModeController
from database.database_manager import DatabaseManager

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

class WindowHistory:
    """
    Intelligent window history manager with database persistence.
    Maintains in-memory cache for current session while persisting to database.
    """
    
    def __init__(self, tracker, session_gap_seconds: int = 30, 
                 Mode_Controller: Optional[ModeController] = None,
                 database_url: str = "sqlite:///window_tracker.db"):
        self.session_gap_seconds = session_gap_seconds
        self.lock = threading.Lock()
        
        # Database manager
        self.db_manager = DatabaseManager(database_url)
        
        # In-memory cache for performance (recent data)
        self.raw_history: List[WindowInfo] = []  # Keep recent records in memory
        self.current_session: Optional[AppSession] = None
        self.app_statistics: Dict[str, AppStatistics] = {}  # Cache recent stats
        
        # Configuration
        self.cache_hours = 24  # Keep last 24 hours in memory
        self.max_raw_records = 10000  # Max records to keep in memory
        
        # Tracking state
        self.last_window_time: Optional[datetime] = None
        self.last_app: Optional[str] = None
        
        # Mode controller for enforcing modes
        self.mode_controller = Mode_Controller
        self.tracker = tracker
        
        # Load recent data into cache on startup
        self._load_recent_data_to_cache()
    
    def _load_recent_data_to_cache(self):
        """Load recent data from database into memory cache"""
        try:
            # Load recent window records
            self.raw_history = self.db_manager.get_window_records(limit=self.max_raw_records)
            
            # Load app statistics
            self.app_statistics = self.db_manager.get_app_statistics()
            
            logging.info(f"Loaded {len(self.raw_history)} records and {len(self.app_statistics)} app stats to cache")
        except Exception as e:
            logging.error(f"Error loading data to cache: {e}")
    
    def add_window_info(self, window_info: WindowInfo):
        """Add a new window info and update sessions accordingly."""
        with self.lock:
            self._add_window_info_unsafe(window_info)
    
    def _add_window_info_unsafe(self, window_info: WindowInfo):
        """Internal method - assumes lock is held."""
        # Parse timestamp
        current_time = datetime.fromisoformat(window_info.timestamp)
        
        # Add to in-memory cache
        self.raw_history.append(window_info)
        
        # Maintain cache size
        if len(self.raw_history) > self.max_raw_records:
            self.raw_history = self.raw_history[-self.max_raw_records:]
        
        # Determine if this is a new session
        is_new_session = self._should_start_new_session(
            window_info.app, current_time
        )
        
        if is_new_session:
            self._end_current_session(current_time)
            self._start_new_session(window_info, current_time)
            if self.mode_controller:
                self.mode_controller.enforce_current_mode(window_info)
        else:
            self._update_current_session(window_info, current_time)
        
        # Save to database (in background)
        try:
            session_id = self.current_session.session_id if self.current_session else None
            self.db_manager.save_window_record(window_info, session_id)
        except Exception as e:
            logging.error(f"Error saving window record to database: {e}")
        
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
        """End the current session and save to database."""
        if self.current_session is None:
            return
        
        self.current_session.end_time = end_time
        
        # Calculate duration
        duration = (end_time - self.current_session.start_time).total_seconds()
        self.current_session.total_duration = duration
        
        # Save session to database
        try:
            if self.current_session.session_id:
                # Update existing session
                self.db_manager.update_app_session(self.current_session.session_id, self.current_session)
            else:
                # This shouldn't happen, but handle it gracefully
                session_id = self.db_manager.save_app_session(self.current_session)
                self.current_session.session_id = session_id
        except Exception as e:
            logging.error(f"Error saving session to database: {e}")
        
        # Update app statistics in memory and database
        self._update_app_statistics(self.current_session)
        
        self.current_session = None
    
    def _start_new_session(self, window_info: WindowInfo, start_time: datetime):
        """Start a new session and save to database."""
        self.current_session = AppSession(
            app_name=window_info.app,
            start_time=start_time,
            context_changes=[window_info.context] if window_info.context else [],
            titles_seen=[window_info.raw_title],
            status_changes=[(start_time.isoformat(), window_info.status)],
            window_count=1
        )
        
        # Save initial session to database
        try:
            session_id = self.db_manager.save_app_session(self.current_session)
            self.current_session.session_id = session_id
        except Exception as e:
            logging.error(f"Error saving new session to database: {e}")
    
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
        
        # Periodically update session in database (every 10 records)
        if session.window_count % 10 == 0:
            try:
                if session.session_id:
                    # Calculate current duration for update
                    current_duration = (current_time - session.start_time).total_seconds()
                    session.total_duration = current_duration
                    self.db_manager.update_app_session(session.session_id, session)
            except Exception as e:
                logging.error(f"Error updating session in database: {e}")
    
    def _update_app_statistics(self, session: AppSession):
        """Update statistics for an app in memory and database."""
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
        
        # Save to database
        try:
            self.db_manager.save_app_statistics(stats)
        except Exception as e:
            logging.error(f"Error saving app statistics to database: {e}")
    
    def force_end_current_session(self):
        """Force end the current session (useful when stopping tracking)."""
        with self.lock:
            if self.current_session and self.last_window_time:
                self._end_current_session(self.last_window_time)
    
    # Database-backed methods (replace memory-only implementations)
    
    def get_app_statistics(self, app_name: Optional[str] = None) -> Dict[str, AppStatistics]:
        """Get statistics from database (with memory cache fallback)."""
        try:
            return self.db_manager.get_app_statistics(app_name)
        except Exception as e:
            logging.error(f"Error getting app statistics from database: {e}")
            # Fallback to memory cache
            with self.lock:
                if app_name:
                    return {app_name: self.app_statistics.get(app_name, AppStatistics(app_name))}
                return dict(self.app_statistics)
    
    def get_recent_sessions(self, hours: int = 24) -> List[AppSession]:
        """Get sessions from database (with memory fallback)."""
        try:
            sessions = self.db_manager.get_recent_sessions(hours)
            
            # Add current session if it's recent and not in database results
            if self.current_session:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                if self.current_session.start_time >= cutoff_time:
                    # Check if current session is already in results
                    current_in_results = any(
                        s.session_id == self.current_session.session_id 
                        for s in sessions if s.session_id
                    )
                    if not current_in_results:
                        sessions.append(self.current_session)
            
            return sessions
            
        except Exception as e:
            logging.error(f"Error getting recent sessions from database: {e}")
            # Fallback to memory-based method
            return self._get_recent_sessions_memory(hours)
    
    def _get_recent_sessions_memory(self, hours: int = 24) -> List[AppSession]:
        """Fallback method using memory cache."""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_sessions = []
            
            # This would need session tracking in memory - simplified for now
            if (self.current_session and 
                self.current_session.start_time >= cutoff_time):
                recent_sessions.append(self.current_session)
            
            return recent_sessions
    
    def get_sessions_by_period(self, period: str = 'day', offset: int = 0) -> List[AppSession]:
        """Get sessions for a specific period from database."""
        try:
            sessions = self.db_manager.get_sessions_by_period(period, offset)
            
            # Add current session if it falls within the period
            if self.current_session and offset == 0:  # Only for current period
                start_date, end_date = self.db_manager._calculate_period_range(period, offset)
                if start_date <= self.current_session.start_time < end_date:
                    # Check if already in results
                    current_in_results = any(
                        s.session_id == self.current_session.session_id 
                        for s in sessions if s.session_id
                    )
                    if not current_in_results:
                        sessions.append(self.current_session)
            
            return sessions
            
        except Exception as e:
            logging.error(f"Error getting sessions by period from database: {e}")
            return []
    
    def get_app_usage_summary(self, hours: int = 24) -> Dict[str, float]:
        """Get total usage time per app from database."""
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
        """Get app usage for a specific period from database."""
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
        """Get status summary for a specific period from database."""
        sessions = self.get_sessions_by_period(period, offset)
        status_times = defaultdict(float)
        status_details = {
            'Productive': defaultdict(float),
            'Neutral': defaultdict(float), 
            'Distracting': defaultdict(float),
            'Blocked': defaultdict(float)
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
        for status in ['Productive', 'Neutral', 'Distracting', 'Blocked']:
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
        """Get daily summaries for the last N days from database."""
        daily_summaries = []
        
        for i in range(days):
            day_summary = self.get_status_summary_by_period('day', i)
            date = datetime.now() - timedelta(days=i)
            day_summary['date'] = date.strftime('%Y-%m-%d')
            day_summary['day_name'] = date.strftime('%A')
            daily_summaries.append(day_summary)
        
        return daily_summaries
    
    def get_weekly_summary_range(self, weeks: int = 4) -> List[Dict]:
        """Get weekly summaries for the last N weeks from database."""
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
        """Get monthly summaries for the last N months from database."""
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
        """Get context usage breakdown for a specific app from database."""
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
        """Get productivity breakdown based on status from database."""
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
        """Get comprehensive status summary from database."""
        return self.get_status_summary_by_period('day', 0) if hours == 24 else self._get_status_summary_custom_hours(hours)
    
    def _get_status_summary_custom_hours(self, hours: int) -> Dict[str, Dict[str, float]]:
        """Get status summary for custom hour range."""
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
                time_per_status = duration / len(session.status_changes)
                for _, status in session.status_changes:
                    status_times[status] += time_per_status
                    status_details[status][session.app_name] += time_per_status
            else:
                status_times['Neutral'] += duration
                status_details['Neutral'][session.app_name] += duration
        
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
    
    def get_status_by_app(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """Get status breakdown by app from database."""
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
        """Get apps ranked by productivity from database."""
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
        """Get apps ranked by distraction time from database."""
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
        """Remove data older than specified days from database."""
        try:
            self.db_manager.cleanup_old_data(days)
            # Refresh cache after cleanup
            self._load_recent_data_to_cache()
        except Exception as e:
            logging.error(f"Error during database cleanup: {e}")
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get overall statistics summary from database."""
        try:
            # Get database stats
            with self.db_manager.get_session() as db_session:
                from database.models import WindowRecord, AppSessionDB, AppStatisticsDB
                
                total_raw_records = db_session.query(WindowRecord).count()
                total_sessions = db_session.query(AppSessionDB).count()
                total_apps = db_session.query(AppStatisticsDB).count()
                
                # Get earliest record
                earliest_record = db_session.query(WindowRecord).order_by(WindowRecord.timestamp).first()
                tracking_since = earliest_record.timestamp.isoformat() if earliest_record else None
                
                return {
                    'total_sessions': total_sessions + (1 if self.current_session else 0),
                    'total_apps_tracked': total_apps,
                    'total_raw_records': total_raw_records + len(self.raw_history),
                    'current_session_active': self.current_session is not None,
                    'tracking_since': tracking_since
                }
        except Exception as e:
            logging.error(f"Error getting stats summary: {e}")
            # Fallback to memory-based summary
            with self.lock:
                return {
                    'total_sessions': 1 if self.current_session else 0,
                    'total_apps_tracked': len(self.app_statistics),
                    'total_raw_records': len(self.raw_history),
                    'current_session_active': self.current_session is not None,
                    'tracking_since': self.raw_history[0].timestamp if self.raw_history else None
                }
    
    # Database-specific methods
    
    def get_raw_history_from_db(self, limit: Optional[int] = None, app_name: Optional[str] = None) -> List[WindowInfo]:
        """Get raw window records directly from database."""
        try:
            return self.db_manager.get_window_records(limit, app_name)
        except Exception as e:
            logging.error(f"Error getting raw history from database: {e}")
            return []
    
    def sync_cache_with_database(self):
        """Manually sync in-memory cache with database."""
        try:
            self._load_recent_data_to_cache()
            logging.info("Cache synced with database successfully")
        except Exception as e:
            logging.error(f"Error syncing cache with database: {e}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the database state."""
        try:
            with self.db_manager.get_session() as db_session:
                from database.models import WindowRecord, AppSessionDB, AppStatisticsDB
                
                return {
                    'window_records_count': db_session.query(WindowRecord).count(),
                    'sessions_count': db_session.query(AppSessionDB).count(),
                    'apps_tracked': db_session.query(AppStatisticsDB).count(),
                    'database_url': str(self.db_manager.engine.url),
                    'cache_size': len(self.raw_history),
                    'cache_hours': self.cache_hours
                }
        except Exception as e:
            logging.error(f"Error getting database info: {e}")
            return {'error': str(e)}