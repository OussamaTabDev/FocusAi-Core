# Core/database/backup.py
"""Database backup and restore utilities."""

import sqlite3
import shutil
import os
import logging
from datetime import datetime
from typing import Optional

class DatabaseBackup:
    """Handle database backup and restore operations."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_sqlite = 'sqlite' in database_url.lower()
        
        if self.is_sqlite:
            # Extract file path from SQLite URL
            self.db_path = database_url.replace('sqlite:///', '')
    
    def create_backup(self, backup_dir: str = 'backups') -> Optional[str]:
        """Create a backup of the database."""
        try:
            if not self.is_sqlite:
                logging.warning("Backup only supported for SQLite databases")
                return None
            
            if not os.path.exists(self.db_path):
                logging.error(f"Database file not found: {self.db_path}")
                return None
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"window_tracker_backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Create backup using SQLite's backup API for consistency
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            logging.info(f"Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logging.error(f"Error creating database backup: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            if not self.is_sqlite:
                logging.warning("Restore only supported for SQLite databases")
                return False
            
            if not os.path.exists(backup_path):
                logging.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current database before restore
            current_backup = self.create_backup('restore_backups')
            if current_backup:
                logging.info(f"Current database backed up to: {current_backup}")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            logging.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error restoring database backup: {e}")
            return False
    
    def cleanup_old_backups(self, backup_dir: str = 'backups', keep_days: int = 30):
        """Remove backup files older than specified days."""
        try:
            if not os.path.exists(backup_dir):
                return
            
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            for filename in os.listdir(backup_dir):
                if filename.startswith('window_tracker_backup_') and filename.endswith('.db'):
                    file_path = os.path.join(backup_dir, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        logging.info(f"Removed old backup: {filename}")
            
        except Exception as e:
            logging.error(f"Error cleaning up old backups: {e}")
