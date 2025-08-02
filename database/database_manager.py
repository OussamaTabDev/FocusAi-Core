
# Core/database/database_manager.py
from sqlalchemy import create_engine, and_, func, desc
from sqlalchemy.orm import sessionmaker, Session
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
import logging
from .models import Base, WindowRecord, AppSessionDB, AppStatisticsDB
from  models import WindowInfo , AppSession, AppStatistics
# from layers.window_history import  

class DatabaseManager:
    """Manages database operations for window tracking data"""
    
    def __init__(self, database_url: str = "sqlite:///window_tracker.db"):
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def save_window_record(self, window_info: WindowInfo, session_id: Optional[int] = None):
        """Save a single window record to database"""
        with self.get_session() as db_session:
            try:
                record = WindowRecord(
                    raw_title=window_info.raw_title,
                    window_id=window_info.window_id,
                    timestamp=datetime.fromisoformat(window_info.timestamp),
                    position_x=window_info.position[0],
                    position_y=window_info.position[1],
                    width=window_info.size[0],
                    height=window_info.size[1],
                    is_active=window_info.is_active,
                    is_minimized=window_info.is_minimized,
                    is_maximized=window_info.is_maximized,
                    is_visible=window_info.is_visible,
                    z_order=window_info.z_order,
                    process_name=window_info.process_name,
                    process=window_info.process,
                    class_name=window_info.class_name,
                    is_system_window=window_info.is_system_window,
                    is_topmost=window_info.is_topmost,
                    parent_window_exists=window_info.parent_window_exists,
                    window_type=window_info.window_type,
                    app=window_info.app,
                    original_app=window_info.original_app,
                    status=window_info.status,
                    context=window_info.context,
                    domain=window_info.domain,
                    display_title=window_info.display_title,
                    extra_info=window_info.extra_info,
                    session_id=session_id
                )
                db_session.add(record)
                db_session.commit()
                return record.id
            except Exception as e:
                db_session.rollback()
                logging.error(f"Error saving window record: {e}")
                raise
    
    def save_app_session(self, session: AppSession) -> int:
        """Save app session to database"""
        with self.get_session() as db_session:
            try:
                db_session_obj = AppSessionDB(
                    app_name=session.app_name,
                    start_time=session.start_time,
                    end_time=session.end_time,
                    total_duration=session.total_duration,
                    window_count=session.window_count,
                    context_changes=session.context_changes,
                    titles_seen=session.titles_seen[-50:],  # Keep only last 50 titles
                    status_changes=session.status_changes
                )
                db_session.add(db_session_obj)
                db_session.commit()
                return db_session_obj.id
            except Exception as e:
                db_session.rollback()
                logging.error(f"Error saving app session: {e}")
                raise
    
    def update_app_session(self, session_id: int, session: AppSession):
        """Update existing app session"""
        with self.get_session() as db_session:
            try:
                db_session_obj = db_session.query(AppSessionDB).filter_by(id=session_id).first()
                if db_session_obj:
                    db_session_obj.end_time = session.end_time
                    db_session_obj.total_duration = session.total_duration
                    db_session_obj.window_count = session.window_count
                    db_session_obj.context_changes = session.context_changes
                    db_session_obj.titles_seen = session.titles_seen[-50:]
                    db_session_obj.status_changes = session.status_changes
                    db_session.commit()
            except Exception as e:
                db_session.rollback()
                logging.error(f"Error updating app session: {e}")
                raise
    
    def save_app_statistics(self, stats: AppStatistics):
        """Save or update app statistics"""
        with self.get_session() as db_session:
            try:
                db_stats = db_session.query(AppStatisticsDB).filter_by(
                    app_name=stats.app_name).first()
                if db_stats:
                    # update existing row
                    db_stats.total_time = stats.total_time
                    db_stats.session_count = stats.session_count
                    db_stats.average_session_duration = stats.average_session_duration
                    db_stats.longest_session = stats.longest_session
                    db_stats.last_used = stats.last_used
                    db_stats.contexts = stats.contexts
                    db_stats.statuses = stats.statuses
                else:
                    # NEW row: stamp with today’s calendar day
                    db_stats = AppStatisticsDB(
                        app_name=stats.app_name,
                        day_use=datetime.today().date(),  # <-- HERE
                        total_time=stats.total_time,
                        session_count=stats.session_count,
                        average_session_duration=stats.average_session_duration,
                        longest_session=stats.longest_session,
                        last_used=stats.last_used,
                        contexts=stats.contexts,
                        statuses=stats.statuses
                    )
                    db_session.add(db_stats)
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                logging.error(f"Error saving app statistics: {e}")
                raise
    
    def get_recent_sessions(self, hours: int = 24) -> List[AppSession]:
        """Get recent sessions from database"""
        with self.get_session() as db_session:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            db_sessions = db_session.query(AppSessionDB).filter(
                AppSessionDB.start_time >= cutoff_time
            ).order_by(AppSessionDB.start_time).all()
            
            return [self._convert_db_session_to_app_session(s) for s in db_sessions]
    
    def get_sessions_by_period(self, period: str, offset: int = 0) -> List[AppSession]:
        """Get sessions for a specific period"""
        start_date, end_date = self._calculate_period_range(period, offset)
        
        with self.get_session() as db_session:
            db_sessions = db_session.query(AppSessionDB).filter(
                and_(
                    AppSessionDB.start_time >= start_date,
                    AppSessionDB.start_time < end_date
                )
            ).order_by(AppSessionDB.start_time).all()
            
            return [self._convert_db_session_to_app_session(s) for s in db_sessions]
    
    def get_app_statistics(self, app_name: Optional[str] = None) -> Dict[str, AppStatistics]:
        """Get app statistics from database"""
        with self.get_session() as db_session:
            query = db_session.query(AppStatisticsDB)
            if app_name:
                query = query.filter_by(app_name=app_name)
            
            db_stats = query.all()
            result = {}
            
            for stat in db_stats:
                result[stat.app_name] = AppStatistics(
                    app_name=stat.app_name,
                    total_time=stat.total_time,
                    session_count=stat.session_count,
                    contexts=stat.contexts or {},
                    statuses=stat.statuses or {},
                    average_session_duration=stat.average_session_duration,
                    longest_session=stat.longest_session,
                    last_used=stat.last_used
                )
            
            return result
    
    def get_window_records(self, limit: Optional[int] = None, app_name: Optional[str] = None) -> List[WindowInfo]:
        """Get window records from database"""
        with self.get_session() as db_session:
            query = db_session.query(WindowRecord).order_by(desc(WindowRecord.timestamp))
            
            if app_name:
                query = query.filter_by(app=app_name)
            if limit:
                query = query.limit(limit)
            
            records = query.all()
            return [self._convert_db_record_to_window_info(r) for r in records]
    
    def cleanup_old_data(self, days: int = 30):
        """Remove data older than specified days"""
        with self.get_session() as db_session:
            try:
                cutoff_time = datetime.now() - timedelta(days=days)
                
                # Delete old window records
                db_session.query(WindowRecord).filter(
                    WindowRecord.timestamp < cutoff_time
                ).delete()
                
                # Delete old sessions
                old_sessions = db_session.query(AppSessionDB).filter(
                    AppSessionDB.start_time < cutoff_time
                ).all()
                
                for session in old_sessions:
                    db_session.delete(session)
                
                # Recalculate statistics for affected apps
                affected_apps = set(session.app_name for session in old_sessions)
                for app_name in affected_apps:
                    self._recalculate_app_statistics(db_session, app_name)
                
                db_session.commit()
                logging.info(f"Cleaned up data older than {days} days")
                
            except Exception as e:
                db_session.rollback()
                logging.error(f"Error during cleanup: {e}")
                raise
    
    def _calculate_period_range(self, period: str, offset: int) -> Tuple[datetime, datetime]:
        """Calculate start and end dates for a period"""
        now = datetime.now()
        
        if period == 'day':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=offset)
            end_date = start_date + timedelta(days=1)
        elif period == 'week':
            days_since_monday = now.weekday()
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                days=days_since_monday + (offset * 7)
            )
            end_date = start_date + timedelta(days=7)
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for _ in range(offset):
                start_date = start_date.replace(day=1) - timedelta(days=1)
                start_date = start_date.replace(day=1)
            
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)
        else:
            raise ValueError("Period must be 'day', 'week', or 'month'")
        
        return start_date, end_date
    
    def _convert_db_session_to_app_session(self, db_session: AppSessionDB) -> AppSession:
        """Convert database session to AppSession object"""
        return AppSession(
            app_name=db_session.app_name,
            start_time=db_session.start_time,
            end_time=db_session.end_time,
            total_duration=db_session.total_duration,
            context_changes=db_session.context_changes or [],
            titles_seen=db_session.titles_seen or [],
            status_changes=db_session.status_changes or [],
            window_count=db_session.window_count
        )
    
    def _convert_db_record_to_window_info(self, record: WindowRecord) -> WindowInfo:
        """Convert database record to WindowInfo object"""
        return WindowInfo(
            raw_title=record.raw_title,
            window_id=record.window_id,
            timestamp=record.timestamp.isoformat(),
            position=(record.position_x, record.position_y),
            size=(record.width, record.height),
            is_active=record.is_active,
            is_minimized=record.is_minimized,
            is_maximized=record.is_maximized,
            is_visible=record.is_visible,
            z_order=record.z_order,
            process_name=record.process_name,
            process=record.process,
            class_name=record.class_name,
            is_system_window=record.is_system_window,
            is_topmost=record.is_topmost,
            parent_window_exists=record.parent_window_exists,
            window_type=record.window_type,
            app=record.app,
            original_app=record.original_app,
            status=record.status,
            context=record.context,
            domain=record.domain,
            display_title=record.display_title,
            extra_info=record.extra_info or {}
        )
    
    def _recalculate_app_statistics(self, db_session: Session, app_name: str):
        """Recalculate statistics for an app based on remaining sessions"""
        sessions = db_session.query(AppSessionDB).filter_by(app_name=app_name).all()
        
        if not sessions:
            # No sessions left, delete statistics
            db_session.query(AppStatisticsDB).filter_by(app_name=app_name).delete()
            return
        
        # Calculate statistics
        total_time = sum(s.total_duration for s in sessions if s.end_time)
        session_count = len([s for s in sessions if s.end_time])
        avg_duration = total_time / session_count if session_count > 0 else 0.0
        longest_session = max((s.total_duration for s in sessions if s.end_time), default=0.0)
        last_used = max((s.end_time for s in sessions if s.end_time), default=None)
        
        # Update or create statistics
        stats = db_session.query(AppStatisticsDB).filter_by(app_name=app_name).first()
        if stats:
            stats.total_time = total_time
            stats.session_count = session_count
            stats.average_session_duration = avg_duration
            stats.longest_session = longest_session
            stats.last_used = last_used
        else:
            stats = AppStatisticsDB(
                app_name=app_name,
                total_time=total_time,
                day_use=datetime.today().date(),
                session_count=session_count,
                average_session_duration=avg_duration,
                longest_session=longest_session,
                last_used=last_used,
                contexts={},
                statuses={}
            )
            db_session.add(stats)
    
    def get_today_statistics(self) -> Dict[str, AppStatistics]:
        """Return per-app usage for the current calendar day."""
        today = datetime.today().date()
        with self.get_session() as db_session:
            rows = db_session.query(AppStatisticsDB).filter(
                func.date(AppStatisticsDB.day_use) == today
            ).all()

            return {
                row.app_name: AppStatistics(
                    app_name=row.app_name,
                    total_time=row.total_time,
                    session_count=row.session_count,
                    contexts=row.contexts or {},
                    statuses=row.statuses or {},
                    average_session_duration=row.average_session_duration,
                    longest_session=row.longest_session,
                    last_used=row.last_used
                )
                for row in rows
            }
            
    def get_statistics_for_day(self, day: date | datetime) -> Dict[str, AppStatistics]:
        """
        Return per-app usage for the given calendar day.
        Accepts either a `date` or `datetime` instance.
        """
        target = day.date() if isinstance(day, datetime) else day

        with self.get_session() as db_session:
            rows = (
                db_session.query(AppStatisticsDB)
                .filter(func.date(AppStatisticsDB.day_use) == target)
                .all()
            )

            return {
                row.app_name: AppStatistics(
                    app_name=row.app_name,
                    total_time=row.total_time,
                    session_count=row.session_count,
                    contexts=row.contexts or {},
                    statuses=row.statuses or {},
                    average_session_duration=row.average_session_duration,
                    longest_session=row.longest_session,
                    last_used=row.last_used,
                )
                for row in rows
            }