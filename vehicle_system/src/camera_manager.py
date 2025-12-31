"""
USB Camera Management for RK3568 Rover
Handles dual USB camera capture and frame processing
"""

import cv2
import asyncio
import threading
from typing import Optional, Callable, Tuple
from collections import deque
from logger import get_logger
from config_manager import get_config

logger = get_logger(__name__)


class USBCamera:
    """USB Camera wrapper for OpenCV"""
    
    def __init__(self, device_id: int, resolution: Tuple[int, int], fps: int = 30):
        """
        Initialize USB camera
        
        Args:
            device_id: Camera device ID (0, 1, etc.)
            resolution: Target resolution (width, height)
            fps: Target frames per second
        """
        self.device_id = device_id
        self.resolution = resolution
        self.fps = fps
        self.cap = None
        self.is_opened = False
        self.frame_count = 0
        self.error_count = 0
        
    def open(self) -> bool:
        """
        Open camera device
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera device {self.device_id}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera {self.device_id} opened: {actual_width}x{actual_height}@{actual_fps}fps")
            
            self.is_opened = True
            return True
            
        except Exception as e:
            logger.error(f"Error opening camera {self.device_id}: {e}")
            return False
    
    def read_frame(self) -> Optional[bytes]:
        """
        Read a frame from camera
        
        Returns:
            Frame as numpy array or None if failed
        """
        if not self.is_opened or self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                self.error_count += 1
                if self.error_count > 10:
                    logger.warning(f"Camera {self.device_id} read errors exceed threshold")
                return None
            
            self.error_count = 0
            self.frame_count += 1
            return frame
            
        except Exception as e:
            logger.error(f"Error reading frame from camera {self.device_id}: {e}")
            self.error_count += 1
            return None
    
    def close(self):
        """Close camera device"""
        if self.cap is not None:
            self.cap.release()
            self.is_opened = False
            logger.info(f"Camera {self.device_id} closed (captured {self.frame_count} frames)")


class CameraManager:
    """Manages dual USB cameras"""
    
    def __init__(self):
        """Initialize camera manager"""
        self.config = get_config()
        self.front_camera: Optional[USBCamera] = None
        self.rear_camera: Optional[USBCamera] = None
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        
        # Frame buffers for each camera
        self.front_frame_buffer = deque(maxlen=3)
        self.rear_frame_buffer = deque(maxlen=3)
        
        # Callbacks
        self.on_front_frame: Optional[Callable] = None
        self.on_rear_frame: Optional[Callable] = None
        
        # Statistics
        self.front_fps = 0
        self.rear_fps = 0
        self.front_frame_count = 0
        self.rear_frame_count = 0
    
    def initialize(self) -> bool:
        """
        Initialize both cameras
        
        Returns:
            True if at least one camera initialized successfully
        """
        try:
            front_config = self.config.get_section('camera').get('front', {})
            rear_config = self.config.get_section('camera').get('rear', {})
            
            success = False
            
            # Initialize front camera
            if front_config.get('enabled', True):
                self.front_camera = USBCamera(
                    device_id=front_config.get('device_id', 0),
                    resolution=tuple(front_config.get('resolution', [1280, 720])),
                    fps=front_config.get('fps', 30)
                )
                if self.front_camera.open():
                    success = True
                else:
                    self.front_camera = None
            
            # Initialize rear camera
            if rear_config.get('enabled', True):
                self.rear_camera = USBCamera(
                    device_id=rear_config.get('device_id', 1),
                    resolution=tuple(rear_config.get('resolution', [1280, 720])),
                    fps=rear_config.get('fps', 30)
                )
                if self.rear_camera.open():
                    success = True
                else:
                    self.rear_camera = None
            
            if not success:
                logger.error("Failed to initialize any camera")
                return False
            
            logger.info("Camera manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera manager: {e}")
            return False
    
    def start_capture(self):
        """Start continuous frame capture"""
        if self.is_running:
            logger.warning("Camera capture already running")
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info("Camera capture started")
    
    def stop_capture(self):
        """Stop continuous frame capture"""
        self.is_running = False
        if self.capture_thread is not None:
            self.capture_thread.join(timeout=5)
        logger.info("Camera capture stopped")
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        import time
        
        front_last_time = time.time()
        rear_last_time = time.time()
        front_frame_count = 0
        rear_frame_count = 0
        
        while self.is_running:
            try:
                # Capture front camera
                if self.front_camera is not None:
                    frame = self.front_camera.read_frame()
                    if frame is not None:
                        self.front_frame_buffer.append(frame)
                        front_frame_count += 1
                        
                        if self.on_front_frame:
                            self.on_front_frame(frame)
                
                # Capture rear camera
                if self.rear_camera is not None:
                    frame = self.rear_camera.read_frame()
                    if frame is not None:
                        self.rear_frame_buffer.append(frame)
                        rear_frame_count += 1
                        
                        if self.on_rear_frame:
                            self.on_rear_frame(frame)
                
                # Update FPS statistics every second
                current_time = time.time()
                if current_time - front_last_time >= 1.0:
                    self.front_fps = front_frame_count
                    front_frame_count = 0
                    front_last_time = current_time
                
                if current_time - rear_last_time >= 1.0:
                    self.rear_fps = rear_frame_count
                    rear_frame_count = 0
                    rear_last_time = current_time
                
                # Small sleep to prevent busy waiting
                time.sleep(0.001)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
    
    def get_front_frame(self) -> Optional:
        """Get latest front camera frame"""
        if self.front_frame_buffer:
            return self.front_frame_buffer[-1]
        return None
    
    def get_rear_frame(self) -> Optional:
        """Get latest rear camera frame"""
        if self.rear_frame_buffer:
            return self.rear_frame_buffer[-1]
        return None
    
    def set_front_frame_callback(self, callback: Callable):
        """Set callback for front camera frames"""
        self.on_front_frame = callback
    
    def set_rear_frame_callback(self, callback: Callable):
        """Set callback for rear camera frames"""
        self.on_rear_frame = callback
    
    def get_stats(self) -> dict:
        """Get camera statistics"""
        return {
            'front_fps': self.front_fps,
            'rear_fps': self.rear_fps,
            'front_frame_count': self.front_camera.frame_count if self.front_camera else 0,
            'rear_frame_count': self.rear_camera.frame_count if self.rear_camera else 0,
            'front_errors': self.front_camera.error_count if self.front_camera else 0,
            'rear_errors': self.rear_camera.error_count if self.rear_camera else 0,
        }
    
    def shutdown(self):
        """Shutdown camera manager"""
        self.stop_capture()
        
        if self.front_camera is not None:
            self.front_camera.close()
        
        if self.rear_camera is not None:
            self.rear_camera.close()
        
        logger.info("Camera manager shutdown complete")


# Global camera manager instance
_camera_manager: Optional[CameraManager] = None


def get_camera_manager() -> CameraManager:
    """Get global camera manager instance"""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = CameraManager()
    return _camera_manager


# Example usage
if __name__ == "__main__":
    import time
    
    manager = get_camera_manager()
    
    if manager.initialize():
        manager.start_capture()
        
        try:
            for _ in range(10):
                stats = manager.get_stats()
                print(f"Front FPS: {stats['front_fps']}, Rear FPS: {stats['rear_fps']}")
                time.sleep(1)
        finally:
            manager.shutdown()
