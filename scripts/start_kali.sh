#!/usr/bin/env bash
# ==============================================================================
# TorChatZ - Kali Linux Launcher Script
# Anonymous P2P Terminal Chat over Tor (v3 Onion Services)
# ==============================================================================

set -e
cd "$(dirname "$0")/.."

echo -e "\033[1;36m[*] Starting TorChatZ for Kali Linux...\033[0m"

# 1. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;31m[!] Python 3 is not installed. Run: sudo apt update && sudo apt install -y python3 python3-pip\033[0m"
    exit 1
fi

# 2. Check and auto-configure Tor service
if [ -f /etc/tor/torrc ]; then
    NEEDS_RESTART=0
    if ! grep -q "^ControlPort 9051" /etc/tor/torrc; then
        echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc >/dev/null
        NEEDS_RESTART=1
    fi
    if grep -q "^CookieAuthentication 1" /etc/tor/torrc || ! grep -q "^CookieAuthentication 0" /etc/tor/torrc; then
        sudo sed -i 's/^CookieAuthentication 1/CookieAuthentication 0/' /etc/tor/torrc 2>/dev/null || true
        grep -q "^CookieAuthentication 0" /etc/tor/torrc || echo "CookieAuthentication 0" | sudo tee -a /etc/tor/torrc >/dev/null
        NEEDS_RESTART=1
    fi
    if [ "$NEEDS_RESTART" -eq 1 ] || ! pgrep -x "tor" > /dev/null; then
        echo -e "\033[1;34m[*] Applying Tor configuration and starting service...\033[0m"
        sudo systemctl restart tor 2>/dev/null || sudo service tor restart 2>/dev/null || sudo systemctl start tor 2>/dev/null || true
        sleep 1
    fi
elif ! pgrep -x "tor" > /dev/null; then
    echo -e "\033[1;33m[!] Tor service is not running.\033[0m"
    if [ -f "$(dirname "$0")/setup_tor_kali.sh" ]; then
        echo -e "\033[1;34m[*] Running automatic Tor CLI setup...\033[0m"
        bash "$(dirname "$0")/setup_tor_kali.sh" || true
    else
        sudo systemctl start tor || true
    fi
fi

# 3. Check / Install Python dependencies
echo -e "\033[1;34m[*] Verifying Python requirements...\033[0m"
python3 -m pip install -q -r requirements.txt || {
    echo -e "\033[1;33m[!] Note: If pip is managed by the OS, install via: sudo apt install -y python3-stem python3-socks python3-prompt-toolkit python3-rich\033[0m"
}

# 4. Launch TorChatZ
echo -e "\033[1;32m[*] Launching TorChatZ terminal interface...\033[0m"
python3 torchatz.py "$@"
