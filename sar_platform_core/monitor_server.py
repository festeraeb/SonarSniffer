"""
SAR Platform Server Monitor
Monitors API server health and displays survey submissions in real-time
"""

import requests
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path

API_PORT = 8000
API_URL = f"http://localhost:{API_PORT}"
CHECK_INTERVAL = 5  # Check every 5 seconds
LAST_RESPONSE_COUNT = 0

def print_status(message, status_type="info"):
    """Print formatted status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status_type == "success":
        print(f"[{timestamp}] ✓ {message}")
    elif status_type == "error":
        print(f"[{timestamp}] ✗ {message}")
    elif status_type == "warning":
        print(f"[{timestamp}] ⚠ {message}")
    else:
        print(f"[{timestamp}] ℹ {message}")

def check_server_health():
    """Check if API server is responding"""
    try:
        response = requests.get(f"{API_URL}/docs", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_survey_stats():
    """Get current survey response statistics"""
    try:
        response = requests.get(f"{API_URL}/api/survey/stats", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('total_responses', 0)
    except:
        pass
    return None

def get_latest_response():
    """Get the most recent survey response"""
    try:
        response = requests.get(f"{API_URL}/api/survey/responses", timeout=2)
        if response.status_code == 200:
            data = response.json()
            responses = data.get('data', [])
            if responses:
                # Get the most recent response
                latest = responses[-1]
                return latest
    except:
        pass
    return None

def display_response(response):
    """Display a survey response in human-readable format"""
    print("\n" + "="*80)
    print("📋 NEW SURVEY RESPONSE RECEIVED")
    print("="*80)
    print(f"Response ID: {response.get('id')}")
    print(f"Submitted: {response.get('submission_time')}")
    print(f"Contact: {response.get('contact_name', 'N/A')} ({response.get('contact_email', 'N/A')})")
    print(f"Organization: {response.get('organization_type', 'N/A')}")
    print(f"Team Size: {response.get('team_size', 'N/A')}")
    print(f"Experience: {response.get('years_experience', 'N/A')}")
    
    # Show key responses
    if response.get('incidents_per_year'):
        print(f"Incidents/Year: {response.get('incidents_per_year')}")
    if response.get('other_feedback'):
        print(f"Feedback: {response.get('other_feedback')[:100]}...")
    print("="*80 + "\n")

def monitor_server():
    """Main monitoring loop"""
    global LAST_RESPONSE_COUNT
    
    print("\n" + "="*80)
    print("🚀 SAR PLATFORM SERVER MONITOR")
    print("="*80)
    print(f"Monitoring API at {API_URL}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print("Press Ctrl+C to stop monitoring")
    print("="*80 + "\n")
    
    server_was_down = False
    last_checked_response = None
    
    while True:
        try:
            # Check server health
            is_healthy = check_server_health()
            
            if is_healthy:
                if server_was_down:
                    print_status("Server is back online!", "success")
                    server_was_down = False
                
                # Get survey stats
                response_count = get_survey_stats()
                if response_count is not None:
                    if response_count > LAST_RESPONSE_COUNT:
                        # New response received
                        new_responses = response_count - LAST_RESPONSE_COUNT
                        print_status(f"Survey responses: {response_count} (+{new_responses} new)", "success")
                        
                        # Display the new response
                        latest = get_latest_response()
                        if latest and latest.get('id') != last_checked_response:
                            display_response(latest)
                            last_checked_response = latest.get('id')
                        
                        LAST_RESPONSE_COUNT = response_count
                    else:
                        print_status(f"Server healthy | Total responses: {response_count}", "success")
                else:
                    print_status("Server healthy | Could not fetch stats", "warning")
            else:
                if not server_was_down:
                    print_status("Server is DOWN - waiting for reconnection...", "error")
                    server_was_down = True
                else:
                    print_status("Still waiting for server...", "warning")
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n" + "="*80)
            print_status("Monitor stopped by user", "warning")
            print("="*80)
            break
        except Exception as e:
            print_status(f"Unexpected error: {str(e)}", "error")
            time.sleep(CHECK_INTERVAL)

def start_api_server():
    """Start the API server in background"""
    try:
        print_status("Attempting to start API server...", "info")
        # This will be called from the main script that already has the server running
        # Just notify the user
        print_status("Make sure the API server is running!", "warning")
    except Exception as e:
        print_status(f"Could not start server: {e}", "error")

if __name__ == "__main__":
    # Give user a moment to see the banner
    time.sleep(1)
    
    # Start monitoring
    monitor_server()
