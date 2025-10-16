#!/usr/bin/env python3
"""
SonarSniffer Web Application Module

Provides a Flask-based web interface for sonar data analysis and visualization.
"""

import os
import sys
from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS

# Add the package to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sonarsniffer import LicenseManager, WebDashboardGenerator

class SonarWebApp:
    """Flask web application for SonarSniffer"""

    def __init__(self, data=None):
        self.app = Flask(__name__)
        CORS(self.app)
        self.data = data
        self.generator = WebDashboardGenerator()
        self.license_mgr = LicenseManager()

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            if not self.license_mgr.is_valid():
                return self._license_page()

            if not self.data:
                return self._upload_page()

            return self._dashboard_page()

        @self.app.route('/upload', methods=['POST'])
        def upload():
            if not self.license_mgr.is_valid():
                return jsonify({'error': 'Invalid license'}), 403

            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No file provided'}), 400

            # Save uploaded file temporarily
            temp_path = f'/tmp/{file.filename}'
            file.save(temp_path)

            try:
                # Parse the file
                from sonarsniffer import SonarParser
                parser = SonarParser()
                self.data = parser.parse_file(temp_path)

                # Clean up
                os.remove(temp_path)

                return jsonify({'success': True, 'message': 'File processed successfully'})

            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/status')
        def status():
            license_status = self.license_mgr.get_status()
            return jsonify({
                'license': license_status,
                'data_loaded': self.data is not None
            })

    def _license_page(self):
        """Render license information page"""
        status = self.license_mgr.get_status()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SonarSniffer - License Required</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .license-box {{ border: 1px solid #ccc; padding: 20px; border-radius: 5px; }}
                .contact {{ color: #0066cc; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>SonarSniffer Professional</h1>
            <div class="license-box">
                <h2>License Required</h2>
                <p>Status: {'Trial' if status['is_trial'] else 'Licensed'}</p>
                <p>Days remaining: {status['days_remaining']}</p>
                <p>Contact: <span class="contact">{status['contact']}</span></p>
                <p>Please contact the above email for licensing information.</p>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)

    def _upload_page(self):
        """Render file upload page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SonarSniffer - Upload Data</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .upload-form { border: 1px solid #ccc; padding: 20px; border-radius: 5px; }
                input[type="file"] { margin: 10px 0; }
                button { background: #0066cc; color: white; padding: 10px 20px; border: none; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>SonarSniffer Professional</h1>
            <div class="upload-form">
                <h2>Upload Sonar Data File</h2>
                <form id="uploadForm" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".rsd,.son,.xtf" required>
                    <br><br>
                    <button type="submit">Process File</button>
                </form>
                <div id="status"></div>
            </div>

            <script>
                document.getElementById('uploadForm').onsubmit = async (e) => {{
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const status = document.getElementById('status');

                    status.textContent = 'Processing...';

                    try {{
                        const response = await fetch('/upload', {{
                            method: 'POST',
                            body: formData
                        }});

                        const result = await response.json();
                        if (result.success) {{
                            status.textContent = 'File processed successfully! Refreshing...';
                            setTimeout(() => location.reload(), 1000);
                        }} else {{
                            status.textContent = 'Error: ' + result.error;
                        }}
                    }} catch (error) {{
                        status.textContent = 'Error: ' + error.message;
                    }}
                }};
            </script>
        </body>
        </html>
        """
        return render_template_string(html)

    def _dashboard_page(self):
        """Render the main dashboard"""
        # Generate dashboard HTML using the existing generator
        dashboard_html = self.generator.generate_dashboard_html(self.data)
        return dashboard_html

    def run(self, host='localhost', port=8080, debug=False):
        """Run the Flask application"""
        print(f"Starting SonarSniffer web server at http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def main():
    """Main entry point for web application"""
    import argparse

    parser = argparse.ArgumentParser(description='SonarSniffer Web Application')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--file', help='Sonar data file to load initially')

    args = parser.parse_args()

    # Check license
    license_mgr = LicenseManager()
    if not license_mgr.is_valid():
        print("ERROR: No valid license found.")
        print(f"Trial days remaining: {license_mgr.get_trial_days_remaining()}")
        print(f"Contact: {license_mgr.get_contact_info()}")
        return 1

    data = None
    if args.file:
        if not os.path.exists(args.file):
            print(f"ERROR: File not found: {args.file}")
            return 1

        print(f"Loading sonar file: {args.file}")
        try:
            from sonarsniffer import SonarParser
            parser = SonarParser()
            data = parser.parse_file(args.file)
            print("File loaded successfully")
        except Exception as e:
            print(f"ERROR: Failed to load file: {e}")
            return 1

    # Start web app
    app = SonarWebApp(data)
    app.run(host=args.host, port=args.port, debug=args.debug)

    return 0

if __name__ == '__main__':
    sys.exit(main())