# Lab Network Setup & Windows Firewall Configuration

This guide explains how to establish an isolated VirtualBox Host-Only lab network between your Windows Host (running the SIEM Dashboard inside Docker Desktop) and your Kali Linux VM (running the Autonomous Server Log Agent).

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│ Windows Host (192.168.56.1)                                     │
│                                                                 │
│   VirtualBox Host-Only Ethernet Adapter: 192.168.56.1           │
│   Windows Firewall: Allows TCP 8431 from 192.168.56.0/24        │
│                                                                 │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │ Docker Desktop                                            │ │
│   │   • Nginx Reverse Proxy (0.0.0.0:8431 -> 80)              │ │
│   │   • Flask SIEM Backend (internal port 5000)               │ │
│   │   • MongoDB 8.0 & Redis 7 Streams                         │ │
│   └───────────────────────────────────────────────────────────┘ │
└──────────────────────────────▲──────────────────────────────────┘
                               │
            VirtualBox Host-Only Network (192.168.56.0/24)
            Isolated Private Lab Subnet
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│ Kali Linux VM (192.168.56.101 or DHCP)                          │
│                                                                 │
│   • eth1 / enp0s8: 192.168.56.x                                 │
│   • Systemd Service: siem-agent                                 │
│   • Monitors: /var/log/auth.log                                 │
│   • Ships events to: http://192.168.56.1:8431/api/v1            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. VirtualBox Network Configuration

To allow the Kali VM to access the Windows host while remaining isolated:

1. Open **VirtualBox Manager**.
2. Select your **Kali Linux** virtual machine and click **Settings** (`Ctrl+S`).
3. Navigate to **Network**:
   - **Adapter 1**:
     - Enable: Checked
     - Attached to: **NAT** (allows Kali to update packages via internet).
   - **Adapter 2**:
     - Enable: Checked
     - Attached to: **Host-only Adapter**
     - Name: `VirtualBox Host-Only Ethernet Adapter` (or `vboxnet0` on Mac/Linux)
     - Promiscuous Mode: `Deny` (or `Allow VMs`)
4. Click **OK** and start the Kali VM.
5. In Kali, verify the IP address:
   ```bash
   ip addr show
   ```
   You should see two interfaces: e.g. `eth0` (NAT `10.0.2.x`) and `eth1` (Host-Only `192.168.56.x`).

---

## 3. Windows Host-Only Adapter Verification

On the Windows host, verify the Host-Only adapter has IP `192.168.56.1`:

Open PowerShell (as Administrator) and run:
```powershell
Get-NetIPAddress -InterfaceAlias "*Host-Only*" | Format-Table IPAddress, InterfaceAlias, IPv4Address
```

If it is not configured, set it in VirtualBox -> Tools -> Network Manager:
- IPv4 Address: `192.168.56.1`
- IPv4 Network Mask: `255.255.255.0`
- DHCP Server: Enabled (or static IPs assigned)

---

## 4. Windows Firewall Inbound Rule

By default, Windows Defender Firewall blocks inbound traffic on non-standard ports like `8431`.
To allow only the Kali VM (and any VM on the Host-Only subnet) to reach the SIEM dashboard without exposing the port to your entire physical LAN:

Run the following command in **PowerShell (Run as Administrator)**:

```powershell
New-NetFirewallRule `
  -DisplayName "SIEM Dashboard Lab (TCP 8431)" `
  -Direction Inbound `
  -LocalPort 8431 `
  -Protocol TCP `
  -Action Allow `
  -RemoteAddress 192.168.56.0/24 `
  -Profile Any `
  -Description "Allows Host-Only VMs to communicate with the SIEM Dashboard and Agent API"
```

To verify the rule was created:
```powershell
Get-NetFirewallRule -DisplayName "SIEM Dashboard Lab*" | Format-List DisplayName, Enabled, Direction, Action
```

If you ever need to remove the rule:
```powershell
Remove-NetFirewallRule -DisplayName "SIEM Dashboard Lab (TCP 8431)"
```

---

## 5. Verify Connectivity from Kali Linux

From your Kali Linux terminal, run:

### Test 1: ICMP Ping
```bash
ping -c 3 192.168.56.1
```
*(If ping fails, Windows Firewall may drop ICMP by default. Proceed to Test 2 to verify TCP port 8431).*

### Test 2: Nmap Port Check
```bash
nmap -p 8431 192.168.56.1
```
Expected output:
```text
PORT     STATE SERVICE
8431/tcp open  unknown
```

### Test 3: HTTP API Health Probe
```bash
curl -I http://192.168.56.1:8431/
```
Expected output:
```text
HTTP/1.1 200 OK
Server: nginx/...
```

---

## 6. TLS / HTTPS Hardening (Production & Secure Lab)

To run the agent with TLS encryption and certificate verification:

### Step 1: Generate a Self-Signed Certificate on Windows
```powershell
# In the project directory:
openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
  -keyout conf/nginx/ssl/siem.key `
  -out conf/nginx/ssl/siem.crt `
  -subj "/CN=192.168.56.1/O=SIEM Lab/C=US"
```

### Step 2: Configure Nginx for SSL
Update `conf/nginx/prod.nginx` to listen on port `8443 ssl` with `ssl_certificate` and `ssl_certificate_key`. Update `compose.yml` to expose port `8443:443`.

### Step 3: Install CA / Certificate on Kali Linux
Copy `siem.crt` to Kali Linux:
```bash
sudo cp siem.crt /usr/local/share/ca-certificates/siem.crt
sudo update-ca-certificates
```

In `agent/config.yaml`:
```yaml
siem_url: "https://192.168.56.1:8443/api/v1"
verify_ssl: true
```
This guarantees full end-to-end transport encryption with strict certificate validation.
