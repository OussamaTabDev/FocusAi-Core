from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from models import AppStatistics, WindowInfo
import logging

class SessionAnalytics:
    """Provides analytics based on window focus history using the WindowHistory class."""

    def __init__(self, window_history):
        self.window_history = window_history

    def get_time_by_app(self, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> Dict[str, float]:
        """Calculates total time spent in each application."""
        try:
            if specific_day:
                start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
                end_of_day = start_of_day + timedelta(days=1)
                records = [r for r in self.window_history.raw_history 
                           if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
            elif hours is not None:
                cutoff = datetime.now() - timedelta(hours=hours)
                records = [r for r in self.window_history.raw_history 
                           if datetime.fromisoformat(r.timestamp) >= cutoff]
            else:
                records = self.window_history.raw_history

            stats = defaultdict(float)
            for record in records:
                stats[record.app] += self.window_history.tracker.interval

            return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))
        except Exception as e:
            logging.error(f"Error in get_time_by_app: {e}")
            return {}

    def get_time_by_window_type(self, specific_day: Optional[str] = str(datetime.today().date())) -> Dict[str, float]:
        """Calculates total time spent in each window type."""
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        else:
            records = self.window_history.raw_history

        stats = defaultdict(float)
        for record in records:
            stats[record.window_type] += self.window_history.tracker.interval

        return dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))

    def get_top_raw_windows(self, n: int = 0, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> List[Dict]:
        """Finds the most frequently focused individual windows."""
        usage = defaultdict(float)
        window_details = {}
        
        # Determine which records to process
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]
        else:
            records = self.window_history.raw_history

        for record in records:
            # print(record)
            usage[record.window_id] += self.window_history.tracker.interval
            window_details[record.window_id] = {
                "display_title": record.display_title,
                "app": record.app,
                "type": record.window_type,
                "status": record.status  
            }

        sorted_usage = sorted(usage.items(), key=lambda item: item[1], reverse=True)
        if n == 0:
            n = len(sorted_usage)
        top_windows = []
        for window_id, total_time in sorted_usage[:n]:
            details = window_details[window_id]
            details["time_seconds"] = total_time
            top_windows.append(details)
            
        return top_windows

    def get_top_windows(self, n: int = 5, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> List[Dict]:
        """Finds the most frequently focused individual windows, combining those with the same app name."""
        all_windows = self.get_top_raw_windows(hours=hours, specific_day=specific_day)
        
        # Aggregate usage times for windows with the same application name (case-insensitive)
        app_usage = defaultdict(float)
        app_details = {}
        
        for window in all_windows:
            print(window)
            app_name = window["app"].lower()
            app_usage[app_name] += window["time_seconds"]
            
            if app_name not in app_details:
                app_details[app_name] = {
                    "display_title": window["display_title"],
                    "app": window["app"],
                    "type": window["type"],
                    "time_seconds": window["time_seconds"],
                    "status": window["status"]  
                }
            else:
                # Update the display title to the most frequently used one
                if window["time_seconds"] > app_details[app_name]["time_seconds"]:
                    app_details[app_name]["display_title"] = window["display_title"]
                    app_details[app_name]["time_seconds"] = window["time_seconds"]
        
        # Sort the aggregated app usage by time
        sorted_app_usage = sorted(app_usage.items(), key=lambda item: item[1], reverse=True)
        
        top_apps = []
        for app_name, total_time in sorted_app_usage[:n]:
            details = app_details[app_name]
            details["time_seconds"] = total_time
            top_apps.append(details)
            
        return top_apps

    def get_productivity_summary(self, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> Dict[str, Dict[str, float]]:
        """
        Get comprehensive productivity status summary.
        If hours is None, returns all-time statistics.
        """
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]
        else:
            records = self.window_history.raw_history

        status_times = defaultdict(float)
        status_details = {
            'Productive': defaultdict(float),
            'Neutral': defaultdict(float),
            'Distracting': defaultdict(float),
            'Blocked': defaultdict(float)
        }
        
        for record in records:
            status = record.status  # Assuming each record has a 'status' attribute
            status_times[status] += self.window_history.tracker.interval
            status_details[status][record.app] += self.window_history.tracker.interval

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

    def get_productive_apps_ranking(self, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by productivity.
        Returns: [(app_name, productive_time, productivity_ratio), ...]
        """
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]
        else:
            records = self.window_history.raw_history

        app_stats = defaultdict(lambda: {'productive': 0.0, 'total': 0.0})
        
        for record in records:
            if record.status == 'Productive':
                app_stats[record.app]['productive'] += self.window_history.tracker.interval
            app_stats[record.app]['total'] += self.window_history.tracker.interval

        app_rankings = []
        for app_name, stats in app_stats.items():
            productivity_ratio = stats['productive'] / stats['total'] if stats['total'] > 0 else 0.0
            app_rankings.append((app_name, stats['productive'], productivity_ratio))
        
        # Sort by productive time (descending)
        app_rankings.sort(key=lambda x: x[1], reverse=True)
        
        return app_rankings

    def get_neutral_apps_ranking(self, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by productivity.
        Returns: [(app_name, productive_time, productivity_ratio), ...]
        """
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]
        else:
            records = self.window_history.raw_history

        app_stats = defaultdict(lambda: {'Neutral': 0.0, 'total': 0.0})
        
        for record in records:
            if record.status == 'Neutral':
                app_stats[record.app]['Neutral'] += self.window_history.tracker.interval
            app_stats[record.app]['total'] += self.window_history.tracker.interval

        app_rankings = []
        for app_name, stats in app_stats.items():
            productivity_ratio = stats['Neutral'] / stats['total'] if stats['total'] > 0 else 0.0
            app_rankings.append((app_name, stats['Neutral'], productivity_ratio))
        
        # Sort by Neutral time (descending)
        app_rankings.sort(key=lambda x: x[1], reverse=True)
        
        return app_rankings

    def get_distracting_apps_ranking(self, hours: Optional[int] = None, specific_day: Optional[str] = str(datetime.today().date())) -> List[Tuple[str, float, float]]:
        """
        Get apps ranked by distraction time.
        Returns: [(app_name, distracting_time, distraction_ratio), ...]
        """
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        elif hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]
        else:
            records = self.window_history.raw_history

        app_stats = defaultdict(lambda: {'distracting': 0.0, 'total': 0.0})
        
        for record in records:
            if record.status == 'Distracting':
                app_stats[record.app]['distracting'] += self.window_history.tracker.interval
            app_stats[record.app]['total'] += self.window_history.tracker.interval

        app_rankings = []
        for app_name, stats in app_stats.items():
            distraction_ratio = stats['distracting'] / stats['total'] if stats['total'] > 0 else 0.0
            app_rankings.append((app_name, stats['distracting'], distraction_ratio))
        
        # Sort by distracting time (descending)
        app_rankings.sort(key=lambda x: x[1], reverse=True)
        
        return app_rankings

    def get_daily_summary(self, days: int = 7, specific_day: Optional[str] = str(datetime.today().date())) -> List[Dict]:
        """Get daily summaries for the last N days or a specific day."""
        if specific_day:
            start_of_day = datetime.strptime(specific_day, "%Y-%m-%d")
            end_of_day = start_of_day + timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
        else:
            cutoff = datetime.now() - timedelta(days=days)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]

        daily_summaries = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            day_records = [r for r in records if start_of_day <= datetime.fromisoformat(r.timestamp) < end_of_day]
            daily_summaries.append({
                'date': start_of_day.date(),
                'total_time': sum(self.window_history.tracker.interval for r in day_records),
                'productive_time': sum(self.window_history.tracker.interval for r in day_records if r.status == 'Productive'),
                'distracting_time': sum(self.window_history.tracker.interval for r in day_records if r.status == 'Distracting')
            })

        return daily_summaries

    def get_weekly_summary(self, weeks: int = 4, specific_day: Optional[str] = str(datetime.today().date())) -> List[Dict]:
        """Get weekly summaries for the last N weeks or a specific week."""
        if specific_day:
            start_of_week = datetime.strptime(specific_day, "%Y-%m-%d") - timedelta(days=datetime.strptime(specific_day, "%Y-%m-%d").weekday())
            end_of_week = start_of_week + timedelta(days=7)
            records = [r for r in self.window_history.raw_history 
                       if start_of_week <= datetime.fromisoformat(r.timestamp) < end_of_week]
        else:
            cutoff = datetime.now() - timedelta(weeks=weeks)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]

        weekly_summaries = []
        for i in range(weeks):
            date = datetime.now() - timedelta(weeks=i)
            start_of_week = date - timedelta(days=date.weekday())
            end_of_week = start_of_week + timedelta(days=7)
            week_records = [r for r in records if start_of_week <= datetime.fromisoformat(r.timestamp) < end_of_week]
            weekly_summaries.append({
                'week_start': start_of_week.date(),
                'total_time': sum(self.window_history.tracker.interval for r in week_records),
                'productive_time': sum(self.window_history.tracker.interval for r in week_records if r.status == 'Productive'),
                'distracting_time': sum(self.window_history.tracker.interval for r in week_records if r.status == 'Distracting')
            })

        return weekly_summaries

    def get_monthly_summary(self, months: int = 6, specific_day: Optional[str] = str(datetime.today().date())) -> List[Dict]:
        """Get monthly summaries for the last N months or a specific month."""
        if specific_day:
            start_of_month = datetime.strptime(specific_day, "%Y-%m-%d").replace(day=1)
            end_of_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            records = [r for r in self.window_history.raw_history 
                       if start_of_month <= datetime.fromisoformat(r.timestamp) <= end_of_month]
        else:
            cutoff = datetime.now() - timedelta(days=months * 30)
            records = [r for r in self.window_history.raw_history 
                       if datetime.fromisoformat(r.timestamp) >= cutoff]

        monthly_summaries = []
        for i in range(months):
            date = datetime.now() - timedelta(days=i * 30)
            start_of_month = date.replace(day=1)
            end_of_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            month_records = [r for r in records if start_of_month <= datetime.fromisoformat(r.timestamp) <= end_of_month]
            monthly_summaries.append({
                'month_start': start_of_month.date(),
                'total_time': sum(self.window_history.tracker.interval for r in month_records),
                'productive_time': sum(self.window_history.tracker.interval for r in month_records if r.status == 'Productive'),
                'distracting_time': sum(self.window_history.tracker.interval for r in month_records if r.status == 'Distracting')
            })

        return monthly_summaries
    
    def get_today_statistics(self):
        return self.window_history.get_today_statistics()
    
    def get_statistics_for_day(self, day: date | datetime) -> Dict[str, AppStatistics]:
        return self.db_manager.get_statistics_for_day(day)