import unittest
import threading
import time
import requests
import subprocess
import os
import sys
import ctypes

# Add parent directory to path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webhook_listener import app, API_KEY

class WebhookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the Flask app in a separate background thread
        cls.server_thread = threading.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': 5001, 'use_reloader': False})
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Give the server a moment to start
        time.sleep(2)

    @unittest.skipIf(not ctypes.windll.shell32.IsUserAnAdmin(), "Requires Administrator privileges to modify Windows Firewall")
    def test_valid_ip_blocks_firewall(self):
        """Test that sending a valid IP results in a Windows Firewall rule being added."""
        test_ip = '192.168.100.100'
        rule_name = f"Block IP {test_ip} from SIEM Webhook"
        
        try:
            # Send the payload to the webhook with auth
            headers = {'x-api-key': API_KEY}
            response = requests.post('http://127.0.0.1:5001/webhook', json={'ip': test_ip}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("blocked via Windows Firewall", response.json().get('message', ''))
            
            # Verify the rule was actually added by querying the Windows Firewall
            result = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"], 
                capture_output=True, text=True
            )
            self.assertIn(rule_name, result.stdout)
            
        finally:
            # Cleanup: delete the rule so we don't clutter the system
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"], 
                capture_output=True, text=True
            )

    def test_invalid_ip_format(self):
        """Test that sending an invalid IP format is rejected."""
        headers = {'x-api-key': API_KEY}
        response = requests.post('http://127.0.0.1:5001/webhook', json={'ip': 'not_an_ip'}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid IP format", response.json().get('error', ''))

    def test_missing_ip_field(self):
        """Test that missing the IP field entirely is rejected."""
        headers = {'x-api-key': API_KEY}
        response = requests.post('http://127.0.0.1:5001/webhook', json={'something_else': '123'}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid payload", response.json().get('error', ''))
        
    def test_unauthorized_access(self):
        """Test that missing or invalid API keys result in 401 Unauthorized."""
        # No headers
        response1 = requests.post('http://127.0.0.1:5001/webhook', json={'ip': '1.1.1.1'})
        self.assertEqual(response1.status_code, 401)
        
        # Bad API key
        headers = {'x-api-key': 'fake_key'}
        response2 = requests.post('http://127.0.0.1:5001/webhook', json={'ip': '1.1.1.1'}, headers=headers)
        self.assertEqual(response2.status_code, 401)

if __name__ == '__main__':
    unittest.main()
