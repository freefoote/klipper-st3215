#!/bin/bash
# ST3215 Klipper Extension Installation Script
#
# Copyright (C) 2026
# This file may be distributed under the terms of the GNU GPLv3 license.

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default paths
KLIPPER_PATH="${HOME}/klipper"
KLIPPY_ENV="${HOME}/klippy-env"
EXTENSION_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    ST3215 Klipper Extension Installer v1.0.0         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}ERROR: Do not run this script as root!${NC}"
    echo "Please run as the normal user that runs Klipper."
    exit 1
fi

# Check if Klipper is installed
echo -e "${BLUE}[1/5]${NC} Checking for Klipper installation..."
if [ ! -d "$KLIPPER_PATH" ]; then
    echo -e "${RED}ERROR: Klipper not found at $KLIPPER_PATH${NC}"
    echo ""
    echo "Please install Klipper first, or set KLIPPER_PATH environment variable:"
    echo "  export KLIPPER_PATH=/path/to/klipper"
    echo "  ./install.sh"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found Klipper at $KLIPPER_PATH"

# Check if klippy-env exists
echo -e "${BLUE}[2/5]${NC} Checking for Klippy Python environment..."
if [ ! -d "$KLIPPY_ENV" ]; then
    echo -e "${RED}ERROR: Klippy environment not found at $KLIPPY_ENV${NC}"
    echo ""
    echo "If your Klipper installation uses a different virtualenv path,"
    echo "please set KLIPPY_ENV environment variable:"
    echo "  export KLIPPY_ENV=/path/to/klippy-env"
    echo "  ./install.sh"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found Klippy environment at $KLIPPY_ENV"

# Check if st3215 library is installed
echo -e "${BLUE}[3/5]${NC} Checking for st3215 Python library..."
if ! "$KLIPPY_ENV/bin/python" -c "import st3215" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  st3215 library not found in klippy-env"
    echo "    Installing st3215 library..."

    if "$KLIPPY_ENV/bin/pip" install st3215; then
        echo -e "${GREEN}✓${NC} st3215 library installed successfully"
    else
        echo -e "${RED}ERROR: Failed to install st3215 library${NC}"
        echo ""
        echo "Please install manually:"
        echo "  $KLIPPY_ENV/bin/pip install st3215"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} st3215 library is installed"
fi

# Create symlink to extras directory
EXTRAS_PATH="$KLIPPER_PATH/klippy/extras/st3215"
echo -e "${BLUE}[4/5]${NC} Creating symlink at $EXTRAS_PATH..."

if [ -L "$EXTRAS_PATH" ]; then
    echo -e "${YELLOW}⚠${NC}  Removing existing symlink..."
    rm "$EXTRAS_PATH"
elif [ -e "$EXTRAS_PATH" ]; then
    echo -e "${RED}ERROR: $EXTRAS_PATH exists but is not a symlink${NC}"
    echo ""
    echo "Please remove it manually and try again:"
    echo "  rm -rf $EXTRAS_PATH"
    exit 1
fi

if ln -s "$EXTENSION_PATH/st3215_servo" "$EXTRAS_PATH"; then
    echo -e "${GREEN}✓${NC} Symlink created successfully"
else
    echo -e "${RED}ERROR: Failed to create symlink${NC}"
    exit 1
fi

# Verify installation
echo -e "${BLUE}[5/5]${NC} Verifying installation..."
if [ -d "$EXTRAS_PATH" ] && [ -f "$EXTRAS_PATH/__init__.py" ]; then
    echo -e "${GREEN}✓${NC} Installation verified"
else
    echo -e "${RED}ERROR: Installation verification failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation completed successfully!        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Add ST3215 servo configuration to your printer.cfg:"
echo ""
echo "   [st3215 my_servo]"
echo "   serial: /dev/ttyUSB0"
echo "   servo_id: 1"
echo "   position_min: 0"
echo "   position_max: 4095"
echo ""
echo "   See examples/printer.cfg.example for more options"
echo ""
echo "2. Restart Klipper service:"
echo ""
echo "   sudo systemctl restart klipper"
echo ""
echo "3. Check Klipper logs for any errors:"
echo ""
echo "   tail -f ~/printer_data/logs/klippy.log"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  - Configuration: $EXTENSION_PATH/docs/configuration.md"
echo "  - Commands: $EXTENSION_PATH/docs/commands.md"
echo "  - Examples: $EXTENSION_PATH/examples/"
echo ""
echo -e "${YELLOW}Note:${NC} Make sure your ST3215 servo is connected and the serial port"
echo "      (/dev/ttyUSB0) exists before restarting Klipper."
echo ""
