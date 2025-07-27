import json
import time
import subprocess
import logging
from typing import List, Dict, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import urllib.parse
import re
import webbrowser
# Import your existing classes
from models import WindowInfo
from .window_controller import ControlResult, WindowController
import extension_tracker as server
# Import your existing classes
from models import WindowInfo
from .window_controller import ControlResult, WindowController
from config_manager import URLS


# server
import extension_tracker # server.py

class TabAction(Enum):
    """Available tab actions"""
    CLOSE = "close"
    FOCUS = "focus"
    RELOAD = "reload"
    DUPLICATE = "duplicate"
    PIN = "pin"
    UNPIN = "unpin"
    MUTE = "mute"
    UNMUTE = "unmute"
    BLOCK_DOMAIN = "block_domain"

@dataclass
class TabInfo:
    """Information about a browser tab"""
    url: str
    title: str
    domain: str
    timestamp: str
    server_timestamp: str
    tab_id: Optional[int] = None
    window_id: Optional[int] = None
    is_active: bool = False
    is_pinned: bool = False
    is_muted: bool = False
    favicon_url: Optional[str] = None
    
    # Productivity classification
    app: str = ""  # Processed domain (youtube, facebook, etc.)
    status: str = "Neutral"  # Productive, Distracting, Neutral
    context: str = ""
    
    @property
    def processed_app(self) -> str:
        """Get processed app name from domain"""
        if not self.domain:
            return "browser"
        
        parts = [part.strip() for part in self.domain.split(".") if part.strip()]
        
        if len(parts) == 1:
            return "browser"
        elif len(parts) == 2:
            return parts[-2]
        else:
            if parts[-2] == "google":
                return parts[-2] + " " + parts[-3]
            else:
                return parts[-2]

@dataclass
class BrowserSession:
    """Information about a browser session"""
    window_info: WindowInfo
    tabs: List[TabInfo] = field(default_factory=list)
    active_tab: Optional[TabInfo] = None
    tab_count: int = 0
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
import time
import subprocess
from typing import Optional, List
from dataclasses import dataclass

# For keyboard automation
try:
    import pyautogui
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False



class BrowserController:
    """Simplified browser controller with keyboard and API methods"""
    
    def __init__(self):
        self.window_controller = WindowController()
        self._tab_history: List[TabInfo] = []
    
    # ==================== KEYBOARD METHOD (FASTEST) ====================
    
    def close_tab_keyboard(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Close tab using Ctrl+W - FASTEST METHOD"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(
                success=False,
                message="Install pyautogui: pip install pyautogui"
            )
        
        try:
            # Focus browser window first
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            # Send Ctrl+W
            pyautogui.hotkey('ctrl', 'w')
            
            return ControlResult(
                success=True,
                message="Tab closed with Ctrl+W"
            )
            
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Keyboard close failed: {str(e)}"
            )
    
    def close_multiple_tabs_keyboard(self, count: int, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Close multiple tabs quickly with Ctrl+W"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            # Close tabs rapidly
            for i in range(count):
                pyautogui.hotkey('ctrl', 'w')
                time.sleep(0.05)  # Small delay
            
            return ControlResult(
                success=True,
                message=f"Closed {count} tabs with keyboard"
            )
            
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed: {str(e)}"
            )
    
    # ==================== API METHOD (YOUR EXISTING) ====================
    
    def close_tabs_by_domain_api(self, domain: str) -> ControlResult:
        """Close tabs using your server API"""
        try:
            server.close_tabs_by_domain(domain)
            return ControlResult(
                success=True,
                message=f"API called to close tabs for '{domain}'"
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"API call failed: {str(e)}"
            )
    
    def close_tab_smart(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Try keyboard first, fallback to API"""
        
        # Try keyboard method first (faster)
        if KEYBOARD_AVAILABLE:
            result = self.close_tab_keyboard(window_info)
            if result.success:
                print("Tab closed with keyboard")
                return result
        
        # Fallback to API if keyboard fails and domain provided
        if window_info.domain:
            return self.close_tabs_by_domain_api(window_info.domain)
        
        return ControlResult(
            success=False,
            message="Both methods failed"
        )
    # ==================== TAB NAVIGATION ====================
    
    def focus_next_tab(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Switch to next tab using Ctrl+Tab"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 'tab')
            
            return ControlResult(success=True, message="Switched to next tab")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def focus_previous_tab(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Switch to previous tab using Ctrl+Shift+Tab"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            
            return ControlResult(success=True, message="Switched to previous tab")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def focus_tab_by_number(self, tab_number: int, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Focus specific tab by number (1-8) using Ctrl+1-8"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        if tab_number < 1 or tab_number > 8:
            return ControlResult(success=False, message="Tab number must be 1-8")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', str(tab_number))
            
            return ControlResult(success=True, message=f"Focused tab {tab_number}")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def focus_last_tab(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Focus last tab using Ctrl+9"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', '9')
            
            return ControlResult(success=True, message="Focused last tab")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    # ==================== TAB MANAGEMENT ====================
    
    def open_new_tab(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Open new tab using Ctrl+T"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 't')
            
            return ControlResult(success=True, message="New tab opened")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def reopen_closed_tab(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Reopen recently closed tab using Ctrl+Shift+T"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 'shift', 't')
            
            return ControlResult(success=True, message="Reopened closed tab")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def duplicate_tab(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Duplicate current tab using Ctrl+L, Ctrl+C, Ctrl+T, Ctrl+V, Enter"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            # Select address bar and copy URL
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            
            # Open new tab
            pyautogui.hotkey('ctrl', 't')
            time.sleep(0.2)
            
            # Paste URL and navigate
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
            pyautogui.press('enter')
            
            return ControlResult(success=True, message="Tab duplicated")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    # ==================== PAGE OPERATIONS ====================
    
    def refresh_page(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Refresh current page using F5"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.press('f5')
            
            return ControlResult(success=True, message="Page refreshed")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def hard_refresh_page(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Hard refresh (ignore cache) using Ctrl+F5"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 'f5')
            
            return ControlResult(success=True, message="Page hard refreshed")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def navigate_back(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Navigate back using Alt+Left"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('alt', 'left')
            
            return ControlResult(success=True, message="Navigated back")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def navigate_forward(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Navigate forward using Alt+Right"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('alt', 'right')
            
            return ControlResult(success=True, message="Navigated forward")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    # ==================== WINDOW OPERATIONS ====================
    
    def open_new_window(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Open new browser window using Ctrl+N"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 'n')
            
            return ControlResult(success=True, message="New window opened")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def open_incognito_window(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Open incognito window using Ctrl+Shift+N"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('ctrl', 'shift', 'n')
            
            return ControlResult(success=True, message="Incognito window opened")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def close_window(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Close browser window using Alt+F4"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            pyautogui.hotkey('alt', 'f4')
            
            return ControlResult(success=True, message="Window closed")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    # ==================== PRODUCTIVITY BLOCKING ====================
    
    def block_site_keyboard(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Block site by navigating away and closing tabs"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            # Navigate to about:blank to "block" current page
            pyautogui.hotkey('ctrl', 'l')  # Focus address bar
            time.sleep(0.1)
            pyautogui.typewrite('about:blank')
            pyautogui.press('enter')
            
            return ControlResult(success=True, message=f"Navigated away from {window_info.domain}")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    def focus_productive_tab(self, productive_sites: List[str], window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Focus on productive tabs by cycling through tabs"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            # Open new tab with productive site
            pyautogui.hotkey('ctrl', 't')
            time.sleep(0.2)
            
            if productive_sites:
                pyautogui.typewrite(productive_sites[0])
                pyautogui.press('enter')
            
            return ControlResult(success=True, message="Focused on productive content")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    # ==================== BATCH OPERATIONS ====================
    
    def close_all_tabs_except_current(self, window_info: Optional[WindowInfo] = None) -> ControlResult:
        """Close all tabs except current using multiple Ctrl+W"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            # Try closing tabs until only one remains
            for i in range(20):  # Max 20 tabs
                pyautogui.hotkey('ctrl', 'shift', 'tab')  # Go to previous tab
                time.sleep(0.05)
                pyautogui.hotkey('ctrl', 'w')  # Close it
                time.sleep(0.05)
            
            return ControlResult(success=True, message="Closed all tabs except current")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    
    
    def cycle_through_all_tabs(self, window_info: Optional[WindowInfo] = None, count: int = 10) -> ControlResult:
        """Cycle through tabs to see what's open"""
        if not KEYBOARD_AVAILABLE:
            return ControlResult(success=False, message="pyautogui not available")
        
        try:
            if window_info:
                self.window_controller.focus_window(window_info)
                time.sleep(0.1)
            
            for i in range(count):
                pyautogui.hotkey('ctrl', 'tab')
                time.sleep(0.3)  # Pause to see each tab
            
            return ControlResult(success=True, message=f"Cycled through {count} tabs")
        except Exception as e:
            return ControlResult(success=False, message=f"Failed: {str(e)}")
    