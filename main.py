# main.py
from tracker import WindowTracker
from datetime import datetime
import time
from ModeController.enums import ModeType, StandardSubMode, FocusType
from config_manager import (
    get_all_categories,
    create_category,
    delete_category,
    add_pattern_to_category,
    remove_pattern_from_category
)

def category_management_demo():
    """Demonstrates the CRUD functionality for categories."""
    print("--- Category Management Demo ---")

    print("\n1. Initial categories:")
    print(get_all_categories())

    print("\n2. Creating a new category 'media_player'...")
    create_category('media_player')
    
    print("\n3. Adding patterns to 'media_player'...")
    add_pattern_to_category('media_player', 'vlc')
    add_pattern_to_category('media_player', 'potplayer')
    
    print("\n4. Current categories after additions:")
    print(get_all_categories())

    print("\n5. Removing a pattern ('opera' from 'browser')...")
    remove_pattern_from_category('browser', 'opera')
    
    print("\n6. Deleting the 'search' category...")
    delete_category('search')

    print("\n7. Final state of categories:")
    print(get_all_categories())

    print("--------------------------------\n")

# In main.py, update the display_analytics function:
def display_analytics(tracker):
    """Display various analytics from the tracker."""
    # Get the analytics helper
    analytics = tracker.analytics
    
    # Get the raw history for debugging
    raw_history = tracker.history.raw_history
    print(f"\nRaw history entries: {len(raw_history)}")
    if raw_history:
        for i, entry in enumerate(raw_history[-5:]):  # Show last 5 entries
            print(f"{i+1}. {entry.app} - {entry.context} ({entry.status}) at {entry.timestamp}")
    else:
        print("No history data available")
    
    # Get recent sessions
    recent_sessions = tracker.history.get_recent_sessions(hours=1)
    print("\nRecent Sessions:")
    if recent_sessions:
        for session in recent_sessions:
            duration = session.total_duration if session.end_time else (datetime.now() - session.start_time).total_seconds()
            print(f"- {session.app_name}: {duration:.1f}s, contexts: {session.context_changes}, statuses: {[s[1] for s in session.status_changes]}")
    else:
        print("No recent sessions available")
    
    # Get time by app
    print("\nTime by App (last hour):")
    time_by_app = analytics.get_time_by_app(hours=1)
    if time_by_app:
        for app, seconds in time_by_app.items():
            print(f"- {app}: {seconds:.1f}s ({seconds/60:.1f} minutes)")
    else:
        print("No app usage data available")
    
    # Get productivity summary
    prod_summary = analytics.get_productivity_summary(hours=1)
    print("\nProductivity Summary (last hour):")
    if prod_summary and 'total_time' in prod_summary:
        print(f"Total time: {prod_summary['total_time']:.1f}s")
        if 'times' in prod_summary:
            for status, time in prod_summary['times'].items():
                print(f"- {status}: {time:.1f}s ({prod_summary['percentages'][status]:.1f}%)")
    else:
        print("No productivity data available")
    
    # Get app rankings
    print("\nMost Productive Apps (last hour):")
    productive_apps = analytics.get_productive_apps_ranking(hours=1)
    if productive_apps:
        for app, time, ratio in productive_apps[:3]:
            print(f"- {app}: {time:.1f}s ({ratio*100:.1f}% productive)")
    else:
        print("No productive apps data available")
    
    print("\nMost Distracting Apps (last hour):")
    distracting_apps = analytics.get_distracting_apps_ranking(hours=1)
    if distracting_apps:
        for app, time, ratio in distracting_apps[:3]:
            print(f"- {app}: {time:.1f}s ({ratio*100:.1f}% distracting)")
    else:
        print("No distracting apps data available")
    
    # Get daily summary
    print("\nDaily Summary (last 7 days):")
    daily_summary = analytics.get_daily_summary(days=7)
    if daily_summary:
        for day in daily_summary:
            print(f"\n{day['day_name']} ({day['date']}):")
            print(f"Total time: {day['total_time']/60:.1f} minutes")
            if 'percentages' in day:
                for status, percent in day['percentages'].items():
                    print(f"- {status}: {percent:.1f}%")
    else:
        print("No daily summary data available")

def main():
    # Run the category management demo first if needed
    # category_management_demo()

    print("Starting the multi-window tracker. Press Ctrl+C to stop.")
    
    tracker = WindowTracker(interval=1)
    mode_controller = tracker.history.mode_controller
    tracker.start()
    
    try:
        # Initial wait to capture some activity
        time.sleep(2)
        
        # Demo mode switching
        # mode_controller.switch_to_focus(FocusType.LIGHT)
        time.sleep(5)
        
        # mode_controller.change_focus_type(FocusType.DEEP)
        time.sleep(5)
        
        # mode_controller.switch_to_standard_normal()
        time.sleep(5)
        
        # mode_controller.switch_to_kids_mode()
        time.sleep(5)
        
        # mode_controller.switch_to_standard_normal()
        
        # Let it run for a while to collect more data
        time.sleep(60)
        
    except KeyboardInterrupt:
        print("\nStopping tracker...")
    finally:
        tracker.stop()
        
        # Display analytics after stopping
        display_analytics(tracker)

if __name__ == "__main__":
    main()