# SAR Platform Server Monitoring

## Quick Start

### Option 1: Full Startup with Monitor (Recommended)
Open PowerShell **as Administrator** and run:
```powershell
cd c:\Temp\Garminjunk\sar_platform_core
.\start_server_with_monitor.ps1
```

This will:
- Start the API server in background
- Start the monitor in the current window
- Display survey submissions in real-time
- Show server health status every 5 seconds

### Option 2: Manual Startup

**Terminal 1 - Start API Server:**
```powershell
# Run as Administrator for port 80 support
cd c:\Temp\Garminjunk\sar_platform_core
conda run -p C:\Users\feste\Miniconda3 python intake_api.py
```

**Terminal 2 - Start Monitor:**
```powershell
cd c:\Temp\Garminjunk\sar_platform_core
conda run -p C:\Users\feste\Miniconda3 python monitor_server.py
```

## Monitor Output

The monitor displays:
- **Server Health** - Green checkmark if running, red X if down
- **Response Count** - Total survey submissions received
- **New Submissions** - Alert when new responses arrive
- **Response Details** - Shows contact info, organization, feedback
- **Timestamps** - When submissions were received

### Example Output:
```
[14:32:15] ✓ Server healthy | Total responses: 2
[14:33:20] ✓ Survey responses: 3 (+1 new)
================================================================================
📋 NEW SURVEY RESPONSE RECEIVED
================================================================================
Response ID: d5cd8c4f-522b-4f0f-b3df-377e84accf01
Submitted: 2025-11-27T04:33:20.123456
Contact: Jane Smith (jane.smith@sarteam.org)
Organization: Volunteer SAR Team
Team Size: 10-20 members
Experience: 5-10 years
Incidents/Year: 5-10
================================================================================
```

## API Health Check

The API now has a health check endpoint:
```
GET http://localhost:8000/api/health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-27T04:33:20.123456+00:00",
  "version": "1.0.0"
}
```

## Keeping Server Running 24/7

To run the server continuously in the background even after closing PowerShell:

### Option 1: Use Task Scheduler (Windows)
1. Create a batch file: `c:\Temp\Garminjunk\sar_platform_core\run_api.bat`
   ```batch
   @echo off
   cd /d c:\Temp\Garminjunk\sar_platform_core
   conda run -p C:\Users\feste\Miniconda3 python intake_api.py
   ```
2. Create a scheduled task to run it on startup or manually

### Option 2: Run as Windows Service
Use NSSM (Non-Sucking Service Manager) to wrap the Python app as a service

### Option 3: Keep Terminal Open
Just leave the terminal window running with the server active

## Monitoring Commands

Monitor the API from any terminal:
```powershell
# Check if server is running
Invoke-WebRequest -Uri "http://localhost:8000/api/health"

# Get survey statistics
Invoke-WebRequest -Uri "http://localhost:8000/api/survey/stats"

# Get all responses (admin)
Invoke-WebRequest -Uri "http://localhost:8000/api/survey/responses"

# Export responses to CSV
Invoke-WebRequest -Uri "http://localhost:8000/api/survey/export"
```

## Troubleshooting

**Monitor says "Server DOWN"**
- Check if the API terminal window is still open and running
- Look for error messages in the API terminal
- Try restarting: Kill Python processes and start again

**Port already in use**
- Kill existing processes: `Stop-Process -Name python -Force`
- Wait a few seconds, then restart

**Permission denied on port 80**
- Run PowerShell as Administrator
- Or stick with port 8000 (HTML form auto-detects)

**Monitor not showing submissions**
- Check that responses are actually being sent to the form
- Verify API is returning data: `Invoke-WebRequest -Uri "http://localhost:8000/api/survey/stats"`
- Check that both server and monitor are running

## Ports

- **Port 8000** - Primary API port (standard, recommended)
- **Port 80** - Fallback HTTP port (requires admin, may not work on all networks)

The form automatically tries 8000 first, then falls back to 80 if needed.
