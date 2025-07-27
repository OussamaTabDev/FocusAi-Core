# utils.py
import platform
import logging
import psutil
from typing import Dict

# Import the loaded map from the single config source
from config_manager import PROCESS_NAME_MAP

try:
    import win32process
    import win32gui
    import win32con
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False




def get_process_name(window_obj) -> str | None:
    """Gets the user-friendly process name for a given window object."""
    if not IS_WINDOWS or not hasattr(window_obj, '_hWnd'):
        return None
    try:
        _, pid = win32process.GetWindowThreadProcessId(window_obj._hWnd)
        process = psutil.Process(pid)
        # The line below is the only change in this function!
        # print(process.name())
        # It now uses the map we loaded from JSON.
        return PROCESS_NAME_MAP.get(process.name(), process.name())
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
        logging.warning(f"Could not get process name for window '{window_obj.title}': {e}")
        return None
    
def get_process(window_obj) -> str | None:
    """Gets the user-friendly process name for a given window object."""
    if not IS_WINDOWS or not hasattr(window_obj, '_hWnd'):
        return None
    try:
        _, pid = win32process.GetWindowThreadProcessId(window_obj._hWnd)
        process = psutil.Process(pid)
        # The line below is the only change in this function!
        # print(process.name())
        # It now uses the map we loaded from JSON.
        return process.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
        logging.warning(f"Could not get process for window '{window_obj.title}': {e}")
        return None

def get_extended_window_info(window_obj) -> Dict:
    """Gets extended, Windows-specific information (styles, parent, etc.)."""
    if not IS_WINDOWS or not hasattr(window_obj, '_hWnd'):
        return {}
        
    info = {}
    try:
        hwnd = window_obj._hWnd
        info['class_name'] = win32gui.GetClassName(hwnd)
        info['parent_hwnd'] = win32gui.GetParent(hwnd)
        info['window_style'] = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        info['extended_style'] = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # Derived boolean flags for easier use
        info['is_tool_window'] = bool(info['extended_style'] & win32con.WS_EX_TOOLWINDOW)
        info['is_popup'] = bool(info['window_style'] & win32con.WS_POPUP)
        info['is_topmost'] = bool(info['extended_style'] & win32con.WS_EX_TOPMOST)

    except Exception as e:
        logging.warning(f"Could not get extended info for window '{window_obj.title}': {e}")

    return info



