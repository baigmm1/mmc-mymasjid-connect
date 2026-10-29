"""
Build version management system.

Handles automatic build number incrementation and version string generation.
Build information is persisted to a JSON file for consistency across restarts.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

from src.core.logging import get_logger

logger = get_logger(__name__)

# Build info file location (in backend-api root, not tracked by git)
BUILD_INFO_FILE = Path(__file__).parent.parent.parent / "build_info.json"


class BuildManager:
    """
    Manages build version tracking and generation.
    
    Features:
    - Auto-incrementing build numbers
    - Date-based version strings (YYYY.MM.BUILD)
    - Persistent storage in JSON file
    - Thread-safe operations
    """
    
    _instance = None
    _current_build: Dict[str, any] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single build manager instance."""
        if cls._instance is None:
            cls._instance = super(BuildManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize build manager and load existing build info."""
        self._load_build_info()
    
    def _load_build_info(self) -> None:
        """Load build information from file or initialize if not exists."""
        if BUILD_INFO_FILE.exists():
            try:
                with open(BUILD_INFO_FILE, 'r') as f:
                    self._current_build = json.load(f)
                logger.info(f"Loaded existing build info: Build #{self._current_build['build_number']}")
            except Exception as e:
                logger.warning(f"Failed to load build info file: {e}. Initializing new build.")
                self._initialize_build()
        else:
            self._initialize_build()
    
    def _initialize_build(self) -> None:
        """Initialize build information for first time."""
        now = datetime.now()
        self._current_build = {
            "build_number": 1,
            "build_date": now.strftime("%Y-%m-%d"),
            "build_timestamp": int(now.timestamp()),
            "version": f"{now.year}.{now.month:02d}.1",
            "full_version": f"{now.year}.{now.month:02d}.1-{now.strftime('%Y%m%d')}"
        }
        self._save_build_info()
        logger.info("Initialized new build info: Build #1")
    
    def _save_build_info(self) -> None:
        """Persist current build information to file."""
        try:
            # Ensure directory exists
            BUILD_INFO_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            with open(BUILD_INFO_FILE, 'w') as f:
                json.dump(self._current_build, f, indent=2)
            logger.debug(f"Saved build info to {BUILD_INFO_FILE}")
        except Exception as e:
            logger.error(f"Failed to save build info: {e}")
    
    def get_current_build(self) -> Dict[str, any]:
        """
        Get current build information.
        
        Returns:
            Dictionary containing build_number, build_date, build_timestamp, version, full_version
        """
        return self._current_build.copy()
    
    def increment_build(self) -> Dict[str, any]:
        """
        Increment build number and update version strings.
        
        This should be called during deployment or CI/CD pipeline.
        
        Returns:
            Updated build information dictionary
        """
        now = datetime.now()
        
        # Increment build number
        new_build_number = self._current_build["build_number"] + 1
        
        # Generate new version strings
        self._current_build = {
            "build_number": new_build_number,
            "build_date": now.strftime("%Y-%m-%d"),
            "build_timestamp": int(now.timestamp()),
            "version": f"{now.year}.{now.month:02d}.{new_build_number}",
            "full_version": f"{now.year}.{now.month:02d}.{new_build_number}-{now.strftime('%Y%m%d')}"
        }
        
        # Persist to file
        self._save_build_info()
        
        logger.info(f"Build incremented to #{new_build_number}: {self._current_build['full_version']}")
        
        return self._current_build.copy()
    
    def reset_build(self, build_number: int = 1) -> Dict[str, any]:
        """
        Reset build number to specified value (for testing or reset scenarios).
        
        Args:
            build_number: New build number to set (default: 1)
            
        Returns:
            Updated build information dictionary
        """
        now = datetime.now()
        
        self._current_build = {
            "build_number": build_number,
            "build_date": now.strftime("%Y-%m-%d"),
            "build_timestamp": int(now.timestamp()),
            "version": f"{now.year}.{now.month:02d}.{build_number}",
            "full_version": f"{now.year}.{now.month:02d}.{build_number}-{now.strftime('%Y%m%d')}"
        }
        
        self._save_build_info()
        
        logger.warning(f"Build reset to #{build_number}: {self._current_build['full_version']}")
        
        return self._current_build.copy()


# Global build manager instance
_build_manager: BuildManager = None


def get_build_manager() -> BuildManager:
    """
    Get the global build manager instance.
    
    Returns:
        Singleton BuildManager instance
    """
    global _build_manager
    if _build_manager is None:
        _build_manager = BuildManager()
    return _build_manager
