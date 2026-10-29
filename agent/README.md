# SIEM Autonomous Linux Server Log Agent

Lightweight, resilient Linux log collection agent designed for standalone deployment on Kali Linux, Debian, and Ubuntu servers. Automatically monitors authentication events, spools events locally in a durable SQLite database during network disconnects, and ships telemetry and security events to the SIEM Dashboard.

---

## Features

- **Continuous Auth Log Tailing**: Monitors `/var/log/auth.log` (with automatic inode/rotation tracking).
- **Security Event Detection**:
  - SSH Failed Logins (`login_failure` / `brute_force`)
  - SSH Invalid Users (`login_failure`)
  - SSH Successful Logins (`login_success`)
  - Sudo Privilege Escalation (`privilege_escalation`)
- **Offline Resilience & Zero Data Loss**: Durable local SQLite spool queue (`spool.db`). If the SIEM or network drops, logs remain safely spooled and replay in chronological order once connectivity resumes.
- **Deduplication Idempotency**: Generates deterministic UUIDv5 event IDs based on log content and timestamps, ensuring repeated transmissions never create duplicate database records or false alert storms.
- **Heartbeat & System Telemetry**: Periodically sends CPU, RAM, disk utilization, and queue depth telemetry to keep the agent status `online` in the SIEM Dashboard.
- **Token Authentication**: Secure bearer token authentication with constant-time cryptographic verification on the server.

---

## 1. Quick Start on Kali Linux

### Step 1: Copy Agent Files to Kali Linux

On Kali Linux, create a dedicated directory and copy the agent files:

```bash
mkdir -p ~/siem-agent
cd ~/siem-agent
# Copy agent.py, requirements.txt, and config.yaml.example into this directory
```

### Step 2: Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Register the Agent in SIEM

1. Open your browser on the host or Kali VM: `http://192.168.56.1:8431/agents`
2. Click **Register New Agent**.
3. Fill in:
   - **Hostname**: `kali-attacker` (or your Kali hostname)
   - **Environment**: `Kali Lab`
   - **Operating System**: `Linux (Kali)`
4. Click **Create Agent**.
5. Copy the generated **Bearer Token** (`siem_agt_...`) — **Note: This token is displayed only once!**

*(Alternative: Register directly from Kali using curl)*
```bash
# Login to get admin JWT:
TOKEN=$(curl -s -X POST http://192.168.56.1:8431/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ChangeMe123!"}' | jq -r '.access_token')

# Register agent:
curl -s -X POST http://192.168.56.1:8431/api/v1/agents/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"kali","os":"Kali Linux 2024","environment":"lab"}' | jq .
```

### Step 4: Configure the Agent

Copy `config.yaml.example` to `config.yaml`:

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

Set the values:
```yaml
siem_url: "http://192.168.56.1:8431/api/v1"
agent_id: "agt_YOUR_AGENT_ID"
agent_token: "siem_agt_YOUR_TOKEN"
auth_log_path: "/var/log/auth.log"
heartbeat_interval: 30
spool_db_path: "spool.db"
agent_version: "1.0.0"
verify_ssl: true
```

### Step 5: Run the Agent

Because `/var/log/auth.log` requires root read permissions:

```bash
sudo ./venv/bin/python3 agent.py --config config.yaml
```

You should see logs indicating:
```text
[INFO] Starting SIEM Log Agent for kali [ID: agt_...]
[INFO] SIEM Gateway: http://192.168.56.1:8431/api/v1
[INFO] Monitoring Log: /var/log/auth.log
[INFO] Heartbeat acknowledged by SIEM gateway
[INFO] Seeking to end of /var/log/auth.log
```

Check the SIEM Dashboard at `http://192.168.56.1:8431/agents` — your agent will now display **ONLINE** with active CPU/RAM/Disk metrics!

---

## 2. Running as a Systemd Background Service

To keep the agent running persistently across reboots:

1. Create `/etc/systemd/system/siem-agent.service`:

```ini
[Unit]
Description=SIEM Autonomous Linux Server Log Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/kali/siem-agent
ExecStart=/home/kali/siem-agent/venv/bin/python3 /home/kali/siem-agent/agent.py --config /home/kali/siem-agent/config.yaml
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable siem-agent
sudo systemctl start siem-agent
sudo systemctl status siem-agent
```

View live logs:
```bash
sudo journalctl -u siem-agent -f
```

---

## 3. Simulating Security Attacks on Kali

Once the agent is active, simulate real attacks to verify event ingestion and detection rules in the SIEM:

### Attack 1: SSH Brute Force Simulation
Generate authentication failures against Kali's SSH service:

```bash
# Using Hydra:
hydra -l root -P /usr/share/wordlists/metasploit/unix_passwords.txt 127.0.0.1 ssh -t 4

# Or using an SSH loop:
for i in {1..8}; do
  sshpass -p "wrongpassword$i" ssh -o StrictHostKeyChecking=no fakeuser$i@127.0.0.1 true 2>/dev/null
done
```

**Result in SIEM**:
- Agent intercepts failed logins in `/var/log/auth.log`.
- Events are sent to `/v1/agents/ingest`.
- Redis Streams distributes events to the Correlation Engine.
- An alert is generated: `SSH Brute Force Detected`!

### Attack 2: Sudo Privilege Escalation
Run commands via sudo:

```bash
sudo whoami
sudo cat /etc/shadow
```

**Result in SIEM**:
- Agent captures `sudo: ... COMMAND=...` events.
- Classified as `privilege_escalation` with `agent_id` context.

---

## 4. Offline Spooling & Resilience Verification

To verify that events are not lost when the SIEM is unreachable:

1. Stop the SIEM backend or disconnect network:
   ```bash
   # On Windows:
   docker compose stop backend
   ```
2. Trigger failed SSH attempts on Kali.
3. Observe agent logs:
   ```text
   [WARNING] Ingestion failed (Connection error). Retrying next cycle...
   ```
4. Query the SQLite spool database on Kali:
   ```bash
   sqlite3 spool.db "SELECT count(*) FROM event_spool;"
   ```
5. Restart the SIEM backend:
   ```bash
   docker compose start backend
   ```
6. The agent automatically flushes the queue in batches and deletes acknowledged events from `spool.db`.
7. Refresh the SIEM Dashboard — all events are present without duplicates!
