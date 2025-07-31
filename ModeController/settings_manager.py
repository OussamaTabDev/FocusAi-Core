import json
import logging
from pathlib import Path
from datetime import timedelta
from typing import Dict, Optional, Any, List
from dataclasses import asdict
from .models import ModeSettings
from .enums import ModeType, StandardSubMode, FocusType

logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Custom exception for configuration-related errors"""
    pass

class SettingsManager:
    """Manages application mode settings with JSON persistence"""
    
    def __init__(self, config_root: str = "config"):
        self.mode_settings: Dict[str, ModeSettings] = {}
        self.config_root = Path(config_root)
        self.config_dir = self.config_root / "modes"
        self.user_prefs_path = self.config_root / "user_preferences.json"
        self.load_settings()
        
    def load_settings(self) -> None:
        """Load all settings from JSON files"""
        try:
            self._ensure_config_structure()
            self._load_all_mode_configs()
            self._load_user_preferences()
            logger.info(f"Loaded {len(self.mode_settings)} mode configurations")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise ConfigError(f"Settings loading failed: {e}")
    
    def _ensure_config_structure(self) -> None:
        """Create config directory structure and default configs"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._create_default_configs()
    
    def _create_default_configs(self) -> None:
        """Create default configuration files if they don't exist"""
        default_configs = {
            "standard_normal.json": self._get_standard_normal_config(),
            "standard_focus_deep.json": self._get_standard_focus_deep_config(),
            "standard_focus_light.json": self._get_standard_focus_light_config(),
            "kids.json": self._get_kids_config(),
        }
        
        for filename, config in default_configs.items():
            config_path = self.config_dir / filename
            if not config_path.exists():
                self._save_config_file(config_path, config)
                logger.info(f"Created default config: {filename}")
    
    def _get_standard_normal_config(self) -> dict:
        """Standard normal mode configuration"""
        return {
            "mode_type": "STANDARD",
            "submode": "NORMAL",
            "description": "Normal usage with no restrictions",
            "settings": {
                "allowed_apps": [],
                "blocked_apps": [],
                "minimized_apps": [],
                "notifications_enabled": True,
                "auto_break_reminder": False
            }
        }
    
    def _get_standard_focus_deep_config(self) -> dict:
        """Deep focus mode configuration"""
        return {
            "mode_type": "STANDARD",
            "submode": "FOCUS",
            "focus_type": "DEEP",
            "description": "Deep focus mode for intensive work",
            "settings": {
                "allowed_apps": ["visual studio code", "notion", "slack"],
                "blocked_apps": ["discord", "steam", "spotify", "facebook", "reddit", "twitter"],
                "minimized_apps": ["vlc", "youtube"],
                "duration": 60,
                "notifications_enabled": False,
                "auto_break_reminder": True,
                "break_interval_minutes": 25,
                "distraction_blocker": True,
                "strict_mode": True
            }
        }
    
    def _get_standard_focus_light_config(self) -> dict:
        """Light focus mode configuration"""
        return {
            "mode_type": "STANDARD",
            "submode": "FOCUS",
            "focus_type": "LIGHT",
            "description": "Light focus mode for general productivity",
            "settings": {
                "allowed_apps": ["visual studio code", "notion", "slack", "spotify"],
                "blocked_apps": ["discord", "steam", "facebook", "reddit"],
                "minimized_apps": ["youtube"],
                "duration": 30,
                "notifications_enabled": True,
                "auto_break_reminder": False,
                "strict_mode": False
            }
        }
    
    
    def _get_kids_config(self) -> dict:
        """Kids educational mode configuration"""
        return {
            "mode_type": "KIDS",
            "description": "Educational mode for learning activities",
            "settings": {
                "allowed_apps": ["scratch", "khan academy", "minecraft education", "duolingo", "prodigy math"],
                "blocked_apps": ["discord", "steam", "facebook", "reddit"],
                "minimized_apps": ["youtube"],
                "time_limit": 90,
                "bedtime_start": "21:00",
                "bedtime_end": "07:00",
                "parental_override_required": False,
                "screen_time_alerts": True,
                "educational_time_bonus": True,
                "achievement_tracking": True
            }
        }
    
    def _load_all_mode_configs(self) -> None:
        """Load all mode configurations from JSON files"""
        config_files = list(self.config_dir.glob("*.json"))
        if not config_files:
            logger.warning("No configuration files found")
            return
        
        for config_file in config_files:
            try:
                self._load_single_config(config_file)
            except Exception as e:
                logger.error(f"Error loading config {config_file.name}: {e}")
                # Continue loading other configs even if one fails
    
    def _load_single_config(self, config_file: Path) -> None:
        """Load a single configuration file"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            self._validate_config(config, config_file.name)
            self._parse_config(config)
            logger.debug(f"Loaded config: {config_file.name}")
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {config_file.name}: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load {config_file.name}: {e}")
    
    def _validate_config(self, config: dict, filename: str) -> None:
        """Validate configuration structure"""
        required_fields = ["mode_type", "settings"]
        for field in required_fields:
            if field not in config:
                raise ConfigError(f"Missing required field '{field}' in {filename}")
        
        # Validate enum values
        try:
            ModeType[config["mode_type"]]
        except KeyError:
            raise ConfigError(f"Invalid mode_type '{config['mode_type']}' in {filename}")
        
        if "submode" in config:
            try:
                StandardSubMode[config["submode"]]
            except KeyError:
                raise ConfigError(f"Invalid submode '{config['submode']}' in {filename}")
    
    def _parse_config(self, config: dict) -> None:
        """Convert JSON config to ModeSettings object and store it"""
        mode_type = ModeType[config["mode_type"]]
        submode = StandardSubMode[config["submode"]] if "submode" in config else None
        focus_type = FocusType[config["focus_type"]] if "focus_type" in config else None
        
        # Generate settings key
        key = self._generate_mode_key(mode_type, submode, focus_type)
        
        # Create ModeSettings object
        settings = self._create_mode_settings(config["settings"])
        
        # Store additional metadata
        settings.description = config.get("description", "")
        settings.mode_type = mode_type
        settings.submode = submode
        settings.focus_type = focus_type
        
        self.mode_settings[key] = settings
    
    def _generate_mode_key(self, mode_type: ModeType, submode: Optional[StandardSubMode] = None, 
                      focus_type: Optional[FocusType] = None) -> str:
        """Generate a unique key for the mode configuration
        
        For STANDARD mode, the key incorporates submode and focus type if applicable.
        KIDS and other modes use simple mode name as key (no submodes supported).
        """
        if mode_type == ModeType.STANDARD:
            if submode == StandardSubMode.FOCUS and focus_type:
                return f"standard_focus_{focus_type.name.lower()}"
            elif submode:
                return f"standard_{submode.name.lower()}"
            return "standard"
        elif mode_type == ModeType.KIDS:
            return "kids"
        return mode_type.name.lower()
    
    def _create_mode_settings(self, settings_dict: dict) -> ModeSettings:
        """Create ModeSettings object from dictionary"""
        settings = ModeSettings()
        
        for key, value in settings_dict.items():
            if hasattr(settings, key):
                # Handle special type conversions
                if key == "duration" and value is not None:
                    setattr(settings, "duration", timedelta(minutes=value))
                elif key == "max_daily_usage_minutes" and value is not None:
                    setattr(settings, "max_daily_usage", timedelta(minutes=value))
                elif key == "break_interval_minutes" and value is not None:
                    setattr(settings, "break_interval", timedelta(minutes=value))
                else:
                    setattr(settings, key, value)
            else:
                logger.warning(f"Unknown setting: {key}")
        
        return settings
    
    def get_mode_setting(self, mode_key: str) -> Optional[ModeSettings]:
        """Get mode settings by key"""
        return self.mode_settings.get(mode_key)
    
    # use this in kids mode and other modes : to-do
    
      
    def list_available_modes(self) -> List[str]:
        """Get list of available mode keys"""
        print(f"Available modes: {self.mode_settings.keys()}")
        return list(self.mode_settings.keys())
    
    def list_available_Focus_modes(self) -> List[str]:
        """Get list of available  focus mode keys"""
        focus_modes = [mode for mode in self.mode_settings.keys() if 'focus' in mode]
        print(f"Focus modes: {focus_modes}")
        return focus_modes
    
    def update_mode_setting(self, mode_key: str, setting_name: str, new_value: Any) -> None:
        """
        Update a specific mode setting and persist to JSON file
        
        Args:
            mode_key: e.g. "standard_focus_deep"
            setting_name: name of the setting to update
            new_value: new value for the setting
        
        Raises:
            ValueError: If mode_key doesn't exist
            AttributeError: If setting_name doesn't exist
            ConfigError: If file operations fail
        """
        if mode_key not in self.mode_settings:
            raise ValueError(f"Unknown mode key: {mode_key}")
        
        # Update in-memory settings
        settings = self.mode_settings[mode_key]
        if not hasattr(settings, setting_name):
            raise AttributeError(f"Setting '{setting_name}' not found in {mode_key}")
        
        old_value = getattr(settings, setting_name)
        setattr(settings, setting_name, new_value)
        
        try:
            # Update the corresponding JSON file
            self._update_config_file(mode_key, setting_name, new_value)
            logger.info(f"Updated {mode_key}.{setting_name}: {old_value} -> {new_value}")
            
        except Exception as e:
            # Rollback in-memory change
            setattr(settings, setting_name, old_value)
            logger.error(f"Failed to update {mode_key}.{setting_name}: {e}")
            raise ConfigError(f"Failed to persist setting update: {e}")
    
    def _update_config_file(self, mode_key: str, setting_name: str, new_value: Any) -> None:
        """Update the JSON configuration file"""
        filename = self._get_config_filename(mode_key)
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file {filename} not found")
        
        # Load current config
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Update the setting
        if setting_name == "duration" and isinstance(new_value, timedelta):
            config["settings"]["duration"] = int(new_value.total_seconds() / 60)
        elif setting_name == "max_daily_usage" and isinstance(new_value, timedelta):
            config["settings"]["max_daily_usage_minutes"] = int(new_value.total_seconds() / 60)
        elif setting_name == "break_interval" and isinstance(new_value, timedelta):
            config["settings"]["break_interval_minutes"] = int(new_value.total_seconds() / 60)
        else:
            config["settings"][setting_name] = new_value
        
        # Save updated config
        self._save_config_file(config_file, config)
    
    def _get_config_filename(self, mode_key: str) -> str:
        """Generate filename from mode key"""
        return f"{mode_key}.json"
    
    def add_mode_config(self, mode_key: str, config: dict) -> None:
        """
        Add a new mode configuration
        
        Args:
            mode_key: unique key for the mode
            config: configuration dictionary
        """
        if mode_key in self.mode_settings:
            raise ValueError(f"Mode key '{mode_key}' already exists")
        
        self._validate_config(config, f"{mode_key}.json")
        
        # Save to file
        filename = self._get_config_filename(mode_key)
        config_file = self.config_dir / filename
        self._save_config_file(config_file, config)
        
        # Add to memory
        self._parse_config(config)
        logger.info(f"Added new mode configuration: {mode_key}")
    
    def delete_mode_config(self, mode_key: str) -> None:
        """
        Delete a mode configuration
        
        Args:
            mode_key: key of the mode to delete
        """
        if mode_key not in self.mode_settings:
            raise ValueError(f"Mode key '{mode_key}' not found")
        
        # Remove from memory
        del self.mode_settings[mode_key]
        
        # Remove file
        filename = self._get_config_filename(mode_key)
        config_file = self.config_dir / filename
        if config_file.exists():
            config_file.unlink()
        
        logger.info(f"Deleted mode configuration: {mode_key}")
    
    def _save_config_file(self, file_path: Path, config: dict) -> None:
        """Save configuration to file with error handling"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"Failed to save config file {file_path.name}: {e}")
    
    def _load_user_preferences(self) -> None:
        """Load user-specific preferences from config file"""
        if not self.user_prefs_path.exists():
            logger.debug("No user preferences file found")
            return
        
        try:
            with open(self.user_prefs_path, "r", encoding="utf-8") as f:
                preferences = json.load(f)
            
            # Apply user preferences to mode settings
            self._apply_user_preferences(preferences)
            logger.info("Loaded user preferences")
            
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
    
    def _apply_user_preferences(self, preferences: dict) -> None:
        """Apply user preferences to loaded mode settings"""
        # Example: Override certain settings based on user preferences
        for mode_key, mode_prefs in preferences.get("mode_overrides", {}).items():
            if mode_key in self.mode_settings:
                settings = self.mode_settings[mode_key]
                for pref_key, pref_value in mode_prefs.items():
                    if hasattr(settings, pref_key):
                        setattr(settings, pref_key, pref_value)
                        logger.debug(f"Applied user preference: {mode_key}.{pref_key} = {pref_value}")
    
    def export_settings(self) -> dict:
        """Export all settings to a dictionary"""
        return {
            key: asdict(settings) if hasattr(settings, '__dict__') else str(settings)
            for key, settings in self.mode_settings.items()
        }
    
    def backup_settings(self, backup_path: Optional[Path] = None) -> Path:
        """Create a backup of all settings"""
        if backup_path is None:
            backup_path = self.config_root / f"backup_{int(Path().stat().st_mtime)}.json"
        
        backup_data = {
            "mode_settings": self.export_settings(),
            "backup_timestamp": Path().stat().st_mtime
        }
        
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Settings backed up to: {backup_path}")
        return backup_path
    
    
    
    
if __name__ == "__main__":
    import logging
    from pprint import pprint

    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    
    def main():
        print("=== Settings Inspector ===")
        
        # Initialize with test config directory
        manager = SettingsManager()
        
        # Get all available mode keys
        available_modes = manager.list_available_modes()
        print("\nAvailable mode keys:")
        print("\n".join(f"- {k}" for k in available_modes))
        
        if not available_modes:
            print("No modes available!")
            return
        
        # Let's inspect a specific mode
        example_key = "standard_focus_deep"  # Change this to any key you want to inspect
        print(f"\nInspecting settings for: {example_key}")
        
        # Get the settings object
        settings = manager.get_mode_setting(example_key)
        
        if not settings:
            print(f"No settings found for key: {example_key}")
            return
        
        # Print all attributes of the settings object
        print("\nAll settings attributes:")
        for attr in dir(settings):
            # Skip private and special attributes
            if not attr.startswith('_') and not callable(getattr(settings, attr)):
                value = getattr(settings, attr)
                print(f"{attr}: {value}")
        
        # Print specific settings in a more readable way
        print("\nKey settings:")
        print(f"Mode Type: {getattr(settings, 'mode_type', 'N/A')}")
        print(f"Submode: {getattr(settings, 'submode', 'N/A')}")
        print(f"Focus Type: {getattr(settings, 'focus_type', 'N/A')}")
        print(f"Description: {getattr(settings, 'description', 'N/A')}")
        
        # Print app restrictions if they exist
        if hasattr(settings, 'allowed_apps'):
            print(f"\nAllowed Apps: {getattr(settings, 'allowed_apps', [])}")
        
        if hasattr(settings, 'blocked_apps'):
            print(f"Blocked Apps: {getattr(settings, 'blocked_apps', [])}")
        
        if hasattr(settings, 'minimized_apps'):
            print(f"Minimized Apps: {getattr(settings, 'minimized_apps', [])}")
        
        # Print timing settings if they exist
        # if hasattr(settings, 'time_limit'):
        print(f"\nDuration: {getattr(settings, 'time_limit', 'N/A')} minutes")
            
        # Print timing settings if they exist
        if hasattr(settings, 'duration'):
            print(f"\nDuration: {getattr(settings, 'duration', 'N/A')} minutes")
        
        if hasattr(settings, 'break_interval_minutes'):
            print(f"Break Interval: {getattr(settings, 'break_interval_minutes', 'N/A')} minutes")
        
        # Print other boolean settings
        if hasattr(settings, 'notifications_enabled'):
            print(f"\nNotifications Enabled: {getattr(settings, 'notifications_enabled', 'N/A')}")
        
        if hasattr(settings, 'auto_break_reminder'):
            print(f"Auto Break Reminder: {getattr(settings, 'auto_break_reminder', 'N/A')}")
        
        if hasattr(settings, 'distraction_blocker'):
            print(f"Distraction Blocker: {getattr(settings, 'distraction_blocker', 'N/A')}")

    main()