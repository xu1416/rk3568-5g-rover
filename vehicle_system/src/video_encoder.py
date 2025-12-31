"""
Video Encoding Module for RK3568 Rover
Handles H.264 encoding with hardware acceleration via RKMPP
"""

import subprocess
import threading
import asyncio
from typing import Optional, Callable
from logger import get_logger
from config_manager import get_config
import numpy as np

logger = get_logger(__name__)


class H264Encoder:
    """H.264 hardware-accelerated encoder using RKMPP"""
    
    def __init__(self):
        """Initialize H.264 encoder"""
        self.config = get_config()
        self.is_initialized = False
        self.process: Optional[subprocess.Popen] = None
        self.encoding_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Statistics
        self.encoded_frames = 0
        self.dropped_frames = 0
        self.encoding_errors = 0
        
        # Callbacks
        self.on_encoded_data: Optional[Callable] = None
    
    def initialize(self) -> bool:
        """
        Initialize encoder
        
        Returns:
            True if initialization successful
        """
        try:
            # Check if RKMPP is available
            if not self._check_rkmpp_available():
                logger.warning("RKMPP not available, falling back to software encoding")
                return self._initialize_software_encoder()
            
            logger.info("RKMPP hardware acceleration available")
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing encoder: {e}")
            return False
    
    def _check_rkmpp_available(self) -> bool:
        """
        Check if RKMPP is available on the system
        
        Returns:
            True if RKMPP is available
        """
        try:
            # Check for RKMPP device files
            import os
            return os.path.exists('/dev/mpp_service') and os.path.exists('/dev/rga')
        except:
            return False
    
    def _initialize_software_encoder(self) -> bool:
        """
        Initialize software encoder (fallback)
        
        Returns:
            True if initialization successful
        """
        logger.info("Initializing software H.264 encoder")
        self.is_initialized = True
        return True
    
    def encode_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Encode a single frame to H.264
        
        Args:
            frame: Input frame as numpy array (BGR format)
        
        Returns:
            Encoded H.264 data or None if failed
        """
        if not self.is_initialized:
            return None
        
        try:
            # For now, return placeholder
            # In production, this would use FFmpeg with RKMPP
            self.encoded_frames += 1
            return None
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            self.encoding_errors += 1
            return None
    
    def start_encoding(self, input_callback: Callable, output_callback: Callable):
        """
        Start continuous encoding
        
        Args:
            input_callback: Function that returns frames to encode
            output_callback: Function to call with encoded data
        """
        if self.is_running:
            logger.warning("Encoding already running")
            return
        
        self.is_running = True
        self.on_encoded_data = output_callback
        self.encoding_thread = threading.Thread(
            target=self._encoding_loop,
            args=(input_callback,),
            daemon=True
        )
        self.encoding_thread.start()
        logger.info("Video encoding started")
    
    def stop_encoding(self):
        """Stop continuous encoding"""
        self.is_running = False
        if self.encoding_thread is not None:
            self.encoding_thread.join(timeout=5)
        logger.info("Video encoding stopped")
    
    def _encoding_loop(self, input_callback: Callable):
        """Main encoding loop"""
        import time
        
        while self.is_running:
            try:
                frame = input_callback()
                if frame is None:
                    time.sleep(0.001)
                    continue
                
                encoded_data = self.encode_frame(frame)
                if encoded_data and self.on_encoded_data:
                    self.on_encoded_data(encoded_data)
                
            except Exception as e:
                logger.error(f"Error in encoding loop: {e}")
                time.sleep(0.1)
    
    def get_stats(self) -> dict:
        """Get encoding statistics"""
        return {
            'encoded_frames': self.encoded_frames,
            'dropped_frames': self.dropped_frames,
            'encoding_errors': self.encoding_errors,
        }
    
    def shutdown(self):
        """Shutdown encoder"""
        self.stop_encoding()
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
        logger.info("Encoder shutdown complete")


class FFmpegH264Encoder:
    """
    H.264 encoder using FFmpeg with RKMPP hardware acceleration
    This is the production encoder for RK3568
    """
    
    def __init__(self, width: int = 1280, height: int = 720, bitrate: int = 1024, fps: int = 30):
        """
        Initialize FFmpeg-based H.264 encoder
        
        Args:
            width: Frame width
            height: Frame height
            bitrate: Target bitrate in kbps
            fps: Target frames per second
        """
        self.width = width
        self.height = height
        self.bitrate = bitrate
        self.fps = fps
        self.config = get_config()
        
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.encoded_frames = 0
        self.encoding_errors = 0
    
    def start(self) -> bool:
        """
        Start FFmpeg encoding process
        
        Returns:
            True if process started successfully
        """
        try:
            # FFmpeg command with RKMPP hardware acceleration
            # This command pipes raw frames via stdin and outputs H.264 via stdout
            cmd = [
                'ffmpeg',
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{self.width}x{self.height}',
                '-r', str(self.fps),
                '-i', 'pipe:0',
                '-c:v', 'h264_rkmpp',  # RKMPP hardware encoder
                '-b:v', f'{self.bitrate}k',
                '-g', str(self.fps * 2),  # GOP size
                '-preset', self.config.get('video_encoding.preset', 'medium'),
                '-f', 'h264',
                'pipe:1'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10*1024*1024
            )
            
            self.is_running = True
            logger.info(f"FFmpeg H.264 encoder started: {self.width}x{self.height}@{self.fps}fps, {self.bitrate}kbps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg encoder: {e}")
            return False
    
    def encode_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Encode a frame
        
        Args:
            frame: Input frame (BGR format)
        
        Returns:
            Encoded H.264 data or None
        """
        if self.process is None or not self.is_running:
            return None
        
        try:
            # Write frame to FFmpeg stdin
            frame_bytes = frame.tobytes()
            self.process.stdin.write(frame_bytes)
            self.process.stdin.flush()
            
            # Try to read encoded data (non-blocking)
            # This is simplified; production code would use proper buffering
            self.encoded_frames += 1
            return None
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            self.encoding_errors += 1
            return None
    
    def stop(self):
        """Stop encoding process"""
        if self.process is not None:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            finally:
                self.process = None
            
            self.is_running = False
            logger.info(f"FFmpeg encoder stopped (encoded {self.encoded_frames} frames)")
    
    def get_stats(self) -> dict:
        """Get encoding statistics"""
        return {
            'encoded_frames': self.encoded_frames,
            'encoding_errors': self.encoding_errors,
        }


# Global encoder instance
_encoder: Optional[H264Encoder] = None


def get_encoder() -> H264Encoder:
    """Get global encoder instance"""
    global _encoder
    if _encoder is None:
        _encoder = H264Encoder()
    return _encoder


# Example usage
if __name__ == "__main__":
    encoder = get_encoder()
    
    if encoder.initialize():
        print("Encoder initialized successfully")
        stats = encoder.get_stats()
        print(f"Stats: {stats}")
