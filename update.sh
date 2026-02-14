#!/bin/bash
# ST3215 Klipper Extension Update Script
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

EXTENSION_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      ST3215 Klipper Extension Updater v1.0.0         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}ERROR: Do not run this script as root!${NC}"
    echo "Please run as the normal user that runs Klipper."
    exit 1
fi

cd "$EXTENSION_PATH"

# Check if git repository
echo -e "${BLUE}[1/3]${NC} Checking repository status..."
if [ ! -d ".git" ]; then
    echo -e "${RED}ERROR: Not a git repository${NC}"
    echo ""
    echo "This directory was not cloned from GitHub."
    echo "To use the update script, please:"
    echo ""
    echo "1. Remove this directory:"
    echo "   rm -rf $EXTENSION_PATH"
    echo ""
    echo "2. Clone from GitHub:"
    echo "   git clone https://github.com/YOUR_USERNAME/klipper-st3215.git"
    echo ""
    echo "3. Run install.sh again:"
    echo "   cd klipper-st3215"
    echo "   ./install.sh"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git repository found"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  You have uncommitted changes in this repository"
    echo ""
    git status --short
    echo ""
    read -p "    Continue with update? This may overwrite changes (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Update cancelled."
        exit 0
    fi
fi

# Fetch and pull latest changes
echo -e "${BLUE}[2/3]${NC} Pulling latest changes from GitHub..."

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "    Current branch: $CURRENT_BRANCH"

# Fetch updates
if git fetch origin; then
    echo -e "${GREEN}✓${NC} Fetched updates from remote"
else
    echo -e "${RED}ERROR: Failed to fetch from remote${NC}"
    exit 1
fi

# Check if there are updates
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
BASE=$(git merge-base @ @{u} 2>/dev/null || echo "")

if [ -z "$REMOTE" ]; then
    echo -e "${YELLOW}⚠${NC}  No upstream branch configured"
    echo "    Attempting to pull from origin/$CURRENT_BRANCH..."
fi

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✓${NC} Already up to date!"
elif [ "$LOCAL" = "$BASE" ]; then
    # Pull updates
    if git pull origin "$CURRENT_BRANCH"; then
        echo -e "${GREEN}✓${NC} Updated successfully!"
        echo ""
        echo "Changes:"
        git log --oneline HEAD@{1}..HEAD
    else
        echo -e "${RED}ERROR: Failed to pull updates${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC}  Your local branch has diverged from remote"
    echo "    Please resolve conflicts manually using git commands."
    exit 1
fi

# Verify installation
echo ""
echo -e "${BLUE}[3/3]${NC} Verifying installation..."
KLIPPER_PATH="${HOME}/klipper"
EXTRAS_PATH="$KLIPPER_PATH/klippy/extras/st3215"

if [ -L "$EXTRAS_PATH" ] && [ -d "$EXTRAS_PATH" ]; then
    # Check if symlink points to correct location
    LINK_TARGET=$(readlink -f "$EXTRAS_PATH")
    EXPECTED_TARGET=$(readlink -f "$EXTENSION_PATH/st3215_servo")

    if [ "$LINK_TARGET" = "$EXPECTED_TARGET" ]; then
        echo -e "${GREEN}✓${NC} Installation verified"
    else
        echo -e "${YELLOW}⚠${NC}  Symlink exists but points to different location"
        echo "    Current: $LINK_TARGET"
        echo "    Expected: $EXPECTED_TARGET"
        echo ""
        echo "    Run ./install.sh to fix the symlink"
    fi
else
    echo -e "${YELLOW}⚠${NC}  ST3215 extension not installed or symlink broken"
    echo "    Run ./install.sh to install/repair"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Update completed successfully!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Restart Klipper to load the updated code:"
echo ""
echo "   sudo systemctl restart klipper"
echo ""
echo "2. Check Klipper logs for any errors:"
echo ""
echo "   tail -f ~/printer_data/logs/klippy.log"
echo ""
echo -e "${YELLOW}Note:${NC} If the update included configuration changes, you may need"
echo "      to update your printer.cfg accordingly. Check the documentation"
echo "      and example configs for any new options."
echo ""
