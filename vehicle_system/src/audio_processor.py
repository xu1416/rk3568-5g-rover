"""
Audio Processing Module for RK3568 Rover
Handles microphone input, speaker output, and Opus encoding/decoding
"""

import threading
import numpy as np
from typing import Optional, Callable
from collections import deque
from logger import get_logger
from config_manager import get_config

logger = get_logger(__name__)


class AudioProcessor:
    """Handles audio capture and playback"""
    
    def __init__(self):
        """Initialize audio processor"""
        self.config = get_config()
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.playback_thread: Optional[threading.Thread] = None
        
        # Audio buffers
        self.capture_buffer = deque(maxlen=10)
        self.playback_buffer = deque(maxlen=10)
        
        # Callbacks
        self.on_audio_frame: Optional[Callable] = None
        
        # Statistics
        self.captured_frames = 0
        self.playback_frames = 0
        self.capture_errors = 0
        self.playback_errors = 0
        
        # Audio parameters
        self.sample_rate = self.config.get('audio.microphone.sample_rate', 16000)
        self.channels = self.config.get('audio.microphone.channels', 1)
        self.chunk_size = self.config.get('audio.microphone.chunk_size', 1024)
        
        # PyAudio objects (lazy initialized)
        self.p_audio = None
        self.stream_in = None
        self.stream_out = None
    
    def initialize(self) -> bool:
        """
        Initialize audio system
        
        Returns:
            True if initialization successful
        """
        try:
            import pyaudio
            
            self.p_audio = pyaudio.PyAudio()
            
            # Initialize input stream
            if self.config.get('audio.microphone.enabled', True):
                self.stream_in = self.p_audio.open(
                    format=pyaudio.paFloat32,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    input_device_index=self.config.get('audio.microphone.device_index', 0)
                )
                logger.info(f"Audio input initialized: {self.sample_rate}Hz, {self.channels}ch")
            
            # Initialize output stream
            if self.config.get('audio.speaker.enabled', True):
                self.stream_out = self.p_audio.open(
                    format=pyaudio.paFloat32,
                    channels=self.channels,
                    rate=self.sample_rate,
                    output=True,
                    frames_per_buffer=self.chunk_size,
                    output_device_index=self.config.get('audio.speaker.device_index', 0)
                )
                logger.info(f"Audio output initialized: {self.sample_rate}Hz, {self.channels}ch")
            
            return True
            
        except ImportError:
            logger.error("PyAudio not installed. Install with: pip install pyaudio")
            return False
        except Exception as e:
            logger.error(f"Error initializing audio: {e}")
            return False
    
    def start_capture(self):
        """Start audio capture"""
        if self.is_running:
            logger.warning("Audio capture already running")
            return
        
        if self.stream_in is None:
            logger.error("Audio input stream not initialized")
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info("Audio capture started")
    
    def stop_capture(self):
        """Stop audio capture"""
        self.is_running = False
        if self.capture_thread is not None:
            self.capture_thread.join(timeout=5)
        logger.info("Audio capture stopped")
    
    def _capture_loop(self):
        """Main audio capture loop"""
        import time
        
        while self.is_running:
            try:
                if self.stream_in is None:
                    time.sleep(0.01)
                    continue
                
                # Read audio frame
                audio_data = self.stream_in.read(self.chunk_size, exception_on_overflow=False)
                audio_frame = np.frombuffer(audio_data, dtype=np.float32)
                
                self.capture_buffer.append(audio_frame)
                self.captured_frames += 1
                
                # Call callback if set
                if self.on_audio_frame:
                    self.on_audio_frame(audio_frame)
                
            except Exception as e:
                logger.error(f"Error capturing audio: {e}")
                self.capture_errors += 1
                time.sleep(0.01)
    
    def play_audio(self, audio_frame: np.ndarray):
        """
        Play audio frame
        
        Args:
            audio_frame: Audio data as numpy array
        """
        if self.stream_out is None:
            logger.warning("Audio output stream not initialized")
            return
        
        try:
            self.playback_buffer.append(audio_frame)
            self.playback_frames += 1
        except Exception as e:
            logger.error(f"Error buffering audio for playback: {e}")
            self.playback_errors += 1
    
    def start_playback(self):
        """Start audio playback from buffer"""
        if self.playback_thread is not None:
            logger.warning("Audio playback already running")
            return
        
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()
        logger.info("Audio playback started")
    
    def stop_playback(self):
        """Stop audio playback"""
        if self.playback_thread is not None:
            self.playback_thread.join(timeout=5)
            self.playback_thread = None
        logger.info("Audio playback stopped")
    
    def _playback_loop(self):
        """Main audio playback loop"""
        import time
        
        while True:
            try:
                if self.playback_buffer:
                    audio_frame = self.playback_buffer.popleft()
                    if self.stream_out is not None:
                        self.stream_out.write(audio_frame.astype(np.float32).tobytes())
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                self.playback_errors += 1
                time.sleep(0.01)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest captured audio frame"""
        if self.capture_buffer:
            return self.capture_buffer[-1]
        return None
    
    def set_audio_callback(self, callback: Callable):
        """Set callback for audio frames"""
        self.on_audio_frame = callback
    
    def get_stats(self) -> dict:
        """Get audio statistics"""
        return {
            'captured_frames': self.captured_frames,
            'playback_frames': self.playback_frames,
            'capture_errors': self.capture_errors,
            'playback_errors': self.playback_errors,
            'capture_buffer_size': len(self.capture_buffer),
            'playback_buffer_size': len(self.playback_buffer),
        }
    
    def shutdown(self):
        """Shutdown audio system"""
        self.stop_capture()
        self.stop_playback()
        
        if self.stream_in is not None:
            self.stream_in.stop_stream()
            self.stream_in.close()
        
        if self.stream_out is not None:
            self.stream_out.stop_stream()
            self.stream_out.close()
        
        if self.p_audio is not None:
            self.p_audio.terminate()
        
        logger.info("Audio processor shutdown complete")


class OpusAudioCodec:
    """Opus audio codec for encoding/decoding"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, bitrate: int = 24):
        """
        Initialize Opus codec
        
        Args:
            sample_rate: Sample rate in Hz
            channels: Number of channels
            bitrate: Bitrate in kbps
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate
        self.encoder = None
        self.decoder = None
        
        self._initialize_codec()
    
    def _initialize_codec(self):
        """Initialize Opus encoder/decoder"""
        try:
            import opuslib
            
            self.encoder = opuslib.Encoder(self.sample_rate, self.channels, opuslib.APPLICATION_VOIP)
            self.encoder.set_bitrate(self.bitrate * 1000)
            
            self.decoder = opuslib.Decoder(self.sample_rate, self.channels)
            
            logger.info(f"Opus codec initialized: {self.sample_rate}Hz, {self.channels}ch, {self.bitrate}kbps")
            
        except ImportError:
            logger.warning("opuslib not installed. Audio encoding will be disabled.")
            logger.info("Install with: pip install opuslib")
    
    def encode(self, audio_frame: np.ndarray) -> Optional[bytes]:
        """
        Encode audio frame to Opus
        
        Args:
            audio_frame: Audio data as numpy array
        
        Returns:
            Encoded Opus data or None
        """
        if self.encoder is None:
            return None
        
        try:
            # Convert to int16 if needed
            if audio_frame.dtype != np.int16:
                audio_frame = (audio_frame * 32767).astype(np.int16)
            
            encoded_data = self.encoder.encode(audio_frame.tobytes(), len(audio_frame))
            return encoded_data
            
        except Exception as e:
            logger.error(f"Error encoding audio: {e}")
            return None
    
    def decode(self, encoded_data: bytes) -> Optional[np.ndarray]:
        """
        Decode Opus data to audio frame
        
        Args:
            encoded_data: Encoded Opus data
        
        Returns:
            Decoded audio frame or None
        """
        if self.decoder is None:
            return None
        
        try:
            decoded_data = self.decoder.decode(encoded_data, len(encoded_data) * 4)
            audio_frame = np.frombuffer(decoded_data, dtype=np.int16)
            return audio_frame.astype(np.float32) / 32767.0
            
        except Exception as e:
            logger.error(f"Error decoding audio: {e}")
            return None


# Global audio processor instance
_audio_processor: Optional[AudioProcessor] = None


def get_audio_processor() -> AudioProcessor:
    """Get global audio processor instance"""
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor()
    return _audio_processor


# Example usage
if __name__ == "__main__":
    import time
    
    processor = get_audio_processor()
    
    if processor.initialize():
        processor.start_capture()
        processor.start_playback()
        
        try:
            for _ in range(10):
                stats = processor.get_stats()
                print(f"Captured: {stats['captured_frames']}, Playback: {stats['playback_frames']}")
                time.sleep(1)
        finally:
            processor.shutdown()
