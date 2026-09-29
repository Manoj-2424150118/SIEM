# SIEM-to-SOAR Automated Defense Pipeline: Interview Prep Guide

This document is your complete cheat sheet for technical interviews. It breaks down the architecture, the "why" behind the technical decisions, and answers common interview questions regarding this project.

## 1. Project Architecture (The Real-World Flow)
If an interviewer asks, "Walk me through your SIEM project," here is the exact flow you describe:

1. **The Attack Surface:** A native Windows OpenSSH server is exposed to the internet. 
2. **Log Generation:** When an attacker attempts to brute-force the SSH server, Windows generates authentication failure logs natively within the Windows Event Viewer.
3. **The SIEM (Elasticsearch):** An Elastic Agent (running on Windows) continuously monitors the Event Viewer. If it detects 5 authentication failures from the same IP address in under a minute, the SIEM triggers a high-severity alert.
4. **The SOAR (Tines):** The SIEM forwards the attacker's IP to the cloud SOAR platform (Tines). 
5. **Threat Intelligence Verification:** Tines (or the local Webhook) queries the **VirusTotal API**. If the IP is safe, the block is aborted to prevent False Positives. If it's malicious, the block proceeds.
6. **The Active Defense Webhook:** The SOAR sends an authenticated POST request over a secure **Ngrok Tunnel** to a local Python WSGI server (`Waitress`).
7. **Execution & Alerting:** The Python server validates the API key, executes a native Windows `netsh` command to drop all future packets from the attacker, and immediately fires a Markdown-formatted incident report to the team's **Telegram** channel.

## 2. Technical Decisions & "The Why"

**Why did you use Waitress instead of the default Flask server?**
> "Flask's default server is single-threaded and not meant for production. In a real-world botnet attack, thousands of requests hit simultaneously. Waitress is a production-grade WSGI server that handles concurrent connections, queues them properly, and prevents the Windows Firewall (`netsh`) from crashing under heavy load."

**Why did you use Ngrok?**
> "Because the SOAR (Tines) is a cloud-hosted SaaS, it cannot send HTTP POST requests directly to `localhost`. Ngrok creates a secure, encrypted tunnel that exposes the local Active Defense Node to the public internet securely."

**How did you prevent False Positives?**
> "I integrated the VirusTotal API as a native fail-safe. Before executing a firewall block, the script checks the IP's malicious score. If it has a score of 0, the script aborts the block, preventing a legitimate user or admin from being locked out of the system."

**How did you prevent firewall pollution?**
> "If an attacker hits the server rapidly, the SIEM might trigger multiple alerts for the same IP. I programmed the webhook to first run `netsh advfirewall firewall show rule` to check if a rule already exists. If it does, it skips the execution, keeping the firewall clean and performant."

## 3. Security Hardening Features
Be sure to highlight these security features you built into the project:
*   **Header Authentication:** The webhook requires a secret `x-api-key` header to accept commands, preventing random internet users from maliciously blocking IPs via your Ngrok URL.
*   **Auto-Generating Secrets:** The code automatically generates a secure, randomized 32-byte API key using Python's `secrets` library if one doesn't exist.
*   **Shell Injection Prevention:** `subprocess.run()` is executed using a strict list of arguments (e.g., `["netsh", "advfirewall", ...]`) rather than a single raw string with `shell=True`. This entirely eliminates the risk of Remote Code Execution (RCE) if an attacker somehow spoofs a malicious IP string.

## 4. The Final Codebase State
You successfully deleted all the "fake" components (the mock honeypot and the demo scripts). Your codebase is now purely real-world production code:
*   `webhook_listener.py`: The core brain.
*   `start_siem.bat`: The automated deployment script.
*   `start_tunnel.py`: The secure cloud link.
*   `attack_simulator.py`: A legitimate penetration testing script to test the strength of the actual Windows OpenSSH server.
