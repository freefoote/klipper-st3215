# ST3215 Serial Servo Control for Klipper
#
# This file may be distributed under the terms of the GNU GPLv3 license.

"""
ST3215 Klipper Extension

Provides support for Feetech ST3215 serial bus servo motors.
Servos are controlled via USB-to-serial adapter.

Example configuration:
    [st3215 gripper]
    serial: /dev/ttyUSB0
    servo_id: 1
    position_min: 500
    position_max: 3500
    initial_position: 2048

Commands:
    ST3215_MOVE SERVO=gripper POSITION=3000
    ST3215_STOP SERVO=gripper
    ST3215_ENABLE SERVO=gripper
    ST3215_DISABLE SERVO=gripper
    ST3215_SET_POSITION SERVO=gripper POSITION=0
    ST3215_STATUS SERVO=gripper
"""

from .st3215_servo import ST3215Servo, load_config_prefix

__all__ = ["ST3215Servo", "load_config_prefix"]
__version__ = "1.0.0"
