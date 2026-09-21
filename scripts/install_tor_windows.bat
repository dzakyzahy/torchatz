@echo off
REM ==============================================================================
REM TorChatZ - 100% CLI Tor Daemon Installer for Windows (No GUI Required)
REM Downloads official Tor Expert Bundle, extracts to bin\tor, and sets up torrc
REM ==============================================================================

setlocal enabledelayedexpansion
title Installing Tor CLI Daemon (Windows)
color 0A

echo =====================================================================
echo      TorChatZ - Automatic Tor CLI Daemon Installer (Windows)
echo =====================================================================
echo.

set "BIN_DIR=%~dp0..\bin\tor"
set "TOR_URL=https://archive.torproject.org/tor-package-archive/torbrowser/14.0.8/tor-expert-bundle-windows-x86_64-14.0.8.tar.gz"
set "TAR_FILE=%~dp0..\bin\tor-expert-bundle.tar.gz"

if not exist "%~dp0..\bin" mkdir "%~dp0..\bin"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%~dp0..\data\tor_data" mkdir "%~dp0..\data\tor_data"

if exist "%BIN_DIR%\tor\tor.exe" (
    echo [v] Tor CLI binary already installed at: %BIN_DIR%\tor\tor.exe
    goto :create_config
)

echo [*] Downloading Tor Expert Bundle CLI (approx 24 MB)...
echo     From: %TOR_URL%
echo.

curl.exe -# -L -o "%TAR_FILE%" "%TOR_URL%"
if %errorlevel% neq 0 (
    echo [!] Download failed. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo [*] Extracting Tor CLI binaries to bin\tor...
tar.exe -xzf "%TAR_FILE%" -C "%BIN_DIR%"
del "%TAR_FILE%" >nul 2>nul

:create_config
echo [*] Creating lightweight CLI torrc configuration...
(
    echo # TorChatZ Local CLI Configuration
    echo SocksPort 9050
    echo ControlPort 9051
    echo CookieAuthentication 1
    echo DataDirectory data/tor_data
) > "%BIN_DIR%\torrc"

echo.
echo [v] Tor CLI daemon successfully installed!
echo.
echo To run Tor daemon anytime via CLI:
echo   call scripts\run_tor_windows.bat
echo.
echo Starting Tor daemon in 2 seconds...
ping 127.0.0.1 -n 2 >nul

call "%~dp0run_tor_windows.bat"
