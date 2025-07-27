# analytics.py
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from layers.window_history import WindowHistory, AppSession, AppStatistics

class ModernAnalytics:
    """
    Advanced analytics system that leverages the WindowHistory class
    to provide comprehensive insights into user behavior and productivity.
    """
    
    def __init__(self, window_history: WindowHistory):
        self.history = window_history
    
    # ========== SESSION-BASED ANALYTICS ==========
    
    def get_session_insights(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive session-based insights."""
        sessions = self.history.get_recent_sessions(hours)
        
        if not sessions:
            return {"error": "No sessions found in the specified time period"}
        
        total_sessions = len(sessions)
        active_sessions = sum(1 for s in sessions if s.is_active)
        completed_sessions = total_sessions - active_sessions
        
        # Session duration statistics
        completed_durations = [s.duration_minutes for s in sessions if not s.is_active]
        
        if completed_durations:
            avg_session_duration = sum(completed_durations) / len(completed_durations)
            max_session_duration = max(completed_durations)
            min_session_duration = min(completed_durations)
        else:
            avg_session_duration = max_session_duration = min_session_duration = 0
        
        # App switching behavior
        app_switches = self._calculate_app_switches(sessions)
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "average_session_duration_minutes": round(avg_session_duration, 2),
            "longest_session_minutes": round(max_session_duration, 2),
            "shortest_session_minutes": round(min_session_duration, 2),
            "app_switching_frequency": app_switches,
            "most_used_apps": self._get_top_apps_from_sessions(sessions, 5),
            "context_diversity": self._calculate_context_diversity(sessions)
        }
    
    def get_focus_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze focus and attention patterns."""
        sessions = self.history.get_recent_sessions(hours)
        
        # Focus duration analysis
        focus_buckets = {
            "short_focus": 0,    # < 5 minutes
            "medium_focus": 0,   # 5-30 minutes
            "long_focus": 0,     # 30+ minutes
            "deep_focus": 0      # 60+ minutes
        }
        
        total_focus_time = 0
        focus_sessions = []
        
        for session in sessions:
            if session.is_active:
                duration = (datetime.now() - session.start_time).total_seconds() / 60
            else:
                duration = session.duration_minutes
            
            total_focus_time += duration
            focus_sessions.append({
                "app": session.app_name,
                "duration_minutes": round(duration, 2),
                "context_changes": len(session.context_changes),
                "window_count": session.window_count
            })
            
            if duration < 5:
                focus_buckets["short_focus"] += 1
            elif duration < 30:
                focus_buckets["medium_focus"] += 1
            elif duration < 60:
                focus_buckets["long_focus"] += 1
            else:
                focus_buckets["deep_focus"] += 1
        
        # Calculate focus quality metrics
        avg_context_changes = sum(len(s.context_changes) for s in sessions) / len(sessions) if sessions else 0
        
        return {
            "focus_distribution": focus_buckets,
            "total_focus_time_minutes": round(total_focus_time, 2),
            "average_context_changes_per_session": round(avg_context_changes, 2),
            "focus_quality_score": self._calculate_focus_quality_score(sessions),
            "detailed_sessions": focus_sessions[:10]  # Top 10 recent sessions
        }
    
    # ========== PRODUCTIVITY ANALYTICS ==========
    
    def get_productivity_insights(self, period: str = 'day', offset: int = 0) -> Dict[str, Any]:
        """Get comprehensive productivity analysis."""
        status_summary = self.history.get_status_summary_by_period(period, offset)
        sessions = self.history.get_sessions_by_period(period, offset)
        
        # Productivity trends
        productive_apps = self.history.get_productive_apps_ranking(24 if period == 'day' else 168)
        distracting_apps = self.history.get_distracting_apps_ranking(24 if period == 'day' else 168)
        
        # Time allocation analysis
        time_allocation = self._analyze_time_allocation(sessions)
        
        # Productivity score calculation
        productivity_score = self._calculate_productivity_score(status_summary)
        
        return {
            "period": period,
            "offset": offset,
            "productivity_score": productivity_score,
            "status_breakdown": status_summary,
            "time_allocation": time_allocation,
            "top_productive_apps": productive_apps[:5],
            "top_distracting_apps": distracting_apps[:5],
            "recommendations": self._generate_productivity_recommendations(status_summary, sessions)
        }
    
    def get_productivity_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze productivity trends over multiple days."""
        daily_summaries = self.history.get_daily_summary_range(days)
        
        trends = {
            "productivity_scores": [],
            "productive_time": [],
            "distracting_time": [],
            "neutral_time": [],
            "dates": []
        }
        
        for day_summary in reversed(daily_summaries):  # Reverse to get chronological order
            score = self._calculate_productivity_score(day_summary)
            trends["productivity_scores"].append(score)
            trends["productive_time"].append(day_summary["times"].get("Productive", 0) / 3600)  # Convert to hours
            trends["distracting_time"].append(day_summary["times"].get("Distracting", 0) / 3600)
            trends["neutral_time"].append(day_summary["times"].get("Neutral", 0) / 3600)
            trends["dates"].append(day_summary["date"])
        
        # Calculate trend direction
        if len(trends["productivity_scores"]) >= 2:
            recent_avg = sum(trends["productivity_scores"][-3:]) / min(3, len(trends["productivity_scores"]))
            earlier_avg = sum(trends["productivity_scores"][:3]) / min(3, len(trends["productivity_scores"]))
            trend_direction = "improving" if recent_avg > earlier_avg else "declining"
        else:
            trend_direction = "insufficient_data"
        
        return {
            "trends": trends,
            "trend_direction": trend_direction,
            "average_productivity_score": sum(trends["productivity_scores"]) / len(trends["productivity_scores"]) if trends["productivity_scores"] else 0,
            "best_day": self._find_best_day(daily_summaries),
            "insights": self._generate_trend_insights(trends)
        }
    
    # ========== BEHAVIORAL ANALYTICS ==========
    
    def get_behavioral_patterns(self, hours: int = 168) -> Dict[str, Any]:  # Default: 1 week
        """Analyze behavioral patterns and habits."""
        sessions = self.history.get_recent_sessions(hours)
        
        # Time-of-day patterns
        hourly_usage = defaultdict(float)
        app_usage_by_hour = defaultdict(lambda: defaultdict(float))
        
        for session in sessions:
            hour = session.start_time.hour
            duration = session.total_duration if not session.is_active else (datetime.now() - session.start_time).total_seconds()
            
            hourly_usage[hour] += duration / 3600  # Convert to hours
            app_usage_by_hour[hour][session.app_name] += duration / 3600
        
        # Day-of-week patterns
        daily_patterns = self._analyze_daily_patterns(sessions)
        
        # Context switching analysis
        context_analysis = self._analyze_context_switching(sessions)
        
        # Habit strength analysis
        habit_analysis = self._analyze_habits(sessions)
        
        return {
            "hourly_usage_patterns": dict(hourly_usage),
            "peak_usage_hours": self._find_peak_hours(hourly_usage),
            "daily_patterns": daily_patterns,
            "context_switching": context_analysis,
            "habit_analysis": habit_analysis,
            "most_consistent_apps": self._find_consistent_apps(sessions)
        }
    
    def get_app_deep_dive(self, app_name: str, hours: int = 168) -> Dict[str, Any]:
        """Get detailed analysis for a specific application."""
        sessions = [s for s in self.history.get_recent_sessions(hours) if s.app_name == app_name]
        app_stats = self.history.get_app_statistics(app_name).get(app_name)
        
        if not sessions:
            return {"error": f"No data found for app: {app_name}"}
        
        # Context breakdown
        context_breakdown = self.history.get_context_breakdown(app_name, hours)
        
        # Usage patterns
        usage_patterns = self._analyze_app_usage_patterns(sessions)
        
        # Efficiency metrics
        efficiency_metrics = self._calculate_app_efficiency(sessions)
        
        return {
            "app_name": app_name,
            "total_sessions": len(sessions),
            "total_time_hours": sum(s.total_duration for s in sessions if not s.is_active) / 3600,
            "average_session_duration": app_stats.average_session_duration / 60 if app_stats else 0,
            "longest_session_minutes": app_stats.longest_session / 60 if app_stats else 0,
            "context_breakdown": context_breakdown,
            "usage_patterns": usage_patterns,
            "efficiency_metrics": efficiency_metrics,
            "recommendations": self._generate_app_recommendations(app_name, sessions)
        }
    
    # ========== COMPARISON AND BENCHMARKING ==========
    
    def compare_periods(self, period1: Tuple[str, int], period2: Tuple[str, int]) -> Dict[str, Any]:
        """Compare two time periods."""
        period1_data = self.history.get_status_summary_by_period(period1[0], period1[1])
        period2_data = self.history.get_status_summary_by_period(period2[0], period2[1])
        
        comparison = {
            "period1": period1_data,
            "period2": period2_data,
            "changes": {}
        }
        
        # Calculate changes
        for status in ["Productive", "Neutral", "Distracting"]:
            time1 = period1_data["times"].get(status, 0)
            time2 = period2_data["times"].get(status, 0)
            
            if time2 > 0:
                change_percent = ((time1 - time2) / time2) * 100
            else:
                change_percent = 100 if time1 > 0 else 0
            
            comparison["changes"][status] = {
                "absolute_change_hours": (time1 - time2) / 3600,
                "percent_change": round(change_percent, 2)
            }
        
        # Overall productivity change
        score1 = self._calculate_productivity_score(period1_data)
        score2 = self._calculate_productivity_score(period2_data)
        
        comparison["productivity_change"] = {
            "score_change": round(score1 - score2, 2),
            "interpretation": "improved" if score1 > score2 else "declined" if score1 < score2 else "unchanged"
        }
        
        return comparison
    
    # ========== EXPORT AND REPORTING ==========
    
    def generate_comprehensive_report(self, period: str = 'week', offset: int = 0) -> Dict[str, Any]:
        """Generate a comprehensive analytics report."""
        report = {
            "report_generated": datetime.now().isoformat(),
            "period": period,
            "offset": offset,
            "summary": {},
            "productivity": {},
            "focus": {},
            "behavioral": {},
            "recommendations": []
        }
        
        # Get data based on period
        hours = {"day": 24, "week": 168, "month": 720}[period]
        
        # Summary metrics
        report["summary"] = self.get_session_insights(hours)
        
        # Productivity analysis
        report["productivity"] = self.get_productivity_insights(period, offset)
        
        # Focus analysis
        report["focus"] = self.get_focus_patterns(hours)
        
        # Behavioral patterns
        report["behavioral"] = self.get_behavioral_patterns(hours)
        
        # Overall recommendations
        report["recommendations"] = self._generate_comprehensive_recommendations(report)
        
        return report
    
    def export_data(self, format: str = 'json', period: str = 'week', offset: int = 0) -> str:
        """Export analytics data in specified format."""
        data = self.generate_comprehensive_report(period, offset)
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2, default=str)
        elif format.lower() == 'csv':
            return self._convert_to_csv(data)
        else:
            raise ValueError("Unsupported format. Use 'json' or 'csv'")
    
    # ========== HELPER METHODS ==========
    
    def _calculate_app_switches(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Calculate app switching frequency and patterns."""
        if len(sessions) < 2:
            return {"switches_per_hour": 0, "average_session_length": 0}
        
        total_switches = len(sessions) - 1
        total_time = sum(s.total_duration for s in sessions if not s.is_active)
        
        if total_time > 0:
            switches_per_hour = (total_switches / total_time) * 3600
        else:
            switches_per_hour = 0
        
        return {
            "total_switches": total_switches,
            "switches_per_hour": round(switches_per_hour, 2),
            "average_session_length": total_time / len(sessions) if sessions else 0
        }
    
    def _get_top_apps_from_sessions(self, sessions: List[AppSession], n: int) -> List[Dict[str, Any]]:
        """Get top apps by usage time from sessions."""
        app_times = defaultdict(float)
        
        for session in sessions:
            duration = session.total_duration
            if session.is_active:
                duration = (datetime.now() - session.start_time).total_seconds()
            app_times[session.app_name] += duration
        
        sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"app": app, "time_seconds": time, "time_hours": round(time / 3600, 2)}
            for app, time in sorted_apps[:n]
        ]
    
    def _calculate_context_diversity(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Calculate context diversity metrics."""
        all_contexts = set()
        context_changes_per_session = []
        
        for session in sessions:
            all_contexts.update(session.context_changes)
            context_changes_per_session.append(len(session.context_changes))
        
        return {
            "unique_contexts": len(all_contexts),
            "contexts": list(all_contexts),
            "average_contexts_per_session": sum(context_changes_per_session) / len(context_changes_per_session) if context_changes_per_session else 0
        }
    
    def _calculate_focus_quality_score(self, sessions: List[AppSession]) -> float:
        """Calculate a focus quality score based on session characteristics."""
        if not sessions:
            return 0.0
        
        total_score = 0
        for session in sessions:
            duration_minutes = session.duration_minutes if not session.is_active else (datetime.now() - session.start_time).total_seconds() / 60
            
            # Longer sessions get higher base score
            duration_score = min(duration_minutes / 30, 1.0)  # Cap at 30 minutes
            
            # Fewer context changes = better focus
            context_penalty = len(session.context_changes) * 0.1
            
            # Fewer window switches = better focus
            window_penalty = (session.window_count - 1) * 0.05
            
            session_score = max(0, duration_score - context_penalty - window_penalty)
            total_score += session_score
        
        return round((total_score / len(sessions)) * 100, 2)  # Convert to 0-100 scale
    
    def _calculate_productivity_score(self, status_summary: Dict[str, Any]) -> float:
        """Calculate productivity score from status summary."""
        percentages = status_summary.get("percentages", {})
        
        productive = percentages.get("Productive", 0)
        distracting = percentages.get("Distracting", 0)
        
        # Simple formula: Productive% - Distracting% + neutral bonus
        score = productive - distracting
        
        # Bonus for having some productive time
        if productive > 0:
            score += 10
        
        return round(max(0, min(100, score)), 2)
    
    def _analyze_time_allocation(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Analyze how time is allocated across different activities."""
        total_time = sum(s.total_duration for s in sessions if not s.is_active)
        
        if total_time == 0:
            return {"error": "No completed sessions to analyze"}
        
        app_categories = self._categorize_apps([s.app_name for s in sessions])
        
        category_times = defaultdict(float)
        for session in sessions:
            category = app_categories.get(session.app_name, "Other")
            duration = session.total_duration if not session.is_active else (datetime.now() - session.start_time).total_seconds()
            category_times[category] += duration
        
        # Convert to percentages
        category_percentages = {
            category: round((time / total_time) * 100, 2)
            for category, time in category_times.items()
        }
        
        return {
            "total_time_hours": round(total_time / 3600, 2),
            "category_breakdown": category_percentages,
            "time_efficiency": self._calculate_time_efficiency(category_percentages)
        }
    
    def _categorize_apps(self, app_names: List[str]) -> Dict[str, str]:
        """Categorize apps into productivity categories."""
        # This could be expanded with a more sophisticated categorization system
        productivity_apps = {"code", "terminal", "editor", "ide", "work", "office"}
        communication_apps = {"slack", "teams", "zoom", "mail", "outlook"}
        browser_apps = {"chrome", "firefox", "safari", "edge"}
        entertainment_apps = {"spotify", "youtube", "netflix", "games"}
        
        categories = {}
        for app in set(app_names):
            app_lower = app.lower()
            
            if any(term in app_lower for term in productivity_apps):
                categories[app] = "Productivity"
            elif any(term in app_lower for term in communication_apps):
                categories[app] = "Communication"
            elif any(term in app_lower for term in browser_apps):
                categories[app] = "Web Browsing"
            elif any(term in app_lower for term in entertainment_apps):
                categories[app] = "Entertainment"
            else:
                categories[app] = "Other"
        
        return categories
    
    def _calculate_time_efficiency(self, category_percentages: Dict[str, float]) -> float:
        """Calculate time efficiency score based on category allocation."""
        productive_categories = ["Productivity", "Communication"]
        efficiency_score = sum(category_percentages.get(cat, 0) for cat in productive_categories)
        
        return round(efficiency_score, 2)
    
    def _generate_productivity_recommendations(self, status_summary: Dict[str, Any], sessions: List[AppSession]) -> List[str]:
        """Generate productivity recommendations based on analysis."""
        recommendations = []
        
        percentages = status_summary.get("percentages", {})
        distracting_pct = percentages.get("Distracting", 0)
        productive_pct = percentages.get("Productive", 0)
        
        if distracting_pct > 30:
            recommendations.append("Consider using app blockers during focus sessions - distracting apps consume over 30% of your time")
        
        if productive_pct < 40:
            recommendations.append("Try to increase productive app usage - currently below 40% of total time")
        
        # Analyze session lengths
        short_sessions = sum(1 for s in sessions if s.duration_minutes < 15)
        if short_sessions > len(sessions) * 0.6:
            recommendations.append("Many sessions are under 15 minutes - consider longer focus blocks")
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations based on full report."""
        recommendations = []
        
        # Add specific recommendations based on different aspects of the report
        productivity_score = report["productivity"].get("productivity_score", 0)
        focus_score = report["focus"].get("focus_quality_score", 0)
        
        if productivity_score < 50:
            recommendations.append("🎯 Focus on increasing productive app usage and reducing distractions")
        
        if focus_score < 60:
            recommendations.append("🧘 Work on maintaining longer focus sessions with fewer interruptions")
        
        # Add more sophisticated recommendations based on patterns
        behavioral = report.get("behavioral", {})
        if behavioral.get("context_switching", {}).get("frequency", 0) > 10:
            recommendations.append("⚡ Reduce context switching to improve focus quality")
        
        return recommendations
    
    def _find_peak_hours(self, hourly_usage: Dict[int, float]) -> List[int]:
        """Find peak usage hours."""
        sorted_hours = sorted(hourly_usage.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]  # Top 3 hours
    
    def _analyze_daily_patterns(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Analyze patterns by day of week."""
        daily_usage = defaultdict(float)
        
        for session in sessions:
            day_name = session.start_time.strftime("%A")
            duration = session.total_duration if not session.is_active else (datetime.now() - session.start_time).total_seconds()
            daily_usage[day_name] += duration / 3600  # Convert to hours
        
        return dict(daily_usage)
    
    def _analyze_context_switching(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Analyze context switching patterns."""
        total_switches = sum(len(s.context_changes) for s in sessions)
        total_sessions = len(sessions)
        
        return {
            "total_context_switches": total_switches,
            "average_switches_per_session": round(total_switches / total_sessions, 2) if total_sessions else 0,
            "frequency": "high" if total_switches / total_sessions > 5 else "moderate" if total_switches / total_sessions > 2 else "low"
        }
    
    def _analyze_habits(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Analyze usage habits and consistency."""
        app_usage_days = defaultdict(set)
        
        for session in sessions:
            day = session.start_time.date()
            app_usage_days[session.app_name].add(day)
        
        # Find most consistent apps (used on most days)
        consistency_scores = {}
        total_days = len(set(s.start_time.date() for s in sessions))
        
        for app, days in app_usage_days.items():
            consistency_scores[app] = len(days) / total_days if total_days else 0
        
        most_consistent = sorted(consistency_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "most_consistent_apps": most_consistent[:5],
            "habit_strength": "strong" if any(score > 0.8 for _, score in most_consistent) else "moderate" if any(score > 0.5 for _, score in most_consistent) else "weak"
        }
    
    def _find_consistent_apps(self, sessions: List[AppSession]) -> List[Dict[str, Any]]:
        """Find apps used most consistently."""
        app_usage_days = defaultdict(set)
        app_sessions = defaultdict(int)
        
        for session in sessions:
            day = session.start_time.date()
            app_usage_days[session.app_name].add(day)
            app_sessions[session.app_name] += 1
        
        total_days = len(set(s.start_time.date() for s in sessions))
        
        consistent_apps = []
        for app in app_usage_days:
            consistency = len(app_usage_days[app]) / total_days if total_days else 0
            consistent_apps.append({
                "app": app,
                "consistency_score": round(consistency, 2),
                "days_used": len(app_usage_days[app]),
                "total_sessions": app_sessions[app]
            })
        
        return sorted(consistent_apps, key=lambda x: x["consistency_score"], reverse=True)
    
    def _analyze_app_usage_patterns(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Analyze usage patterns for a specific app."""
        if not sessions:
            return {}
        
        # Time of day analysis
        hourly_usage = defaultdict(int)
        daily_usage = defaultdict(int)
        
        for session in sessions:
            hourly_usage[session.start_time.hour] += 1
            daily_usage[session.start_time.strftime("%A")] += 1
        
        return {
            "preferred_hours": dict(hourly_usage),
            "preferred_days": dict(daily_usage),
            "peak_usage_hour": max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else None,
            "most_active_day": max(daily_usage.items(), key=lambda x: x[1])[0] if daily_usage else None
        }
    
    def _calculate_app_efficiency(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Calculate efficiency metrics for an app."""
        if not sessions:
            return {}
        
        total_duration = sum(s.total_duration for s in sessions if not s.is_active)
        total_context_changes = sum(len(s.context_changes) for s in sessions)
        total_window_changes = sum(s.window_count for s in sessions)
        
        return {
            "average_session_efficiency": round(total_duration / len(sessions) / 60, 2) if sessions else 0,  # minutes per session
            "context_change_rate": round(total_context_changes / (total_duration / 3600), 2) if total_duration else 0,  # changes per hour
            "window_change_rate": round(total_window_changes / (total_duration / 3600), 2) if total_duration else 0,  # changes per hour
            "focus_stability": "high" if total_context_changes / len(sessions) < 2 else "medium" if total_context_changes / len(sessions) < 5 else "low"
        }
    
    def _generate_app_recommendations(self, app_name: str, sessions: List[AppSession]) -> List[str]:
        """Generate recommendations for specific app usage."""
        if not sessions:
            return []
        
        recommendations = []
        
        avg_duration = sum(s.duration_minutes for s in sessions if not s.is_active) / len(sessions)
        avg_context_changes = sum(len(s.context_changes) for s in sessions) / len(sessions)
        
        if avg_duration < 10:
            recommendations.append(f"Consider longer focus sessions with {app_name} - current average is {avg_duration:.1f} minutes")
        
        if avg_context_changes > 3:
            recommendations.append(f"Try to reduce context switching within {app_name} sessions")
        
        return recommendations
    
    def _find_best_day(self, daily_summaries: List[Dict]) -> Dict[str, Any]:
        """Find the most productive day from daily summaries."""
        if not daily_summaries:
            return {}
        
        best_day = max(daily_summaries, key=lambda x: self._calculate_productivity_score(x))
        
        return {
            "date": best_day.get("date"),
            "day_name": best_day.get("day_name"),
            "productivity_score": self._calculate_productivity_score(best_day),
            "productive_time_hours": best_day["times"].get("Productive", 0) / 3600
        }
    
    def _generate_trend_insights(self, trends: Dict[str, List]) -> List[str]:
        """Generate insights from productivity trends."""
        insights = []
        
        scores = trends["productivity_scores"]
        if len(scores) >= 3:
            recent_trend = scores[-3:]
            if all(recent_trend[i] <= recent_trend[i+1] for i in range(len(recent_trend)-1)):
                insights.append("📈 Productivity is trending upward over the last few days")
            elif all(recent_trend[i] >= recent_trend[i+1] for i in range(len(recent_trend)-1)):
                insights.append("📉 Productivity has been declining recently")
        
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score > 70:
                insights.append("🎯 Overall productivity levels are strong")
            elif avg_score < 40:
                insights.append("⚠️ Productivity levels need improvement")
        
        return insights
    
    def _convert_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert analytics data to CSV format."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Metric', 'Value', 'Category'])
        
        # Summary data
        if 'summary' in data:
            summary = data['summary']
            writer.writerow(['Total Sessions', summary.get('total_sessions', 0), 'Summary'])
            writer.writerow(['Active Sessions', summary.get('active_sessions', 0), 'Summary'])
            writer.writerow(['Average Session Duration (min)', summary.get('average_session_duration_minutes', 0), 'Summary'])
        
        # Productivity data
        if 'productivity' in data and 'status_breakdown' in data['productivity']:
            status = data['productivity']['status_breakdown']
            if 'times' in status:
                for status_type, time_seconds in status['times'].items():
                    writer.writerow([f'{status_type} Time (hours)', round(time_seconds / 3600, 2), 'Productivity'])
            
            if 'percentages' in status:
                for status_type, percentage in status['percentages'].items():
                    writer.writerow([f'{status_type} Percentage', f'{percentage}%', 'Productivity'])
        
        # Focus data
        if 'focus' in data:
            focus = data['focus']
            writer.writerow(['Focus Quality Score', focus.get('focus_quality_score', 0), 'Focus'])
            writer.writerow(['Total Focus Time (min)', focus.get('total_focus_time_minutes', 0), 'Focus'])
        
        return output.getvalue()

    # ========== ADVANCED ANALYTICS METHODS ==========
    
    def get_interruption_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze interruption patterns and their impact on productivity."""
        sessions = self.history.get_recent_sessions(hours)
        
        interruptions = []
        total_sessions = len(sessions)
        short_sessions = 0  # Sessions under 5 minutes (likely interruptions)
        
        for i, session in enumerate(sessions):
            duration_minutes = session.duration_minutes if not session.is_active else (datetime.now() - session.start_time).total_seconds() / 60
            
            if duration_minutes < 5:
                short_sessions += 1
                
            # Analyze rapid app switching
            if i > 0:
                prev_session = sessions[i-1]
                time_gap = (session.start_time - (prev_session.end_time or prev_session.start_time)).total_seconds()
                
                if time_gap < 60:  # Less than 1 minute gap
                    interruptions.append({
                        'from_app': prev_session.app_name,
                        'to_app': session.app_name,
                        'gap_seconds': time_gap,
                        'timestamp': session.start_time.isoformat()
                    })
        
        interruption_rate = len(interruptions) / total_sessions if total_sessions > 0 else 0
        
        return {
            'total_interruptions': len(interruptions),
            'interruption_rate': round(interruption_rate, 3),
            'short_sessions_count': short_sessions,
            'short_sessions_percentage': round((short_sessions / total_sessions) * 100, 2) if total_sessions > 0 else 0,
            'most_disruptive_apps': self._find_disruptive_apps(interruptions),
            'interruption_timeline': interruptions[-10:],  # Last 10 interruptions
            'recommendations': self._generate_interruption_recommendations(interruption_rate, short_sessions, total_sessions)
        }
    
    def get_cognitive_load_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze cognitive load based on app switching and multitasking patterns."""
        sessions = self.history.get_recent_sessions(hours)
        
        if not sessions:
            return {"error": "No sessions found"}
        
        # Calculate cognitive load metrics
        total_switches = len(sessions) - 1
        total_time = sum(s.total_duration for s in sessions if not s.is_active)
        
        # Context switching frequency
        context_switches = sum(len(s.context_changes) for s in sessions)
        
        # Multitasking detection (multiple apps within short time windows)
        multitasking_periods = self._detect_multitasking_periods(sessions)
        
        # Cognitive load score (0-100, higher = more load)
        if total_time > 0:
            switch_rate = (total_switches / total_time) * 3600  # switches per hour
            context_rate = (context_switches / total_time) * 3600  # context switches per hour
            
            cognitive_load_score = min(100, (switch_rate * 10) + (context_rate * 5) + (len(multitasking_periods) * 2))
        else:
            cognitive_load_score = 0
        
        return {
            'cognitive_load_score': round(cognitive_load_score, 2),
            'app_switches_per_hour': round((total_switches / total_time) * 3600, 2) if total_time > 0 else 0,
            'context_switches_per_hour': round((context_switches / total_time) * 3600, 2) if total_time > 0 else 0,
            'multitasking_periods': len(multitasking_periods),
            'load_category': self._categorize_cognitive_load(cognitive_load_score),
            'peak_load_periods': multitasking_periods[:5],  # Top 5 most intensive periods
            'recommendations': self._generate_cognitive_load_recommendations(cognitive_load_score)
        }
    
    def get_attention_span_analysis(self, hours: int = 168) -> Dict[str, Any]:
        """Analyze attention span patterns and trends."""
        sessions = self.history.get_recent_sessions(hours)
        
        if not sessions:
            return {"error": "No sessions found"}
        
        # Group sessions by app to analyze attention spans
        app_attention_spans = defaultdict(list)
        
        for session in sessions:
            duration_minutes = session.duration_minutes if not session.is_active else (datetime.now() - session.start_time).total_seconds() / 60
            app_attention_spans[session.app_name].append(duration_minutes)
        
        # Calculate attention span metrics
        attention_metrics = {}
        overall_spans = []
        
        for app, spans in app_attention_spans.items():
            overall_spans.extend(spans)
            attention_metrics[app] = {
                'average_span': round(sum(spans) / len(spans), 2),
                'max_span': round(max(spans), 2),
                'min_span': round(min(spans), 2),
                'span_consistency': round(1 - (np.std(spans) / np.mean(spans)), 2) if len(spans) > 1 and np.mean(spans) > 0 else 0
            }
        
        # Overall attention metrics
        if overall_spans:
            avg_attention_span = sum(overall_spans) / len(overall_spans)
            attention_categories = {
                'deep_focus': sum(1 for span in overall_spans if span >= 30),  # 30+ minutes
                'moderate_focus': sum(1 for span in overall_spans if 10 <= span < 30),  # 10-30 minutes
                'brief_focus': sum(1 for span in overall_spans if 2 <= span < 10),  # 2-10 minutes
                'micro_focus': sum(1 for span in overall_spans if span < 2)  # <2 minutes
            }
        else:
            avg_attention_span = 0
            attention_categories = {'deep_focus': 0, 'moderate_focus': 0, 'brief_focus': 0, 'micro_focus': 0}
        
        return {
            'average_attention_span_minutes': round(avg_attention_span, 2),
            'attention_distribution': attention_categories,
            'app_specific_metrics': dict(attention_metrics),
            'best_focus_apps': self._find_best_focus_apps(attention_metrics),
            'attention_quality_score': self._calculate_attention_quality_score(attention_categories),
            'trends': self._analyze_attention_trends(sessions),
            'recommendations': self._generate_attention_recommendations(avg_attention_span, attention_categories)
        }
    
    def get_energy_pattern_analysis(self, days: int = 14) -> Dict[str, Any]:
        """Analyze energy and productivity patterns throughout the day over multiple days."""
        sessions = self.history.get_recent_sessions(days * 24)
        
        if not sessions:
            return {"error": "No sessions found"}
        
        # Group sessions by hour of day
        hourly_productivity = defaultdict(list)
        hourly_focus_duration = defaultdict(list)
        
        for session in sessions:
            hour = session.start_time.hour
            duration_minutes = session.duration_minutes if not session.is_active else (datetime.now() - session.start_time).total_seconds() / 60
            
            # Estimate productivity based on status changes and duration
            productivity_score = self._estimate_session_productivity(session)
            
            hourly_productivity[hour].append(productivity_score)
            hourly_focus_duration[hour].append(duration_minutes)
        
        # Calculate average metrics for each hour
        energy_pattern = {}
        for hour in range(24):
            if hourly_productivity[hour]:
                energy_pattern[hour] = {
                    'avg_productivity': round(sum(hourly_productivity[hour]) / len(hourly_productivity[hour]), 2),
                    'avg_focus_duration': round(sum(hourly_focus_duration[hour]) / len(hourly_focus_duration[hour]), 2),
                    'session_count': len(hourly_productivity[hour])
                }
            else:
                energy_pattern[hour] = {
                    'avg_productivity': 0,
                    'avg_focus_duration': 0,
                    'session_count': 0
                }
        
        # Identify peak energy periods
        peak_hours = sorted(energy_pattern.items(), key=lambda x: x[1]['avg_productivity'], reverse=True)[:3]
        low_energy_hours = sorted(energy_pattern.items(), key=lambda x: x[1]['avg_productivity'])[:3]
        
        return {
            'hourly_energy_pattern': energy_pattern,
            'peak_productivity_hours': [{'hour': h, **data} for h, data in peak_hours],
            'low_energy_hours': [{'hour': h, **data} for h, data in low_energy_hours],
            'energy_consistency': self._calculate_energy_consistency(energy_pattern),
            'optimal_work_window': self._find_optimal_work_window(energy_pattern),
            'recommendations': self._generate_energy_recommendations(energy_pattern, peak_hours)
        }
    
    def get_workflow_efficiency_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze workflow efficiency and identify bottlenecks."""
        sessions = self.history.get_recent_sessions(hours)
        
        if not sessions:
            return {"error": "No sessions found"}
        
        # Analyze app transition patterns
        transitions = []
        for i in range(1, len(sessions)):
            prev_session = sessions[i-1]
            current_session = sessions[i]
            
            transition_time = (current_session.start_time - (prev_session.end_time or prev_session.start_time)).total_seconds()
            
            transitions.append({
                'from_app': prev_session.app_name,
                'to_app': current_session.app_name,
                'transition_time': transition_time,
                'from_duration': prev_session.duration_minutes,
                'to_duration': current_session.duration_minutes if not current_session.is_active else 0
            })
        
        # Find common workflows
        workflow_patterns = self._identify_workflow_patterns(transitions)
        
        # Calculate efficiency metrics
        avg_transition_time = sum(t['transition_time'] for t in transitions) / len(transitions) if transitions else 0
        quick_transitions = sum(1 for t in transitions if t['transition_time'] < 5)  # Under 5 seconds
        slow_transitions = sum(1 for t in transitions if t['transition_time'] > 60)  # Over 1 minute
        
        # Identify inefficient patterns
        inefficient_patterns = self._find_inefficient_patterns(transitions)
        
        return {
            'total_transitions': len(transitions),
            'average_transition_time': round(avg_transition_time, 2),
            'quick_transitions': quick_transitions,
            'slow_transitions': slow_transitions,
            'transition_efficiency': round((quick_transitions / len(transitions)) * 100, 2) if transitions else 0,
            'common_workflows': workflow_patterns[:5],
            'inefficient_patterns': inefficient_patterns[:3],
            'workflow_recommendations': self._generate_workflow_recommendations(transitions, inefficient_patterns)
        }
    
    # ========== HELPER METHODS FOR ADVANCED ANALYTICS ==========
    
    def _find_disruptive_apps(self, interruptions: List[Dict]) -> List[Dict[str, Any]]:
        """Find apps that cause the most interruptions."""
        app_disruptions = defaultdict(int)
        
        for interruption in interruptions:
            app_disruptions[interruption['to_app']] += 1
        
        sorted_apps = sorted(app_disruptions.items(), key=lambda x: x[1], reverse=True)
        
        return [{'app': app, 'interruptions': count} for app, count in sorted_apps[:5]]
    
    def _generate_interruption_recommendations(self, interruption_rate: float, short_sessions: int, total_sessions: int) -> List[str]:
        """Generate recommendations for reducing interruptions."""
        recommendations = []
        
        if interruption_rate > 0.3:
            recommendations.append("⚠️ High interruption rate detected - consider using focus modes or app blockers")
        
        if short_sessions / total_sessions > 0.4 if total_sessions > 0 else False:
            recommendations.append("🎯 Many sessions are very short - try batching similar tasks together")
        
        if interruption_rate > 0.1:
            recommendations.append("📱 Consider turning off non-essential notifications during work periods")
        
        return recommendations
    
    def _detect_multitasking_periods(self, sessions: List[AppSession]) -> List[Dict[str, Any]]:
        """Detect periods of intensive multitasking."""
        multitasking_periods = []
        
        # Look for periods with rapid app switching
        for i in range(len(sessions) - 2):  # Need at least 3 sessions to detect pattern
            current_time = sessions[i].start_time
            apps_in_window = set()
            
            # Look at next 5 minutes
            j = i
            while j < len(sessions) and (sessions[j].start_time - current_time).total_seconds() <= 300:
                apps_in_window.add(sessions[j].app_name)
                j += 1
            
            if len(apps_in_window) >= 3:  # 3+ different apps in 5 minutes
                multitasking_periods.append({
                    'start_time': current_time.isoformat(),
                    'apps_count': len(apps_in_window),
                    'apps': list(apps_in_window),
                    'intensity': len(apps_in_window) / 5  # apps per minute
                })
        
        return sorted(multitasking_periods, key=lambda x: x['intensity'], reverse=True)
    
    def _categorize_cognitive_load(self, score: float) -> str:
        """Categorize cognitive load score."""
        if score < 20:
            return "Low"
        elif score < 40:
            return "Moderate"
        elif score < 60:
            return "High"
        else:
            return "Very High"
    
    def _generate_cognitive_load_recommendations(self, score: float) -> List[str]:
        """Generate recommendations for managing cognitive load."""
        recommendations = []
        
        if score > 60:
            recommendations.append("🧠 Very high cognitive load detected - consider taking regular breaks")
            recommendations.append("🎯 Try single-tasking: focus on one app/task at a time")
        elif score > 40:
            recommendations.append("⚡ Moderate to high cognitive load - reduce app switching frequency")
        
        if score > 20:
            recommendations.append("🔔 Consider using focus modes to minimize distractions")
        
        return recommendations
    
    def _find_best_focus_apps(self, attention_metrics: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Find apps with the best attention/focus metrics."""
        focus_scores = []
        
        for app, metrics in attention_metrics.items():
            # Calculate focus score based on average span and consistency
            focus_score = metrics['average_span'] * (1 + metrics['span_consistency'])
            focus_scores.append({
                'app': app,
                'focus_score': round(focus_score, 2),
                'avg_span': metrics['average_span'],
                'consistency': metrics['span_consistency']
            })
        
        return sorted(focus_scores, key=lambda x: x['focus_score'], reverse=True)[:5]
    
    def _calculate_attention_quality_score(self, categories: Dict[str, int]) -> float:
        """Calculate overall attention quality score."""
        total_sessions = sum(categories.values())
        if total_sessions == 0:
            return 0
        
        # Weight different focus categories
        weighted_score = (
            categories['deep_focus'] * 4 +
            categories['moderate_focus'] * 2 +
            categories['brief_focus'] * 1 +
            categories['micro_focus'] * 0
        )
        
        return round((weighted_score / (total_sessions * 4)) * 100, 2)
    
    def _analyze_attention_trends(self, sessions: List[AppSession]) -> Dict[str, Any]:
        """Analyze attention span trends over time."""
        if len(sessions) < 7:
            return {"insufficient_data": True}
        
        # Split sessions into early and recent periods
        mid_point = len(sessions) // 2
        early_sessions = sessions[:mid_point]
        recent_sessions = sessions[mid_point:]
        
        early_avg = sum(s.duration_minutes for s in early_sessions if not s.is_active) / len(early_sessions)
        recent_avg = sum(s.duration_minutes for s in recent_sessions if not s.is_active) / len(recent_sessions)
        
        trend = "improving" if recent_avg > early_avg else "declining" if recent_avg < early_avg else "stable"
        change_percent = ((recent_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0
        
        return {
            "trend": trend,
            "change_percent": round(change_percent, 2),
            "early_period_avg": round(early_avg, 2),
            "recent_period_avg": round(recent_avg, 2)
        }
    
    def _generate_attention_recommendations(self, avg_span: float, categories: Dict[str, int]) -> List[str]:
        """Generate recommendations for improving attention span."""
        recommendations = []
        
        if avg_span < 10:
            recommendations.append("⏰ Average attention span is quite short - try the Pomodoro technique")
        elif avg_span < 20:
            recommendations.append("🎯 Consider gradually increasing focus session lengths")
        
        total_sessions = sum(categories.values())
        if total_sessions > 0:
            deep_focus_ratio = categories['deep_focus'] / total_sessions
            if deep_focus_ratio < 0.2:
                recommendations.append("🧘 Aim for more deep focus sessions (30+ minutes)")
        
        micro_focus_ratio = categories['micro_focus'] / total_sessions if total_sessions > 0 else 0
        if micro_focus_ratio > 0.3:
            recommendations.append("⚡ Too many very short sessions - try to minimize interruptions")
        
        return recommendations
    
    def _estimate_session_productivity(self, session: AppSession) -> float:
        """Estimate productivity score for a session."""
        base_score = 50  # Neutral baseline
        
        # Duration bonus (longer sessions generally more productive)
        duration_minutes = session.duration_minutes if not session.is_active else (datetime.now() - session.start_time).total_seconds() / 60
        if duration_minutes > 30:
            base_score += 20
        elif duration_minutes > 15:
            base_score += 10
        elif duration_minutes < 5:
            base_score -= 20
        
        # Context switching penalty
        context_penalty = len(session.context_changes) * 5
        base_score -= context_penalty
        
        # Window switching penalty
        window_penalty = (session.window_count - 1) * 2
        base_score -= window_penalty
        
        # Status-based adjustment (if available)
        if session.status_changes:
            latest_status = session.status_changes[-1][1]
            if latest_status == "Productive":
                base_score += 30
            elif latest_status == "Distracting":
                base_score -= 30
        
        return max(0, min(100, base_score))
    
    def _calculate_energy_consistency(self, energy_pattern: Dict[int, Dict]) -> float:
        """Calculate how consistent energy levels are throughout the day."""
        productivity_scores = [data['avg_productivity'] for data in energy_pattern.values() if data['session_count'] > 0]
        
        if len(productivity_scores) < 2:
            return 0
        
        mean_productivity = sum(productivity_scores) / len(productivity_scores)
        variance = sum((score - mean_productivity) ** 2 for score in productivity_scores) / len(productivity_scores)
        std_dev = variance ** 0.5
        
        # Consistency score: higher when std dev is lower relative to mean
        consistency = max(0, 1 - (std_dev / mean_productivity)) if mean_productivity > 0 else 0
        
        return round(consistency * 100, 2)
    
    def _find_optimal_work_window(self, energy_pattern: Dict[int, Dict]) -> Dict[str, Any]:
        """Find the optimal continuous work window based on energy patterns."""
        # Find the longest continuous period of high productivity
        high_productivity_threshold = 60  # Productivity score threshold
        
        best_window = {"start_hour": None, "end_hour": None, "duration": 0, "avg_productivity": 0}
        current_window_start = None
        current_window_productivity = []
        
        for hour in sorted(energy_pattern.keys()):
            productivity = energy_pattern[hour]['avg_productivity']
            
            if productivity >= high_productivity_threshold:
                if current_window_start is None:
                    current_window_start = hour
                current_window_productivity.append(productivity)
            else:
                if current_window_start is not None:
                    # End of window
                    window_duration = len(current_window_productivity)
                    if window_duration > best_window["duration"]:
                        best_window = {
                            "start_hour": current_window_start,
                            "end_hour": current_window_start + window_duration - 1,
                            "duration": window_duration,
                            "avg_productivity": sum(current_window_productivity) / len(current_window_productivity)
                        }
                    
                    current_window_start = None
                    current_window_productivity = []
        
        # Check if window extends to end of day
        if current_window_start is not None:
            window_duration = len(current_window_productivity)
            if window_duration > best_window["duration"]:
                best_window = {
                    "start_hour": current_window_start,
                    "end_hour": current_window_start + window_duration - 1,
                    "duration": window_duration,
                    "avg_productivity": sum(current_window_productivity) / len(current_window_productivity)
                }
        
        return best_window
    
    def _generate_energy_recommendations(self, energy_pattern: Dict[int, Dict], peak_hours: List[Tuple]) -> List[str]:
        """Generate recommendations based on energy patterns."""
        recommendations = []
        
        if peak_hours:
            peak_time = peak_hours[0][0]  # First peak hour
            if 6 <= peak_time <= 10:
                recommendations.append("🌅 You're most productive in the morning - schedule important tasks early")
            elif 11 <= peak_time <= 14:
                recommendations.append("☀️ Peak productivity around midday - use this time for focused work")
            elif 15 <= peak_time <= 18:
                recommendations.append("🌆 Afternoon productivity peak - schedule demanding tasks then")
            elif 19 <= peak_time <= 22:
                recommendations.append("🌙 Evening productivity - you might be a night owl")
        
        # Check for consistency
        productive_hours = sum(1 for data in energy_pattern.values() if data['avg_productivity'] > 50)
        if productive_hours < 4:
            recommendations.append("⚡ Limited high-productivity hours - focus on optimizing your peak times")
        
        return recommendations
    
    def _identify_workflow_patterns(self, transitions: List[Dict]) -> List[Dict[str, Any]]:
        """Identify common workflow patterns from app transitions."""
        # Look for sequences of 2-3 app transitions that repeat
        pattern_counts = defaultdict(int)
        
        for i in range(len(transitions) - 1):
            pattern = (transitions[i]['from_app'], transitions[i]['to_app'], transitions[i+1]['to_app'])
            pattern_counts[pattern] += 1
        
        common_patterns = []
        for pattern, count in pattern_counts.items():
            if count >= 2:  # Pattern appears at least twice
                avg_transition_time = sum(
                    t['transition_time'] for t in transitions 
                    if t['from_app'] == pattern[0] and t['to_app'] == pattern[1]
                ) / max(1, sum(1 for t in transitions if t['from_app'] == pattern[0] and t['to_app'] == pattern[1]))
                
                common_patterns.append({
                    'pattern': ' → '.join(pattern),
                    'frequency': count,
                    'avg_transition_time': round(avg_transition_time, 2)
                })
        
        return sorted(common_patterns, key=lambda x: x['frequency'], reverse=True)
    
    def _find_inefficient_patterns(self, transitions: List[Dict]) -> List[Dict[str, Any]]:
        """Find inefficient workflow patterns."""
        inefficient = []
        
        # Find slow transitions
        slow_transitions = [t for t in transitions if t['transition_time'] > 30]  # Over 30 seconds
        
        if slow_transitions:
            slow_apps = defaultdict(list)
            for t in slow_transitions:
                slow_apps[f"{t['from_app']} → {t['to_app']}"].append(t['transition_time'])
            
            for transition, times in slow_apps.items():
                if len(times) >= 2:  # Multiple slow transitions for same pattern
                    inefficient.append({
                        'pattern': transition,
                        'avg_delay': round(sum(times) / len(times), 2),
                        'occurrences': len(times),
                        'type': 'slow_transition'
                    })
        
        # Find back-and-forth patterns (indicating indecision or poor workflow)
        for i in range(len(transitions) - 1):
            if (transitions[i]['from_app'] == transitions[i+1]['to_app'] and 
                transitions[i]['to_app'] == transitions[i+1]['from_app']):
                inefficient.append({
                    'pattern': f"{transitions[i]['from_app']} ↔ {transitions[i]['to_app']}",
                    'type': 'back_and_forth',
                    'time_wasted': transitions[i]['transition_time'] + transitions[i+1]['transition_time']
                })
        
        return sorted(inefficient, key=lambda x: x.get('avg_delay', x.get('time_wasted', 0)), reverse=True)
    
    def _generate_workflow_recommendations(self, transitions: List[Dict], inefficient_patterns: List[Dict]) -> List[str]:
        """Generate workflow optimization recommendations."""
        recommendations = []
        
        if inefficient_patterns:
            slow_patterns = [p for p in inefficient_patterns if p['type'] == 'slow_transition']
            if slow_patterns:
                recommendations.append(f"⚡ Optimize transitions - {slow_patterns[0]['pattern']} takes {slow_patterns[0]['avg_delay']:.1f}s on average")
            
            back_forth = [p for p in inefficient_patterns if p['type'] == 'back_and_forth']
            if back_forth:
                recommendations.append("🔄 Reduce back-and-forth app switching - plan tasks in advance")
        
        avg_transition = sum(t['transition_time'] for t in transitions) / len(transitions) if transitions else 0
        if avg_transition > 10:
            recommendations.append("🎯 Consider batching similar tasks to reduce context switching")
        
        return recommendations

# Helper function for numpy operations (simplified version)
class np:
    @staticmethod
    def mean(data):
        return sum(data) / len(data) if data else 0
    
    @staticmethod
    def std(data):
        if len(data) < 2:
            return 0
        mean_val = sum(data) / len(data)
        variance = sum((x - mean_val) ** 2 for x in data) / len(data)
        return variance ** 0.5