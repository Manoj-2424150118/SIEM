import socket
import paramiko
import threading
import time

class FakeSSHServer(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        # Always fail authentication to simulate brute force logging
        print(f"[-] HONEYPOT: Failed password for {username} with password '{password}'")
        return paramiko.AUTH_FAILED
    
    def get_allowed_auths(self, username):
        return "password"
    
    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

def start_honeypot():
    # Generate a temporary RSA key for the honeypot
    host_key = paramiko.RSAKey.generate(2048)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('127.0.0.1', 2222))
    server_socket.listen(100)
    
    print("========================================================")
    print("🍯 ACTIVE DEFENSE HONEYPOT (SSH SERVER) STARTED 🍯")
    print("========================================================")
    print("[*] Listening for malicious SSH connections on port 2222...\n")
    
    def handle_client(client, addr):
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)
        server = FakeSSHServer()
        try:
            transport.start_server(server=server)
            # Wait for auth to fail
            channel = transport.accept(20)
        except paramiko.SSHException:
            pass
        finally:
            transport.close()
            
    try:
        while True:
            client, addr = server_socket.accept()
            # print(f"[*] Incoming connection from {addr[0]}:{addr[1]}")
            client_thread = threading.Thread(target=handle_client, args=(client, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down honeypot...")
        server_socket.close()

if __name__ == "__main__":
    start_honeypot()
