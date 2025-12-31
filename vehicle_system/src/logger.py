"""
Logging system for RK3568 Rover
Provides centralized logging with file and console output
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import os


class RoverLogger:
    """Centralized logging system for the rover"""
    
    _instance: Optional['RoverLogger'] = None
    _loggers: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger system"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        log_dir = Path("/var/log")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up root logger
        self.root_logger = logging.getLogger("rover")
        self.root_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.root_logger.handlers = []
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler (INFO level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.root_logger.addHandler(console_handler)
        
        # File handler (DEBUG level) - rotating file
        try:
            log_file = "/var/log/rk3568_rover.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            self.root_logger.addHandler(file_handler)
        except PermissionError:
            # Fallback to home directory if /var/log is not writable
            log_file = Path.home() / "rover_logs" / "rk3568_rover.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),
                maxBytes=10*1024*1024,
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            self.root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module
        
        Args:
            name: Logger name (typically __name__)
        
        Returns:
            Logger instance
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(f"rover.{name}")
        return self._loggers[name]


# Global logger instance
_logger_system = RoverLogger()


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return _logger_system.get_logger(name)


# Example usage
if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
