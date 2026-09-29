from flask import Flask, request, jsonify
import subprocess
import re
import logging
import ipaddress

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_valid_ip(ip):
    """Validate that the provided string is a valid IP address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

@app.route('/webhook', methods=['POST'])
def tines_webhook():
    data = request.json
    
    if not data or 'ip' not in data:
        logging.warning("Received invalid payload")
        return jsonify({"error": "Invalid payload, 'ip' field is required"}), 400
        
    malicious_ip = data['ip']
    
    if not is_valid_ip(malicious_ip):
        logging.warning(f"Received invalid IP address format: {malicious_ip}")
        return jsonify({"error": "Invalid IP format"}), 400
        
    logging.info(f"Received request to block IP: {malicious_ip}")
    
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
        
        logging.info(f"Executing: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        logging.info(f"Successfully blocked {malicious_ip}. Output: {result.stdout.strip()}")
        return jsonify({"status": "success", "message": f"IP {malicious_ip} blocked via Windows Firewall"}), 200
        
    except subprocess.CalledProcessError as e:
        error_msg = f"stdout: {e.stdout.strip()} | stderr: {e.stderr.strip()}"
        logging.error(f"Failed to execute firewall command. Details: {error_msg}")
        return jsonify({
            "error": "Failed to update firewall rules", 
            "details": error_msg
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Listen on all interfaces on port 5001
    # Note: In a real scenario, you should add authentication/API keys for this endpoint
    logging.info("Starting Active Defense Webhook Listener on port 5001")
    app.run(host='0.0.0.0', port=5001)
