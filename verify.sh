#!/bin/bash
# ST3215 Klipper Extension Verification Script
#
# Copyright (C) 2026
# This file may be distributed under the terms of the GNU GPLv3 license.

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

EXTENSION_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KLIPPER_PATH="${HOME}/klipper"
KLIPPY_ENV="${HOME}/klippy-env"
EXTRAS_PATH="$KLIPPER_PATH/klippy/extras/st3215"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    ST3215 Klipper Extension Verification Tool        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Check file structure
echo -e "${BLUE}[1/7]${NC} Checking file structure..."

REQUIRED_FILES=(
    "st3215_servo/__init__.py"
    "st3215_servo/st3215_bus.py"
    "st3215_servo/st3215_servo.py"
    "install.sh"
    "uninstall.sh"
    "update.sh"
    "README.md"
    "LICENSE"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$EXTENSION_PATH/$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (MISSING)"
        ((ERRORS++))
    fi
done

REQUIRED_DIRS=(
    "st3215_servo"
    "examples"
    "docs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$EXTENSION_PATH/$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir/"
    else
        echo -e "  ${RED}✗${NC} $dir/ (MISSING)"
        ((ERRORS++))
    fi
done

# Check scripts are executable
echo ""
echo -e "${BLUE}[2/7]${NC} Checking script permissions..."

SCRIPTS=(
    "install.sh"
    "uninstall.sh"
    "update.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$EXTENSION_PATH/$script" ]; then
        echo -e "  ${GREEN}✓${NC} $script is executable"
    else
        echo -e "  ${YELLOW}⚠${NC}  $script is not executable (can be fixed with: chmod +x $script)"
        ((WARNINGS++))
    fi
done

# Check Python syntax
echo ""
echo -e "${BLUE}[3/7]${NC} Checking Python syntax..."

PYTHON_FILES=(
    "st3215_servo/__init__.py"
    "st3215_servo/st3215_bus.py"
    "st3215_servo/st3215_servo.py"
)

if command -v python3 &> /dev/null; then
    for pyfile in "${PYTHON_FILES[@]}"; do
        if python3 -m py_compile "$EXTENSION_PATH/$pyfile" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $pyfile syntax OK"
        else
            echo -e "  ${RED}✗${NC} $pyfile syntax ERROR"
            ((ERRORS++))
        fi
    done
else
    echo -e "  ${YELLOW}⚠${NC}  python3 not found, skipping syntax check"
    ((WARNINGS++))
fi

# Check for required Python imports
echo ""
echo -e "${BLUE}[4/7]${NC} Checking Python imports..."

if [ -d "$KLIPPY_ENV" ]; then
    echo "  Using klippy environment: $KLIPPY_ENV"

    # Check for st3215 library
    if "$KLIPPY_ENV/bin/python" -c "import st3215" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} st3215 library is installed"
    else
        echo -e "  ${YELLOW}⚠${NC}  st3215 library not found (install with: $KLIPPY_ENV/bin/pip install st3215)"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  klippy-env not found at $KLIPPY_ENV"
    echo "     Cannot verify st3215 library installation"
    ((WARNINGS++))
fi

# Check installation status
echo ""
echo -e "${BLUE}[5/7]${NC} Checking installation status..."

if [ -L "$EXTRAS_PATH" ]; then
    LINK_TARGET=$(readlink -f "$EXTRAS_PATH")
    EXPECTED_TARGET=$(readlink -f "$EXTENSION_PATH/st3215_servo")

    if [ "$LINK_TARGET" = "$EXPECTED_TARGET" ]; then
        echo -e "  ${GREEN}✓${NC} Extension installed correctly"
        echo "     Symlink: $EXTRAS_PATH"
        echo "     Points to: $LINK_TARGET"
    else
        echo -e "  ${YELLOW}⚠${NC}  Symlink exists but points to wrong location"
        echo "     Expected: $EXPECTED_TARGET"
        echo "     Actual: $LINK_TARGET"
        ((WARNINGS++))
    fi
elif [ -e "$EXTRAS_PATH" ]; then
    echo -e "  ${YELLOW}⚠${NC}  $EXTRAS_PATH exists but is not a symlink"
    echo "     Run ./uninstall.sh then ./install.sh to fix"
    ((WARNINGS++))
else
    echo -e "  ${YELLOW}⚠${NC}  Extension not installed"
    echo "     Run ./install.sh to install"
    ((WARNINGS++))
fi

# Check documentation
echo ""
echo -e "${BLUE}[6/7]${NC} Checking documentation..."

DOCS=(
    "README.md"
    "ST3215_PLAN.md"
    "IMPLEMENTATION_SUMMARY.md"
    "docs/QUICK_REFERENCE.md"
    "examples/printer.cfg.example"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$EXTENSION_PATH/$doc" ]; then
        size=$(wc -l < "$EXTENSION_PATH/$doc" 2>/dev/null || echo 0)
        if [ "$size" -gt 10 ]; then
            echo -e "  ${GREEN}✓${NC} $doc ($size lines)"
        else
            echo -e "  ${YELLOW}⚠${NC}  $doc (only $size lines)"
            ((WARNINGS++))
        fi
    else
        echo -e "  ${YELLOW}⚠${NC}  $doc (not found)"
        ((WARNINGS++))
    fi
done

# Check code metrics
echo ""
echo -e "${BLUE}[7/7]${NC} Code metrics..."

if command -v wc &> /dev/null; then
    TOTAL_PY_LINES=$(find "$EXTENSION_PATH/st3215_servo" -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
    TOTAL_SH_LINES=$(wc -l "$EXTENSION_PATH"/*.sh 2>/dev/null | tail -1 | awk '{print $1}')
    TOTAL_MD_LINES=$(find "$EXTENSION_PATH" -name "*.md" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')

    echo "  Python code: $TOTAL_PY_LINES lines"
    echo "  Shell scripts: $TOTAL_SH_LINES lines"
    echo "  Documentation: $TOTAL_MD_LINES lines"
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "The ST3215 extension is properly structured and ready to use."
    EXIT_CODE=0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Verification completed with $WARNINGS warning(s)${NC}"
    echo ""
    echo "The extension should work, but review warnings above."
    EXIT_CODE=0
else
    echo -e "${RED}✗ Verification failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix the errors above before using the extension."
    EXIT_CODE=1
fi

echo ""
echo "Next steps:"
if [ -L "$EXTRAS_PATH" ]; then
    echo "  - Extension is installed"
    echo "  - Add [st3215 ...] configuration to printer.cfg"
    echo "  - Restart Klipper: sudo systemctl restart klipper"
else
    echo "  - Run ./install.sh to install the extension"
    echo "  - Add [st3215 ...] configuration to printer.cfg"
    echo "  - Restart Klipper: sudo systemctl restart klipper"
fi

echo ""
echo "Documentation:"
echo "  - README: $EXTENSION_PATH/README.md"
echo "  - Quick Reference: $EXTENSION_PATH/docs/QUICK_REFERENCE.md"
echo "  - Examples: $EXTENSION_PATH/examples/"
echo ""

exit $EXIT_CODE
