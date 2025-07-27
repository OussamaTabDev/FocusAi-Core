import psutil
import pygetwindow as gw
import subprocess
import time
import win32gui
import win32con
import win32process
import win32api
import os
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# Import your existing WindowInfo class
from models import WindowInfo

class WindowState(Enum):
    """Enum for different window states"""
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    HIDDEN = "hidden"
    FULLSCREEN = "fullscreen"

class Priority(Enum):
    """Process priority levels"""
    LOW = psutil.BELOW_NORMAL_PRIORITY_CLASS
    NORMAL = psutil.NORMAL_PRIORITY_CLASS
    HIGH = psutil.HIGH_PRIORITY_CLASS
    REALTIME = psutil.REALTIME_PRIORITY_CLASS

@dataclass
class ControlResult:
    """Result of a control operation"""
    success: bool
    message: str
    window_id: Optional[int] = None
    process_id: Optional[int] = None
    details: Dict = field(default_factory=dict)

class WindowController:
    """
    Advanced window and process controller with comprehensive management capabilities
    """
    
    def __init__(self, productivity_tracker=None):
        """
        Initialize the WindowController
        
        Args:
            productivity_tracker: Optional productivity tracker instance
        """
        self.productivity_tracker = productivity_tracker
        self._blocked_apps = set()
        self._monitoring = False
        
    # ==================== HELPER METHODS ====================
    
    def _get_real_window_handle(self, window_info: WindowInfo) -> Optional[int]:
        """Get the real Windows handle (HWND) for a window"""
        try:
            # First, try to find the window by title and process
            def enum_windows_proc(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        windows.append((hwnd, pid, title))
                    except:
                        pass
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_proc, windows)
            
            # Find matching window by title and process name
            for hwnd, pid, title in windows:
                if title == window_info.raw_title:
                    try:
                        process = psutil.Process(pid)
                        if process.name() == window_info.process:
                            return hwnd
                    except:
                        continue
            
            # Fallback: try pygetwindow
            try:
                windows = gw.getWindowsWithTitle(window_info.raw_title)
                for window in windows:
                    if hasattr(window, '_hWnd'):
                        return window._hWnd
            except:
                pass
                
            return None
            
        except Exception as e:
            print(f"Error getting window handle: {e}")
            return None
    
    def _extract_process_name(self, process_path: str) -> str:
        """Extract just the executable name from a full path"""
        if not process_path:
            return ""
        
        # Handle both forward and backward slashes
        process_name = os.path.basename(process_path)
        
        # Remove .exe extension if present
        if process_name.lower().endswith('.exe'):
            process_name = process_name[:-4]
            
        return process_name
    
    # ==================== BASIC WINDOW OPERATIONS ====================
    
    def close_window(self, window_info: WindowInfo, force: bool = False) -> ControlResult:
        """
        Close a window gracefully or forcefully
        
        Args:
            window_info: WindowInfo object
            force: If True, force close the process
        """
        try:
            if force:
                return self._force_close_process(window_info)
            
            # Get the real window handle
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                print(f"Could not find window handle for: {window_info.display_title}")
                # Fallback to killing by process name
                return self.kill_process_by_name(window_info.process)
            
            print(f"Attempting to close window: {window_info.display_title} (HWND: {hwnd})")
            
            # Check if window is still valid
            if not win32gui.IsWindow(hwnd):
                return ControlResult(
                    success=False,
                    message=f"Window handle {hwnd} is no longer valid",
                    window_id=hwnd
                )
            
            # Try graceful close first
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            
            # Wait and verify
            time.sleep(1.0)  # Increased wait time
            
            # Check if window still exists
            if not win32gui.IsWindow(hwnd):
                return ControlResult(
                    success=True,
                    message=f"Window '{window_info.display_title}' closed gracefully",
                    window_id=hwnd
                )
            else:
                # If graceful close failed, try force close
                print("Graceful close failed, attempting force close...")
                return self._force_close_process(window_info)
                
        except Exception as e:
            print(f"Exception in close_window: {e}")
            # Fallback to killing by process name
            return self.kill_process_by_name(window_info.process)

    def kill_process_by_name(self, process_input: str) -> ControlResult:
        """
        Kill process by name (handles both full paths and process names)
        
        Args:
            process_input: Either a process name or full path to executable
        """
        # Extract just the process name
        process_name = self._extract_process_name(process_input)
        if not process_name:
            process_name = process_input
            
        print(f"Attempting to kill process: {process_name}")
        
        killed_processes = []
        found = False
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name']
                    if not proc_name:
                        continue
                        
                    # Compare without .exe extension
                    proc_base = proc_name.lower()
                    if proc_base.endswith('.exe'):
                        proc_base = proc_base[:-4]
                    
                    target_base = process_name.lower()
                    if target_base.endswith('.exe'):
                        target_base = target_base[:-4]
                    
                    if proc_base == target_base:
                        found = True
                        try:
                            proc.terminate()
                            proc.wait(timeout=3)
                            killed_processes.append(f"{proc_name} (PID: {proc.pid})")
                            print(f"[✓] Terminated: {proc_name} (PID: {proc.pid})")
                        except psutil.TimeoutExpired:
                            proc.kill()
                            killed_processes.append(f"{proc_name} (PID: {proc.pid}) - Force killed")
                            print(f"[!] Force killed: {proc_name} (PID: {proc.pid})")
                        except psutil.AccessDenied:
                            print(f"[✗] Access denied for {proc_name} (PID: {proc.pid})")
                        except Exception as e:
                            print(f"[✗] Failed to kill {proc_name} (PID: {proc.pid}): {e}")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Error enumerating processes: {str(e)}"
            )
        
        if found and killed_processes:
            return ControlResult(
                success=True,
                message=f"Killed processes: {', '.join(killed_processes)}",
                details={"killed_processes": killed_processes}
            )
        elif not found:
            return ControlResult(
                success=False,
                message=f"No process found with name: {process_name}"
            )
        else:
            return ControlResult(
                success=False,
                message=f"Found process '{process_name}' but failed to kill it"
            )
        
    def _force_close_process(self, window_info: WindowInfo) -> ControlResult:
        """Force close the process owning the window"""
        try:
            # First try to get process ID from window handle
            hwnd = self._get_real_window_handle(window_info)
            process_id = None
            
            if hwnd and win32gui.IsWindow(hwnd):
                try:
                    _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                except:
                    pass
            
            # If we got a process ID, try to kill it directly
            if process_id:
                try:
                    process = psutil.Process(process_id)
                    process.terminate()
                    process.wait(timeout=3)
                    
                    return ControlResult(
                        success=True,
                        message=f"Process '{window_info.process}' terminated forcefully",
                        window_id=hwnd,
                        process_id=process_id
                    )
                    
                except psutil.TimeoutExpired:
                    # If terminate didn't work, kill it
                    try:
                        process.kill()
                        return ControlResult(
                            success=True,
                            message=f"Process '{window_info.process}' killed forcefully",
                            window_id=hwnd,
                            process_id=process_id
                        )
                    except Exception as e:
                        print(f"Failed to kill process {process_id}: {e}")
                        
                except Exception as e:
                    print(f"Failed to terminate process {process_id}: {e}")
            
            # Fallback to killing by process name
            print("Falling back to kill by process name...")
            return self.kill_process_by_name(window_info.process)
                
        except Exception as e:
            print(f"Error in _force_close_process: {e}")
            # Final fallback
            return self.kill_process_by_name(window_info.process)

    def minimize_window(self, window_info: WindowInfo) -> ControlResult:
        """Minimize a window"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' minimized",
                window_id=hwnd
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to minimize window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def maximize_window(self, window_info: WindowInfo) -> ControlResult:
        """Maximize a window"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' maximized",
                window_id=hwnd
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to maximize window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def restore_window(self, window_info: WindowInfo) -> ControlResult:
        """Restore a window to normal state"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' restored",
                window_id=hwnd
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to restore window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def hide_window(self, window_info: WindowInfo) -> ControlResult:
        """Hide a window"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' hidden",
                window_id=hwnd
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to hide window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def show_window(self, window_info: WindowInfo) -> ControlResult:
        """Show a hidden window"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' shown",
                window_id=hwnd
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to show window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def focus_window(self, window_info: WindowInfo) -> ControlResult:
        """Bring window to front and focus it"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            # First restore if minimized
            if window_info.is_minimized:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Bring to front
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' focused",
                window_id=hwnd
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to focus window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def move_window(self, window_info: WindowInfo, x: int, y: int) -> ControlResult:
        """Move window to specified position"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            width = window_info.size[0]
            height = window_info.size[1]
            
            win32gui.MoveWindow(hwnd, x, y, width, height, True)
            
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' moved to ({x}, {y})",
                window_id=hwnd,
                details={"new_position": (x, y)}
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to move window: {str(e)}",
                window_id=window_info.window_id
            )
    
    def resize_window(self, window_info: WindowInfo, width: int, height: int) -> ControlResult:
        """Resize window to specified dimensions"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if not hwnd:
                return ControlResult(
                    success=False,
                    message=f"Could not find window handle for: {window_info.display_title}"
                )
            
            x, y = window_info.position
            
            win32gui.MoveWindow(hwnd, x, y, width, height, True)
            
            return ControlResult(
                success=True,
                message=f"Window '{window_info.display_title}' resized to {width}x{height}",
                window_id=hwnd,
                details={"new_size": (width, height)}
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to resize window: {str(e)}",
                window_id=window_info.window_id
            )
    
    # ==================== PROCESS CONTROL ====================
    
    def set_process_priority(self, window_info: WindowInfo, priority: Priority) -> ControlResult:
        """Set process priority"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if hwnd:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            else:
                # Fallback: find process by name
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] == window_info.process:
                        process_id = proc.info['pid']
                        break
                else:
                    return ControlResult(
                        success=False,
                        message=f"Could not find process: {window_info.process}"
                    )
            
            process = psutil.Process(process_id)
            process.nice(priority.value)
            
            return ControlResult(
                success=True,
                message=f"Process '{window_info.process}' priority set to {priority.name}",
                window_id=hwnd,
                process_id=process_id
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to set priority: {str(e)}",
                window_id=window_info.window_id
            )
    
    def suspend_process(self, window_info: WindowInfo) -> ControlResult:
        """Suspend/pause a process"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if hwnd:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            else:
                # Fallback: find process by name
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] == window_info.process:
                        process_id = proc.info['pid']
                        break
                else:
                    return ControlResult(
                        success=False,
                        message=f"Could not find process: {window_info.process}"
                    )
            
            process = psutil.Process(process_id)
            process.suspend()
            
            return ControlResult(
                success=True,
                message=f"Process '{window_info.process}' suspended",
                window_id=hwnd,
                process_id=process_id
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to suspend process: {str(e)}",
                window_id=window_info.window_id
            )
    
    def resume_process(self, window_info: WindowInfo) -> ControlResult:
        """Resume a suspended process"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if hwnd:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            else:
                # Fallback: find process by name
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] == window_info.process:
                        process_id = proc.info['pid']
                        break
                else:
                    return ControlResult(
                        success=False,
                        message=f"Could not find process: {window_info.process}"
                    )
            
            process = psutil.Process(process_id)
            process.resume()
            
            return ControlResult(
                success=True,
                message=f"Process '{window_info.process}' resumed",
                window_id=hwnd,
                process_id=process_id
            )
        except Exception as e:
            return ControlResult(
                success=False,
                message=f"Failed to resume process: {str(e)}",
                window_id=window_info.window_id
            )
    
    def get_process_info(self, window_info: WindowInfo) -> Dict:
        """Get detailed process information"""
        try:
            hwnd = self._get_real_window_handle(window_info)
            if hwnd:
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            else:
                # Fallback: find process by name
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] == window_info.process:
                        process_id = proc.info['pid']
                        break
                else:
                    return {"error": f"Could not find process: {window_info.process}"}
            
            process = psutil.Process(process_id)
            
            return {
                "pid": process_id,
                "name": process.name(),
                "exe": process.exe(),
                "cmdline": process.cmdline(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_info": process.memory_info()._asdict(),
                "status": process.status(),
                "create_time": process.create_time(),
                "num_threads": process.num_threads(),
                "connections": len(process.connections()),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== PRODUCTIVITY CONTROL ====================
    
    def block_app(self, app_name: str) -> ControlResult:
        """Add app to blocked list"""
        self._blocked_apps.add(app_name.lower())
        return ControlResult(
            success=True,
            message=f"App '{app_name}' added to blocked list",
            details={"blocked_apps": list(self._blocked_apps)}
        )
    
    def unblock_app(self, app_name: str) -> ControlResult:
        """Remove app from blocked list"""
        self._blocked_apps.discard(app_name.lower())
        return ControlResult(
            success=True,
            message=f"App '{app_name}' removed from blocked list",
            details={"blocked_apps": list(self._blocked_apps)}
        )
    
    def handle_distracting_window(self, window_info: WindowInfo, action: str = "minimize") -> ControlResult:
        """Handle distracting windows based on productivity status"""
        if not self.productivity_tracker:
            return ControlResult(
                success=False,
                message="No productivity tracker configured"
            )
        
        status = self.productivity_tracker.detect_status(window_info.app)
        
        if status == "Distracting":
            if action == "close":
                return self.close_window(window_info)
            elif action == "minimize":
                return self.minimize_window(window_info)
            elif action == "hide":
                return self.hide_window(window_info)
            elif action == "block":
                self.block_app(window_info.app)
                return self.close_window(window_info, force=True)
        
        return ControlResult(
            success=False,
            message=f"Window '{window_info.display_title}' is not distracting ({status})"
        )
    
    def check_blocked_apps(self, windows: List[WindowInfo]) -> List[ControlResult]:
        """Check and close any blocked apps"""
        results = []
        
        for window in windows:
            if window.app.lower() in self._blocked_apps:
                result = self.close_window(window, force=True)
                results.append(result)
        
        return results
    
    # ==================== BATCH OPERATIONS ====================
    
    def close_all_by_status(self, windows: List[WindowInfo], status: str) -> List[ControlResult]:
        """Close all windows with specified productivity status"""
        results = []
        
        for window in windows:
            if window.status == status:
                result = self.close_window(window)
                results.append(result)
        
        return results
    
    def minimize_all_distracting(self, windows: List[WindowInfo]) -> List[ControlResult]:
        """Minimize all distracting windows"""
        results = []
        
        for window in windows:
            if window.status == "Distracting":
                result = self.minimize_window(window)
                results.append(result)
        
        return results
    
    def focus_productive_windows(self, windows: List[WindowInfo]) -> List[ControlResult]:
        """Focus on productive windows"""
        results = []
        
        for window in windows:
            if window.status == "Productive":
                result = self.focus_window(window)
                results.append(result)
        
        return results
    
    # ==================== ADVANCED FEATURES ====================
    
    def create_window_snapshot(self, windows: List[WindowInfo]) -> Dict:
        """Create a snapshot of current window states"""
        snapshot = {
            "timestamp": time.time(),
            "windows": []
        }
        
        for window in windows:
            snapshot["windows"].append({
                "title": window.display_title,
                "app": window.app,
                "position": window.position,
                "size": window.size,
                "state": {
                    "minimized": window.is_minimized,
                    "maximized": window.is_maximized,
                    "visible": window.is_visible,
                    "active": window.is_active
                }
            })
        
        return snapshot
    
    def restore_window_snapshot(self, snapshot: Dict, current_windows: List[WindowInfo]) -> List[ControlResult]:
        """Restore windows to a previous snapshot state"""
        results = []
        
        # Create mapping of current windows by title
        window_map = {w.display_title: w for w in current_windows}
        
        for saved_window in snapshot["windows"]:
            title = saved_window["title"]
            if title in window_map:
                window = window_map[title]
                hwnd = self._get_real_window_handle(window)
                
                if not hwnd:
                    results.append(ControlResult(
                        success=False,
                        message=f"Could not find window handle for '{title}'"
                    ))
                    continue
                
                # Restore position and size
                x, y = saved_window["position"]
                width, height = saved_window["size"]
                
                try:
                    win32gui.MoveWindow(hwnd, x, y, width, height, True)
                    
                    # Restore state
                    state = saved_window["state"]
                    if state["minimized"]:
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    elif state["maximized"]:
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    else:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    
                    results.append(ControlResult(
                        success=True,
                        message=f"Window '{title}' restored to snapshot state",
                        window_id=hwnd
                    ))
                    
                except Exception as e:
                    results.append(ControlResult(
                        success=False,
                        message=f"Failed to restore window '{title}': {str(e)}",
                        window_id=hwnd
                    ))
        
        return results
    
    def get_system_stats(self) -> Dict:
        """Get system performance statistics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "processes": len(psutil.pids()),
            "boot_time": psutil.boot_time()
        }
        