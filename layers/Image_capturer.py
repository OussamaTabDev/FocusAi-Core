import pyautogui
import time
import threading
import logging
import os
import shutil
from datetime import datetime

class ImageCapturer:
    def __init__(self, interval):
        self.screenshot = None
        self.capture_time = None
        self.image_history = []
        self.interval = interval * 60
        self.is_capturing = False
        self.lock = threading.Lock()
        self.base_folder = "screenshots"  # Base folder for all screenshots
        self.max_history_size = 100  # Maximum number of screenshots to keep in memory
        self.auto_cleanup_days = 7  # Auto-cleanup files older than X days
        
        
    def _create_folder_structure(self):
        """Create folder structure: screenshots/month_MM/day_DD/"""
        timestamp = datetime.now()
        month_folder = f"month_{timestamp.month:02d}"
        day_folder = f"day_{timestamp.day:02d}"
        
        folder_path = os.path.join(self.base_folder, month_folder, day_folder)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
        
    def _capture_loop(self):  # Fixed typo: cupture -> capture
        if self.interval == 0:
            return         
        """The internal loop that runs on a separate thread."""
        while self.is_capturing and self.interval > 0:
            screenshot = pyautogui.screenshot()
            self.screenshot = screenshot
            self.capture_time = time.time()
            
            # Create folder structure and filename
            folder_path = self._create_folder_structure()
            timestamp = datetime.now()
            filename = timestamp.strftime("screenshot_%Y-%m-%d_%H-%M-%S.png")
            filepath = os.path.join(folder_path, filename)
            
            screenshot.save(filepath)  # Save with date-time filename in organized folders
            self.image_history.append((self.capture_time, screenshot, filepath))
            
            # Auto-cleanup history if it gets too large
            if len(self.image_history) > self.max_history_size:
                self.image_history = self.image_history[-self.max_history_size:]
            
            time.sleep(self.interval)


    def start(self):
        """Starts the image capturing in a background thread."""
        if self.is_capturing:
            logging.warning("Tracking is already running.")
            return
            
        self.is_capturing = True
        self.tracking_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.tracking_thread.start()
        
    def stop(self):
        """Stops the image capturing."""
        self.is_capturing = False
        if hasattr(self, 'tracking_thread'):
            self.tracking_thread.join()
    
    def clear_history(self):
        """Clear the image history from memory."""
        with self.lock:
            self.image_history.clear()
            self.screenshot = None
            self.capture_time = None
            print("Image history cleared from memory.")
    
    def clean_storage(self, days_old=None, specific_month=None, specific_day=None):
        """
        Clean storage by removing old files or specific folders.
        
        Args:
            days_old: Remove files older than X days (default: self.auto_cleanup_days)
            specific_month: Remove specific month folder (1-12)
            specific_day: Remove specific day folder (1-31, requires specific_month)
        """
        if not os.path.exists(self.base_folder):
            print("No screenshot folder found.")
            return
        
        if days_old is None:
            days_old = self.auto_cleanup_days
        
        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 60 * 60)  # Convert days to seconds
        
        removed_count = 0
        
        # If specific month/day is specified, remove that folder
        if specific_month:
            month_folder = f"month_{specific_month:02d}"
            if specific_day:
                day_folder = f"day_{specific_day:02d}"
                target_path = os.path.join(self.base_folder, month_folder, day_folder)
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                    print(f"Removed folder: {target_path}")
                    return
            else:
                target_path = os.path.join(self.base_folder, month_folder)
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                    print(f"Removed folder: {target_path}")
                    return
        
        # Otherwise, remove files older than specified days
        for root, dirs, files in os.walk(self.base_folder):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('.png') and os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
        
        # Remove empty directories
        for root, dirs, files in os.walk(self.base_folder, topdown=False):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                if not os.listdir(dir_path):  # If directory is empty
                    os.rmdir(dir_path)
        
        print(f"Removed {removed_count} old files (older than {days_old} days).")
    
    def get_storage_info(self):
        """Get information about stored screenshots."""
        if not os.path.exists(self.base_folder):
            return "No screenshots folder found."
        
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(self.base_folder):
            for file in files:
                if file.endswith('.png'):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    total_size += os.path.getsize(file_path)
        
        size_mb = total_size / (1024 * 1024)
        return f"Total screenshots: {total_files}, Total size: {size_mb:.2f} MB"
        
     
## test the ImageCapturer class   
# if __name__ == "__main__":
#     capturer = ImageCapturer(interval=2)  # Capture every 2 seconds
#     capturer.start()
    
#     # Keep the main thread alive to allow background capturing
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("Stopping image capture.")
#         capturer.stop()
        
#         # Example usage of new functions
#         print("\n" + capturer.get_storage_info())
        
#         # Uncomment to test cleanup functions:
#         # capturer.clear_history()
#         # capturer.clean_storage(days_old=1)  # Remove files older than 1 day
#         # capturer.clean_storage(specific_month=7, specific_day=12)  # Remove specific day folder