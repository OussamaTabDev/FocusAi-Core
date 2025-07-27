# config_manager.py
import json
import logging
import os
import psutil
import platform
from typing import Optional, List

# --- Constants ---
PROCESS_MAP_FILE = 'config/process_map.json'
CATEGORIES_FILE = 'config/categories.json'
URL_FILE = 'config/url_history.json'
UNWANTED_PREFIXES_FILE = "config/uprefixes.json"


DEFAULT_PROCESS_MAP = {
    "Code.exe": "Visual Studio Code", "brave.exe": "Brave", "vlc.exe": "VLC media player",
    "explorer.exe": "File Explorer", "chrome.exe": "Chrome", "firefox.exe": "Firefox",
    "msedge.exe": "Edge", "notepad.exe": "Notepad", "devenv.exe": "Visual Studio",
    "pycharm64.exe": "PyCharm", "SearchUI.exe": "Windows Search", 
    "StartMenuExperienceHost.exe": "Start Menu", "ShellExperienceHost.exe": "Windows Shell",
    "SystemSettings.exe": "Windows Settings", "winlogon.exe": "Windows Logon",
    "dwm.exe": "Desktop Window Manager", "rundll32.exe": "Windows System Process",
    "svchost.exe": "Windows Service Host", "cortana.exe": "Cortana", 
    "SearchApp.exe": "Windows Search App" , "cmd.exe": "Terminal" 
}

DEFAULT_CATEGORIES = {
    "search": ["search", "find", "cortana", "spotlight", "launcher"],
    "system_dialog": ["properties", "settings", "control panel", "options"],
    "file_manager": ["explorer", "finder", "nautilus", "dolphin"],
    "terminal": ["terminal", "cmd", "powershell", "bash", "konsole"],
    "browser": ["chrome", "firefox", "edge", "brave", "opera"],
    "code_editor": ["code", "pycharm", "sublime", "atom", "vim", "devenv"]
}

DEFAULT_URL = []
DEFAULT_PREFIXE = []
# --- Generic Helper Functions ---

def _load_json_config(file_path: str, default_data: dict) -> dict:
    """A generic function to load a JSON file, creating it if it doesn't exist."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.info(f"Config file {file_path} not found. Creating with default values.")
        _save_json_config(file_path, default_data)
        return default_data
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error reading/parsing {file_path}: {e}. Returning defaults.")
        return default_data

def _save_json_config(file_path: str, data: dict):
    """A generic function to save data to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logging.error(f"Could not write to config file {file_path}: {e}")

#region PROCESS

# --- Process Map Management ---

def load_process_map() -> dict:
    """Loads the process map from its JSON file."""
    return _load_json_config(PROCESS_MAP_FILE, DEFAULT_PROCESS_MAP)

def add_or_update_mapping(process_exe: str, friendly_name: str):
    """Adds or updates a process mapping."""
    current_map = load_process_map()
    current_map[process_exe] = friendly_name
    _save_json_config(PROCESS_MAP_FILE, current_map)
    



def find_process_location(process_name: str) -> Optional[str]:
    """
    Find the executable path of a running process by name.
    Works on both Windows and Linux.
    
    Args:
        process_name: Name of the process (e.g., "fmd.exe" on Windows, "fmd" on Linux)
    
    Returns:
        Path to the executable if found, None otherwise
    """
    try:
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    return proc.info['exe']
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have ended, no permission, or zombie process
                continue
    except Exception as e:
        print(f"Error searching for process: {e}")
    
    return None


def get_name(process_name):
       location = find_process_location(process_name)
       print(f"location : {location}")
       app_name = [part.strip() for part in location.split("\\") if part.strip()][-2:-1][0] \
       if [part.strip() for part in location.split("\\") if part.strip()][-2:-1][0] != bin \
           else [part.strip() for part in location.split("\\") if part.strip()][-3:-2][0]
       return [part.strip() for part in location.split("\\") if part.strip()][-2:-1][0] 
   
def ensure_process_mapped(process_exe: str):
    """
    Checks if a process exists in the mapping, if not adds it with a default friendly name.
    Returns the friendly name (either existing or newly added).
    """
    process_map = load_process_map()
    
    # Check if process already exists in mapping
    if process_exe in process_map  :
        return process_map[process_exe]
    
    # print(process_exe)
    # Create a default friendly name by removing .exe and capitalizing
    # friendly_name = os.path.splitext(process_exe)[0].capitalize()
    friendly_name = get_name(process_exe)
    
    # Add to mapping
    add_or_update_mapping(process_exe, friendly_name)
    
    return friendly_name
#endregion
#region CATS
# --- Category CRUD Management ---

def get_all_categories() -> dict:
    """Reads all categories and their patterns from the config file."""
    return _load_json_config(CATEGORIES_FILE , DEFAULT_CATEGORIES)

def create_category(category_name: str) -> bool:
    """Creates a new, empty category."""
    categories = get_all_categories()
    if category_name in categories:
        logging.warning(f"Category '{category_name}' already exists.")
        return False
    categories[category_name] = []
    _save_json_config(CATEGORIES_FILE, categories)
    logging.info(f"Category '{category_name}' created.")
    return True

def delete_category(category_name: str) -> bool:
    """Deletes a category and all its patterns."""
    categories = get_all_categories()
    if category_name not in categories:
        logging.warning(f"Category '{category_name}' not found.")
        return False
    del categories[category_name]
    _save_json_config(CATEGORIES_FILE, categories)
    logging.info(f"Category '{category_name}' deleted.")
    return True

def add_pattern_to_category(category_name: str, pattern: str) -> bool:
    """Adds a regex pattern to a specified category."""
    categories = get_all_categories()
    if category_name not in categories:
        logging.error(f"Cannot add pattern. Category '{category_name}' does not exist.")
        return False
    if pattern in categories[category_name]:
        logging.warning(f"Pattern '{pattern}' already exists in category '{category_name}'.")
        return False
    categories[category_name].append(pattern)
    _save_json_config(CATEGORIES_FILE, categories)
    logging.info(f"Pattern '{pattern}' added to category '{category_name}'.")
    return True
    
def remove_pattern_from_category(category_name: str, pattern: str) -> bool:
    """Removes a regex pattern from a specified category."""
    categories = get_all_categories()
    if category_name not in categories:
        logging.error(f"Cannot remove pattern. Category '{category_name}' does not exist.")
        return False
    if pattern not in categories[category_name]:
        logging.warning(f"Pattern '{pattern}' not found in category '{category_name}'.")
        return False
    categories[category_name].remove(pattern)
    _save_json_config(CATEGORIES_FILE, categories)
    logging.info(f"Pattern '{pattern}' removed from category '{category_name}'.")
    return True
#endregion


#region URLS
# --- Urls CRUD Management----
def _load_json_config_url(file_path: str, default_data: dict) -> dict:
    """A generic function to load a JSON file, creating it if it doesn't exist."""
    try:
        with open(file_path, 'r' , encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.info(f"Config file {file_path} not found. Creating with default values.")
        _save_json_config(file_path, default_data)
        return default_data
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error reading/parsing {file_path}: {e}. Returning defaults.")
        return default_data
    

           
def get_all_urls() -> dict:
    """Reads all categories and their patterns from the config file."""
    return _load_json_config_url(URL_FILE , DEFAULT_URL)

def last_url() -> dict:
    # URLS  = max(get_all_urls(), key=lambda x: datetime.fromisoformat(x["server_timestamp"]))
    URLS  = get_all_urls()[-1]

    return URLS

def get_domain():
    return last_url()["domain"]

def processed_domain():
    parts = parts = [part.strip() for part in get_domain().split(".") if part.strip()]

    if len(parts) == 1:
        return "browser"
    elif len(parts) == 2:
        return parts[-2]
    else :
        if parts[-2] == "google":
            return parts[-2] + " " + parts[-3]
        else :
            return parts[-2]   
#endregion       
#region UP

# --- Profixes ----
def get_all_prefixes() -> list:
    """Reads all prefixes from the config file."""
    try:
        prefixes = _load_json_config(UNWANTED_PREFIXES_FILE , DEFAULT_PREFIXE)
        if not isinstance(prefixes, list):
            # If the file is corrupted or in wrong format, return default
            return DEFAULT_PREFIXE.copy()
        return prefixes
    except FileNotFoundError:
        return DEFAULT_PREFIXE.copy()

def add_prefix(prefix: str) -> bool:
    """Adds a new prefix to the list if it doesn't already exist."""
    prefixes = get_all_prefixes()
    if prefix in prefixes:
        logging.warning(f"Prefix '{prefix}' already exists.")
        return False
    prefixes.append(prefix)
    _save_json_config(UNWANTED_PREFIXES_FILE, prefixes)
    logging.info(f"Prefix '{prefix}' added.")
    return True

def remove_prefix(prefix: str) -> bool:
    """Removes a prefix from the list if it exists."""
    prefixes = get_all_prefixes()
    if prefix not in prefixes:
        logging.warning(f"Prefix '{prefix}' not found.")
        return False
    prefixes.remove(prefix)
    _save_json_config(UNWANTED_PREFIXES_FILE, prefixes)
    logging.info(f"Prefix '{prefix}' removed.")
    return True



#endregion    

# --- Load initial configs for the application to use ---
PROCESS_NAME_MAP = load_process_map()
CATEGORIES = get_all_categories()
URLS = get_all_urls()
PREFIXES = get_all_prefixes()