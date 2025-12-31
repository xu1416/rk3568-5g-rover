"""
RK3568 Remote Rover System - Main Application
Integrates all components: cameras, audio, video encoding, WebRTC, and motor control
"""

import asyncio
import signal
import sys
from typing import Optional
from logger import get_logger
from config_manager import get_config
from camera_manager import get_camera_manager
from audio_processor import get_audio_processor
from video_encoder import get_encoder
from motor_controller import get_motor_controller
from webrtc_service import get_webrtc_service, WebRTCMediaManager

logger = get_logger(__name__)


class RoverSystem:
    """Main rover system controller"""
    
    def __init__(self):
        """Initialize rover system"""
        self.config = get_config()
        self.camera_manager = get_camera_manager()
        self.audio_processor = get_audio_processor()
        self.motor_controller = get_motor_controller()
        self.webrtc_service: Optional = None
        self.media_manager = WebRTCMediaManager()
        
        self.is_running = False
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize all rover subsystems
        
        Returns:
            True if all systems initialized successfully
        """
        try:
            logger.info("=" * 60)
            logger.info("RK3568 Remote Rover System - Initialization Starting")
            logger.info("=" * 60)
            
            # Initialize camera system
            logger.info("Initializing camera system...")
            if not self.camera_manager.initialize():
                logger.error("Failed to initialize camera system")
                return False
            
            # Initialize audio system
            logger.info("Initializing audio system...")
            if not self.audio_processor.initialize():
                logger.warning("Audio system initialization failed (non-critical)")
            
            # Initialize motor controller
            logger.info("Initializing motor controller...")
            if not self.motor_controller.connect():
                logger.warning("Motor controller connection failed (non-critical)")
            
            # Initialize WebRTC service
            logger.info("Initializing WebRTC service...")
            self.webrtc_service = await get_webrtc_service()
            
            # Initialize video encoder
            logger.info("Initializing video encoder...")
            encoder = get_encoder()
            if not encoder.initialize():
                logger.warning("Video encoder initialization failed (non-critical)")
            
            self.is_initialized = True
            logger.info("=" * 60)
            logger.info("RK3568 Remote Rover System - Initialization Complete")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}", exc_info=True)
            return False
    
    async def start(self):
        """Start rover system"""
        if not self.is_initialized:
            logger.error("System not initialized")
            return
        
        if self.is_running:
            logger.warning("System already running")
            return
        
        try:
            logger.info("Starting rover system...")
            
            # Start camera capture
            self.camera_manager.start_capture()
            
            # Start audio capture and playback
            self.audio_processor.start_capture()
            self.audio_processor.start_playback()
            
            # Start monitoring
            self._start_monitoring()
            
            self.is_running = True
            logger.info("Rover system started successfully")
            
        except Exception as e:
            logger.error(f"Error starting system: {e}", exc_info=True)
    
    async def stop(self):
        """Stop rover system"""
        if not self.is_running:
            return
        
        try:
            logger.info("Stopping rover system...")
            
            self.is_running = False
            
            # Stop camera capture
            self.camera_manager.stop_capture()
            
            # Stop audio
            self.audio_processor.stop_capture()
            self.audio_processor.stop_playback()
            
            # Stop motor
            self.motor_controller.emergency_stop()
            
            logger.info("Rover system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}", exc_info=True)
    
    async def shutdown(self):
        """Shutdown rover system"""
        logger.info("Shutting down rover system...")
        
        await self.stop()
        
        # Shutdown all components
        self.camera_manager.shutdown()
        self.audio_processor.shutdown()
        self.motor_controller.shutdown()
        
        if self.webrtc_service:
            await self.webrtc_service.shutdown()
        
        logger.info("Rover system shutdown complete")
    
    def _start_monitoring(self):
        """Start system monitoring"""
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Get statistics from all subsystems
                camera_stats = self.camera_manager.get_stats()
                audio_stats = self.audio_processor.get_stats()
                motor_stats = self.motor_controller.get_status()
                webrtc_stats = self.webrtc_service.get_peer_stats() if self.webrtc_service else {}
                
                # Log statistics every 10 seconds
                logger.debug(
                    f"System Stats - "
                    f"Camera: {camera_stats['front_fps']}fps (front), {camera_stats['rear_fps']}fps (rear) | "
                    f"Audio: {audio_stats['captured_frames']} frames | "
                    f"Motor: {motor_stats['current_direction']} | "
                    f"WebRTC: {webrtc_stats.get('active_peers', 0)} peers"
                )
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def handle_control_command(self, peer_id: str, command: str):
        """
        Handle control command from remote client
        
        Args:
            peer_id: Peer identifier
            command: Control command JSON string
        """
        try:
            import json
            
            cmd_data = json.loads(command)
            cmd_type = cmd_data.get('type')
            
            if cmd_type == 'motor':
                # Motor control command
                action = cmd_data.get('action')
                speed = cmd_data.get('speed', 200)
                
                if action == 'forward':
                    self.motor_controller.move_forward(speed)
                elif action == 'backward':
                    self.motor_controller.move_backward(speed)
                elif action == 'left':
                    self.motor_controller.turn_left(speed)
                elif action == 'right':
                    self.motor_controller.turn_right(speed)
                elif action == 'stop':
                    self.motor_controller.stop()
                
                logger.debug(f"Motor command: {action} at speed {speed}")
            
            elif cmd_type == 'camera':
                # Camera control command
                action = cmd_data.get('action')
                
                if action == 'switch_front':
                    logger.debug("Switching to front camera")
                elif action == 'switch_rear':
                    logger.debug("Switching to rear camera")
            
            elif cmd_type == 'system':
                # System control command
                action = cmd_data.get('action')
                
                if action == 'emergency_stop':
                    logger.warning("Emergency stop received from remote")
                    self.motor_controller.emergency_stop()
            
        except Exception as e:
            logger.error(f"Error handling control command: {e}")
    
    def get_system_status(self) -> dict:
        """Get overall system status"""
        return {
            'is_running': self.is_running,
            'is_initialized': self.is_initialized,
            'camera': self.camera_manager.get_stats(),
            'audio': self.audio_processor.get_stats(),
            'motor': self.motor_controller.get_status(),
            'webrtc': self.webrtc_service.get_peer_stats() if self.webrtc_service else {},
        }


async def main():
    """Main application entry point"""
    rover = RoverSystem()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(rover.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize system
        if not await rover.initialize():
            logger.error("Failed to initialize rover system")
            return 1
        
        # Start system
        await rover.start()
        
        # Run until shutdown
        while rover.is_running:
            await asyncio.sleep(1)
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await rover.shutdown()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
