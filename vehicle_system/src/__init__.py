"""
RK3568 Remote Rover System
A professional-grade remote-controlled tracked rover system based on RK3568 development board
"""

__version__ = "1.0.0"
__author__ = "Manus Team"
__description__ = "RK3568 Remote Rover System with real-time video, audio, and motor control"

from .logger import get_logger
from .config_manager import get_config
from .camera_manager import get_camera_manager
from .audio_processor import get_audio_processor
from .motor_controller import get_motor_controller
from .video_encoder import get_encoder
from .webrtc_service import get_webrtc_service

__all__ = [
    'get_logger',
    'get_config',
    'get_camera_manager',
    'get_audio_processor',
    'get_motor_controller',
    'get_encoder',
    'get_webrtc_service',
]
