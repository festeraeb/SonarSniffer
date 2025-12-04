# SAR Platform Core System
## Search & Rescue Operations Management - Foundation Layer

**Version**: 1.0.0  
**Status**: Foundation/Alpha  
**Last Updated**: November 26, 2025

---

## Overview

This is the **core operational backbone** for a unified Search & Rescue platform. It handles:

- **Case Intake**: Structured intake form → database persistence
- **Resource Management**: Asset registry, status tracking, availability
- **Task Coordination**: Assign search tasks to assets, track progress
- **Findings Logging**: Record discoveries with location, confidence, evidence
- **Incident Timeline**: Automatic audit trail of all actions
- **API-First Design**: RESTful backend for web UI, mobile apps, integrations

**Design Philosophy**:
- **Modular**: Plug in discipline-specific modules (water, land, K9, drone, dive)
- **Scalable**: Single small team to multi-agency incident command
- **Offline-Capable**: Works in field with no network (sync when online)
- **Extensible**: Add fields, reports, integrations without touching core schema
- **Privacy-First**: Separation between public SAR ops and private case details

---

## Quick Start

### 1. Database Setup

```bash
# Create database and schema
python -c "from models import SARDatabaseManager; db = SARDatabaseManager(); print('Database ready:', db.db_path)"
```

This creates `sar_platform.db` with all tables:
- `cases`, `subjects`, `contacts`
- `persons`, `organizations`, `assets`
- `tasks`, `task_updates`, `findings`
- `predictions`, `messages`, `incident_log`

### 2. Start API Server

```bash
# Install dependencies (if needed)
pip install fastapi uvicorn pydantic

# Run API (localhost:8000)
python intake_api.py

# Or with uvicorn directly:
# uvicorn intake_api:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`

### 3. Open Intake Form

Open in browser:
```
file:///path/to/intake.html
```

Or serve via HTTP:
```bash
python -m http.server 8080
# Then go to http://localhost:8080/intake.html
```

---

## System Architecture

```
┌─────────────────────────────────────────────┐
│        Web UI / Mobile App / CLI            │
│    (intake.html, React app, bot, etc)      │
└──────────────────┬──────────────────────────┘
                   │ HTTP/REST
┌──────────────────┴──────────────────────────┐
│         FastAPI Backend (intake_api.py)     │
├──────────────────────────────────────────────┤
│  • Case management (/api/cases/*)           │
│  • Task coordination (/api/tasks/*)         │
│  • Resource management (/api/resources/*)   │
│  • Findings logging (/api/findings/*)       │
│  • Incident log (automatic)                 │
└──────────────────┬──────────────────────────┘
                   │ SQLite ORM
┌──────────────────┴──────────────────────────┐
│    SQLite Database (sar_platform.db)        │
├──────────────────────────────────────────────┤
│  Tables:                                    │
│  • Core: cases, subjects, contacts          │
│  • Resources: persons, organizations,       │
│             assets                          │
│  • Operations: tasks, findings,             │
│              predictions                    │
│  • Tracking: incident_log, messages         │
└──────────────────────────────────────────────┘

        Third-Party Integrations:
          ↓ (plugins/modules)
    ┌─────────────────────────┐
    │   CESAROPS (drift pred) │
    │   SonarSniffer (sonar)  │
    │   Weather services      │
    │   Communications (radio)│
    └─────────────────────────┘
```

---

## Core Concepts

### Case
Central unified incident record. Types:
- `person_missing`: Individual lost
- `vessel_missing`: Boat, ship, or watercraft
- `aircraft_missing`: Plane or helicopter
- `water_rescue`: Active water emergency

**Key Fields**:
- Last known position (lat/lon with confidence radius)
- Subject details (person or vessel characteristics)
- Environmental conditions (weather, water state)
- Priority level (1=critical child, 2=high, 3=normal, 4=low)
- Status: intake → active → closed

### Subject
The person or vessel being searched for.

**Person Subject Fields**:
- Name, age, gender, physical description
- Medical conditions, medications, mobility issues
- Survival skills, equipment with subject
- Photo, contact info

**Vessel Subject Fields**:
- Name, type (sailboat, cargo, etc), length, color
- Material, buoyancy, registration
- Radio callsign, equipment

### Task
Atomic search action assigned to an asset.

**Types**:
- `sonar_search`: Boat with sonar scanning zone
- `drone_search`: UAV covering area
- `k9_search`: Canine team ground search
- `diver_deployment`: Underwater search
- `shore_search`: Volunteer line search
- `vehicle_patrol`: Vehicle-based search

**Tracking**:
- Status: assigned → in_progress → paused → complete
- Search zone (lat/lon + radius or polygon)
- Search pattern (grid, spiral, sweep)
- Coverage % (% of zone searched)
- Results: targets found, confidence scores

### Finding
Evidence discovered during search.

**Types**:
- `debris`: Wreckage or floating material
- `personal_item`: Clothing, gear, etc
- `vessel_part`: Hull section, equipment
- `remains`: Physical remains
- `footprint`: Ground evidence

**Key Data**:
- Location (lat/lon + accuracy radius)
- Confidence (0-100%)
- Photos, measurements, chain of custody
- Whether it matches subject

### Asset
Any searchable resource.

**Types**:
- `k9_unit`: Canine team with handler
- `boat`: Vessel with crew
- `drone`: Unmanned aircraft
- `vehicle`: Car, truck, ATV
- `diver_team`: Underwater specialist
- `aircraft`: Helicopter or plane

**Status**: available → deployed → returning → fatigued → unavailable

**Tracking**:
- Current location (GPS)
- Fuel/battery level
- Hours deployed today (fatigue)
- Capabilities (what they can search)
- Cost per hour (for accounting)

---

## API Endpoints

### Intake / Case Creation

**POST /api/intake/new_case**
Create new case from intake call.
```json
{
  "caller_name": "John Smith",
  "caller_phone": "555-1234",
  "incident_type": "person_missing",
  "incident_description": "Missing hiker, age 8",
  "incident_date": "2025-11-26",
  "incident_time": "14:30",
  "subject_name": "Sarah Smith",
  "subject_age": 8,
  "subject_description": "5'2\", brown hair, blue eyes, wearing pink jacket",
  "last_known_lat": 42.3601,
  "last_known_lon": -87.1245,
  "last_known_location_description": "Hiking trail, State Park",
  "last_known_time": "14:00",
  "subject_is_child": true,
  "subject_has_medical_condition": false,
  "family_contact_phone": "555-5678"
}
```

**Response**:
```json
{
  "case_id": "abc123...",
  "case_number": "SAR-2025-ABC123",
  "status": "intake",
  "priority_level": 1,
  "subject_name": "Sarah Smith",
  "incident_time": "14:30",
  "last_known_position": {"lat": 42.3601, "lon": -87.1245},
  "next_steps": [
    "Assign incident coordinator",
    "Define search zones",
    "Deploy initial resources"
  ]
}
```

### Case Management

**GET /api/cases**
List all active cases.

**GET /api/cases/{case_id}**
Get complete case information.

**PUT /api/cases/{case_id}/status**
Update case status.
```json
{
  "new_status": "active"  // or "suspended", "closed_found", etc
}
```

### Resources

**GET /api/resources/available?asset_type=boat**
List available assets (optionally filtered by type).

**POST /api/resources/register**
Register new asset in system.
```json
{
  "asset_type": "boat",
  "name": "SeaHawk",
  "organization_id": "org123",
  "primary_operator_id": "person456",
  "capabilities": ["sonar_search", "surface_search"],
  "max_range_nm": 50,
  "max_duration_hours": 8
}
```

**PUT /api/resources/{asset_id}/status**
Update asset status and location.
```json
{
  "status": "deployed",
  "lat": 42.3601,
  "lon": -87.1245
}
```

### Tasks

**POST /api/tasks/create**
Assign task to asset.
```json
{
  "case_id": "case123",
  "asset_id": "boat1",
  "asset_type": "boat",
  "task_type": "sonar_search",
  "search_zone_lat": 42.3601,
  "search_zone_lon": -87.1245,
  "search_zone_radius_nm": 3,
  "search_pattern": "grid",
  "estimated_duration_minutes": 120,
  "priority": 1
}
```

**GET /api/cases/{case_id}/tasks**
Get all tasks for a case.

**PUT /api/tasks/{task_id}/status**
Update task status from field.
```json
{
  "task_id": "task456",
  "status": "in_progress",
  "progress_pct": 45,
  "current_lat": 42.3605,
  "current_lon": -87.1250,
  "message": "Sonar scan in progress, no targets yet"
}
```

### Findings

**POST /api/findings/report**
Field team reports finding.
```json
{
  "case_id": "case123",
  "task_id": "task456",
  "finding_type": "debris",
  "description": "Pink fabric, appears to be from clothing",
  "confidence_pct": 75,
  "latitude": 42.3608,
  "longitude": -87.1248,
  "accuracy_m": 10,
  "location_description": "50m south of search zone center",
  "reported_by": "person123"
}
```

### System

**GET /api/health**
Check API health.

**GET /api/info**
Get system information and available endpoints.

---

## Database Schema

### Core Tables

**cases**: Main incident record
- `id` (TEXT, PK)
- `case_number` (TEXT, UNIQUE) - e.g., "SAR-2025-ABC123"
- `case_type` - person_missing, vessel_missing, etc
- `status` - intake, active, suspended, closed_*
- `priority_level` - 1 to 4
- `last_known_location_lat`, `last_known_location_lon`
- `last_known_time`, `position_confidence_m`
- `incident_description`, `incident_date`, `incident_time`
- Contact IDs: `primary_contact_id`, `family_contact_id`, `incident_coordinator_id`
- Prediction/search data: `search_zones`, `search_zones_generated_by`
- Coverage: `area_searched_sq_nm`, `findings_count`, `high_confidence_findings`
- Resolution: `outcome`, `resolution_date`, `resolution_location_*`, `resolution_notes`

**subjects**: Person or vessel being searched
- `id`, `case_id`, `full_name`, `age`, `gender`
- Person fields: `height_cm`, `weight_kg`, `hair_color`, `eye_color`, `photo_path`
- Vessel fields: `vessel_name`, `vessel_type`, `vessel_length_m`, `vessel_material`, `vessel_color`, `vessel_registration`, `vessel_radio_callsign`, `vessel_buoyancy_kg`
- Medical: `medical_conditions`, `medications_required`, `allergies`, `mobility_limitations`

**tasks**: Assigned search operations
- `id`, `case_id`, `task_number`, `task_type`, `status`
- Assignment: `assigned_asset_id`, `assigned_personnel_ids`, `assigned_time`, `assigned_by_id`
- Search zone: `search_zone_lat`, `search_zone_lon`, `search_zone_radius_nm`, `search_pattern`, `priority`, `reasoning`
- Execution: `started_time`, `estimated_completion_time`, `actual_completion_time`
- Results: `targets_found`, `high_confidence_targets`, `coverage_achieved_pct`, `result_summary`
- Data collected: `sonar_data_files`, `photos_collected`, `gps_trackline_path`, `video_file_path`

**assets**: Searchable resources
- `id`, `asset_type`, `name`, `asset_number`, `organization_id`, `primary_operator_id`
- Status: `status`, `current_location_lat`, `current_location_lon`, `current_location_time`
- Operational: `deployments_today`, `hours_deployed_today`, `fuel_level_pct`, `battery_level_pct`
- Capabilities: `capabilities`, `max_range_nm`, `max_duration_hours`, `specialized_equipment`
- Constraints: `personnel_required`, `support_vehicle_needed`, `maintenance_requirements`
- Contact: `radio_channel`, `call_sign`
- Maintenance: `maintenance_status`, `last_maintenance_date`, `next_maintenance_due`
- Cost: `acquisition_cost_usd`, `operational_cost_per_hour_usd`

**findings**: Evidence discovered
- `id`, `case_id`, `task_id`, `finding_type`, `description`, `confidence_pct`
- Location: `location_lat`, `location_lon`, `location_accuracy_m`, `location_description`
- Timing: `found_time`, `found_by_id`
- Evidence: `evidence_collected`, `evidence_storage_location`, `photo_paths`, `measurement_notes`
- Analysis: `initial_assessment`, `expert_analysis`, `matches_subject`, `contributes_to_resolution`

**incident_log**: Automatic audit trail
- `id` (AUTOINCREMENT)
- `case_id`, `action_time`, `action_type`, `action_description`
- `actor_id`, `actor_name`
- Links: `related_task_id`, `related_asset_id`, `related_finding_id`
- Location context: `location_lat`, `location_lon`
- `summary` (for chronology), `details` (extended notes)

**messages**: Communication log
- `id`, `case_id`, `sender_id`, `recipient_ids`, `recipient_org_ids`
- Content: `priority`, `message_type`, `subject`, `body`
- Delivery: `delivery_method`, `delivery_time`, `is_broadcast`
- Metadata: `attachments`, `location_context_lat`, `location_context_lon`
- `read_by_ids`, `read_times` (read receipts)
- Radio-specific: `radio_channel`, `radio_recording_path`

**persons**: Individuals in system
- `id`, `full_name`, `phone`, `email`, `radio_callsign`
- Affiliation: `organization_id`, `role`
- Credentials: `certifications`, `specializations`, `years_experience`
- Status: `availability_status`, `last_deployed`, `deployments_this_month`, `total_hours_this_month`

**organizations**: SAR teams, agencies
- `id`, `name`, `type`, `jurisdiction`
- Contact: `primary_contact_id`, `phone`, `email`, `website`
- Location: `station_lat`, `station_lon`, `station_address`
- Operations: `is_active`, `response_capability`, `avg_response_time_minutes`
- Capacity: `typical_personnel_available`, `maximum_personnel_available`, `assets_owned`

---

## Extensibility & Customization

### Adding Fields to Case

1. **Add to database schema** (`database_schema.sql`):
```sql
ALTER TABLE cases ADD COLUMN my_new_field TEXT DEFAULT '';
```

2. **Add to Python model** (`models.py`, `Case` dataclass):
```python
@dataclass
class Case:
    # ... existing fields ...
    my_new_field: str = ""
```

3. **Add to API** (`intake_api.py`, `IntakeCallRequest`):
```python
class IntakeCallRequest(BaseModel):
    # ... existing fields ...
    my_new_field: str = ""
```

4. **Add to form** (`intake.html`):
```html
<input type="text" name="my_new_field">
```

### Adding Module-Specific Assets

Create module for your SAR discipline:

```python
# modules/water_search.py
from models import Asset, AssetStatus

class BoatAsset(Asset):
    """Water-specific asset"""
    asset_type = "boat"
    
    # Water-specific fields
    sonar_type: str  # "side_scan", "forward_looking", "multibeam"
    max_depth_m: float
    propulsion_type: str  # "jet_drive", "prop", "other"

# modules/drone_search.py
class DroneAsset(Asset):
    """Aerial asset"""
    asset_type = "drone"
    
    # Drone-specific
    max_altitude_m: int
    sensor_type: str  # "rgb", "thermal", "lidar", "hyperspectral"
    endurance_minutes: int
    payload_kg: float
```

### Adding Custom Reports

```python
# reports/post_incident.py
def generate_post_incident_report(case_id: str) -> Dict:
    """Generate comprehensive after-action report"""
    case = db.get_case(case_id)
    tasks = db.get_tasks_for_case(case_id)
    
    return {
        "case_summary": {...},
        "timeline": {...},
        "resource_utilization": {...},
        "cost_analysis": {...},
        "findings_analysis": {...},
        "lessons_learned": {...}
    }
```

---

## Data Privacy & Security

### Sensitive Data Handling

- **Family contact information**: Only accessible to case coordinator
- **Medical conditions**: Redacted from public-facing reports
- **Personal identifying information**: Encrypted in logs
- **Incident timeline**: Audit trail preserves all actions (immutable)

### Access Control (Future)

```python
class AccessControl:
    """Role-based access"""
    coordinator: can_view_all_data, can_create_tasks, can_close_case
    searcher: can_view_assigned_tasks, can_report_findings
    family: can_view_non_sensitive_updates_only
    public: no_access (case privacy until resolution)
```

---

## Running Tests

```bash
# Unit tests for database operations
python -m pytest tests/test_models.py -v

# Integration tests
python -m pytest tests/test_api.py -v

# Full test suite
python -m pytest tests/ -v
```

---

## Next Steps / Roadmap

### Phase 2: Field Operations
- [ ] Mobile app (React Native) for field teams
- [ ] Offline sync capability
- [ ] Real-time GPS tracking of assets
- [ ] Photo/evidence upload from field

### Phase 3: Intelligence Integration
- [ ] CESAROPS drift prediction integration
- [ ] SonarSniffer target detection integration
- [ ] Confidence scoring for all predictions
- [ ] Back-drift analysis (given finding, where'd it come from?)

### Phase 4: Multi-Discipline Modules
- [ ] Water search (boat, sonar, diver)
- [ ] Land search (K9, volunteers, terrain analysis)
- [ ] Aerial (drone, helicopter, satellite)
- [ ] Equine/specialized teams

### Phase 5: Communication & Coordination
- [ ] Radio gateway (VHF integration)
- [ ] SMS/email alerts
- [ ] Multi-agency coordination
- [ ] Family notification system

### Phase 6: Advanced Analytics
- [ ] Post-incident analysis with accuracy assessment
- [ ] Machine learning on case patterns
- [ ] Resource utilization optimization
- [ ] Cost modeling and budgeting

---

## Support & Contribution

**Issues / Bugs**: Log to [GitHub Issues]  
**Feature Requests**: See [Survey Results]  
**Contributions**: Follow SAR best practices, include tests  
**Documentation**: Keep this README updated

---

## License & Attribution

Foundation layer based on:
- NIMS/ICS standards
- SAR community best practices
- Stakeholder feedback from marine, land, K9, drone, dive teams

---

## Contact

**Project Lead**: Thom (festeraeb)  
**Database Architect**: Agent  
**Testing & Validation**: YOUR SAR TEAMS

---

**Last Update**: November 26, 2025  
**Next Review**: December 31, 2025 (survey deadline - Midnight)
