# main.py
# main.py

from tracker import WindowTracker
from analytics import SessionAnalytics
from datetime import datetime
import time
from ModeController.mode_controller import ModeController
from ModeController.enums import ModeType, StandardSubMode, FocusType
# Import our new category management functions
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



def main():
    # Run the category management demo first if needed
    # category_management_demo()

    print("Starting the multi-window tracker. Press Ctrl+C to stop.")
    
    tracker = WindowTracker(interval=1)
    mode_controller = mode_controller = tracker.history.mode_controller
    tracker.start()
    
    try:
        import time
        # Let it run longer to capture more activity
        time.sleep(2)  # 2 minutes instead of 30 seconds
        # Switch directly to any state:
        # mode_controller.switch_to_mode(ModeType.STANDARD, StandardSubMode.FOCUS, FocusType.DEEP)

        # # Or use convenience methods:
        # mode_controller.switch_to_focus(FocusType.LIGHT)
        # time.sleep(5)  # 2 minutes instead of 30 seconds
        # mode_controller.change_focus_type(FocusType.DEEP)  # Change focus type while in focus mode
        time.sleep(5)  # 2 minutes instead of 30 seconds
        mode_controller.switch_to_standard_normal()        # Back to normal
        # time.sleep(5)  # 2 minutes instead of 30 seconds
        # mode_controller.switch_to_kids_mode()             # Switch to kids mode
        # time.sleep(5)  # 2 minutes instead of 30 seconds

        
        
        # time.sleep(0.5)  # 2 minutes instead of 30 seconds
        # mode_controller.switch_submode(StandardSubMode.NORMAL)
        
        time.sleep(60)  # 2 minutes instead of 30 seconds
        # print("\nTracker is running. we switch to kids mode.")
        # mode_controller.switch_mode(ModeType.KIDS)

        time.sleep(60)  # 2 minutes instead of 30 seconds
    except KeyboardInterrupt:
        print("\nStopping tracker...")
    finally:
        tracker.stop()
        # time.sleep(tracker.interval)
        
        # Get the raw history for debugging
        raw_history = tracker.history.raw_history
        print(f"\nRaw history entries: {len(raw_history)}")
        for i, entry in enumerate(raw_history[-5:]):  # Show last 5 entries
            print(f"{i+1}. {entry.app} - {entry.context} ({entry.status}) at {entry.timestamp}")
        
        # Get recent sessions
        recent_sessions = tracker.history.get_recent_sessions(hours=1)
        print("\nRecent Sessions:")
        for session in recent_sessions:
            duration = session.total_duration if session.end_time else (datetime.now() - session.start_time).total_seconds()
            print(f"- {session.app_name}: {duration:.1f}s, contexts: {session.context_changes}, statuses: {[s[1] for s in session.status_changes]}")
        
        # Get productivity summary
        prod_summary = tracker.history.get_status_summary(hours=1)
        print("\nProductivity Summary:")
        print(f"Total time: {prod_summary['total_time']:.1f}s")
        for status, time in prod_summary['times'].items():
            print(f"- {status}: {time:.1f}s ({prod_summary['percentages'][status]:.1f}%)")
        
        # Get app rankings
        print("\nMost Productive Apps:")
        for app, time, ratio in tracker.history.get_productive_apps_ranking(hours=1)[:3]:
            print(f"- {app}: {time:.1f}s ({ratio*100:.1f}% productive)")
        
        print("\nMost Distracting Apps:")
        for app, time, ratio in tracker.history.get_distracting_apps_ranking(hours=1)[:3]:
            print(f"- {app}: {time:.1f}s ({ratio*100:.1f}% distracting)")

if __name__ == "__main__":
    main()