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
    if exist "%~dp0..\bin\tor\tor\tor.exe" (
        echo [*] Tor CLI binary found. Starting background Tor daemon...
        call "%~dp0run_tor_windows.bat"
    ) else (
        echo [!] Tor daemon (port 9050/9150) is not running.
        echo [*] Would you like to automatically download and run Tor CLI Daemon now?
        set /p "INSTALL_TOR=[Y/N] (Default: Y): "
        if /i "!INSTALL_TOR!" neq "n" (
            call "%~dp0install_tor_windows.bat"
        )
    )
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
