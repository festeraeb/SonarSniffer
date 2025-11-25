# Sonar Sniffer Survey Results - Family Access Guide

## Welcome!

Your SAR team has successfully completed a sonar survey mission. Here's how to view all the results as if you were the family receiving the data.

---

## Quick Links

### 1. **Main Survey Viewer** (Start Here!)
   - **Local Access**: `http://localhost:8080/`
   - **Network Access**: `http://<YOUR-IP-ADDRESS>:8080/`
   - Beautiful home page with welcome, survey info, and quick links to all resources

### 2. **Interactive Map Viewer**
   - **Direct Link**: `http://localhost:8080/map_viewer.html`
   - View the actual survey track on an interactive Leaflet.js map
   - See survey points, depth data, and coverage areas
   - Pan, zoom, and explore the mapped area

### 3. **Survey Statistics Dashboard**
   - **Direct Link**: `http://localhost:8080/statistics.html`
   - Key metrics: Total records, GPS points, coverage area, mission duration
   - Depth range analysis and missing person location estimates
   - Professional data summary for family briefing

### 4. **Help & FAQ**
   - **Direct Link**: `http://localhost:8080/help.html`
   - Common questions answered in family-friendly language
   - Understanding survey terms and what the data means
   - How to interpret the results

### 5. **About This Project**
   - **Direct Link**: `http://localhost:8080/about.html`
   - Mission statement and project background
   - Technology details and open-source credits
   - CESARops SAR integration information

---

## How to Start the Server

Open PowerShell and run:

```powershell
cd 'C:\Temp\Garminjunk'
python integration_server.py
```

You'll see:
```
INFO: Sonar Sniffer Survey Results Server starting on http://localhost:8080/
INFO: Type 'quit' to stop the server
```

Then visit `http://localhost:8080/` in your web browser.

---

## Sharing with Family Members

### Local Network (Same WiFi/Office)
1. Find your computer's IP address (usually 192.168.x.x)
2. Share the link: `http://<YOUR-IP>:8080/`
3. Family members on the same network can access all pages

### Remote Access
For secure remote access, consider:
- **SSH tunnel** if you have remote server capabilities
- **VPN** for secure family access
- **Export to USB/Email** - All HTML files can be copied and shared directly

---

## What Family Members Will See

### Home Page (index.html)
- Welcome banner with mission overview
- 4 quick-link buttons to pages
- Survey information boxes explaining the data
- 6 key features of the system
- Getting started guide
- CESARops integration info

### Map Viewer (map_viewer.html)
- Full-screen interactive map powered by Leaflet.js
- Survey track visualization with color coding
- Sample sonar measurement points
- Sidebar with quick information
- Zoom controls and full map features

### Statistics (statistics.html)
- 6 key metric cards:
  - Total Records: Number of sonar measurements
  - GPS Points: Coverage area markers
  - Coverage: Total area surveyed
  - Duration: Mission time
  - Depth Range: Water depth variations
  - Missing Person Location: Most likely location based on search pattern

### Help Page (help.html)
- 7 common questions answered
- What each data type means
- How to use the interactive map
- Platform compatibility (Windows, Mac, Linux, Mobile)
- Contact information for team

### About Page (about.html)
- SAR mission overview
- Project mission statement
- Technology stack details
- GitHub repository link
- CESARops drift modeling integration
- Open-source software credits

---

## Technical Details

### System Architecture
- **Frontend**: HTML5 + CSS3 with Leaflet.js for mapping
- **Backend**: Python Flask/HTTP server (port 8080)
- **Branding**: Sonar Sniffer by CESARops
- **Design**: Responsive, mobile-friendly, modern gradient UI

### Generated Files
```
family_viewer_output/
├── index.html              (15.9 KB) - Main home page
├── map_viewer.html         (4.0 KB)  - Interactive map
├── statistics.html         (4.2 KB)  - Metrics dashboard
├── help.html              (4.4 KB)  - FAQ guide
├── about.html             (5.1 KB)  - Project info
└── ACCESS_LINK.html       (9.7 KB)  - This access guide

pathc_tiles_output/
├── mbtiles_viewer.html    (5.9 KB)  - Tile viewer
├── PATH_C_SUMMARY.md      (1.6 KB)  - Implementation notes
└── sample_survey.geojson  (0.6 KB)  - Sample data
```

### Total Size: ~57 KB of data
- Lightweight for email/USB sharing
- No external dependencies beyond Leaflet.js (via CDN)
- Works offline after initial load

---

## Troubleshooting

### "Connection refused" error
- Make sure `integration_server.py` is still running
- Check that Python is installed: `python --version`
- Try `http://127.0.0.1:8080/` instead of localhost

### Maps not loading
- Check internet connection (maps use OpenStreetMap)
- Try a different browser (Chrome, Firefox, Edge all supported)
- Clear browser cache: Ctrl+Shift+Delete

### Can't access from another device on network
- Find your computer's IP: Type `ipconfig` in PowerShell
- Look for IPv4 Address (usually 192.168.x.x)
- Make sure firewall allows port 8080 (or disable for testing)

---

## Contact & Support

For questions about:
- **SAR Operations**: Contact your SAR team lead
- **Data Interpretation**: See the Help page in the viewer
- **Technical Issues**: Check integration_server.py output for error messages
- **SAR Drift Modeling**: Visit [CESARops on GitHub](https://github.com/festeraeb)

---

## Mission Summary

This survey represents [NUMBER] hours of dedicated SAR work by our team, resulting in comprehensive sonar data coverage of the search area. Every metric, map point, and statistic tells the story of our commitment to locating the missing person.

**Viewing this interface is your window into that mission.**

---

Generated by Sonar Sniffer v2.0 | Powered by CESARops SAR Framework
*Helping families understand search and rescue missions*
