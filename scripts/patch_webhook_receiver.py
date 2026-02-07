#!/usr/bin/env python3
"""Simple webhook receiver for patch approvals.

This is an example server intended to run on a trusted host and receives
POSTs from the telemetry server when a patch is approved. The payload is
expected to contain a patch object. The receiver verifies the HMAC signature
using SONARSNIFFER_PATCH_SECRET and writes approved patches to
patches/approved/ for later processing.

Use via: python scripts/patch_webhook_receiver.py --port 8080
"""

import argparse
import json
import os
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

SECRET = os.environ.get('SONARSNIFFER_PATCH_SECRET')
OUT_DIR = os.path.join(os.getcwd(), 'patches', 'approved')
os.makedirs(OUT_DIR, exist_ok=True)

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length)
        sig = self.headers.get('X-SonarSniffer-Signature')
        if SECRET and sig:
            mac = hmac.new(SECRET.encode('utf-8'), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, sig):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b'Invalid signature')
                return
        try:
            patch = json.loads(body.decode('utf-8'))
            pid = patch.get('id') or 'unknown'
            with open(os.path.join(OUT_DIR, f'{pid}.json'), 'w', encoding='utf-8') as fh:
                json.dump(patch, fh, indent=2)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as ex:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(str(ex).encode('utf-8'))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8080)
    args = p.parse_args()
    httpd = HTTPServer(('0.0.0.0', args.port), Handler)
    print('Listening on port', args.port)
    httpd.serve_forever()
