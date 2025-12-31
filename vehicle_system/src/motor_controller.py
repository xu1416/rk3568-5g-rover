"""
Motor Controller Module for RK3568 Rover
Handles communication with balance car motor driver board
"""

import serial
import threading
import time
from typing import Optional, Tuple
from enum import Enum
from logger import get_logger
from config_manager import get_config

logger = get_logger(__name__)


class MotorDirection(Enum):
    """Motor direction enumeration"""
    FORWARD = 1
    BACKWARD = 2
    LEFT = 3
    RIGHT = 4
    STOP = 0


class MotorController:
    """Controls motor via balance car driver board"""
    
    def __init__(self):
        """Initialize motor controller"""
        self.config = get_config()
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.is_running = False
        self.command_thread: Optional[threading.Thread] = None
        
        # Motor state
        self.left_speed = 0
        self.right_speed = 0
        self.current_direction = MotorDirection.STOP
        
        # Statistics
        self.commands_sent = 0
        self.command_errors = 0
        self.last_command_time = 0
        
        # Command queue for thread-safe communication
        self.command_queue = []
        self.queue_lock = threading.Lock()
    
    def connect(self) -> bool:
        """
        Connect to motor driver via serial port
        
        Returns:
            True if connection successful
        """
        try:
            motor_config = self.config.get_section('motor_control')
            serial_config = motor_config.get('serial', {})
            
            port = serial_config.get('port', '/dev/ttyUSB0')
            baudrate = serial_config.get('baudrate', 115200)
            timeout = serial_config.get('timeout', 1.0)
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            self.is_connected = True
            logger.info(f"Connected to motor driver at {port} ({baudrate} baud)")
            
            # Start command processing thread
            self.is_running = True
            self.command_thread = threading.Thread(target=self._command_loop, daemon=True)\n            self.command_thread.start()
            
            return True
            
        except serial.SerialException as e:
            logger.error(f"Failed to connect to motor driver: {e}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to motor driver: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from motor driver"""
        self.is_running = False
        
        if self.command_thread is not None:
            self.command_thread.join(timeout=5)
        
        if self.serial_port is not None:
            try:
                self.serial_port.close()
            except:
                pass
        
        self.is_connected = False
        logger.info("Disconnected from motor driver")
    
    def move_forward(self, speed: int = 200):
        """
        Move rover forward
        
        Args:
            speed: Speed value (0-255)
        """
        speed = max(0, min(255, speed))
        self.left_speed = speed
        self.right_speed = speed
        self.current_direction = MotorDirection.FORWARD
        self._send_motor_command(speed, speed)
    
    def move_backward(self, speed: int = 200):
        """
        Move rover backward
        
        Args:
            speed: Speed value (0-255)
        """
        speed = max(0, min(255, speed))
        self.left_speed = -speed
        self.right_speed = -speed
        self.current_direction = MotorDirection.BACKWARD
        self._send_motor_command(-speed, -speed)
    
    def turn_left(self, speed: int = 150):
        """
        Turn rover left
        
        Args:
            speed: Speed value (0-255)
        """
        speed = max(0, min(255, speed))
        self.left_speed = speed // 2
        self.right_speed = speed
        self.current_direction = MotorDirection.LEFT
        self._send_motor_command(speed // 2, speed)
    
    def turn_right(self, speed: int = 150):
        """
        Turn rover right
        
        Args:
            speed: Speed value (0-255)
        """
        speed = max(0, min(255, speed))
        self.left_speed = speed
        self.right_speed = speed // 2
        self.current_direction = MotorDirection.RIGHT
        self._send_motor_command(speed, speed // 2)
    
    def stop(self):
        """Stop rover"""
        self.left_speed = 0
        self.right_speed = 0
        self.current_direction = MotorDirection.STOP
        self._send_motor_command(0, 0)
    
    def set_motor_speed(self, left_speed: int, right_speed: int):
        """
        Set individual motor speeds
        
        Args:
            left_speed: Left motor speed (-255 to 255)
            right_speed: Right motor speed (-255 to 255)
        """
        left_speed = max(-255, min(255, left_speed))
        right_speed = max(-255, min(255, right_speed))
        
        self.left_speed = left_speed
        self.right_speed = right_speed
        
        self._send_motor_command(left_speed, right_speed)
    
    def _send_motor_command(self, left_speed: int, right_speed: int):
        """
        Send motor command to driver board
        
        Args:
            left_speed: Left motor speed
            right_speed: Right motor speed
        """
        if not self.is_connected:
            return
        
        # Queue command for thread-safe transmission
        with self.queue_lock:
            self.command_queue.append((left_speed, right_speed))
    
    def _command_loop(self):
        """Main command processing loop"""
        while self.is_running:
            try:
                with self.queue_lock:
                    if self.command_queue:
                        left_speed, right_speed = self.command_queue.pop(0)
                    else:
                        left_speed = right_speed = None
                
                if left_speed is not None and right_speed is not None:
                    self._transmit_command(left_speed, right_speed)
                
                time.sleep(0.01)  # 100Hz command rate
                
            except Exception as e:
                logger.error(f"Error in command loop: {e}")
                time.sleep(0.1)
    
    def _transmit_command(self, left_speed: int, right_speed: int):
        \"\"\"
        Transmit motor command to driver board via serial
        
        Protocol (example for balance car):
        Frame format: [0xAA, 0x55, left_speed, right_speed, checksum]
        
        Args:
            left_speed: Left motor speed (-255 to 255)
            right_speed: Right motor speed (-255 to 255)
        \"\"\"
        if not self.is_connected or self.serial_port is None:
            return
        
        try:
            # Convert signed speeds to unsigned bytes
            left_byte = self._speed_to_byte(left_speed)
            right_byte = self._speed_to_byte(right_speed)
            
            # Build command frame
            # This is a generic protocol; adjust based on your specific driver board
            frame = bytearray([0xAA, 0x55, left_byte, right_byte])
            
            # Calculate checksum (simple XOR)
            checksum = 0
            for byte in frame:
                checksum ^= byte
            frame.append(checksum)
            
            # Send command
            self.serial_port.write(frame)
            self.commands_sent += 1
            self.last_command_time = time.time()
            
        except Exception as e:
            logger.error(f"Error transmitting motor command: {e}")
            self.command_errors += 1
    
    @staticmethod
    def _speed_to_byte(speed: int) -> int:
        \"\"\"
        Convert signed speed (-255 to 255) to unsigned byte
        
        Args:
            speed: Speed value
        
        Returns:
            Unsigned byte representation
        \"\"\"
        if speed >= 0:
            return min(255, speed)
        else:
            return 256 + speed  # Two's complement
    
    def emergency_stop(self):
        \"\"\"Emergency stop - immediately halt all motors\"\"\"
        logger.warning("EMERGENCY STOP activated")
        self.stop()
    
    def get_status(self) -> dict:
        \"\"\"Get motor controller status\"\"\"
        return {
            'is_connected': self.is_connected,
            'left_speed': self.left_speed,
            'right_speed': self.right_speed,
            'current_direction': self.current_direction.name,
            'commands_sent': self.commands_sent,
            'command_errors': self.command_errors,
            'last_command_time': self.last_command_time,
        }
    
    def shutdown(self):
        \"\"\"Shutdown motor controller\"\"\"
        self.emergency_stop()
        self.disconnect()
        logger.info("Motor controller shutdown complete")


# Global motor controller instance
_motor_controller: Optional[MotorController] = None


def get_motor_controller() -> MotorController:
    \"\"\"Get global motor controller instance\"\"\"
    global _motor_controller
    if _motor_controller is None:
        _motor_controller = MotorController()
    return _motor_controller


# Example usage
if __name__ == "__main__":
    controller = get_motor_controller()
    
    if controller.connect():
        try:
            # Test movements
            print("Moving forward...")
            controller.move_forward(200)
            time.sleep(2)
            
            print("Turning left...")
            controller.turn_left(150)
            time.sleep(2)
            
            print("Stopping...")
            controller.stop()
            
            print("Status:", controller.get_status())
            
        finally:
            controller.shutdown()
