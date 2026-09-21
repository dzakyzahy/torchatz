@echo off
REM ==============================================================================
REM TorChatZ - Windows Launcher Script (CMD / PowerShell)
REM Anonymous P2P Terminal Chat over Tor (v3 Onion Services)
REM ==============================================================================

title TorChatZ - Anonymous Terminal Chat
color 0B

echo =====================================================================
echo    TorChatZ - Anonymous P2P Terminal Chat over Tor (v3 Onion)
echo =====================================================================
echo.

REM 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python is not found in your PATH.
    echo     Please install Python 3.10+ from https://python.org and check 'Add to PATH'.
    pause
    exit /b 1
)

REM 2. Check Tor SOCKS5 port (9050 or 9150)
netstat -ano | findstr "9050 9150" >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Warning: Tor SOCKS5 proxy port (9050 or 9150) not detected!
    echo     Please make sure Tor Browser or Tor Expert Bundle is running.
    echo     - Tor Browser: Open Tor Browser and leave it open in the background (port 9150).
    echo     - Or Tor Daemon: run tor.exe (port 9050).
    echo.
    echo Starting TorChatZ anyway...
    echo.
)

REM 3. Install/verify dependencies
echo [*] Checking Python dependencies...
python -m pip install -q -r requirements.txt

REM 4. Run TorChatZ
echo [*] Launching TorChatZ...
echo.
python torchatz.py %*

if %errorlevel% neq 0 (
    echo.
    echo [!] TorChatZ stopped with an error code: %errorlevel%
    pause
)
