import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
import threading
import signal
import sys
import atexit
from concurrent.futures import ThreadPoolExecutor

from .enums import ModeType, StandardSubMode, FocusType
from .models import ModeSettings
from .settings_manager import SettingsManager
from models import WindowInfo
from layers.browser_controller import BrowserController
from layers.window_controller import WindowController
from layers.device_controller import DeviceController
from layers.notification_controller import NotificationController

class ModeController:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Initialize components
        self.active_block = True
        self.active_allowed = False
        self.active_minimized = True
        
        # Initialize controllers
        self.browser_controller = BrowserController()
        self.window_controller = WindowController()
        self.device_controller = DeviceController()
        self.notification_controller = NotificationController()
        
        # Settings management
        self.settings_manager = SettingsManager()
        self.settings_manager.load_settings()
        
        # Current state - initialize to safe defaults
        self.current_mode = ModeType.STANDARD
        self.current_submode = StandardSubMode.NORMAL
        self.current_focus_type: Optional[FocusType] = None
        self.is_active = False
        self.mode_start_time: Optional[datetime] = None
        
        # Tracking metrics
        self.focus_streak = 0
        self.last_focus_session: Optional[datetime] = None
        self.productivity_score = 0
        
        # Thread management
        self.tracking_thread = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.mode_lock = threading.Lock()
        
        # Shutdown management
        self._shutdown_event = threading.Event()
        self._active_futures = set()
        self._cleanup_registered = False
        
        # Transition state management
        self._transitioning = False
        self._pending_cleanup = []
        
        # Register cleanup handlers
        self._register_cleanup_handlers()
        
        # Initialize to standard/normal mode
        self._apply_mode_settings(ModeType.STANDARD, StandardSubMode.NORMAL, None)
        self._initialized = True

    def _register_cleanup_handlers(self):
        """Register cleanup handlers for graceful shutdown."""
        if self._cleanup_registered:
            return
            
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}, initiating graceful shutdown...")
            self._graceful_shutdown()
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
        
        # Register atexit handler as backup
        atexit.register(self._graceful_shutdown)
        
        self._cleanup_registered = True
        logging.info("Cleanup handlers registered")

    def _graceful_shutdown(self):
        """Perform graceful shutdown of all threads and resources."""
        if self._shutdown_event.is_set():
            return  # Already shutting down
            
        logging.info("Starting graceful shutdown...")
        self._shutdown_event.set()
        
        try:
            with self.mode_lock:
                self._transitioning = True
                
                # Cancel all active futures
                self._cancel_all_futures()
                
                # Save any ongoing session data
                if (self.current_submode == StandardSubMode.FOCUS and 
                    self.current_focus_type and self.mode_start_time):
                    session_duration = datetime.now() - self.mode_start_time
                    self._save_session_data(session_duration)
                    logging.info("Saved ongoing focus session data")
                
                # Shutdown executor
                self.executor.shutdown(wait=False)
                
                # Wait for tracking thread to finish
                if self.tracking_thread and self.tracking_thread.is_alive():
                    self.tracking_thread.join(timeout=2)
                    if self.tracking_thread.is_alive():
                        logging.warning("Tracking thread did not terminate gracefully")
                
                logging.info("Graceful shutdown completed")
                
        except Exception as e:
            logging.error(f"Error during graceful shutdown: {e}")

    def _cancel_all_futures(self):
        """Cancel all active futures and clear the set."""
        cancelled_count = 0
        for future in list(self._active_futures):
            if not future.done():
                future.cancel()
                cancelled_count += 1
        self._active_futures.clear()
        if cancelled_count > 0:
            logging.info(f"Cancelled {cancelled_count} active futures")

    def _track_future(self, future):
        """Add future to tracking set and set up cleanup callback."""
        self._active_futures.add(future)
        future.add_done_callback(lambda f: self._active_futures.discard(f))
        return future

    def enforce_current_mode(self, window_info: WindowInfo):
        """Enforce the rules and restrictions of the current mode on the active window."""
        with self.mode_lock:
            if not window_info or self._transitioning or self._shutdown_event.is_set():
                return
                
            if self.active_block:
                self._handle_blocked_app(window_info)
            
            # Get current mode settings and apply them
            settings = self._get_current_mode_settings()
            if settings:
                self._apply_window_restrictions(window_info, settings)

    def _get_current_mode_settings(self) -> Optional[ModeSettings]:
        """Get settings for the current mode/submode combination."""
        if self.current_mode == ModeType.KIDS:
            return self.settings_manager.get_mode_setting("kids")
        elif self.current_mode == ModeType.STANDARD:
            if self.current_submode == StandardSubMode.NORMAL:
                return self.settings_manager.get_mode_setting("standard_normal")
            elif self.current_submode == StandardSubMode.FOCUS and self.current_focus_type:
                settings_key = f"standard_focus_{self.current_focus_type.name.lower()}"
                return self.settings_manager.get_mode_setting(settings_key)
        return None

    def _apply_window_restrictions(self, window_info: WindowInfo, settings: ModeSettings):
        """Apply window restrictions based on current settings."""
        if not settings:
            return
            
        # Check if app should be blocked
        app_name = window_info.app.lower()
        should_block = False
        
        if app_name in settings.blocked_apps:
            should_block = True
        # elif hasattr(settings, 'allowed_apps') and settings.allowed_apps and app_name not in settings.allowed_apps and app_name not in settings.minimized_apps and  :
        #     should_block = True
        else:
            should_block = False
            
        if should_block:
            if window_info.window_type == "browser":
                self.browser_controller.close_tab_smart(window_info)
            else:
                self.window_controller.close_window(window_info)
                
        elif app_name in getattr(settings, 'minimized_apps', []):
            self.window_controller.minimize_window(window_info)
            
        # Check time limits for focus sessions
        if self.current_submode == StandardSubMode.FOCUS and settings.duration and self.mode_start_time:
            elapsed = datetime.now() - self.mode_start_time
            if elapsed >= settings.duration:
                self._schedule_focus_end()

    def _handle_blocked_app(self, window_info: WindowInfo, action_block: bool = True):
        """Handle blocked apps based on current mode settings"""
        if not action_block or window_info.status != "Blocked":
            return
            
        if window_info.window_type == "browser":
            self.browser_controller.close_tab_smart(window_info)
        else:
            self.window_controller.close_window(window_info)

    # === FLEXIBLE MODE SWITCHING METHODS ===
    
    def switch_to_mode(self, mode: ModeType, submode: Optional[StandardSubMode] = None, 
                      focus_type: Optional[FocusType] = None, custom_settings: Optional[Dict] = None) -> bool:
        """
        Universal method to switch to any mode/submode/focus combination.
        Returns True if switch was successful, False otherwise.
        """
        with self.mode_lock:
            if self._transitioning or self._shutdown_event.is_set():
                logging.warning("Mode switch not available during transition/shutdown")
                return False
                
            # Validate the requested combination
            if not self._validate_mode_combination(mode, submode, focus_type):
                return False
                
            # Check if we're already in the requested state
            if (self.current_mode == mode and 
                self.current_submode == submode and 
                self.current_focus_type == focus_type):
                logging.info("Already in requested mode state")
                return True
                
            return self._perform_mode_switch(mode, submode, focus_type, custom_settings)

    def _validate_mode_combination(self, mode: ModeType, submode: Optional[StandardSubMode], 
                                 focus_type: Optional[FocusType]) -> bool:
        """Validate that the requested mode combination is valid."""
        if mode == ModeType.KIDS:
            if submode is not None or focus_type is not None:
                logging.error("Kids mode doesn't support submodes or focus types")
                return False
        elif mode == ModeType.STANDARD:
            if submode is None:
                submode = StandardSubMode.NORMAL
            if submode == StandardSubMode.FOCUS and focus_type is None:
                logging.error("Focus submode requires a focus type")
                return False
            if submode == StandardSubMode.NORMAL and focus_type is not None:
                logging.error("Normal submode doesn't support focus types")
                return False
        else:
            logging.error(f"Unknown mode type: {mode}")
            return False
        return True

    def _perform_mode_switch(self, mode: ModeType, submode: Optional[StandardSubMode], 
                           focus_type: Optional[FocusType], custom_settings: Optional[Dict]) -> bool:
        """Perform the actual mode switch with proper cleanup and setup."""
        self._transitioning = True
        
        try:
            logging.info(f"Switching to mode: {mode.name}, submode: {submode.name if submode else None}, "
                        f"focus: {focus_type.name if focus_type else None}")
            
            # Step 1: Clean up current state
            self._cleanup_current_mode()
            
            # Step 2: Update state
            old_state = (self.current_mode, self.current_submode, self.current_focus_type)
            self.current_mode = mode
            self.current_submode = submode or (StandardSubMode.NORMAL if mode == ModeType.STANDARD else None)
            self.current_focus_type = focus_type
            
            # Step 3: Apply custom settings if provided
            if custom_settings and focus_type:
                self._apply_custom_settings(focus_type, custom_settings)
            
            # Step 4: Initialize new mode
            success = self._initialize_new_mode()
            
            if not success:
                # Rollback on failure
                self.current_mode, self.current_submode, self.current_focus_type = old_state
                logging.error("Failed to initialize new mode, rolling back")
                return False
                
            logging.info(f"Successfully switched to {mode.name}/{submode.name if submode else 'None'}"
                        f"/{focus_type.name if focus_type else 'None'}")
            return True
            
        except Exception as e:
            logging.error(f"Error during mode switch: {e}")
            return False
        finally:
            self._transitioning = False

    def _cleanup_current_mode(self):
        """Clean up current mode without causing recursion."""
        try:
            # Cancel any running timers or background tasks
            if hasattr(self, '_focus_timer_future'):
                if not self._focus_timer_future.done():
                    self._focus_timer_future.cancel()
                self._active_futures.discard(self._focus_timer_future)
                    
            # Save session data if we're ending a focus session
            if (self.current_submode == StandardSubMode.FOCUS and 
                self.current_focus_type and self.mode_start_time):
                session_duration = datetime.now() - self.mode_start_time
                self._save_session_data(session_duration)
                
            # Reset timing
            self.mode_start_time = None
            self.is_active = False
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def _initialize_new_mode(self) -> bool:
        """Initialize the new mode settings and restrictions."""
        try:
            # Apply mode-specific settings
            success = self._apply_mode_settings(self.current_mode, self.current_submode, self.current_focus_type)
            if not success:
                return False
                
            # Start timing for focus sessions
            if self.current_submode == StandardSubMode.FOCUS:
                self.mode_start_time = datetime.now()
                self.is_active = True
                self._start_focus_timer()
                
            return True
            
        except Exception as e:
            logging.error(f"Error initializing new mode: {e}")
            return False

    def _apply_mode_settings(self, mode: ModeType, submode: Optional[StandardSubMode], 
                           focus_type: Optional[FocusType]) -> bool:
        """Apply settings for the specified mode combination."""
        try:
            if mode == ModeType.KIDS:
                return self._apply_kids_mode_settings()
            elif mode == ModeType.STANDARD:
                if submode == StandardSubMode.NORMAL:
                    return self._apply_normal_mode_settings()
                elif submode == StandardSubMode.FOCUS and focus_type:
                    return self._apply_focus_mode_settings(focus_type)
            return False
        except Exception as e:
            logging.error(f"Error applying mode settings: {e}")
            return False

    def _apply_normal_mode_settings(self) -> bool:
        """Apply normal mode settings."""
        settings = self.settings_manager.get_mode_setting("standard_normal")
        # Apply any normal mode specific logic here
        return True

    def _apply_focus_mode_settings(self, focus_type: FocusType) -> bool:
        """Apply focus mode settings."""
        settings_key = f"standard_focus_{focus_type.name.lower()}"
        settings = self.settings_manager.get_mode_setting(settings_key)
        
        if not settings:
            logging.warning(f"No settings found for {settings_key}")
            return True  # Don't fail if settings are missing
            
        # Apply focus-specific settings
        if hasattr(settings, 'enable_sounds') and settings.enable_sounds:
            # Start ambient sounds
            pass
            
        return True

    def _apply_kids_mode_settings(self) -> bool:
        """Apply kids mode settings."""
        settings = self.settings_manager.get_mode_setting("kids")
        print("settings :" , settings.duration)
        
        if settings and hasattr(settings, 'duration'):
            # Convert timedelta to minutes for the device controller
            if isinstance(settings.duration, timedelta):
                time_limit_minutes = settings.duration.total_seconds() / 60
            else:
                # If it's already a number, assume it's in minutes
                time_limit_minutes = float(settings.duration)
            
            print(f"Starting kids mode timer for {time_limit_minutes} minutes")
            
            # Start the checking loop with proper parameters
            future = self.executor.submit(
                self.device_controller._checking_loop,
                time_limit=time_limit_minutes,  # in minutes
                action="sleep",
                is_warning=False,  # Apply action directly without warning
                grace_seconds=10
            )
            self._focus_timer_future = self._track_future(future)
            
            # Also start the device controller timer if it's not already running
            if not self.device_controller.is_timing:
                self.device_controller.start()
        
        return True

    def _start_focus_timer(self):
        """Start timer for focus session if duration is set."""
        if self._shutdown_event.is_set():
            return
            
        settings = self._get_current_mode_settings()
        if settings and settings.duration:
            future = self.executor.submit(
                self._focus_timer_worker, settings.duration
            )
            self._focus_timer_future = self._track_future(future)

    def _focus_timer_worker(self, duration: timedelta):
        """Worker function for focus timer."""
        import time
        total_seconds = duration.total_seconds()
        check_interval = min(1.0, total_seconds / 10)  # Check shutdown every second or 10% of duration
        
        elapsed = 0
        while elapsed < total_seconds:
            if self._shutdown_event.is_set():
                logging.info("Focus timer interrupted by shutdown")
                return
                
            sleep_time = min(check_interval, total_seconds - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time
            
        # Timer completed naturally
        if not self._shutdown_event.is_set() and not self._transitioning:
            self._schedule_focus_end()

    def _schedule_focus_end(self):
        """Schedule focus session to end (thread-safe)."""
        if self._shutdown_event.is_set():
            return
            
        if self.current_submode == StandardSubMode.FOCUS:
            # Switch back to normal mode
            future = self.executor.submit(self._end_focus_session_async)
            self._track_future(future)

    def _end_focus_session_async(self):
        """Asynchronously end focus session."""
        try:
            if self._shutdown_event.is_set():
                return
                
            self.switch_to_mode(ModeType.STANDARD, StandardSubMode.NORMAL)
            
            if not self._shutdown_event.is_set():
                self.notification_controller.send_notification(
                    "Focus session complete!", 
                    f"Your focus session has ended"
                )
        except Exception as e:
            logging.error(f"Error ending focus session: {e}")

    # === CONVENIENCE METHODS ===
    
    def switch_to_standard_normal(self) -> bool:
        """Switch to standard/normal mode."""
        return self.switch_to_mode(ModeType.STANDARD, StandardSubMode.NORMAL)
    
    def switch_to_focus(self, focus_type: FocusType, custom_settings: Optional[Dict] = None) -> bool:
        """Switch to focus mode with specified type."""
        return self.switch_to_mode(ModeType.STANDARD, StandardSubMode.FOCUS, focus_type, custom_settings)
    
    def switch_to_kids_mode(self) -> bool:
        """Switch to kids mode."""
        return self.switch_to_mode(ModeType.KIDS)
    
    def change_focus_type(self, new_focus_type: FocusType) -> bool:
        """Change focus type while staying in focus mode."""
        if self.current_submode != StandardSubMode.FOCUS:
            logging.error("Can only change focus type when in focus mode")
            return False
        return self.switch_to_mode(ModeType.STANDARD, StandardSubMode.FOCUS, new_focus_type)

    # === LEGACY COMPATIBILITY METHODS ===
    
    def switch_mode(self, new_mode: ModeType = ModeType.STANDARD):
        """Legacy method for basic mode switching."""
        if new_mode == ModeType.KIDS:
            return self.switch_to_kids_mode()
        else:
            return self.switch_to_standard_normal()

    def switch_submode(self, new_submode: StandardSubMode, focus_type: FocusType = FocusType.DEEP):
        """Legacy method for submode switching."""
        if new_submode == StandardSubMode.FOCUS:
            return self.switch_to_focus(focus_type)
        else:
            return self.switch_to_standard_normal()

    def start_focus_session(self, focus_type: FocusType, custom_settings: Optional[Dict] = None):
        """Legacy method for starting focus sessions."""
        return self.switch_to_focus(focus_type, custom_settings)

    def end_focus_session(self):
        """Legacy method for ending focus sessions."""
        if self.current_submode == StandardSubMode.FOCUS:
            return self.switch_to_standard_normal()
        return True

    # === UTILITY METHODS ===
    
    def get_current_state(self) -> Tuple[ModeType, Optional[StandardSubMode], Optional[FocusType]]:
        """Get current mode state as tuple."""
        return (self.current_mode, self.current_submode, self.current_focus_type)
    
    def is_in_focus_mode(self) -> bool:
        """Check if currently in any focus mode."""
        return (self.current_mode == ModeType.STANDARD and 
                self.current_submode == StandardSubMode.FOCUS and 
                self.current_focus_type is not None)
    
    def get_session_duration(self) -> Optional[timedelta]:
        """Get current session duration if active."""
        if self.mode_start_time:
            return datetime.now() - self.mode_start_time
        return None

    # === DATA PERSISTENCE ===
    ## Not MVP
    def _calculate_productivity_score(self, session_duration: timedelta) -> None:
        """
        Compute a 0-100 productivity score based on
        1. Raw focus duration
        2. Whether the user reached / exceeded the target
        3. How many times the user tried to open a blocked app (penalty)
        4. Current streak multiplier
        """
        import math

        # ------------------------------------------------------------------
        # 1. Base configuration
        # ------------------------------------------------------------------
        settings = self._get_current_mode_settings()
        target = getattr(settings, "duration", timedelta(hours=1))
        block_attempts = getattr(settings, "block_attempts", 0)  # increment this elsewhere

        # ------------------------------------------------------------------
        # 2. Duration component (0-60 pts, super-linear)
        # ------------------------------------------------------------------
        actual_min = max(session_duration.total_seconds() / 60, 0)
        target_min = max(target.total_seconds() / 60, 1)

        # S-curve that rewards longer sessions disproportionally
        ratio = actual_min / target_min
        duration_score = 60 * math.tanh(ratio ** 1.8)  # tanh keeps it <= 60

        # ------------------------------------------------------------------
        # 3. Target-bonus component (0-25 pts)
        # ------------------------------------------------------------------
        bonus = 0
        if actual_min >= target_min:
            # Up to 15 extra points for hitting the target
            bonus += 15
            # Additional 10 points if they exceeded by ≥20 %
            if ratio >= 1.2:
                bonus += 10
        target_bonus = min(bonus, 25)

        # ------------------------------------------------------------------
        # 4. Penalty for blocked-app attempts (0-10 pts lost)
        # ------------------------------------------------------------------
        penalty = min(block_attempts * 2, 10)

        # ------------------------------------------------------------------
        # 5. Streak multiplier (1.0 – 1.5×, capped at 100)
        # ------------------------------------------------------------------
        streak = max(self.focus_streak, 1)
        multiplier = 1 + 0.05 * math.log2(streak)  # log2 keeps growth sane
        multiplier = min(multiplier, 1.5)

        # ------------------------------------------------------------------
        # 6. Final score
        # ------------------------------------------------------------------
        raw = (duration_score + target_bonus - penalty) * multiplier
        self.productivity_score = max(int(round(raw)), 0)

    def _save_session_data(self, duration: timedelta):
        """Save focus session data to history"""
        if not self.current_focus_type:
            return
            
        session_data = {
            "date": datetime.now().isoformat(),
            "focus_type": self.current_focus_type.name,
            "duration": str(duration),
            "productivity_score": self.productivity_score,
            "streak": self.focus_streak
        }
        
        try:
            history_path = Path("config/focus_sessions.json")
            history_path.parent.mkdir(exist_ok=True)
            
            history = []
            if history_path.exists():
                with open(history_path, "r") as f:
                    history = json.load(f)
            
            history.append(session_data)
            
            with open(history_path, "w") as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving session data: {e}")

    def _apply_custom_settings(self, focus_type: FocusType, custom_settings: Dict):
        """Apply user-customized settings for focus session"""
        settings_key = f"standard_focus_{focus_type.name.lower()}"
        
        # Apply custom settings to the settings manager
        try:
            current_settings = self.settings_manager.get_mode_setting(settings_key)
            if current_settings:
                for key, value in custom_settings.items():
                    if hasattr(current_settings, key):
                        setattr(current_settings, key, value)
            logging.info(f"Applied custom settings for {focus_type.name} focus")
        except Exception as e:
            logging.error(f"Error applying custom settings: {e}")

    def cleanup(self):
        """Clean up resources - can be called manually or automatically."""
        if not self._shutdown_event.is_set():
            self._graceful_shutdown()

    def __del__(self):
        """Destructor to ensure cleanup happens."""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during destruction