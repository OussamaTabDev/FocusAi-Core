
# Core/database/migrations.py
"""Database migration utilities for window tracking."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
import os
import logging
from .models import Base

class DatabaseMigration:
    """Handle database migrations and schema updates."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Error creating database tables: {e}")
            raise
    
    def check_database_exists(self) -> bool:
        """Check if database exists and has required tables."""
        try:
            inspector = inspect(self.engine)
            required_tables = ['window_records', 'app_sessions', 'app_statistics']
            existing_tables = inspector.get_table_names()
            
            return all(table in existing_tables for table in required_tables)
        except Exception as e:
            logging.error(f"Error checking database: {e}")
            return False
    
    def initialize_database(self):
        """Initialize database with required tables."""
        if not self.check_database_exists():
            logging.info("Database not found or incomplete, creating tables...")
            self.create_tables()
        else:
            logging.info("Database already exists with required tables")
