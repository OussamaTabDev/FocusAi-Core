# tracker.py
import os
import pygetwindow as gw
import time
import threading
import logging
import win32gui
import win32process
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional

# Import our new modules
from models import WindowInfo
from productivity_tracker import ProductivityTracker
import utils
from category_classifier import CategoryClassifier
from parser import WindowTitleParser

from analytics import SessionAnalytics
from layers.window_history import WindowHistory
from layers.Image_capturer import ImageCapturer
# from layers.browser_controller import BrowserController
from ModeController.mode_controller import ModeController
from Providers.InitAIProvider import AIProviderManager , ProviderType
# from Providers.provider_singleton import get_provider, save_provider , load_provider



logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WindowTracker:
    def __init__(self, interval: int = 1, session_gap_seconds: int = 30):
        self.interval = interval
        self.is_tracking = False
        
        # New intelligent history manager
        self.mode_controller = ModeController()
        self.history = WindowHistory(self , session_gap_seconds=session_gap_seconds , Mode_Controller=self.mode_controller)
        self.analytics = SessionAnalytics(self.history)
        # New image capturer
        self.capturer = ImageCapturer(interval=self.interval)
        # New mode controller
        # self.mode_controller = ModeController(self)
        # Threading handler
        self.lock = threading.Lock()
        # Providers
        self.provider = AIProviderManager()
        # self.provider_mgr =           # always returns the same instance
        # if self.provider_mgr.get_default_provider() is None:
        #     # first run – ask user or read from env
        #     save_provider(ProviderType.GEMINI, os.getenv("GEMINI_API_KEY"))
        #     self.provider_mgr = get_provider()
        if self.provider.load_provider():
            self.ai_provider = self.provider.create_ai_provider(self.provider.load_provider()[0],self.provider.load_provider()[1])
        else:
            self.ai_provider = None
        # Composition: The tracker USES these helpers, but doesn't implement them.
        self.cat_classifier = CategoryClassifier()
        self.title_parser = WindowTitleParser(self.cat_classifier)
        self.Pr_classier = ProductivityTracker(
            ai_provider=self.ai_provider
        )
        self.tracking_thread: Optional[threading.Thread] = None

    def _get_real_window_handle(self, pygetwindow_obj) -> Optional[int]:
        """Get the real Windows handle (HWND) from pygetwindow object"""
        try:
            # Method 1: Try to get the handle directly if available
            if hasattr(pygetwindow_obj, '_hWnd') and pygetwindow_obj._hWnd:
                return pygetwindow_obj._hWnd
            
            # Method 2: Find window by title and process
            title = pygetwindow_obj.title
            if not title.strip():
                return None
                
            def enum_windows_proc(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    try:
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title == title:
                            windows.append(hwnd)
                    except:
                        pass
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_proc, windows)
            
            # If we found matching windows, return the first visible one
            for hwnd in windows:
                try:
                    if win32gui.IsWindowVisible(hwnd) and not win32gui.GetParent(hwnd):
                        return hwnd
                except:
                    continue
            
            # Method 3: Fallback - enumerate all windows and match by position/size
            try:
                target_rect = (pygetwindow_obj.left, pygetwindow_obj.top, 
                              pygetwindow_obj.width, pygetwindow_obj.height)
                
                def enum_windows_proc2(hwnd, windows):
                    try:
                        if win32gui.IsWindowVisible(hwnd):
                            rect = win32gui.GetWindowRect(hwnd)
                            window_rect = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                            window_title = win32gui.GetWindowText(hwnd)
                            
                            # Match by title or position
                            if (window_title == title or 
                                (abs(window_rect[0] - target_rect[0]) < 5 and 
                                 abs(window_rect[1] - target_rect[1]) < 5)):
                                windows.append(hwnd)
                    except:
                        pass
                    return True
                
                windows2 = []
                win32gui.EnumWindows(enum_windows_proc2, windows2)
                
                if windows2:
                    return windows2[0]
                    
            except:
                pass
                
            return None
            
        except Exception as e:
            logging.error(f"Error getting real window handle: {e}")
            return None

    def _get_active_window_info(self) -> Optional[WindowInfo]:
        """Captures and enriches data for the currently active window."""
        try:
            active_window = gw.getActiveWindow()
            if not active_window or not active_window.title.strip():
                return None

            timestamp = datetime.now().isoformat()
            ext_info = utils.get_extended_window_info(active_window)
            process_name = utils.get_process_name(active_window)
            process = utils.get_process(active_window)
            class_name = ext_info.get('class_name')
            
            # Get the real Windows handle
            real_hwnd = self._get_real_window_handle(active_window)
            if not real_hwnd:
                # Fallback to a generated ID if we can't get the real handle
                real_hwnd = hash((active_window.title, process_name, time.time())) & 0x7FFFFFFF
                logging.warning(f"Could not get real HWND for window: {active_window.title}, using fallback ID: {real_hwnd}")
            
            parsed_title_info = self.title_parser.parse(
                active_window.title, process_name, class_name
            )
            
            status = self.Pr_classier.detect_status(parsed_title_info['app'])
            print(f"Status: {status}")
            
            return WindowInfo(
                raw_title=active_window.title,
                window_id=real_hwnd,  # Use real HWND instead of Python object ID
                timestamp=timestamp,
                position=(active_window.left, active_window.top),
                size=(active_window.width, active_window.height),
                is_active=active_window.isActive,
                is_minimized=active_window.isMinimized,
                is_maximized=active_window.isMaximized,
                is_visible=active_window.visible,
                z_order=-1,  # Z-order is expensive, maybe calculate it only when needed
                process_name=process_name,  # name for a file
                process=process,  # .exe
                class_name=class_name,
                is_system_window=ext_info.get('is_tool_window', False) or ext_info.get('is_popup', False),
                is_topmost=ext_info.get('is_topmost', False),
                parent_window_exists=bool(ext_info.get('parent_hwnd')),
                window_type=parsed_title_info['window_type'],
                app=parsed_title_info['app'],
                original_app=parsed_title_info['original_app'],
                domain=parsed_title_info['domain'],
                status=status,
                context=parsed_title_info['context'],
                display_title=parsed_title_info['display_title'],
                extra_info=ext_info
            )

        except Exception as e:
            logging.error(f"Error detecting active window: {e}")
            return None

    def _track_loop(self):
        """The internal loop that runs on a separate thread."""
        logging.info("Window tracking started.")
        
        while self.is_tracking:
            window_info = self._get_active_window_info()

            if window_info:
                # Add to intelligent history manager
                self.history.add_window_info(window_info)
                # Optional: Log current app for debugging
                logging.info(f"Active: {window_info.app} - {window_info.context} (HWND: {window_info.window_id})")
            
            time.sleep(self.interval)
        
        logging.info("Window tracking stopped.")

    def start(self):
        """Starts the window tracking in a background thread."""
        if self.is_tracking:
            logging.warning("Tracking is already running.")
            return
            
        self.is_tracking = True
        self.capturer.start()  # Start image capturing
        
        self.tracking_thread = threading.Thread(target=self._track_loop, daemon=True)
        self.tracking_thread.start()

    def stop(self):
        """Stops the window tracking."""
        self.is_tracking = False
        self.capturer.stop()  # Stop image capturing
        
        if self.tracking_thread:
            logging.info("Stop signal sent to tracking thread.")

    def get_expanded_history(self) -> List[WindowInfo]:
        """Safely returns a copy of the focus history."""
        with self.lock:
            return list(self.expanded_history) if hasattr(self, 'expanded_history') else []
        
    def get_focus_history(self) -> List[WindowInfo]:
        """Safely returns a copy of the focus history."""
        with self.lock:
            return list(self.focus_history) if hasattr(self, 'focus_history') else []
    
    def get_current_window(self) -> Optional[WindowInfo]:
        """Get the currently active window info"""
        return self._get_active_window_info()
    
    def quick_restart(self) -> None:
        """
        Performs a quick restart of the WindowTracker to reload all components,
        configurations, and files without creating a new instance.
        """
        logging.info("Starting quick restart...")
        
        # 1. Stop current tracking
        was_tracking = self.is_tracking
        if self.is_tracking:
            self.stop()
            # Wait for tracking thread to finish
            if self.tracking_thread and self.tracking_thread.is_alive():
                self.tracking_thread.join(timeout=5.0)
                if self.tracking_thread.is_alive():
                    logging.warning("Tracking thread did not stop gracefully")
        
        try:
            # 2. Stop and cleanup image capturer
            if hasattr(self, 'capturer') and self.capturer:
                self.capturer.stop()
            
            # 3. Save current session data (if needed)
            if hasattr(self, 'history') and self.history:
                try:
                    # Assuming history has a save method or similar
                    if hasattr(self.history, 'save_session'):
                        self.history.save_session()
                except Exception as e:
                    logging.warning(f"Could not save history during restart: {e}")
            
            # 4. Reinitialize AI Provider (reload from config/env)
            try:
                if self.provider.load_provider():
                    self.ai_provider = self.provider.create_ai_provider(self.provider.load_provider()[0], self.provider.load_provider()[1])
                    logging.info("AI Provider reloaded successfully")
                else:
                    self.ai_provider = None
                    logging.info("No AI Provider configuration found")
            except Exception as e:
                logging.error(f"Error reloading AI Provider: {e}")
                self.ai_provider = None
            
            # 5. Reinitialize all components with fresh instances
            
            # Reinitialize mode controller
            self.mode_controller = ModeController()
            
            # Reinitialize history with new mode controller
            session_gap = getattr(self.history, 'session_gap_seconds', 30) if hasattr(self, 'history') else 30
            self.history = WindowHistory(self, session_gap_seconds=session_gap, Mode_Controller=self.mode_controller)
            
            # Reinitialize analytics
            self.analytics = SessionAnalytics(self.history)
            
            # Reinitialize image capturer
            self.capturer = ImageCapturer(interval=self.interval)
            
            # Reinitialize classifiers and parsers (to reload any config files)
            self.cat_classifier = CategoryClassifier()
            self.title_parser = WindowTitleParser(self.cat_classifier)
            
            # Reinitialize productivity tracker with new AI provider
            self.Pr_classier = ProductivityTracker(ai_provider=self.ai_provider)
            
            # 6. Reset thread-related attributes
            self.tracking_thread = None
            self.is_tracking = False
            
            # 7. Force garbage collection to clean up old instances
            import gc
            gc.collect()
            
            logging.info("Quick restart completed successfully")
            
            # 8. Restart tracking if it was running before
            if was_tracking:
                logging.info("Restarting tracking...")
                self.start()
                
        except Exception as e:
            logging.error(f"Error during quick restart: {e}")
            # Ensure we're in a clean state even if restart failed
            self.is_tracking = False
            self.tracking_thread = None
            raise RuntimeError(f"Quick restart failed: {e}")

    def reload_config_files(self) -> None:
        """
        Helper method to reload configuration files without full restart.
        Can be called independently or as part of quick_restart.
        """
        try:
            logging.info("Reloading configuration files...")
            
            # Reload AI provider settings
            if self.provider.load_provider():
                old_provider = self.ai_provider
                self.ai_provider = self.provider.create_ai_provider(self.provider.load_provider()[0], self.provider.load_provider()[1])
                logging.info("AI Provider configuration reloaded")
            
            # Reload category classifier (if it has config files)
            if hasattr(self.cat_classifier, 'reload_config'):
                self.cat_classifier.reload_config()
            else:
                # Reinitialize if no reload method exists
                self.cat_classifier = CategoryClassifier()
            
            # Reload title parser
            self.title_parser = WindowTitleParser(self.cat_classifier)
            
            # Reload productivity tracker with new AI provider
            self.Pr_classier = ProductivityTracker(ai_provider=self.ai_provider)
            
            # Reload mode controller settings
            if hasattr(self.mode_controller, 'reload_config'):
                self.mode_controller.reload_config()
            else:
                self.mode_controller = ModeController()
                # Update history's mode controller reference
                if hasattr(self.history, 'Mode_Controller'):
                    self.history.Mode_Controller = self.mode_controller
            
            logging.info("Configuration files reloaded successfully")
            
        except Exception as e:
            logging.error(f"Error reloading configuration files: {e}")
            raise

    def get_restart_status(self) -> Dict[str, any]:
        """
        Returns the current status of all components for debugging restart issues.
        """
        return {
            'is_tracking': self.is_tracking,
            'tracking_thread_alive': self.tracking_thread.is_alive() if self.tracking_thread else False,
            'capturer_active': getattr(self.capturer, 'is_active', False) if hasattr(self, 'capturer') else False,
            'ai_provider_loaded': self.ai_provider is not None,
            'components_initialized': {
                'mode_controller': hasattr(self, 'mode_controller') and self.mode_controller is not None,
                'history': hasattr(self, 'history') and self.history is not None,
                'analytics': hasattr(self, 'analytics') and self.analytics is not None,
                'cat_classifier': hasattr(self, 'cat_classifier') and self.cat_classifier is not None,
                'title_parser': hasattr(self, 'title_parser') and self.title_parser is not None,
                'productivity_classifier': hasattr(self, 'Pr_classier') and self.Pr_classier is not None,
            },
            'provider_info': self.provider.load_provider() if self.provider.load_provider() else None
        }