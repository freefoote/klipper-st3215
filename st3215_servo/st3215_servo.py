# ST3215 Servo Controller - Individual Servo Instance Management
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging

from .st3215_bus import ST3215Bus, ST3215BusError


class ST3215Servo:
    """
    Individual ST3215 servo instance controller.

    Manages a single servo on the ST3215 bus, including configuration,
    position tracking, safety checks, and status reporting.
    """

    def __init__(self, config):
        """
        Initialize servo from Klipper configuration.

        Args:
            config: Klipper ConfigWrapper object
        """
        self.printer = config.get_printer()
        self.name = config.get_name()

        # Parse required parameters
        self.servo_id = config.getint("servo_id", minval=0, maxval=253)
        serial = config.get("serial")

        # Parse optional parameters
        baudrate = config.getint("baudrate", 1000000)
        self.position_min = config.getint("position_min", 0, minval=0, maxval=4095)
        self.position_max = config.getint("position_max", 4095, minval=0, maxval=4095)
        self.max_speed = config.getint("max_speed", 3400, minval=0, maxval=3400)
        self.max_accel = config.getint("max_acceleration", 254, minval=0, maxval=254)
        self.initial_position = config.getint(
            "initial_position", None, minval=self.position_min, maxval=self.position_max
        )
        self.status_update_interval = config.getfloat(
            "status_update_interval", 1.0, minval=0.1, maxval=10.0
        )
        self.temperature_warning = config.getint(
            "temperature_warning", 70, minval=0, maxval=100
        )
        self.temperature_critical = config.getint(
            "temperature_critical", 85, minval=0, maxval=100
        )

        # Validate configuration
        if self.position_min >= self.position_max:
            raise config.error(
                f"position_min ({self.position_min}) must be less than "
                f"position_max ({self.position_max})"
            )

        if self.temperature_warning >= self.temperature_critical:
            raise config.error(
                f"temperature_warning ({self.temperature_warning}) must be less than "
                f"temperature_critical ({self.temperature_critical})"
            )

        # Get or create shared bus instance
        self.bus = ST3215Bus.get_instance(serial, baudrate)

        # State tracking
        self.current_position = None
        self.target_position = None
        self.is_moving = False
        self.enabled = False

        # Status cache (updated periodically)
        self.last_status_update = 0
        self.cached_temperature = None
        self.cached_current = None
        self.cached_voltage = None
        self.last_error = None

        # Timer for status updates
        self.status_timer = None

        # Register event handlers
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
        self.printer.register_event_handler("klippy:ready", self._handle_ready)
        self.printer.register_event_handler("klippy:shutdown", self._handle_shutdown)

        # Register commands
        self._register_commands()

        logging.info(
            f"ST3215Servo: Initialized {self.name} "
            f"(ID={self.servo_id}, range={self.position_min}-{self.position_max})"
        )

    def _register_commands(self):
        """Register G-code commands for this servo."""
        gcode = self.printer.lookup_object("gcode")
        servo_name = self.name.split()[1]  # Extract name after 'st3215'

        # Register commands with servo name as MUX parameter
        # Primary (new) command names
        gcode.register_mux_command(
            "STSERVO_MOVE",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_MOVE,
            desc=self.cmd_STSERVO_MOVE_help,
        )

        gcode.register_mux_command(
            "STSERVO_STOP",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_STOP,
            desc=self.cmd_STSERVO_STOP_help,
        )

        gcode.register_mux_command(
            "STSERVO_ENABLE",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_ENABLE,
            desc=self.cmd_STSERVO_ENABLE_help,
        )

        gcode.register_mux_command(
            "STSERVO_DISABLE",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_DISABLE,
            desc=self.cmd_STSERVO_DISABLE_help,
        )

        gcode.register_mux_command(
            "STSERVO_SET_POSITION",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_SET_POSITION,
            desc=self.cmd_STSERVO_SET_POSITION_help,
        )

        gcode.register_mux_command(
            "STSERVO_STATUS",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_STATUS,
            desc=self.cmd_STSERVO_STATUS_help,
        )

        # Backwards-compatible ST3215_* aliases (map to same handlers)
        # These allow existing configs/examples that use ST3215_* to work.
        gcode.register_mux_command(
            "ST3215_MOVE",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_MOVE,
            desc=self.cmd_STSERVO_MOVE_help,
        )

        gcode.register_mux_command(
            "ST3215_STOP",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_STOP,
            desc=self.cmd_STSERVO_STOP_help,
        )

        gcode.register_mux_command(
            "ST3215_ENABLE",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_ENABLE,
            desc=self.cmd_STSERVO_ENABLE_help,
        )

        gcode.register_mux_command(
            "ST3215_DISABLE",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_DISABLE,
            desc=self.cmd_STSERVO_DISABLE_help,
        )

        gcode.register_mux_command(
            "ST3215_SET_POSITION",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_SET_POSITION,
            desc=self.cmd_STSERVO_SET_POSITION_help,
        )

        gcode.register_mux_command(
            "ST3215_STATUS",
            "SERVO",
            servo_name,
            self.cmd_STSERVO_STATUS,
            desc=self.cmd_STSERVO_STATUS_help,
        )

    def _handle_connect(self):
        """Called when Klipper connects to MCU."""
        try:
            # Connect to bus
            self.bus.connect()

            # Verify servo presence
            if not self.bus.ping_servo(self.servo_id):
                raise self.printer.command_error(
                    f"Servo ID {self.servo_id} not found on {self.bus.serial_port}"
                )

            logging.info(f"ST3215Servo: {self.name} detected on bus")

            # Read initial position
            pos = self.bus.read_position(self.servo_id)
            if pos is not None:
                self.current_position = pos
                self.target_position = pos
                logging.info(f"ST3215Servo: {self.name} initial position: {pos}")

        except Exception as e:
            raise self.printer.command_error(f"Failed to initialize {self.name}: {e}")

    def _handle_ready(self):
        """Called when Klipper is ready."""
        # Move to initial position if configured
        if self.initial_position is not None:
            try:
                logging.info(
                    f"ST3215Servo: Moving {self.name} to initial position "
                    f"{self.initial_position}"
                )
                self.enable()
                self.move_to(self.initial_position)
            except Exception as e:
                logging.error(f"ST3215Servo: Failed to move to initial position: {e}")

        # Start status update timer
        reactor = self.printer.get_reactor()
        self.status_timer = reactor.register_timer(
            self._update_status_timer, reactor.NOW
        )

    def _handle_shutdown(self):
        """Called on Klipper shutdown."""
        try:
            # Disable servo on shutdown (best effort)
            self.disable()
            logging.info(f"ST3215Servo: {self.name} disabled on shutdown")
        except:
            pass  # Best effort during shutdown

    def _validate_position(self, position):
        """
        Validate position is within configured limits.

        Args:
            position: Position to validate (0-4095)

        Returns:
            Validated position

        Raises:
            ValueError: If position is out of range
        """
        if position < self.position_min:
            raise ValueError(f"Position {position} below minimum {self.position_min}")
        if position > self.position_max:
            raise ValueError(f"Position {position} above maximum {self.position_max}")
        return position

    def _check_temperature(self):
        """
        Check temperature and warn/shutdown if necessary.

        Raises:
            Exception: If temperature is critical
        """
        if self.cached_temperature is None:
            return

        if self.cached_temperature >= self.temperature_critical:
            # Critical temperature - invoke shutdown
            msg = (
                f"ST3215 {self.name} temperature critical: {self.cached_temperature}°C"
            )
            logging.error(msg)
            self.printer.invoke_shutdown(msg)
            raise Exception(msg)

        elif self.cached_temperature >= self.temperature_warning:
            # Warning temperature
            logging.warning(
                f"ST3215 {self.name} temperature high: {self.cached_temperature}°C"
            )

    def move_to(self, position, speed=None, accel=None):
        """
        Move servo to absolute position.

        Args:
            position: Target position (0-4095)
            speed: Movement speed (0-3400), uses max_speed if None
            accel: Acceleration (0-254), uses max_accel if None

        Raises:
            ValueError: If position is out of range
            ST3215BusError: If move command fails
        """
        # Validate position
        position = self._validate_position(position)

        # Check temperature before moving
        self._check_temperature()

        # Use defaults if not specified
        if speed is None:
            speed = self.max_speed
        if accel is None:
            accel = self.max_accel

        # Clamp speed and accel to valid ranges
        speed = max(0, min(3400, speed))
        accel = max(0, min(254, accel))

        # Execute move
        self.bus.move_to(self.servo_id, position, speed, accel)

        # Update state
        self.target_position = position
        self.is_moving = True

        logging.info(
            f"ST3215Servo: {self.name} moving to {position} "
            f"(speed={speed}, accel={accel})"
        )

    def stop(self):
        """
        Stop servo movement immediately.

        Note: This reads current position and commands servo to stay there.
        Not a true emergency stop.
        """
        # Read current position
        pos = self.bus.read_position(self.servo_id)
        if pos is not None:
            self.current_position = pos
            # Command to stay at current position
            self.bus.move_to(self.servo_id, pos, 0, 0)
            self.target_position = pos
            self.is_moving = False
            logging.info(f"ST3215Servo: {self.name} stopped at position {pos}")

    def enable(self):
        """Enable servo motor (allows movement)."""
        self.bus.enable_servo(self.servo_id)
        self.enabled = True
        logging.info(f"ST3215Servo: {self.name} enabled")

    def disable(self):
        """Disable servo motor (free to move manually)."""
        self.bus.disable_servo(self.servo_id)
        self.enabled = False
        self.is_moving = False
        logging.info(f"ST3215Servo: {self.name} disabled")

    def set_position(self, position):
        """
        Set current position without moving (for homing/zeroing).

        Args:
            position: New position value

        Note: This is a logical operation only - doesn't send commands to servo.
        """
        position = self._validate_position(position)
        self.current_position = position
        self.target_position = position
        logging.info(f"ST3215Servo: {self.name} position set to {position}")

    def get_status(self, eventtime):
        """
        Return status dictionary for Klipper's object system.

        Called by Moonraker and other subsystems to query servo state.

        Args:
            eventtime: Current event time

        Returns:
            Dictionary with status information
        """
        return {
            "position": self.current_position,
            "target_position": self.target_position,
            "is_moving": self.is_moving,
            "temperature": self.cached_temperature,
            "current": self.cached_current,
            "voltage": self.cached_voltage,
            "enabled": self.enabled,
            "last_error": self.last_error,
        }

    def get_current_status(self):
        """
        Get current status (for command responses).

        Returns:
            Status dictionary
        """
        return self.get_status(0)

    def _update_status_timer(self, eventtime):
        """
        Periodic status update callback (runs in reactor context).

        Args:
            eventtime: Current event time

        Returns:
            Next callback time
        """
        try:
            # Read current position (frequent)
            pos = self.bus.read_position(self.servo_id)
            if pos is not None:
                self.current_position = pos

                # Update is_moving based on position vs target
                if self.target_position is not None:
                    self.is_moving = abs(pos - self.target_position) > 5

            # Update other status less frequently (every 5 seconds)
            if eventtime - self.last_status_update > 5.0:
                status = self.bus.read_status(self.servo_id)
                if status:
                    self.cached_temperature = status.get("temperature")
                    self.cached_current = status.get("current")
                    self.cached_voltage = status.get("voltage")

                # Check temperature
                try:
                    self._check_temperature()
                except:
                    pass  # Error already logged/handled

                self.last_status_update = eventtime

            # Clear error on successful update
            self.last_error = None

        except Exception as e:
            self.last_error = str(e)
            logging.debug(f"ST3215Servo: Status update error for {self.name}: {e}")

        # Schedule next update
        return eventtime + self.status_update_interval

    # G-code command handlers

    cmd_STSERVO_MOVE_help = "Move ST3215 servo to position"

    def cmd_STSERVO_MOVE(self, gcmd):
        """
        STSERVO_MOVE SERVO=name POSITION=value [SPEED=value] [ACCEL=value] [WAIT=<seconds>]

        WAIT:
          - 0 (default) : don't block, return immediately after queuing move
          - >0           : block (in klipper reactor fashion) until move completes
                           or until WAIT seconds elapse (timeout)
        """
        position = gcmd.get_int(
            "POSITION", minval=self.position_min, maxval=self.position_max
        )
        speed = gcmd.get_int("SPEED", self.max_speed, minval=0, maxval=3400)
        accel = gcmd.get_int("ACCEL", self.max_accel, minval=0, maxval=254)
        # WAIT is a timeout in seconds; 0 means don't wait
        wait = gcmd.get_float("WAIT", 0.0)

        try:
            # Queue the move
            self.move_to(position, speed, accel)
            gcmd.respond_info(
                f"Moving {self.name} to position {position} "
                f"(speed={speed}, accel={accel})"
            )

            # If WAIT is requested, poll the servo using the reactor until move completes
            if wait and wait > 0.0:
                reactor = self.printer.get_reactor()
                poll_interval = max(0.01, min(1.0, self.status_update_interval))
                start_time = reactor.monotonic()
                end_time = start_time + float(wait)
                # Initial event time for reactor.pause
                eventtime = reactor.monotonic()

                while True:
                    # Check movement state via bus (thread-safe)
                    try:
                        moving = self.bus.is_moving(self.servo_id)
                    except Exception as e:
                        # If bus check fails, record and break with error
                        raise gcmd.error(f"Error checking servo moving state: {e}")

                    if not moving:
                        gcmd.respond_info(f"{self.name} reached position {position}")
                        break
                    # Check timeout
                    now = reactor.monotonic()
                    if now >= end_time:
                        raise gcmd.error(f"Timeout waiting for {self.name} move")
                    # Sleep using reactor.pause to remain reactor-friendly
                    eventtime = reactor.pause(now + poll_interval)

        except Exception as e:
            raise gcmd.error(str(e))

    cmd_STSERVO_STOP_help = "Stop ST3215 servo immediately"

    def cmd_STSERVO_STOP(self, gcmd):
        """STSERVO_STOP SERVO=name"""
        try:
            self.stop()
            gcmd.respond_info(f"Stopped {self.name}")
        except Exception as e:
            raise gcmd.error(str(e))

    cmd_STSERVO_ENABLE_help = "Enable ST3215 servo motor"

    def cmd_STSERVO_ENABLE(self, gcmd):
        """STSERVO_ENABLE SERVO=name"""
        try:
            self.enable()
            gcmd.respond_info(f"Enabled {self.name}")
        except Exception as e:
            raise gcmd.error(str(e))

    cmd_STSERVO_DISABLE_help = "Disable ST3215 servo motor"

    def cmd_STSERVO_DISABLE(self, gcmd):
        """STSERVO_DISABLE SERVO=name"""
        try:
            self.disable()
            gcmd.respond_info(f"Disabled {self.name}")
        except Exception as e:
            raise gcmd.error(str(e))

    cmd_STSERVO_SET_POSITION_help = "Set servo position without moving"

    def cmd_STSERVO_SET_POSITION(self, gcmd):
        """STSERVO_SET_POSITION SERVO=name POSITION=value"""
        position = gcmd.get_int(
            "POSITION", minval=self.position_min, maxval=self.position_max
        )
        try:
            self.set_position(position)
            gcmd.respond_info(f"Set {self.name} position to {position}")
        except Exception as e:
            raise gcmd.error(str(e))

    cmd_STSERVO_STATUS_help = "Query ST3215 servo status"

    def cmd_STSERVO_STATUS(self, gcmd):
        """STSERVO_STATUS SERVO=name"""
        try:
            status = self.get_current_status()

            # Format response
            response = f"{self.name} Status:\n"
            response += f"  Position: {status['position']}\n"
            response += f"  Target: {status['target_position']}\n"
            response += f"  Moving: {status['is_moving']}\n"

            if status["temperature"] is not None:
                response += f"  Temperature: {status['temperature']:.1f}°C\n"
            if status["current"] is not None:
                response += f"  Current: {status['current']:.1f}mA\n"
            if status["voltage"] is not None:
                response += f"  Voltage: {status['voltage']:.1f}V\n"

            response += f"  Enabled: {status['enabled']}"

            if status["last_error"]:
                response += f"\n  Last Error: {status['last_error']}"

            gcmd.respond_info(response)

        except Exception as e:
            raise gcmd.error(str(e))


def load_config_prefix(config):
    """
    Klipper module loader for [st3215 name] sections.

    Args:
        config: Klipper ConfigWrapper object

    Returns:
        ST3215Servo instance
    """
    return ST3215Servo(config)
