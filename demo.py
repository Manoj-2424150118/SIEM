import time
import threading
import requests
import subprocess
from unittest.mock import patch
from webhook_listener import app

def run_demo():
    print("\n" + "="*60)
    print("🚀 SIEM TO SOAR AUTOMATION PIPELINE DEMO 🚀")
    print("="*60 + "\n")
    
    # 1. Start the webhook listener in the background
    print("[1] Starting Active Defense Webhook Node (Listening on port 5001)...")
    server_thread = threading.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': 5001, 'use_reloader': False})
    server_thread.daemon = True
    
    # We patch subprocess.run so we don't need Admin rights or modify your real firewall during the demo
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "Ok."
        mock_run.return_value.returncode = 0
        server_thread.start()
        time.sleep(2) # Give the Flask server time to start
        
        target_ip = "192.168.1.200"
        
        # 2. Run the attack simulator
        print("\n[2] Attacker is initiating an SSH Brute Force Attack...")
        print("-" * 40)
        subprocess.run(["python", "attack_simulator.py", "--target", target_ip, "--count", "3"])
        print("-" * 40)
        
        # 3. Simulate SIEM / SOAR processing
        print(f"\n[3] 🔍 SIEM (Elastic): Detected 3 consecutive auth failures from {target_ip} in under 1 minute!")
        time.sleep(2)
        print(f"[4] 🧠 SOAR (Tines): Checked {target_ip} against VirusTotal API -> 100% Malicious confidence.")
        time.sleep(2)
        print(f"[5] ⚡ SOAR (Tines): Sending automated block command to Active Defense Webhook...")
        time.sleep(2)
        
        # 4. Trigger Webhook
        print("\n[6] Active Defense Node received instruction. Executing Firewall block...")
        from webhook_listener import API_KEY
        headers = {'x-api-key': API_KEY}
        response = requests.post('http://127.0.0.1:5001/webhook', json={'ip': target_ip}, headers=headers)
        
        print(f"    Webhook Status Code: {response.status_code}")
        print(f"    Webhook Message: {response.json().get('message')}")
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETE: The attacker was successfully and automatically blocked!")
        print("="*60 + "\n")

if __name__ == "__main__":
    run_demo()
