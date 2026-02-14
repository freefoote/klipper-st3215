#!/bin/bash
# ST3215 Klipper Extension Uninstallation Script
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
EXTRAS_PATH="$KLIPPER_PATH/klippy/extras/st3215"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    ST3215 Klipper Extension Uninstaller v1.0.0       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}ERROR: Do not run this script as root!${NC}"
    echo "Please run as the normal user that runs Klipper."
    exit 1
fi

# Check if Klipper is installed
if [ ! -d "$KLIPPER_PATH" ]; then
    echo -e "${YELLOW}⚠${NC}  Klipper not found at $KLIPPER_PATH"
    echo "   (This might be expected if you've already removed Klipper)"
    KLIPPER_PATH=""
fi

# Check and remove symlink
if [ -n "$KLIPPER_PATH" ]; then
    echo -e "${BLUE}[1/2]${NC} Checking for ST3215 extension..."

    if [ -L "$EXTRAS_PATH" ]; then
        echo "    Removing symlink at $EXTRAS_PATH"
        if rm "$EXTRAS_PATH"; then
            echo -e "${GREEN}✓${NC} Symlink removed successfully"
        else
            echo -e "${RED}ERROR: Failed to remove symlink${NC}"
            echo "You may need to remove it manually:"
            echo "  rm $EXTRAS_PATH"
            exit 1
        fi
    elif [ -e "$EXTRAS_PATH" ]; then
        echo -e "${YELLOW}⚠${NC}  $EXTRAS_PATH exists but is not a symlink"
        echo "    This may be from a manual installation."
        echo ""
        read -p "    Do you want to remove it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if rm -rf "$EXTRAS_PATH"; then
                echo -e "${GREEN}✓${NC} Directory removed successfully"
            else
                echo -e "${RED}ERROR: Failed to remove directory${NC}"
                echo "You may need to remove it manually:"
                echo "  rm -rf $EXTRAS_PATH"
                exit 1
            fi
        else
            echo "    Skipped. Please remove manually if needed."
        fi
    else
        echo -e "${YELLOW}⚠${NC}  ST3215 extension not found at $EXTRAS_PATH"
        echo "    (Already uninstalled?)"
    fi
else
    echo -e "${YELLOW}⚠${NC}  Skipping symlink removal (Klipper path not found)"
fi

# Ask about removing Python library
echo ""
echo -e "${BLUE}[2/2]${NC} ST3215 Python library..."

if [ -d "$KLIPPY_ENV" ] && "$KLIPPY_ENV/bin/python" -c "import st3215" 2>/dev/null; then
    echo "    The st3215 Python library is currently installed."
    echo ""
    read -p "    Do you want to remove it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if "$KLIPPY_ENV/bin/pip" uninstall -y st3215; then
            echo -e "${GREEN}✓${NC} st3215 library removed successfully"
        else
            echo -e "${RED}ERROR: Failed to remove st3215 library${NC}"
            echo "You may need to remove it manually:"
            echo "  $KLIPPY_ENV/bin/pip uninstall st3215"
        fi
    else
        echo "    Kept st3215 library (may be used by other code)"
    fi
else
    echo -e "${GREEN}✓${NC} st3215 library not installed or already removed"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Uninstallation completed successfully!       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Remove ST3215 configuration from your printer.cfg:"
echo ""
echo "   Remove all [st3215 ...] sections and related macros"
echo ""
echo "2. Restart Klipper service:"
echo ""
echo "   sudo systemctl restart klipper"
echo ""
echo "3. Verify Klipper starts without errors:"
echo ""
echo "   tail -f ~/printer_data/logs/klippy.log"
echo ""
echo -e "${YELLOW}Note:${NC} The ST3215 extension files in this directory have not been"
echo "      deleted. You can safely delete this directory if you don't need them:"
echo "      rm -rf $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo ""
