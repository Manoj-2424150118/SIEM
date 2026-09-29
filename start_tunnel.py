import os
import sys
from pyngrok import ngrok
from dotenv import load_dotenv

load_dotenv()

def start_secure_tunnel():
    print("\n" + "="*60)
    print("🌐 PHASE 5: SECURE PUBLIC TUNNEL (NGROK) 🌐")
    print("="*60 + "\n")
    
    auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if not auth_token:
        print("[!] ERROR: No NGROK_AUTH_TOKEN found in your .env file!")
        print("    Ngrok requires a free auth token to expose HTTP tunnels.")
        print("    1. Go to https://dashboard.ngrok.com/signup")
        print("    2. Copy your Auth Token from the dashboard.")
        print("    3. Add this line to your .env file: NGROK_AUTH_TOKEN=your_token_here")
        print("    4. Run this script again.")
        sys.exit(1)
        
    print("[*] Authenticating with Ngrok...")
    ngrok.set_auth_token(auth_token)
    
    print("[*] Opening Secure Public Tunnel to local port 5001...")
    # Open a HTTP tunnel on the default port 80, routing to localhost:5001
    public_url = ngrok.connect(5001, "http").public_url
    
    print("\n" + "="*60)
    print(f"✅ TUNNEL ACTIVE!")
    print(f"🔗 Public URL: {public_url}")
    print("="*60 + "\n")
    
    print("To link the Tines SOAR to your local machine, update your Tines HTTP Request action with:")
    print(f"URL: {public_url}/webhook")
    print("\n(Press CTRL+C to close the tunnel)\n")
    
    try:
        # Block until CTRL-C or some other terminating event
        ngrok_process = ngrok.get_ngrok_process()
        ngrok_process.proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Shutting down secure tunnel...")
        ngrok.kill()
        print("[+] Tunnel closed.")

if __name__ == "__main__":
    start_secure_tunnel()
