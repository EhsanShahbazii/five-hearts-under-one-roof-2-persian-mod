#!/bin/bash
# ==============================================================================
# Five Hearts Under One Roof 2 — Persian Subtitle Mod Installer
# Author: Ehsan
# Version: 1.0.0
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_DIR="${SCRIPT_DIR}/game_mod_toolkit"
VENV_DIR="${SCRIPT_DIR}/.venv"
GAME_APP="/Applications/Five Hearts Under One Roof 2.app"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=================================================================="
echo "    Five Hearts Under One Roof 2 — Persian Subtitle Mod v1.0.0    "
echo "        پچ زیرنویس فارسی بازی «یک سقف و پنج قلب ۲»               "
echo "=================================================================="
echo -e "${NC}"

# Check for custom game path argument
if [ -n "$2" ] && [ -d "$2" ]; then
    GAME_APP="$2"
fi

if [ ! -d "$GAME_APP" ]; then
    echo -e "${RED}[!] Error: Could not find game at:${NC} ${GAME_APP}"
    echo -e "    Please drag 'Five Hearts Under One Roof 2.app' into /Applications/ or pass the path as argument:"
    echo -e "    ./install.sh --apply \"/path/to/Five Hearts Under One Roof 2.app\""
    exit 1
fi

echo -e "${BLUE}[*] Target Game:${NC} ${GAME_APP}"

# Setup Python environment
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}[*] Setting up local Python environment...${NC}"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet UnityPy arabic-reshaper python-bidi pillow
fi

PYTHON_BIN="${VENV_DIR}/bin/python"

# Handle restore flag
if [ "$1" == "--restore" ] || [ "$1" == "-r" ]; then
    echo -e "${YELLOW}[*] Restoring game files to original factory state...${NC}"
    "$PYTHON_BIN" "${TOOLKIT_DIR}/patcher.py" --game-path "$GAME_APP" --restore
    echo -e "\n${GREEN}${BOLD}[✔] بازی با موفقیت به حالت اولیه کارخانه بازگردانده شد!${NC}\n"
    exit 0
fi

# Apply patch
echo -e "${BLUE}[*] Applying Persian subtitles and Lahzeh font patch...${NC}"
"$PYTHON_BIN" "${TOOLKIT_DIR}/patcher.py" --game-path "$GAME_APP" --apply

echo -e "\n${GREEN}${BOLD}=================================================================="
echo "  [✔] پچ با موفقیت اعمال شد! (Patch Applied Successfully)         "
echo "==================================================================${NC}"
echo -e "${CYAN}
راهنمای اجرا:
1. بازی Five Hearts Under One Roof 2 را باز کنید.
2. در منوی Settings (تنظیمات)، بخش Language:
   - گزینه 한국어 (Korean) را انتخاب کنید تا زیرنویس‌های فارسی با فونت لحظه نمایش داده شوند.
   - یا گزینه English را انتخاب کنید تا زیرنویس‌های انگلیسی اصلی بازی نمایش داده شوند.

برای حذف پچ و بازگردانی به نسخه کارخانه:
./install.sh --restore
${NC}"
