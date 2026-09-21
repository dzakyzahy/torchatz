@echo off
REM ==============================================================================
REM TorChatZ - Run Tor CLI Daemon on Windows
REM ==============================================================================

cd /d "%~dp0.."
set "TOR_BIN=%CD%\bin\tor\tor\tor.exe"
set "TORRC=%CD%\bin\tor\torrc"

if not exist "%TOR_BIN%" (
    where tor.exe >nul 2>nul
    if %errorlevel% equ 0 (
        set "TOR_BIN=tor.exe"
    ) else (
        echo [!] Tor binary not found.
        echo     Run: scripts\install_tor_windows.bat
        pause
        exit /b 1
    )
)

if not exist "data\tor_data" mkdir "data\tor_data"

echo [*] Starting Tor CLI Daemon on port 9050 / control port 9051...
if exist "%TORRC%" (
    powershell -NoProfile -Command "Start-Process -FilePath '%TOR_BIN%' -ArgumentList '-f \"%TORRC%\"' -WindowStyle Hidden"
) else (
    powershell -NoProfile -Command "Start-Process -FilePath '%TOR_BIN%' -ArgumentList '--SocksPort 9050 --ControlPort 9051 --CookieAuthentication 1' -WindowStyle Hidden"
)

echo [v] Tor Daemon launched in background.
ping 127.0.0.1 -n 3 >nul
