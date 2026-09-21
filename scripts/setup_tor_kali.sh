#!/usr/bin/env bash
# ==============================================================================
# TorChatZ - 100% CLI Tor Daemon Setup for Kali Linux
# Installs Tor, configures ControlPort 9051, and enables systemd service
# ==============================================================================

set -e

echo -e "\033[1;36m[*] Setting up Tor Daemon CLI for Kali Linux...\033[0m"

# 1. Install Tor and Python system packages
echo -e "\033[1;34m[*] Installing Tor and Python requirements via apt...\033[0m"
sudo apt update
sudo apt install -y tor python3-stem python3-socks python3-prompt-toolkit python3-rich python3-cryptography

# 2. Configure /etc/tor/torrc for ControlPort 9051
TORRC="/etc/tor/torrc"
echo -e "\033[1;34m[*] Configuring ControlPort in $TORRC...\033[0m"

if ! grep -q "^ControlPort 9051" "$TORRC"; then
    echo "ControlPort 9051" | sudo tee -a "$TORRC" > /dev/null
fi

# Set CookieAuthentication 0 for seamless localhost access without permission conflicts
sudo sed -i 's/^CookieAuthentication 1/CookieAuthentication 0/' "$TORRC" 2>/dev/null || true
if ! grep -q "^CookieAuthentication 0" "$TORRC"; then
    echo "CookieAuthentication 0" | sudo tee -a "$TORRC" > /dev/null
fi

# Add debian-tor permissions for cookie authentication if applicable
CURRENT_USER=$(whoami)
sudo usermod -a -G debian-tor "$CURRENT_USER" 2>/dev/null || true

# 3. Enable and start Tor daemon service
echo -e "\033[1;34m[*] Enabling and starting Tor systemd service...\033[0m"
sudo systemctl enable tor
sudo systemctl restart tor
sleep 1
sudo chmod 644 /run/tor/control.authcookie /var/run/tor/control.authcookie /var/lib/tor/control_auth_cookie 2>/dev/null || true

# 4. Verify port 9050 & 9051
echo -e "\033[1;32m[*] Verifying Tor daemon ports...\033[0m"
sleep 2
if ss -tuln | grep -q ":9050"; then
    echo -e "\033[1;32m[v] Tor SOCKS5 proxy active on 127.0.0.1:9050\033[0m"
fi
if ss -tuln | grep -q ":9051"; then
    echo -e "\033[1;32m[v] Tor ControlPort active on 127.0.0.1:9051\033[0m"
fi

echo -e "\033[1;32m[v] Setup complete! You can now run TorChatZ via: ./scripts/start_kali.sh\033[0m"
