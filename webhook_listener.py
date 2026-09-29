from flask import Flask, request, jsonify
import subprocess
import re
import logging
import requests
from logging.handlers import RotatingFileHandler
import ipaddress
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# Initialize the Flask app
app = Flask(__name__)

# 1. Resilience: Set up Rotating Log Files (max 5MB per file, keep 3 backups)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler('webhook_defense.log', maxBytes=5*1024*1024, backupCount=3)
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 2. Security: Ensure API Key exists
API_KEY = os.getenv("WEBHOOK_API_KEY")
if not API_KEY:
    logger.warning("No WEBHOOK_API_KEY found in environment! Generating a secure random key...")
    API_KEY = secrets.token_urlsafe(32)
    with open(".env", "a") as f:
        f.write(f"WEBHOOK_API_KEY={API_KEY}\n")
    logger.info(f"Generated new API Key and saved to .env file: {API_KEY}")


def is_valid_ip(ip):
    """Validate that the provided string is a valid IP address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

@app.route('/webhook', methods=['POST'])
def tines_webhook():
    # 3. Security: Authenticate the request
    provided_key = request.headers.get('x-api-key')
    if not provided_key or provided_key != API_KEY:
        logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    
    if not data or 'ip' not in data:
        logger.warning("Received invalid payload")
        return jsonify({"error": "Invalid payload, 'ip' field is required"}), 400
        
    malicious_ip = data['ip']
    
    if not is_valid_ip(malicious_ip):
        logger.warning(f"Received invalid IP address format: {malicious_ip}")
        return jsonify({"error": "Invalid IP format"}), 400
        
    logger.info(f"Received authenticated request to block IP: {malicious_ip}")
    
    # --- PHASE 6: NATIVE THREAT INTELLIGENCE VERIFICATION ---
    vt_api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if vt_api_key:
        logger.info(f"Querying VirusTotal API to verify IP: {malicious_ip}")
        try:
            vt_response = requests.get(
                f"https://www.virustotal.com/api/v3/ip_addresses/{malicious_ip}",
                headers={"x-apikey": vt_api_key},
                timeout=5
            )
            if vt_response.status_code == 200:
                stats = vt_response.json().get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                malicious_score = stats.get('malicious', 0)
                if malicious_score == 0:
                    logger.warning(f"VirusTotal reported 0 malicious hits for {malicious_ip}. Block aborted (False Positive).")
                    return jsonify({"status": "aborted", "message": f"IP {malicious_ip} was deemed safe by VirusTotal"}), 200
                else:
                    logger.info(f"VirusTotal confirmed {malicious_ip} is malicious (Score: {malicious_score}). Proceeding with block.")
            else:
                logger.warning(f"VirusTotal API returned {vt_response.status_code}. Bypassing verification.")
        except Exception as e:
            logger.error(f"VirusTotal API request failed: {e}. Bypassing verification.")
    else:
        logger.info("VIRUSTOTAL_API_KEY not found in .env. Skipping threat intelligence verification.")
    # --------------------------------------------------------
    
    try:
        # Execute netsh command to block the IP via Windows Firewall
        # We use a list for subprocess to prevent shell injection vulnerabilities
        rule_name = f"Block IP {malicious_ip} from SIEM Webhook"
        command = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=in",
            "action=block",
            f"remoteip={malicious_ip}"
        ]
        
        logger.info(f"Executing: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        logger.info(f"Successfully blocked {malicious_ip}. Output: {result.stdout.strip()}")
        
        # --- PHASE 7: AUTOMATED TEAM ALERTS ---
        discord_url = os.getenv("DISCORD_WEBHOOK_URL")
        slack_url = os.getenv("SLACK_WEBHOOK_URL")
        
        vt_text = f" (VirusTotal Score: {malicious_score})" if 'malicious_score' in locals() else ""
        alert_msg = f"🚨 **THREAT BLOCKED** 🚨\n**IP Address:** `{malicious_ip}`\n**Action:** Automatically added to Windows Firewall Blocklist.{vt_text}"
        
        try:
            if discord_url:
                requests.post(discord_url, json={"content": alert_msg}, timeout=3)
                logger.info("Alert dispatched to Discord.")
            elif slack_url:
                requests.post(slack_url, json={"text": alert_msg}, timeout=3)
                logger.info("Alert dispatched to Slack.")
        except Exception as e:
            logger.error(f"Failed to dispatch team alert: {e}")
        # ---------------------------------------
        
        return jsonify({"status": "success", "message": f"IP {malicious_ip} blocked via Windows Firewall"}), 200
        
    except subprocess.CalledProcessError as e:
        error_msg = f"stdout: {e.stdout.strip()} | stderr: {e.stderr.strip()}"
        logger.error(f"Failed to execute firewall command. Details: {error_msg}")
        return jsonify({
            "error": "Failed to update firewall rules", 
            "details": error_msg
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    from waitress import serve
    logger.info("Starting Production Active Defense Webhook Listener (Waitress) on port 5001")
    logger.info("Use the WEBHOOK_API_KEY to authenticate.")
    serve(app, host='0.0.0.0', port=5001, threads=8)
