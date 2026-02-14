# ST3215 Bus Manager - Shared Serial Connection Handler
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging
import threading
import time


class ST3215BusError(Exception):
    """Exception raised for ST3215 bus communication errors"""

    pass


class ST3215Bus:
    """
    Manages shared serial bus connection to ST3215 servos.

    Implements singleton pattern per serial port to ensure multiple servo
    instances can share the same serial connection without conflicts.
    """

    # Class-level registry of bus instances (one per serial port)
    _instances = {}
    _instances_lock = threading.Lock()

    def __init__(self, serial_port, baudrate=1000000):
        """
        Private constructor - use get_instance() instead.

        Args:
            serial_port: Serial port device path (e.g., '/dev/ttyUSB0')
            baudrate: Serial communication baudrate (default: 1000000)
        """
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.st3215 = None
        self.connected = False
        self.lock = threading.Lock()
        self.last_error = None
        self.reconnect_attempt = 0
        self.max_reconnect_attempts = 3

        # Cache for servo positions (fallback when connection fails)
        self._position_cache = {}

        logging.info(f"ST3215Bus: Initialized for {serial_port} @ {baudrate} baud")

    @classmethod
    def get_instance(cls, serial_port, baudrate=1000000):
        """
        Get or create singleton bus instance for the given serial port.

        Args:
            serial_port: Serial port device path
            baudrate: Serial communication baudrate

        Returns:
            ST3215Bus instance for the specified port
        """
        with cls._instances_lock:
            key = (serial_port, baudrate)
            if key not in cls._instances:
                cls._instances[key] = cls(serial_port, baudrate)
            return cls._instances[key]

    def connect(self):
        """
        Establish serial connection to ST3215 bus.

        Raises:
            ST3215BusError: If connection fails
        """
        with self.lock:
            if self.connected:
                return

            try:
                # Import ST3215 library
                import st3215

                # Create ST3215 instance
                self.st3215 = st3215.ST3215(self.serial_port)
                self.connected = True
                self.reconnect_attempt = 0
                self.last_error = None

                logging.info(f"ST3215Bus: Connected to {self.serial_port}")

            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                error_msg = f"Failed to connect to {self.serial_port}: {e}"
                logging.error(f"ST3215Bus: {error_msg}")
                raise ST3215BusError(error_msg)

    def disconnect(self):
        """Close serial connection to ST3215 bus."""
        with self.lock:
            if self.st3215 is not None:
                try:
                    if hasattr(self.st3215, "portHandler"):
                        self.st3215.portHandler.closePort()
                except:
                    pass  # Best effort

                self.st3215 = None
                self.connected = False
                logging.info(f"ST3215Bus: Disconnected from {self.serial_port}")

    def _execute_with_retry(self, operation_name, func, *args, **kwargs):
        """
        Execute a function with automatic retry on communication failure.

        Args:
            operation_name: Name of operation (for logging)
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result from function execution

        Raises:
            ST3215BusError: If operation fails after retries
        """
        max_retries = kwargs.pop("max_retries", 3)

        for attempt in range(max_retries):
            try:
                if not self.connected:
                    self.connect()

                result = func(*args, **kwargs)

                # Reset reconnect counter on success
                if self.reconnect_attempt > 0:
                    logging.info(
                        f"ST3215Bus: {operation_name} succeeded after reconnect"
                    )
                    self.reconnect_attempt = 0

                return result

            except Exception as e:
                self.last_error = str(e)

                if attempt < max_retries - 1:
                    logging.warning(
                        f"ST3215Bus: {operation_name} failed (attempt {attempt + 1}/"
                        f"{max_retries}): {e}"
                    )

                    # Try reconnecting
                    try:
                        self.disconnect()
                        time.sleep(0.5)
                        self.connect()
                        self.reconnect_attempt += 1
                    except:
                        pass  # Will retry on next iteration
                else:
                    error_msg = (
                        f"{operation_name} failed after {max_retries} attempts: {e}"
                    )
                    logging.error(f"ST3215Bus: {error_msg}")
                    raise ST3215BusError(error_msg)

    def ping_servo(self, servo_id):
        """
        Check if servo is present on the bus.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            True if servo responds, False otherwise
        """
        with self.lock:
            try:
                if not self.connected:
                    self.connect()

                return self.st3215.PingServo(servo_id)

            except Exception as e:
                logging.error(f"ST3215Bus: Failed to ping servo {servo_id}: {e}")
                return False

    def list_servos(self):
        """
        Scan bus for all servos present.

        Returns:
            List of servo IDs found on the bus
        """
        with self.lock:
            try:
                if not self.connected:
                    self.connect()

                return self.st3215.ListServos()

            except Exception as e:
                logging.error(f"ST3215Bus: Failed to list servos: {e}")
                return []

    def move_to(self, servo_id, position, speed, acceleration):
        """
        Move servo to absolute position.

        Args:
            servo_id: Servo ID (0-253)
            position: Target position (0-4095)
            speed: Movement speed (0-3400)
            acceleration: Acceleration (0-254)

        Raises:
            ST3215BusError: If move command fails
        """

        def _move():
            self.st3215.MoveTo(servo_id, position, speed, acceleration)

        self._execute_with_retry(f"MoveTo(servo={servo_id}, pos={position})", _move)

        # Update position cache
        self._position_cache[servo_id] = position

    def read_position(self, servo_id):
        """
        Read current servo position.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            Current position (0-4095) or None if read fails
        """

        def _read():
            return self.st3215.ReadPosition(servo_id)

        try:
            pos = self._execute_with_retry(f"ReadPosition(servo={servo_id})", _read)

            if pos is not None:
                self._position_cache[servo_id] = pos

            return pos

        except ST3215BusError:
            # Return cached position if available
            cached = self._position_cache.get(servo_id)
            if cached is not None:
                logging.warning(
                    f"ST3215Bus: Using cached position for servo {servo_id}: {cached}"
                )
            return cached

    def read_temperature(self, servo_id):
        """
        Read servo temperature.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            Temperature in °C or None if read fails
        """

        def _read():
            return self.st3215.ReadTemperature(servo_id)

        with self.lock:
            try:
                if not self.connected:
                    self.connect()
                return _read()
            except Exception as e:
                logging.debug(f"ST3215Bus: Failed to read temperature: {e}")
                return None

    def read_voltage(self, servo_id):
        """
        Read servo voltage.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            Voltage in V or None if read fails
        """

        def _read():
            return self.st3215.ReadVoltage(servo_id)

        with self.lock:
            try:
                if not self.connected:
                    self.connect()
                return _read()
            except Exception as e:
                logging.debug(f"ST3215Bus: Failed to read voltage: {e}")
                return None

    def read_current(self, servo_id):
        """
        Read servo current.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            Current in mA or None if read fails
        """

        def _read():
            return self.st3215.ReadCurrent(servo_id)

        with self.lock:
            try:
                if not self.connected:
                    self.connect()
                return _read()
            except Exception as e:
                logging.debug(f"ST3215Bus: Failed to read current: {e}")
                return None

    def read_status(self, servo_id):
        """
        Read all status values from servo.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            Dictionary with 'temperature', 'voltage', 'current' keys
        """
        status = {
            "temperature": self.read_temperature(servo_id),
            "voltage": self.read_voltage(servo_id),
            "current": self.read_current(servo_id),
        }
        return status

    def enable_servo(self, servo_id):
        """
        Enable servo motor (allows movement).

        Args:
            servo_id: Servo ID (0-253)

        Raises:
            ST3215BusError: If enable command fails
        """

        def _enable():
            self.st3215.StartServo(servo_id)

        self._execute_with_retry(f"StartServo(servo={servo_id})", _enable)

    def disable_servo(self, servo_id):
        """
        Disable servo motor (free to move manually).

        Args:
            servo_id: Servo ID (0-253)

        Raises:
            ST3215BusError: If disable command fails
        """

        def _disable():
            self.st3215.StopServo(servo_id)

        self._execute_with_retry(f"StopServo(servo={servo_id})", _disable)

    def is_moving(self, servo_id):
        """
        Check if servo is currently moving.

        Args:
            servo_id: Servo ID (0-253)

        Returns:
            True if moving, False otherwise
        """

        def _check():
            return self.st3215.IsMoving(servo_id)

        with self.lock:
            try:
                if not self.connected:
                    self.connect()
                return _check()
            except Exception as e:
                logging.debug(f"ST3215Bus: Failed to check if moving: {e}")
                return False

    def set_speed(self, servo_id, speed):
        """
        Set servo maximum speed.

        Args:
            servo_id: Servo ID (0-253)
            speed: Maximum speed (0-3400)

        Raises:
            ST3215BusError: If command fails
        """

        def _set():
            self.st3215.SetSpeed(servo_id, speed)

        self._execute_with_retry(f"SetSpeed(servo={servo_id}, speed={speed})", _set)

    def set_acceleration(self, servo_id, acceleration):
        """
        Set servo acceleration.

        Args:
            servo_id: Servo ID (0-253)
            acceleration: Acceleration (0-254)

        Raises:
            ST3215BusError: If command fails
        """

        def _set():
            self.st3215.SetAcceleration(servo_id, acceleration)

        self._execute_with_retry(
            f"SetAcceleration(servo={servo_id}, accel={acceleration})", _set
        )
