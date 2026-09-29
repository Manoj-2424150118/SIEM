import concurrent.futures
import requests
import time
import subprocess
from webhook_listener import API_KEY

def send_request(ip):
    """Send an authenticated POST request to the webhook"""
    headers = {'x-api-key': API_KEY}
    try:
        response = requests.post('http://127.0.0.1:5001/webhook', json={'ip': ip}, headers=headers, timeout=10)
        return response.status_code
    except Exception as e:
        return 500

def run_stress_test(num_requests=50):
    print("\n" + "="*60)
    print(f"🔥 PHASE 3: STRESS TESTING ACTIVE DEFENSE ({num_requests} CONCURRENT ALERTS) 🔥")
    print("="*60 + "\n")
    print(f"[*] Simulating a massive burst of alerts from the SOAR...")
    
    # Generate dummy IPs to block
    ips = [f"10.0.0.{i}" for i in range(1, num_requests + 1)]
    
    start_time = time.time()
    
    success_count = 0
    error_count = 0
    
    # Fire off requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(send_request, ips))
        
    for res in results:
        if res == 200:
            success_count += 1
        else:
            error_count += 1
            
    end_time = time.time()
    
    print("\n" + "="*40)
    print("📊 STRESS TEST RESULTS")
    print("="*40)
    print(f"Total Requests: {num_requests}")
    print(f"Time Taken: {end_time - start_time:.2f} seconds")
    print(f"✅ Successful Blocks (200 OK): {success_count}")
    print(f"❌ Failed/Dropped (500 Error/Timeouts): {error_count}")
    
    if error_count > 0:
        print("\n[!] The server dropped or failed some requests under load!")
        print("[!] We might be hitting a Windows Firewall concurrency limit with 'netsh'.")
    else:
        print("\n[+] Success! The Waitress production server successfully handled the traffic spike!")
        
    print("\n[*] Cleaning up the dummy firewall rules created during the test... (Please wait)")
    
    # Clean up firewall rules
    for ip in ips:
        rule_name = f"Block IP {ip} from SIEM Webhook"
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"], 
            capture_output=True
        )
        
    print("[+] Cleanup complete. System is ready.")

if __name__ == "__main__":
    run_stress_test(50)
