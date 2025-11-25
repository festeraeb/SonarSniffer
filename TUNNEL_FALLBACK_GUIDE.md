# Tunnel Fallback System - Remote Access Guide

## Overview

The Sonar Sniffer server binds to **0.0.0.0:8080** and works great on local networks. For remote access (families in different locations), use tunnel fallbacks.

**Default**: `python integration_server.py` - Local network only (0.0.0.0:8080)
**With Tunnels**: `python tunnel_fallbacks.py` - Adds remote internet access

---

## Quick Comparison

| Tunnel | Speed | Setup | Pros | Cons |
|--------|-------|-------|------|------|
| **ngrok** | ⚡⚡⚡ Fast | Account + Install | Instant URL, very reliable | Requires paid plan for long URLs |
| **Cloudflare** | ⚡⚡ Good | Install + Auth | Enterprise-grade, secure | Slightly slower auth |
| **localhost.run** | ⚡⚡ Good | SSH only | No setup, no account | SSH must be open |
| **serveo.net** | ⚡ Okay | SSH only | SSH alternative | Less reliable than localhost.run |
| **Tailscale** | ⚡⚡⚡ Very Fast | Install + Join | Private network, very secure | Requires all devices install |

---

## Setup Instructions by Tunnel Type

### 1. **ngrok** (Recommended - Fastest & Most Reliable)

**Best for**: Quick public URL sharing with families

#### Setup:
```bash
# Install ngrok
# Windows: Download from https://ngrok.com/download
# Or: choco install ngrok

# Sign up for free account: https://ngrok.com/

# Download and authenticate
ngrok config add-authtoken <YOUR_AUTH_TOKEN>

# Run tunnel (while integration_server.py is running)
ngrok http 8080

# Output will show:
# Forwarding https://xxxx-xxx-xxx.ngrok.io -> http://localhost:8080
```

#### Usage:
```python
from tunnel_fallbacks import TunnelManager, TunnelType

manager = TunnelManager(local_port=8080)
success, url = manager.setup_ngrok()
# url = "https://xxxx-xxx-xxx.ngrok.io"
```

#### Share with families:
- Simple to explain: "Go to https://xxxx-xxx-xxx.ngrok.io"
- Works from anywhere with internet
- URL changes on restart (unless you upgrade)

---

### 2. **Cloudflare Tunnel** (Enterprise-Grade)

**Best for**: Permanent, professional deployment

#### Setup:
```bash
# Install cloudflared
# Windows: Download from https://developers.cloudflare.com/cloudflare-one/
# Or: choco install cloudflare-warp

# Authenticate
cloudflared tunnel login

# Create tunnel (one-time)
cloudflared tunnel create sonar-sniffer

# Configure (create config file)
# Then run:
cloudflared tunnel run sonar-sniffer
```

#### Usage:
```python
from tunnel_fallbacks import TunnelManager

manager = TunnelManager(local_port=8080)
success, url = manager.setup_cloudflare()
```

#### Share with families:
- Professional appearance (your-domain.com)
- Most secure option
- Works from anywhere
- Persistent URL

---

### 3. **localhost.run** (No Setup Required!)

**Best for**: Immediate access - no account needed

#### Setup:
```bash
# Just run (SSH must be available)
ssh -R 80:localhost:8080 localhost.run

# Output will show:
# Connect to https://random-hash.localhost.run/ whenever you are ready.
```

#### Usage:
```python
from tunnel_fallbacks import TunnelManager

manager = TunnelManager(local_port=8080)
success, url = manager.setup_localhost_run()
```

#### Share with families:
- Instant - no account or setup
- Temporary URL (changes each run)
- Works on any system with SSH
- Great for ad-hoc sharing

---

### 4. **serveo.net** (SSH Alternative)

**Best for**: Backup when localhost.run is down

#### Setup:
```bash
# Just run (SSH must be available)
ssh -R 80:localhost:8080 serveo.net

# Output will show:
# Forwarding HTTP traffic from https://random-hash.serveo.net
```

#### Usage:
```python
from tunnel_fallbacks import TunnelManager

manager = TunnelManager(local_port=8080)
success, url = manager.setup_serveo()
```

#### Share with families:
- Same as localhost.run
- Alternative provider
- Useful as backup option

---

### 5. **Tailscale VPN** (Most Secure - Private Network)

**Best for**: SAR teams with consistent membership

#### Setup:
```bash
# All users install Tailscale from https://tailscale.com/

# User 1 (Server):
tailscale up

# Get IP address:
tailscale ip -4
# Returns: 100.xx.xx.xx

# Share URL with other team members (same network):
# http://100.xx.xx.xx:8080

# User 2+ (Family):
tailscale up
# Joins same Tailscale network
# Can now access http://100.xx.xx.xx:8080
```

#### Usage:
```python
from tunnel_fallbacks import TunnelManager

manager = TunnelManager(local_port=8080)
success, url = manager.setup_tailscale()
# url = "http://100.xx.xx.xx:8080"
```

#### Advantages:
- ✅ Most secure - private network
- ✅ Very fast - direct connection
- ✅ No external services
- ✅ Works behind any firewall
- ⚠️ All users must install Tailscale

---

## Combined Usage

### Start Server + Auto-Detect Tunnel

```python
from integration_server import FamilyViewerServer
from tunnel_fallbacks import TunnelManager

# Start local server
server = FamilyViewerServer(port=8080)
server.start()

# Setup best available tunnel
tunnel = TunnelManager(local_port=8080)
success, url = tunnel.setup_fallback_tunnel()

if success:
    print(f"Remote URL: {url}")
else:
    print("Local network only")

# Keep running
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    tunnel.stop()
```

### Manual Orchestration

```bash
# Terminal 1: Start main server
python integration_server.py

# Terminal 2: Start tunnel fallback
python tunnel_fallbacks.py

# Now families can access via:
# - Local: http://localhost:8080
# - Network: http://192.168.x.x:8080
# - Remote: https://xxx.ngrok.io (if ngrok running)
```

---

## Troubleshooting

### "Connection refused"
- Ensure `integration_server.py` is still running
- Check server logs for errors
- Try `http://127.0.0.1:8080` instead of localhost

### Tunnel not working
- Verify internet connection
- Check if tunnel provider is available (some may be down)
- Try next fallback option
- Use local network access as backup

### SSH tunnel error (localhost.run/serveo)
- Ensure SSH is installed (`ssh --version`)
- Check if SSH port 22 is blocked by firewall
- Some corporate networks block SSH

### ngrok authentication failed
- Verify authtoken is correct
- Check ngrok account status
- Try refreshing token from dashboard

### Tailscale not found
- Install from https://tailscale.com/
- Ensure all team members are on same Tailscale account/network
- Check Tailscale is running: `tailscale status`

---

## Security Considerations

| Tunnel | Encryption | Privacy | Recommended For |
|--------|-----------|---------|-----------------|
| ngrok | ✅ HTTPS | ⚠️ ngrok can see traffic | Testing, demos |
| Cloudflare | ✅ HTTPS | ✅ Very private | Production, families |
| localhost.run | ✅ HTTPS | ⚠️ SSH tunnel | Quick testing |
| serveo.net | ✅ HTTPS | ⚠️ SSH tunnel | Backup only |
| Tailscale | ✅ HTTPS | ✅✅ Private network | SAR teams, most secure |

---

## Recommended Setups

### For Quick Family Sharing (No Prep)
```bash
# Terminal 1
python integration_server.py

# Terminal 2 (if you have ngrok installed)
ngrok http 8080

# Share ngrok URL with family
```

### For Professional SAR Team
```bash
# Setup once
cloudflared tunnel create sonar-sniffer

# Run server
python integration_server.py

# Run tunnel
cloudflared tunnel run sonar-sniffer

# Use permanent domain with family
```

### For Internal SAR Team (Most Secure)
```bash
# All team members install Tailscale once
# Then just run:
python integration_server.py

# Family accesses via Tailscale private network
```

---

## Automation Script

Here's a helper script to auto-select tunnel:

```python
# auto_tunnel.py
from tunnel_fallbacks import TunnelManager
from integration_server import FamilyViewerServer
import signal
import sys

def signal_handler(sig, frame):
    """Handle Ctrl+C."""
    print("\nShutting down...")
    if tunnel:
        tunnel.stop()
    if server:
        server.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Start server
print("Starting Sonar Sniffer Family Viewer...")
server = FamilyViewerServer(port=8080)
if not server.start():
    sys.exit(1)

# Auto-detect best tunnel
print("\nSetting up remote access...")
tunnel = TunnelManager(local_port=8080)
success, url = tunnel.setup_fallback_tunnel()

if success and url:
    print(f"\n✓ Remote Access: {url}")
else:
    print("\nℹ Using local network only")

print("Server running. Press Ctrl+C to stop.\n")

# Keep running
import time
try:
    while True:
        time.sleep(1)
except:
    pass
```

Then just run:
```bash
python auto_tunnel.py
```

---

## Summary

| Need | Tunnel | Command |
|------|--------|---------|
| Quick test | localhost.run | `ssh -R 80:localhost:8080 localhost.run` |
| Professional | Cloudflare | `cloudflared tunnel run sonar-sniffer` |
| Fast & simple | ngrok | `ngrok http 8080` |
| Private network | Tailscale | `tailscale up` + share IP |
| Local only | None | Just use 0.0.0.0:8080 |

**Recommendation**: Start with **localhost.run** for immediate family sharing. Use **Cloudflare** for permanent deployments. Use **Tailscale** for secure internal teams.
