#!/usr/bin/env python3
"""
Tunnel Fallback System for Sonar Sniffer Family Viewer
Provides multiple options for remote access when local network isn't available.

Options (in priority order):
1. ngrok (fastest, most reliable)
2. Cloudflare Tunnel (enterprise-grade)
3. localhost.run (simple SSH tunnel)
4. serveo (SSH reverse tunnel)
5. Tailscale/Zerotier (VPN - requires setup)
"""

import os
import sys
import json
import logging
import subprocess
import time
import socket
from pathlib import Path
from typing import Optional, Dict, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TunnelType(Enum):
    """Available tunnel types."""
    NGROK = "ngrok"
    CLOUDFLARE = "cloudflare"
    LOCALHOST_RUN = "localhost.run"
    SERVEO = "serveo"
    TAILSCALE = "tailscale"
    LOCAL = "local"


class TunnelManager:
    """Manages remote access tunnels for family viewer."""
    
    def __init__(self, local_port: int = 8080):
        """Initialize tunnel manager."""
        self.local_port = local_port
        self.local_host = "localhost"
        self.active_tunnel = None
        self.tunnel_process = None
        self.tunnel_url = None
    
    def get_local_ip(self) -> str:
        """Get local IP address for network access."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "192.168.1.100"  # Fallback
    
    def check_command_available(self, command: str) -> bool:
        """Check if command is available in PATH."""
        result = subprocess.run(
            f"where {command}" if sys.platform == "win32" else f"which {command}",
            shell=True,
            capture_output=True
        )
        return result.returncode == 0
    
    # ============== TUNNEL OPTIONS ==============
    
    def setup_ngrok(self) -> Optional[str]:
        """
        Setup ngrok tunnel.
        Requires: ngrok installed and account
        URL: https://ngrok.com/
        Command: ngrok http 8080
        """
        logger.info("Attempting ngrok tunnel...")
        
        if not self.check_command_available("ngrok"):
            logger.warning("ngrok not found. Install from https://ngrok.com/")
            return None
        
        try:
            # Start ngrok
            cmd = f"ngrok http {self.local_port} --log=stdout"
            self.tunnel_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Give ngrok time to start and connect
            time.sleep(3)
            
            # Try to get URL from ngrok API
            try:
                api_response = subprocess.run(
                    'curl http://localhost:4040/api/tunnels',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if api_response.returncode == 0:
                    data = json.loads(api_response.stdout)
                    if data.get('tunnels'):
                        for tunnel in data['tunnels']:
                            if tunnel['proto'] == 'https':
                                url = tunnel['public_url']
                                logger.info(f"✓ ngrok tunnel established: {url}")
                                self.tunnel_url = url
                                self.active_tunnel = TunnelType.NGROK
                                return url
            except Exception as e:
                logger.debug(f"Could not query ngrok API: {e}")
            
            logger.info("ngrok started - watch console for URL")
            self.active_tunnel = TunnelType.NGROK
            return "ngrok-started"
        
        except Exception as e:
            logger.error(f"ngrok setup failed: {e}")
            return None
    
    def setup_cloudflare(self) -> Optional[str]:
        """
        Setup Cloudflare Tunnel.
        Requires: cloudflared CLI installed
        URL: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
        Command: cloudflared tunnel --url http://localhost:8080
        """
        logger.info("Attempting Cloudflare Tunnel...")
        
        if not self.check_command_available("cloudflared"):
            logger.warning("cloudflared not found. Install from https://developers.cloudflare.com/cloudflare-one/")
            return None
        
        try:
            cmd = f"cloudflared tunnel --url http://localhost:{self.local_port}"
            self.tunnel_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Read first few lines to find URL
            time.sleep(2)
            if self.tunnel_process.stdout:
                for _ in range(10):
                    line = self.tunnel_process.stdout.readline()
                    if "https://" in line:
                        url = line.split("https://")[1].split(" ")[0]
                        url = f"https://{url}"
                        logger.info(f"✓ Cloudflare tunnel established: {url}")
                        self.tunnel_url = url
                        self.active_tunnel = TunnelType.CLOUDFLARE
                        return url
            
            logger.info("cloudflared started - watch console for URL")
            self.active_tunnel = TunnelType.CLOUDFLARE
            return "cloudflare-started"
        
        except Exception as e:
            logger.error(f"Cloudflare setup failed: {e}")
            return None
    
    def setup_localhost_run(self) -> Optional[str]:
        """
        Setup localhost.run tunnel.
        Requires: SSH (standard on most systems)
        URL: https://localhost.run/
        No account needed - generates temporary URL
        """
        logger.info("Attempting localhost.run tunnel...")
        
        try:
            # localhost.run uses SSH reverse tunnel
            cmd = f"ssh -R 80:localhost:{self.local_port} localhost.run"
            
            logger.info(f"Running: {cmd}")
            logger.info("Watch for URL with https:// prefix in output...")
            
            self.tunnel_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info("✓ localhost.run tunnel starting")
            logger.info("  (Watch console output for public URL)")
            
            self.active_tunnel = TunnelType.LOCALHOST_RUN
            return "localhost-run-started"
        
        except Exception as e:
            logger.error(f"localhost.run setup failed: {e}")
            return None
    
    def setup_serveo(self) -> Optional[str]:
        """
        Setup serveo.net tunnel.
        Requires: SSH (standard on most systems)
        URL: https://serveo.net/
        Alternative to localhost.run
        """
        logger.info("Attempting serveo.net tunnel...")
        
        try:
            cmd = f"ssh -R 80:localhost:{self.local_port} serveo.net"
            
            logger.info(f"Running: {cmd}")
            logger.info("Watch for URL in output...")
            
            self.tunnel_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info("✓ serveo.net tunnel starting")
            logger.info("  (Watch console output for public URL)")
            
            self.active_tunnel = TunnelType.SERVEO
            return "serveo-started"
        
        except Exception as e:
            logger.error(f"serveo.net setup failed: {e}")
            return None
    
    def setup_tailscale(self) -> Optional[str]:
        """
        Setup Tailscale VPN tunnel.
        Requires: Tailscale installed on all devices
        URL: https://tailscale.com/
        Most secure - creates private network
        """
        logger.info("Attempting Tailscale setup...")
        
        if not self.check_command_available("tailscale"):
            logger.warning(
                "Tailscale not installed.\n"
                "Download from https://tailscale.com/\n"
                "Then join same Tailscale network as family members"
            )
            return None
        
        try:
            # Get Tailscale IP
            result = subprocess.run(
                "tailscale ip -4",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                tailscale_ip = result.stdout.strip().split('\n')[0]
                url = f"http://{tailscale_ip}:{self.local_port}"
                logger.info(f"✓ Tailscale address: {url}")
                logger.info("  (Share this URL with family on same Tailscale network)")
                self.tunnel_url = url
                self.active_tunnel = TunnelType.TAILSCALE
                return url
        except Exception as e:
            logger.error(f"Tailscale setup failed: {e}")
        
        return None
    
    def setup_local_network(self) -> Dict[str, str]:
        """Get local network access info."""
        local_ip = self.get_local_ip()
        
        return {
            "local": f"http://localhost:{self.local_port}",
            "network": f"http://{local_ip}:{self.local_port}",
            "bind": f"0.0.0.0:{self.local_port}"
        }
    
    # ============== ORCHESTRATION ==============
    
    def setup_fallback_tunnel(self, preferred: Optional[TunnelType] = None) -> Tuple[bool, Optional[str]]:
        """
        Try to setup a tunnel, falling back through options.
        
        Returns: (success, url)
        """
        options = [
            (TunnelType.NGROK, self.setup_ngrok),
            (TunnelType.CLOUDFLARE, self.setup_cloudflare),
            (TunnelType.LOCALHOST_RUN, self.setup_localhost_run),
            (TunnelType.SERVEO, self.setup_serveo),
            (TunnelType.TAILSCALE, self.setup_tailscale),
        ]
        
        # Try preferred first
        if preferred:
            for tunnel_type, setup_func in options:
                if tunnel_type == preferred:
                    url = setup_func()
                    if url:
                        return (True, url)
                    break
        
        # Try remaining options
        for tunnel_type, setup_func in options:
            logger.info(f"\nTrying {tunnel_type.value}...")
            url = setup_func()
            if url:
                return (True, url)
            logger.info(f"{tunnel_type.value} not available, trying next option...\n")
        
        logger.warning("All tunnel options failed - using local network only")
        return (False, None)
    
    def get_access_info(self) -> Dict:
        """Get all access information."""
        local = self.setup_local_network()
        
        return {
            "local_access": local,
            "tunnel": {
                "active": self.active_tunnel.value if self.active_tunnel else None,
                "url": self.tunnel_url
            },
            "available_tunnels": [t.value for t in TunnelType]
        }
    
    def stop(self):
        """Stop active tunnel."""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping tunnel: {e}")
                self.tunnel_process.kill()
            
            logger.info(f"Stopped {self.active_tunnel.value} tunnel")


def generate_tunnel_instruction_page(access_info: Dict) -> str:
    """Generate HTML page with tunnel instructions."""
    
    local_url = access_info['local_access']['local']
    network_url = access_info['local_access']['network']
    tunnel_url = access_info['tunnel']['url']
    tunnel_type = access_info['tunnel']['active']
    
    tunnel_section = ""
    if tunnel_url:
        tunnel_section = f"""
        <div class="access-method">
            <div class="method-icon">🌐</div>
            <h3>Remote Access (Internet)</h3>
            <p>Share this link with remote team members:</p>
            <div class="url-box">{tunnel_url}</div>
            <p class="method-type">Via {tunnel_type}</p>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sonar Sniffer - Access Methods</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #999;
            margin-bottom: 50px;
        }}
        .methods {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }}
        .access-method {{
            padding: 30px;
            border: 2px solid #667eea;
            border-radius: 12px;
            background: #f8f9fa;
        }}
        .access-method h3 {{
            color: #667eea;
            margin: 15px 0;
        }}
        .access-method p {{
            color: #666;
            line-height: 1.6;
            margin-bottom: 15px;
            font-size: 14px;
        }}
        .method-icon {{
            font-size: 40px;
            text-align: center;
            margin-bottom: 15px;
        }}
        .method-type {{
            text-align: center;
            font-size: 12px;
            color: #999;
            margin-top: 10px;
        }}
        .url-box {{
            background: white;
            border: 1px dashed #667eea;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            word-break: break-all;
            font-size: 13px;
            color: #333;
            text-align: center;
        }}
        .info-box {{
            background: #e8f0ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }}
        .info-box h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .info-box p {{
            color: #666;
            line-height: 1.6;
            font-size: 14px;
        }}
        @media (max-width: 768px) {{
            .methods {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Sonar Sniffer Family Viewer</h1>
        <p class="subtitle">Access Methods & Sharing Options</p>
        
        <div class="methods">
            <div class="access-method">
                <div class="method-icon">🖥️</div>
                <h3>Local Access</h3>
                <p>From the same computer:</p>
                <div class="url-box">{local_url}</div>
                <p class="method-type">Same machine</p>
            </div>
            
            <div class="access-method">
                <div class="method-icon">📡</div>
                <h3>Network Access</h3>
                <p>From same WiFi/office network:</p>
                <div class="url-box">{network_url}</div>
                <p class="method-type">Local network</p>
            </div>
            {tunnel_section}
        </div>
        
        <div class="info-box">
            <h3>How to Share</h3>
            <p>
                <strong>Same Location:</strong> Share local network URL above<br/>
                <strong>Remote Family:</strong> Use remote access URL (if available)<br/>
                <strong>Email/USB:</strong> Copy family_viewer_output folder directly
            </p>
        </div>
    </div>
</body>
</html>
"""
    return html


def main():
    """Demonstrate tunnel setup."""
    print("\n" + "=" * 70)
    print("SONAR SNIFFER - TUNNEL FALLBACK SYSTEM")
    print("=" * 70)
    print("\nAutomatic Remote Access Options:")
    print("1. ngrok - Instant public URL")
    print("2. Cloudflare Tunnel - Enterprise secure")
    print("3. localhost.run - Simple SSH tunnel")
    print("4. serveo.net - Alternative SSH")
    print("5. Tailscale - Private network VPN")
    print("6. Local Network - No setup required")
    print("\n" + "=" * 70)
    
    # Create manager
    manager = TunnelManager(local_port=8080)
    
    # Get local info
    print("\nLocal Network Access:")
    local_info = manager.setup_local_network()
    print(f"  Local:   {local_info['local']}")
    print(f"  Network: {local_info['network']}")
    
    # Try to setup tunnel (optional - requires external tools)
    print("\nOptional: Setting up remote tunnel...")
    success, url = manager.setup_fallback_tunnel()
    
    if success and url:
        print(f"✓ Tunnel established: {url}")
    else:
        print("ℹ Tunnel setup skipped (requires ngrok, cloudflare, or SSH)")
        print("  You can still use local/network access above")
    
    # Get complete access info
    info = manager.get_access_info()
    print("\nAccess Information:")
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
