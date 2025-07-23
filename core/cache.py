"""
This module handles all file-based caching operations for the application.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRATION = timedelta(hours=24)


def get_cache_path(username: str) -> Path:
    """Generates the file path for a user's cache file."""
    return CACHE_DIR / f"{username.lower()}.json"

def load_from_cache(username: str) -> Dict[str, Any] | None:
    """Loads user data from cache if it exists and is not expired."""
    cache_file = get_cache_path(username)
    if cache_file.exists():
        modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - modified_time < CACHE_EXPIRATION:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading cache file for {username}: {e}")
                return None
    return None

def save_to_cache(username: str, data: Dict[str, Any]):
    """Saves user data to a JSON file."""
    cache_file = get_cache_path(username)
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving cache file for {username}: {e}")

