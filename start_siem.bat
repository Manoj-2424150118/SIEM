@echo off
setlocal EnableDelayedExpansion
title SIEM to SOAR Pipeline - Real-World Deployment

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator privileges required. Requesting elevation...
    powershell -Command "Start-Process -FilePath '%~dpnx0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"

echo ========================================================
echo   SIEM to SOAR Pipeline - Production Environment
echo ========================================================
echo.

echo [*] Step 1: Checking Python installation and Dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
echo [+] Python and Dependencies are ready.

echo.
echo [*] Step 2: Ensuring Native Windows OpenSSH is running...
powershell -Command "Start-Service sshd -ErrorAction SilentlyContinue; Set-Service -Name sshd -StartupType 'Automatic' -ErrorAction SilentlyContinue"
echo [+] OpenSSH Server is active and listening on port 22.

echo.
echo [*] Step 3: Starting Elastic SIEM and Kibana (via Docker)...
docker-compose up -d >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Docker Compose failed. Please ensure Docker Desktop is running!
) else (
    echo [+] SIEM infrastructure is up and running.
)

echo.
echo [*] Step 4: Starting Active Defense Webhook Node...
start "Active Defense Node (Port 5001)" cmd /k "title Active Defense Node && echo [*] Running Webhook Listener... && python webhook_listener.py"

echo.
echo [*] Step 5: Establishing Secure Public Cloud Tunnel...
start "Ngrok Secure Tunnel" cmd /k "title Ngrok Secure Tunnel && echo [*] Connecting to Ngrok... && python start_tunnel.py"

echo.
echo ========================================================
echo ✅ Deployment Complete! System is Armed and Ready.
echo ========================================================
echo.
echo - The Active Defense Webhook is running in a new window.
echo - The Public Ngrok Tunnel is running in a new window.
echo - Paste your Ngrok URL into your Tines Webhook action to link the SOAR.
echo.
pause
