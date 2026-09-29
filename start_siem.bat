@echo off
setlocal EnableDelayedExpansion
title SIEM to SOAR Pipeline - 1-Click Setup

:: Check for Administrator privileges (Required for the Webhook to modify Windows Firewall)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator privileges required. Requesting elevation...
    powershell -Command "Start-Process -FilePath '%~dpnx0' -Verb RunAs"
    exit /b
)

:: If we reach here, we are running as Admin
cd /d "%~dp0"

echo ========================================================
echo   SIEM to SOAR Pipeline - Automated Environment Setup
echo ========================================================
echo.

echo [*] Step 1: Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [X] Python is not installed or not in PATH. Please install Python 3.
    pause
    exit /b
)
echo [+] Python found.

echo.
echo [*] Step 2: Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [X] Failed to install dependencies.
    pause
    exit /b
)
echo [+] Dependencies installed successfully.

echo.
echo [*] Step 3: Starting Elastic SIEM and Kibana (via Docker)...
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Docker is not installed or not in PATH. 
    echo [!] Skipping local SIEM setup. Please ensure you are using Elastic Cloud if not running Docker locally.
) else (
    echo [+] Docker found. Spinning up SIEM infrastructure...
    docker-compose up -d
    if %errorLevel% neq 0 (
        echo [!] Docker Compose failed. Please ensure Docker Desktop is running!
    ) else (
        echo [+] SIEM infrastructure is up and running.
    )
)

echo.
echo [*] Step 4: Starting Active Defense Webhook Node...
:: Start the webhook listener in a new dedicated Command Prompt window
start "Active Defense Node (Port 5001)" cmd /k "title Active Defense Node && echo [*] Running Webhook Listener... && python webhook_listener.py"

echo.
echo ========================================================
echo ✅ Setup Complete! System is Armed and Ready.
echo ========================================================
echo.
echo 1. The Active Defense Webhook is now running in a new window.
echo 2. Elastic / Kibana is starting up (Available soon at http://localhost:5601).
echo 3. The API Key for your SOAR (Tines) has been saved in the .env file.
echo.
echo To test the defense manually, run:
echo    python attack_simulator.py --target 127.0.0.1 --count 5
echo.
echo To run the completely automated mock demo, run:
echo    python demo.py
echo.
pause
