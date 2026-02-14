# ST3215 Klipper Extension

A Klipper extension for controlling Feetech ST3215 serial bus servo motors. Perfect for grippers, tool changers, camera pan/tilt, and other positioning applications on 3D printers.

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![Klipper](https://img.shields.io/badge/klipper-compatible-orange.svg)

## LLM Disclaimer

This extension was completely coded by LLM tools, and then verified by hand. Please verify this for your use case carefully before use.

## Features

- ✅ **Multi-Servo Support** - Control multiple servos on shared or separate buses
- ✅ **Full Position Control** - Precise 12-bit positioning (0-4095)
- ✅ **Safety Features** - Position limits, temperature monitoring, error recovery
- ✅ **Status Monitoring** - Real-time position, temperature, current, and voltage
- ✅ **G-code Integration** - Native Klipper commands and macro support
- ✅ **Moonraker/Mainsail Compatible** - Status accessible via web interface
- ✅ **Easy Installation** - Automated installation script
- ✅ **Version Control** - Git-based updates

## What You Can Build

- **Grippers** - Pick and place objects during prints
- **Tool Changers** - Automatic tool changing systems
- **Camera Control** - Pan/tilt camera positioning
- **Part Ejectors** - Automated part removal
- **Bed Probes** - Deployable probe mechanisms
- **Material Feeders** - Automated filament/material handling

## Requirements

### Hardware
- Feetech ST3215 serial bus servo motor(s)
- USB-to-serial adapter (FTDI, CP2102, CH340, etc.)
- Klipper-compatible controller board (Manta M4P, etc.)
- Power supply appropriate for ST3215 (11.1-14.8V)

### Software
- Klipper firmware (already installed)
- Python 3.7+
- Git (for installation and updates)

## Quick Start

### 1. Installation

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/klipper-st3215.git
cd klipper-st3215
./install.sh
```

The installation script will:
- ✓ Check for Klipper installation
- ✓ Install the st3215 Python library if needed
- ✓ Create a symlink in Klipper's extras directory
- ✓ Verify the installation

### 2. Configuration

Add to your `printer.cfg`:

```ini
[st3215 gripper]
serial: /dev/ttyUSB0
servo_id: 1
position_min: 500
position_max: 3500
initial_position: 2048
```

### 3. Restart Klipper

```bash
sudo systemctl restart klipper
```

### 4. Test Commands

```gcode
STSERVO_ENABLE SERVO=gripper
STSERVO_MOVE SERVO=gripper POSITION=3000
STSERVO_STATUS SERVO=gripper
STSERVO_DISABLE SERVO=gripper
```

## Configuration Reference

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `serial` | string | Serial port device (e.g., `/dev/ttyUSB0`) |
| `servo_id` | int (0-253) | Unique servo ID on the bus |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `baudrate` | int | 1000000 | Serial communication baud rate |
| `position_min` | int (0-4095) | 0 | Minimum allowed position |
| `position_max` | int (0-4095) | 4095 | Maximum allowed position |
| `initial_position` | int (0-4095) | None | Position to move to on startup |
| `max_speed` | int (0-3400) | 3400 | Maximum movement speed |
| `max_acceleration` | int (0-254) | 254 | Maximum acceleration |
| `status_update_interval` | float | 1.0 | Status polling interval (seconds) |
| `temperature_warning` | int (0-100) | 70 | Temperature warning threshold (°C) |
| `temperature_critical` | int (0-100) | 85 | Temperature shutdown threshold (°C) |

### Example: Multiple Servos

```ini
# First servo on bus
[st3215 gripper]
serial: /dev/ttyUSB0
servo_id: 1
position_min: 500
position_max: 3500

# Second servo on same bus
[st3215 tool_changer]
serial: /dev/ttyUSB0
servo_id: 2
position_min: 0
position_max: 4095

# Servo on different bus
[st3215 camera_pan]
serial: /dev/ttyUSB1
servo_id: 1
```

## G-code Commands

Note: Command names containing a letter sequence followed immediately by digits (for example `ST3215_*`) can be parsed incorrectly by Klipper's gcode parser. This extension registers new command names without embedded digits. If you have existing workflows that use the older `ST3215_*` names, see the "Legacy command aliases" section below.

### STSERVO_MOVE
Move servo to absolute position.

```gcode
STSERVO_MOVE SERVO=<name> POSITION=<value> [SPEED=<value>] [ACCEL=<value>] [WAIT=<seconds>]
```

With `WAIT`, the command will block (in a Klipper friendly way) until the position has been reached. This is done via polling; use `status_update_interval` to tune how often this polls (default `1.0 seconds`).

**Examples:**
```gcode
STSERVO_MOVE SERVO=gripper POSITION=3000
STSERVO_MOVE SERVO=gripper POSITION=3000 SPEED=2000
STSERVO_MOVE SERVO=gripper POSITION=3000 SPEED=2000 ACCEL=200
```

### STSERVO_STOP
Stop servo immediately.

```gcode
STSERVO_STOP SERVO=<name>
```

### STSERVO_ENABLE
Enable servo motor (allows movement).

```gcode
STSERVO_ENABLE SERVO=<name>
```

### STSERVO_DISABLE
Disable servo motor (free to move manually).

```gcode
STSERVO_DISABLE SERVO=<name>
```

### STSERVO_SET_POSITION
Set current position without moving (for homing/zeroing).

```gcode
STSERVO_SET_POSITION SERVO=<name> POSITION=<value>
```

### STSERVO_STATUS
Query servo status (position, temperature, current, voltage).

```gcode
STSERVO_STATUS SERVO=<name>
```

### Legacy command aliases (optional)
If you prefer to keep the original `ST3215_*` command names in your macros or scripts, add the following macros to your `printer.cfg`. They map the legacy names to the new `STSERVO_*` commands:

```ini
[gcode_macro ST3215_STATUS]
gcode:
    STSERVO_STATUS SERVO={params.SERVO}

[gcode_macro ST3215_MOVE]
gcode:
    STSERVO_MOVE SERVO={params.SERVO} POSITION={params.POSITION} {% if params.SPEED %}SPEED={params.SPEED}{% endif %} {% if params.ACCEL %}ACCEL={params.ACCEL}{% endif %}

[gcode_macro ST3215_ENABLE]
gcode:
    STSERVO_ENABLE SERVO={params.SERVO}

[gcode_macro ST3215_DISABLE]
gcode:
    STSERVO_DISABLE SERVO={params.SERVO}

[gcode_macro ST3215_STOP]
gcode:
    STSERVO_STOP SERVO={params.SERVO}

[gcode_macro ST3215_SET_POSITION]
gcode:
    STSERVO_SET_POSITION SERVO={params.SERVO} POSITION={params.POSITION}
```

These macros are lightweight and preserve backward compatibility with scripts or example configs that reference the older names.

## Macro Examples

### Basic Gripper Control

```ini
[gcode_macro GRIPPER_OPEN]
gcode:
    ST3215_MOVE SERVO=gripper POSITION=500 SPEED=2000

[gcode_macro GRIPPER_CLOSE]
gcode:
    ST3215_MOVE SERVO=gripper POSITION=3500 SPEED=2000

[gcode_macro GRIPPER_GRAB]
gcode:
    GRIPPER_OPEN
    G4 P500  # Wait 500ms
    GRIPPER_CLOSE
```

### Camera Pan/Tilt

```ini
[gcode_macro CAMERA_CENTER]
gcode:
    ST3215_MOVE SERVO=camera_pan POSITION=2048
    ST3215_MOVE SERVO=camera_tilt POSITION=2048

[gcode_macro CAMERA_LOOK_AT_BED]
gcode:
    ST3215_MOVE SERVO=camera_pan POSITION=2048
    ST3215_MOVE SERVO=camera_tilt POSITION=3000
```

See [`examples/printer.cfg.example`](examples/printer.cfg.example) for more examples.

## Status Monitoring

### Via G-code

```gcode
STSERVO_STATUS SERVO=gripper
```

Output:
```
st3215 gripper Status:
  Position: 2048
  Target: 2048
  Moving: False
  Temperature: 35.2°C
  Current: 125.5mA
  Voltage: 12.1V
  Enabled: True
```

### Via Moonraker API

Query servo status programmatically:

```bash
curl http://mainsail.local/printer/objects/query?st3215%20gripper
```

Response:
```json
{
  "result": {
    "status": {
      "st3215 gripper": {
        "position": 2048,
        "target_position": 2048,
        "is_moving": false,
        "temperature": 35.2,
        "current": 125.5,
        "voltage": 12.1,
        "enabled": true,
        "last_error": null
      }
    }
  }
}
```

## Troubleshooting

### Servo Not Detected

**Problem:** `Servo ID X not found on /dev/ttyUSB0`

**Solutions:**
1. Check servo is powered on
2. Verify servo_id is correct (default is usually 1)
3. Check serial cable connections
4. Try scanning: Run `ST3215_STATUS` to trigger detection

### Permission Denied

**Problem:** `Permission denied: '/dev/ttyUSB0'`

**Solution:**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in, or reboot
```

### Serial Port Not Found

**Problem:** `/dev/ttyUSB0` doesn't exist

**Solutions:**
```bash
# List available serial ports
ls -l /dev/ttyUSB* /dev/ttyACM*

# Use persistent device names
ls -l /dev/serial/by-id/

# Update config with correct port
```

### Klipper Won't Start

**Problem:** Klipper fails to start after adding servo config

**Solutions:**
1. Check Klipper logs:
   ```bash
   tail -f ~/printer_data/logs/klippy.log
   ```
2. Verify configuration syntax
3. Ensure servo_id is valid (0-253)
4. Check position_min < position_max

### Servo Overheating

**Problem:** Temperature warnings in logs

**Solutions:**
1. Reduce duty cycle (don't move continuously)
2. Lower max_speed and max_acceleration
3. Add cooling (fan)
4. Adjust temperature thresholds if appropriate

### Erratic Movement

**Problem:** Servo moves unpredictably

**Solutions:**
1. Check power supply voltage (should be 11.1-14.8V)
2. Ensure adequate current capacity
3. Reduce speed/acceleration
4. Check for loose connections
5. Verify no electrical interference

## Updating

Keep your installation up to date:

```bash
cd ~/klipper-st3215
./update.sh
sudo systemctl restart klipper
```

## Uninstalling

To remove the extension:

```bash
cd ~/klipper-st3215
./uninstall.sh
# Then remove [st3215 ...] sections from printer.cfg
sudo systemctl restart klipper
```

## Technical Details

### Position Range
- ST3215 uses 12-bit positioning: 0-4095
- Position 2048 ≈ center (180°)
- Full range ≈ 360° (model dependent)

### Speed Range
- 0-3400 units
- Higher = faster movement
- Adjust based on load and application

### Communication
- Protocol: Feetech SCS serial protocol
- Default baud rate: 1,000,000 bps
- Half-duplex serial communication

### Thread Safety
- Internal locking for multi-servo bus sharing
- Reactor-safe callbacks for Klipper integration
- Automatic retry on communication failures

## Project Structure

```
klipper-st3215/
├── st3215_servo/           # Main module
│   ├── __init__.py         # Module entry point
│   ├── st3215_bus.py       # Bus manager
│   └── st3215_servo.py     # Servo controller
├── examples/               # Example configurations
│   └── printer.cfg.example
├── docs/                   # Documentation
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
├── update.sh               # Update script
├── README.md               # This file
└── LICENSE                 # GPL v3 license
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/klipper-st3215/issues)
- **Discussions:** [GitHub Discussions](https://github.com/YOUR_USERNAME/klipper-st3215/discussions)
- **Documentation:** See `docs/` directory

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Klipper firmware team for the excellent 3D printer firmware
- Feetech for ST3215 servo motors
- st3215 Python library developers

## Changelog

### v1.0.0 (2026)
- Initial release
- Multi-servo support
- Full G-code command set
- Status monitoring
- Temperature safety features
- Automated installation

---

**Made with ❤️ for the Klipper community**
