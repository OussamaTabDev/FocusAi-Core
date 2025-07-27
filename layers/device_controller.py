import time
import platform
import subprocess
import os
import json
import getpass
from datetime import date, datetime, timedelta
# from config import HISTORY_FILE , PASSCODE

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "config/device_history.json")
PASSCODE = "2025"   # <-- change this

class DeviceController:
    """
    Timer + history + lock-screen pass-code.
    """
    


    def __init__(self):
        self.is_timing = False
        self.start_time = 0.0
        self.end_time = 0.0
        self.time_limit = 0.0
        self.action = "sleep" # sleep , shutdown , reboot , hibernate , logoff
        self.is_warning = True  # whether to show warning before action
        self.HISTORY_FILE = HISTORY_FILE
        self.PASSCODE = PASSCODE
        # load history (or create empty)
        self.history = self._load_history()

        # Check if passcode is needed BEFORE starting timer
        self._enforce_lock_if_needed()

        # Only start timing after passcode is verified (if needed)
        self.start()

    def _load_history(self) -> dict:
        # If file doesn't exist, return empty dict
        if not os.path.exists(self.HISTORY_FILE):
            return {}

        try:
            # Check if file is empty
            if os.path.getsize(self.HISTORY_FILE) == 0:
                return {}

            # Try to read and parse the file
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
                
        except (json.JSONDecodeError, IOError, PermissionError) as e:
            print(f"Warning: Could not read history file ({e}). Starting with empty history.")
            return {}

    # ------------------------------------------------------------------
    # Public timer interface (unchanged signature)
    # ------------------------------------------------------------------
    def start(self) -> None:
        self.is_timing = True
        self.start_time = time.time()

    def elapsed(self) -> float:
        if not self.is_timing:
            return 0.0
        return time.time() - self.start_time

    def stop(self) -> None:
        self.is_timing = False
        self.end_time = time.time()

    def set_timer(
        self,
        time_limit: float = 0.0,
        is_warning: bool = True,
        action: str = "sleep",
        grace_seconds: float = 10.0
    ) -> None:
        if time_limit <= 0.0:
            return True

        # Only check timer if we're not currently enforcing the lock
        if self.elapsed() >= time_limit:
            if is_warning:
                self._notify("Timeout!", "Limit reached. Pass-code will be required tomorrow.")
                self.stop()
                return True
            else:
                self._notify("Timeout!", f"Limit reached. {action} will apply after {grace_seconds}.")
                self.power_action(action, grace_seconds)
                self.stop()
                return True

    def _checking_loop(self, time_limit: float = 0.0, action: str = "sleep", is_warning: bool = True, grace_seconds: float = 0.0) -> None:
        """
        Main checking loop for kids mode timer.
        time_limit: in minutes
        """
        if time_limit <= 0.0:
            print("No time limit set, exiting timer")
            return
            
        self.time_limit = time_limit * 60  # convert minutes to seconds
        self.action = action
        self.is_warning = is_warning
        
        print(f"Starting timer: {time_limit} minutes ({self.time_limit} seconds)")
        print(f"Action: {action}, Warning: {is_warning}, Grace: {grace_seconds}s")
        
        # Ensure the timer is started
        if not self.is_timing:
            self.start()
        
        start_loop_time = time.time()
        
        while self.is_timing:
            # Use both elapsed() and direct time calculation as backup
            elapsed_from_start = self.elapsed()
            elapsed_from_loop = time.time() - start_loop_time
            
            # Use the maximum of both to be safe
            elapsed = max(elapsed_from_start, elapsed_from_loop)
            
            print(f"Elapsed: {elapsed:.1f}s / {self.time_limit}s ({elapsed/60:.1f} min)")
            
            if elapsed >= self.time_limit:
                print(f"Time limit reached! Elapsed: {elapsed:.1f}s, Limit: {self.time_limit}s")
                
                if is_warning:
                    self._notify("Timeout!", "Limit reached. Pass-code will be required tomorrow.")
                    self.stop()
                    break
                else:
                    self._notify("Timeout!", f"Limit reached. {action} will apply after {grace_seconds} seconds.")
                    # Add a small delay to ensure notification is seen
                    time.sleep(2)
                    self.power_action(action, grace_seconds)
                    self.stop()
                    break
                    
            time.sleep(1)  # Check every second
        
        print("Timer loop ended")
    
    # ------------------------------------------------------------------
    # Power action + record keeping
    # ------------------------------------------------------------------
    def power_action(self, action: str = "sleep", delay: float = 0.0) -> None:
        """Execute action and record today's date."""
        if delay > 0:
            time.sleep(delay)

        today = str(date.today())
        self.history[today] = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "requires_passcode": True
        }
        self._save_history()

        # actually run the command
        system = platform.system()
        cmd = None
        if system == "Windows":
            if action == "logoff":
                cmd = ["shutdown", "/l"]
            elif action == "sleep":
                cmd = ["rundll32.exe", "powrprof.dll", "SetSuspendState", "0,1,0"]
            elif action == "hibernate":
                cmd = ["rundll32.exe", "powrprof.dll", "SetSuspendState", "1,1,0"]
            elif action == "reboot":
                cmd = ["shutdown", "/r", "/t", "0"]
            elif action == "shutdown":
                cmd = ["shutdown", "/s", "/t", "0"]
            else:
                raise ValueError(f"Unknown action: {action}")
        else:  # Linux/Mac
            if action == "lock":
                cmd = ["loginctl", "lock-session"]
            elif action == "sleep":
                cmd = ["systemctl", "suspend"]
            elif action == "hibernate":
                cmd = ["systemctl", "hibernate"]
            elif action == "reboot":
                cmd = ["systemctl", "reboot"]
            elif action == "shutdown":
                cmd = ["systemctl", "poweroff"]
            else:
                raise ValueError(f"Unknown action: {action}")

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to execute {action}: {e}")
        except FileNotFoundError:
            print(f"Command not found for {action} on {system}")

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------
    def _save_history(self) -> None:
        try:
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except (IOError, PermissionError) as e:
            print(f"Warning: Could not save history file ({e})")

    # ------------------------------------------------------------------
    # Lock-screen pass-code gate
    # ------------------------------------------------------------------
    def _enforce_lock_if_needed(self) -> None:
        """Check if passcode is required and enforce it"""
        today = str(date.today())
        
        # Check if today's entry exists and requires passcode
        if today in self.history:
            entry = self.history[today]
            
            # Handle both old format (string) and new format (dict)
            requires_passcode = False
            if isinstance(entry, dict):
                requires_passcode = entry.get("requires_passcode", False)
            elif isinstance(entry, str):
                # Old format - any action requires passcode
                requires_passcode = True
                
            if requires_passcode:
                self._request_passcode(today)
        
        # Also check yesterday's entry (in case of date rollover)
        yesterday = str(date.today() - timedelta(days=1))
        if yesterday in self.history:
            entry = self.history[yesterday]
            requires_passcode = False
            if isinstance(entry, dict):
                requires_passcode = entry.get("requires_passcode", False)
            elif isinstance(entry, str):
                requires_passcode = True
                
            if requires_passcode:
                self._request_passcode(yesterday)

    def _request_passcode(self, date_key: str) -> None:
        """Request passcode and handle the response"""
        entry = self.history[date_key]
        action_name = entry if isinstance(entry, str) else entry.get("action", "unknown action")
        
        self._notify("Access Restricted", f"Passcode required after {action_name}.")
        print(f"\n=== PASSCODE REQUIRED ===")
        print(f"PC was locked due to: {action_name}")
        print(f"Enter passcode to continue using the PC")
        print("=" * 25)
        
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:
                pw = getpass.getpass(prompt=f"Enter passcode ({max_attempts - attempts} attempts left): ")
            except (KeyboardInterrupt, EOFError):
                print("\nAccess denied.")
                self._force_action()
                return
            
            if pw == self.PASSCODE:
                print("✓ Passcode correct. Access granted.")
                # Clear the passcode requirement
                if isinstance(self.history[date_key], dict):
                    self.history[date_key]["requires_passcode"] = False
                else:
                    # Convert old format to new format
                    self.history[date_key] = {
                        "action": self.history[date_key],
                        "timestamp": datetime.now().isoformat(),
                        "requires_passcode": False
                    }
                self._save_history()
                return  # Correct passcode → allow access
            
            attempts += 1
            remaining = max_attempts - attempts
            if remaining > 0:
                print(f"✗ Incorrect passcode. {remaining} attempts remaining.")
            else:
                print("✗ All attempts exhausted.")

        # If all attempts fail → force action
        print("Access denied. Executing security action...")
        self._force_action()

    def _force_action(self) -> None:
        """Execute security action when passcode fails"""
        self.power_action("sleep")  # You can change this to "shutdown" for stricter security

    # ------------------------------------------------------------------
    # Small desktop notification
    # ------------------------------------------------------------------
    def _notify(self, title: str, message: str) -> None:
        system = platform.system()
        if system == "Windows":
            try:
                # Use a simpler PowerShell command that's more reliable
                ps_cmd = f'powershell -WindowStyle Hidden -Command "[System.Reflection.Assembly]::LoadWithPartialName(\\"System.Windows.Forms\\"); [System.Windows.Forms.MessageBox]::Show(\\"{message}\\", \\"{title}\\")"'
                subprocess.run(ps_cmd, shell=True, check=False)
            except Exception:
                print(f"{title}: {message}")
        else:
            try:
                subprocess.run(["notify-send", title, message], check=False)
            except FileNotFoundError:
                try:
                    subprocess.run(["zenity", "--info", "--title", title, "--text", message], check=False)
                except FileNotFoundError:
                    print(f"{title}: {message}")

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    def clear_history(self) -> None:
        """Clear all history - useful for testing"""
        self.history = {}
        self._save_history()
        print("History cleared.")

    def show_history(self) -> None:
        """Display current history"""
        if not self.history:
            print("No history found.")
            return
            
        print("\n=== DEVICE HISTORY ===")
        for date_str, entry in sorted(self.history.items()):
            if isinstance(entry, dict):
                action = entry.get("action", "unknown")
                timestamp = entry.get("timestamp", "unknown time")
                requires_passcode = entry.get("requires_passcode", False)
                status = "🔒 Passcode required" if requires_passcode else "✓ Cleared"
                print(f"{date_str}: {action} at {timestamp} - {status}")
            else:
                print(f"{date_str}: {entry} - 🔒 Passcode required")
        print("=" * 20)

    
# ----------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # For testing, you can clear history first
    # dc = DeviceController()
    # dc.clear_history()  # Uncomment to reset
    
    try:
        dc = DeviceController()
        print(f"Timer started. Current elapsed time: {dc.elapsed():.1f}s")
        
        # Show current history
        dc.show_history()
        
        # Start the checking loop
        print("Starting timer check loop (Ctrl+C to stop)...")
        dc._checking_loop(time_limit=1/30, action="sleep", is_warning=False, grace_seconds=10)
        
    except KeyboardInterrupt:
        if 'dc' in locals():
            dc.stop()
        print("\nTimer stopped.")
    except Exception as e:
        print(f"Error: {e}")
        if 'dc' in locals():
            dc.stop()