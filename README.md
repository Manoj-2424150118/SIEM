# Automated Threat Hunting & Incident Response Pipeline

This project implements a fully automated, closed-loop SIEM to SOAR pipeline. When an attacker attempts to brute force SSH, the system automatically detects the threat, verifies the IP against Threat Intelligence (VirusTotal), alerts the team via Slack, and actively blocks the attacker using local firewall rules.

## Project Structure

- `attack_simulator.py`: Python script to simulate SSH brute force attacks to trigger your detection rules.
- `webhook_listener.py`: Flask-based webhook listener acting as the "Active Defense" node to receive SOAR instructions and block the malicious IP via `ufw`.
- `requirements.txt`: Python dependencies needed for the scripts.

## Setup Instructions

### Phase 1: Infrastructure Preparation (Linux VM)

1. Provision a Linux VM (Ubuntu recommended). This will be both the "victim" and the active defense node.
2. Clone this folder/files onto the VM.
3. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
4. Start the Active Defense webhook listener on the VM:
   ```bash
   python3 webhook_listener.py
   ```
   *Ensure port 5000 is open in your cloud provider's network security group.*

### Phase 2: SIEM Setup (Elastic Security)

1. Deploy Elastic Cloud.
2. Use **Integrations** in Elastic to deploy an **Elastic Agent** onto your Linux VM. Select the "System" integration to ensure auth logs (`/var/log/auth.log`) are ingested.
3. Once data is flowing, go to **Rules** -> **Create new rule** in Elastic Security.
   - **Rule Type**: Custom Query
   - **Index**: `logs-*` or `logs-system.auth-*`
   - **Query**: `event.action: "ssh_login" AND outcome: "failure"`
   - **Threshold**: When query results > 5 from the same `source.ip` within 5 minutes.
4. Under **Actions**, create a new **Webhook Connector** pointing to the URL you'll generate in Phase 3.

### Phase 3: SOAR Configuration (Tines)

Sign up for Tines Community Edition and build your Storyboard with the following components connected sequentially:

1. **Webhook (Trigger)**
   - Drag a Webhook action. Copy the provided URL.
   - Paste this URL into your Elastic Security Rule Action from Phase 2.
2. **Event Transformation (Parse JSON)**
   - Name it "Extract Malicious IP".
   - Use Tines formulas to parse the Elastic payload and grab the attacker's source IP.
3. **HTTP Request (VirusTotal Intel)**
   - URL: `https://www.virustotal.com/api/v3/ip_addresses/<<ip_variable>>`
   - Headers: `x-apikey: YOUR_VIRUSTOTAL_API_KEY`
4. **Trigger (Decision Logic)**
   - Add a Trigger action that inspects the output of the VirusTotal HTTP request.
   - Rules: `last_analysis_stats.malicious` is greater than `0`.
5. **HTTP Request (Slack Alert)**
   - URL: Your Slack Incoming Webhook URL.
   - Method: POST
   - Payload:
     ```json
     {
       "text": "🚨 *High Severity Alert* 🚨\nBrute force detected from IP: <<ip_variable>>.\nVirusTotal Malicious Score: <<score>>.\nAction taken: Automated Block initiated."
     }
     ```
6. **HTTP Request (Active Defense - Block IP)**
   - URL: `http://<YOUR_VM_PUBLIC_IP>:5000/webhook`
   - Method: POST
   - Content-Type: `application/json`
   - Payload:
     ```json
     {
       "ip": "<<ip_variable>>"
     }
     ```

### Testing the Pipeline

Once everything is connected, use the `attack_simulator.py` script from another machine (or even locally) to trigger the alerts:

```bash
python3 attack_simulator.py --target <YOUR_VM_IP> --user root --count 10
```

Watch the Elastic SIEM register the failures, Tines orchestrate the intel lookup and Slack notification, and finally the `webhook_listener.py` successfully block the IP using UFW!