# Core/database/config.py
"""Database configuration for different environments."""

import os
from typing import Dict, Any

class DatabaseConfig:
    """Database configuration manager."""
    
    @staticmethod
    def get_database_url(environment: str = 'development') -> str:
        """Get database URL for specified environment."""
        
        configs = {
            'development': {
                'url': os.getenv('DEV_DATABASE_URL', 'sqlite:///window_tracker_dev.db')
            },
            'production': {
                'url': os.getenv('DATABASE_URL', 'sqlite:///window_tracker.db')
            },
            'testing': {
                'url': os.getenv('TEST_DATABASE_URL', 'sqlite:///window_tracker_test.db')
            }
        }
        
        return configs.get(environment, configs['development'])['url']
    
    @staticmethod
    def get_engine_kwargs(environment: str = 'development') -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration."""
        
        base_config = {
            'echo': False,
            'pool_pre_ping': True,
        }
        
        if environment == 'development':
            base_config['echo'] = os.getenv('SQL_DEBUG', 'false').lower() == 'true'
        
        # For SQLite, add some optimizations
        if 'sqlite' in DatabaseConfig.get_database_url(environment):
            base_config.update({
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 20
                }
            })
        
        return base_config

