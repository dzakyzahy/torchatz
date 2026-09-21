#!/usr/bin/env bash
# ==============================================================================
# TorChatZ - Kali Linux Launcher Script
# Anonymous P2P Terminal Chat over Tor (v3 Onion Services)
# ==============================================================================

set -e

echo -e "\033[1;36m[*] Starting TorChatZ for Kali Linux...\033[0m"

# 1. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;31m[!] Python 3 is not installed. Run: sudo apt update && sudo apt install -y python3 python3-pip\033[0m"
    exit 1
fi

# 2. Check Tor service
if ! pgrep -x "tor" > /dev/null; then
    echo -e "\033[1;33m[!] Tor service is not running.\033[0m"
    echo -e "\033[1;32m[*] Attempting to start Tor service (sudo systemctl start tor)...\033[0m"
    sudo systemctl start tor || {
        echo -e "\033[1;31m[!] Could not start Tor automatically. Please run:\033[0m"
        echo -e "    sudo apt install -y tor"
        echo -e "    sudo systemctl enable --now tor"
    }
fi

# 3. Check / Install Python dependencies
echo -e "\033[1;34m[*] Verifying Python requirements...\033[0m"
python3 -m pip install -q -r requirements.txt || {
    echo -e "\033[1;33m[!] Note: If pip is managed by the OS, install via: sudo apt install -y python3-stem python3-socks python3-prompt-toolkit python3-rich\033[0m"
}

# 4. Launch TorChatZ
echo -e "\033[1;32m[*] Launching TorChatZ terminal interface...\033[0m"
python3 torchatz.py "$@"
