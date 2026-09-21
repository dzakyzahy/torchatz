@echo off
REM ==============================================================================
REM TorChatZ - Windows Launcher Script
REM Anonymous P2P Terminal Chat over Tor (v3 Onion Services)
REM ==============================================================================

cd /d "%~dp0.."

title TorChatZ - Anonymous Terminal Chat
color 0B

echo =====================================================================
echo    TorChatZ - Anonymous P2P Terminal Chat over Tor (v3 Onion)
echo =====================================================================
echo.

REM 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python is not found in your PATH.
    echo     Please install Python 3.10+ from https://python.org and check 'Add to PATH'.
    pause
    exit /b 1
)

REM 2. Launch TorChatZ (Tor daemon & Onion v3 auto-starts inside Python)
echo [*] Launching TorChatZ...
echo.
python torchatz.py %*

if errorlevel 1 (
    echo.
    echo [!] TorChatZ stopped with an error code.
    pause
)
