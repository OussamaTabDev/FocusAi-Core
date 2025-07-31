# requirements.txt (add these to your existing requirements)
# sqlalchemy>=1.4.0
# alembic>=1.7.0

# Core/database/__init__.py
"""Database package for window tracking persistence."""

from .database_manager import DatabaseManager
from .models import Base, WindowRecord, AppSessionDB, AppStatisticsDB

__all__ = ['DatabaseManager', 'Base', 'WindowRecord', 'AppSessionDB', 'AppStatisticsDB']



# Server/app/database_setup.py
"""Database setup script for the Flask application."""

import sys
from pathlib import Path

# Add Core to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Core"))

from database.database_manager import DatabaseManager
from database.migrations import DatabaseMigration
from database.config import DatabaseConfig
from database.backup import DatabaseBackup
import logging
import os

def setup_database(environment: str = 'development'):
    """Set up database for the application."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get database configuration
    database_url = DatabaseConfig.get_database_url(environment)
    logging.info(f"Setting up database: {database_url}")
    
    try:
        # Initialize database
        migration = DatabaseMigration(database_url)
        migration.initialize_database()
        
        # Test database connection
        db_manager = DatabaseManager(database_url)
        with db_manager.get_session() as session:
            # Simple test query
            from database.models import AppStatisticsDB
            session.query(AppStatisticsDB).count()
        
        logging.info("Database setup completed successfully")
        
        # Create initial backup
        if environment == 'production':
            backup = DatabaseBackup(database_url)
            backup_path = backup.create_backup('initial_backups')
            if backup_path:
                logging.info(f"Initial backup created: {backup_path}")
        
        return True
        
    except Exception as e:
        logging.error(f"Database setup failed: {e}")
        return False

def migrate_from_memory_to_database():
    """
    Migration script to move existing in-memory data to database.
    This would be useful if you have existing tracking data to preserve.
    """
    logging.info("Starting migration from memory to database...")
    
    # This is a placeholder - you would implement the actual migration logic
    # based on any existing data files or memory dumps you might have
    
    logging.info("Migration completed")
    
# if __name__ == "__main__":
#     import argparse
    
#     parser = argparse.ArgumentParser(description='Database setup for Window Tracker')
#     parser.add_argument('--env', default='development', 
#                        choices=['development', 'production', 'testing'],
#                        help='Environment to set up database for')
#     parser.add_argument('--migrate', action='store_true',
#                        help='Run migration from memory to database')
    
#     args = parser.parse_args()
    
#     if args.migrate:
#         migrate_from_memory_to_database()
#     else:
#         success = setup_database(args.env)
#         exit(0 if success else 1)