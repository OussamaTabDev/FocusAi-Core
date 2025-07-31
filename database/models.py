# Core/database/models.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

Base = declarative_base()

class WindowRecord(Base):
    """Raw window information records - exact copy of WindowInfo"""
    __tablename__ = 'window_records'
    
    id = Column(Integer, primary_key=True)
    raw_title = Column(Text, nullable=False)
    window_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Position and size
    position_x = Column(Integer)
    position_y = Column(Integer) 
    width = Column(Integer)
    height = Column(Integer)
    
    # Window states
    is_active = Column(Boolean, default=True)
    is_minimized = Column(Boolean, default=False)
    is_maximized = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    z_order = Column(Integer, default=-1)
    
    # Process info
    process_name = Column(String(255))
    process = Column(String(255))
    class_name = Column(String(255))
    
    # Window classification
    is_system_window = Column(Boolean, default=False)
    is_topmost = Column(Boolean, default=False)
    parent_window_exists = Column(Boolean, default=False)
    
    # Parsed data
    window_type = Column(String(50), default='unknown')
    app = Column(String(255), nullable=False, index=True)
    original_app = Column(String(255), default="Desktop App")
    status = Column(String(50), default="Neutral", index=True)
    context = Column(Text)
    domain = Column(String(500))
    display_title = Column(Text)
    
    # Extra info as JSON
    extra_info = Column(JSON)
    
    # Foreign key to session
    session_id = Column(Integer, ForeignKey('app_sessions.id'), index=True)
    session = relationship("AppSessionDB", back_populates="window_records")

class AppSessionDB(Base):
    """App usage sessions"""
    __tablename__ = 'app_sessions'
    
    id = Column(Integer, primary_key=True)
    app_name = Column(String(255), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, index=True)
    total_duration = Column(Float, default=0.0)  # seconds
    
    # Session metadata
    window_count = Column(Integer, default=0)
    context_changes = Column(JSON)  # List of contexts
    titles_seen = Column(JSON)  # List of titles
    status_changes = Column(JSON)  # List of (timestamp, status) tuples
    
    # Foreign key to AppStatisticsDB
    statistics_id = Column(Integer, ForeignKey('app_statistics.id'), index=True)
    
    # Relationships
    window_records = relationship("WindowRecord", back_populates="session")
    statistics = relationship("AppStatisticsDB", back_populates="sessions")

class AppStatisticsDB(Base):
    """Aggregated app statistics"""
    __tablename__ = 'app_statistics'
    
    id = Column(Integer, primary_key=True)
    app_name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Time tracking
    total_time = Column(Float, default=0.0)  # seconds
    session_count = Column(Integer, default=0)
    average_session_duration = Column(Float, default=0.0)
    longest_session = Column(Float, default=0.0)
    last_used = Column(DateTime)
    
    # Context and status breakdowns as JSON
    contexts = Column(JSON)  # {context: time_spent}
    statuses = Column(JSON)  # {status: time_spent}
    
    # Update timestamp
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("AppSessionDB", back_populates="statistics")
