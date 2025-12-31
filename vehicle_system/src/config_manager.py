"""
Configuration management for RK3568 Rover
Loads and manages configuration from YAML files and environment variables
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class CameraConfig:
    """Camera configuration"""
    device_id: int
    resolution: list
    fps: int
    format: str
    enabled: bool


@dataclass
class AudioConfig:
    """Audio configuration"""
    sample_rate: int
    channels: int
    chunk_size: int
    enabled: bool


@dataclass
class VideoEncodingConfig:
    """Video encoding configuration"""
    codec: str
    profile: str
    level: str
    bitrate: int
    gop: int
    hardware_acceleration: bool
    rkmpp_enabled: bool
    preset: str


@dataclass
class WebRTCConfig:
    """WebRTC configuration"""
    ice_servers: list
    signaling_url: str
    reconnect_interval: int
    max_reconnect_attempts: int


@dataclass
class MotorControlConfig:
    """Motor control configuration"""
    driver_type: str
    serial_port: str
    baudrate: int
    max_speed: int
    timeout: int


class ConfigManager:
    """Singleton configuration manager"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to YAML configuration file
        """
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_config(config_file)
    
    def _load_config(self, config_file: Optional[str] = None):
        """
        Load configuration from YAML file and environment variables
        
        Args:
            config_file: Path to YAML configuration file
        """
        # Default config file location
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config" / "config.yaml"
        
        config_file = Path(config_file)
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}, using defaults")
            self._config = self._get_default_config()
        else:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Configuration loaded from {config_file}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                self._config = self._get_default_config()
        
        # Override with environment variables
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # System
        if os.getenv('ROVER_DEBUG'):
            self._config.setdefault('system', {})['debug_mode'] = os.getenv('ROVER_DEBUG').lower() == 'true'
        
        # Camera
        if os.getenv('CAMERA_FRONT_DEVICE'):
            self._config.setdefault('camera', {}).setdefault('front', {})['device_id'] = int(os.getenv('CAMERA_FRONT_DEVICE'))
        
        if os.getenv('CAMERA_REAR_DEVICE'):
            self._config.setdefault('camera', {}).setdefault('rear', {})['device_id'] = int(os.getenv('CAMERA_REAR_DEVICE'))
        
        # WebRTC
        if os.getenv('WEBRTC_SIGNALING_URL'):
            self._config.setdefault('webrtc', {}).setdefault('signaling', {})['server_url'] = os.getenv('WEBRTC_SIGNALING_URL')
        
        # Motor
        if os.getenv('MOTOR_SERIAL_PORT'):
            self._config.setdefault('motor_control', {}).setdefault('serial', {})['port'] = os.getenv('MOTOR_SERIAL_PORT')
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'system': {
                'device_name': 'RK3568-Rover-01',
                'platform': 'rk3568',
                'debug_mode': True,
                'log_level': 'INFO'
            },
            'camera': {
                'front': {
                    'device_id': 0,
                    'resolution': [1280, 720],
                    'fps': 30,
                    'format': 'MJPEG',
                    'enabled': True
                },
                'rear': {
                    'device_id': 1,
                    'resolution': [1280, 720],
                    'fps': 30,
                    'format': 'MJPEG',
                    'enabled': True
                }
            },
            'video_encoding': {
                'codec': 'h264',
                'profile': 'baseline',
                'level': '3.1',
                'bitrate': 1024,
                'gop': 60,
                'hardware_acceleration': True,
                'rkmpp_enabled': True,
                'preset': 'medium'
            },
            'audio': {
                'microphone': {
                    'sample_rate': 16000,
                    'channels': 1,
                    'chunk_size': 1024,
                    'enabled': True
                },
                'speaker': {
                    'sample_rate': 16000,
                    'channels': 1,
                    'enabled': True
                },
                'encoding': {
                    'codec': 'opus',
                    'bitrate': 24,
                    'frame_duration': 20,
                    'sample_rate': 16000
                }
            },
            'motor_control': {
                'driver_type': 'balance_car',
                'serial': {
                    'port': '/dev/ttyUSB0',
                    'baudrate': 115200,
                    'timeout': 1.0
                },
                'motor': {
                    'max_speed': 255,
                    'min_speed': 0,
                    'timeout': 5000
                }
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., 'camera.front.device_id')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name
        
        Returns:
            Section configuration dictionary
        """
        return self._config.get(section, {})
    
    def set(self, key: str, value: Any):
        """
        Set configuration value by dot-notation key
        
        Args:
            key: Configuration key (e.g., 'camera.front.device_id')
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.debug(f"Configuration updated: {key} = {value}")
    
    def reload(self, config_file: Optional[str] = None):
        """
        Reload configuration from file
        
        Args:
            config_file: Path to YAML configuration file
        """
        self._config = {}
        self._load_config(config_file)
        logger.info("Configuration reloaded")
    
    def to_dict(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary"""
        return self._config.copy()


# Global configuration manager instance
_config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """Get global configuration manager instance"""
    return _config_manager


# Example usage
if __name__ == "__main__":
    config = get_config()
    
    print("Device name:", config.get('system.device_name'))
    print("Front camera device:", config.get('camera.front.device_id'))
    print("Video bitrate:", config.get('video_encoding.bitrate'))
    
    # Get entire section
    camera_config = config.get_section('camera')
    print("Camera config:", camera_config)
