"""
SAR Platform - Intake API
Backend endpoints for case intake and initial SAR operations
"""

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
import logging
import json

from models import (
    SARDatabaseManager,
    Case, Subject, Contact, Person, Organization, Asset, Task, Finding,
    CaseStatus, CaseType, PersonRole, AssetStatus, IncidentLogEntry
)

# ============================================================================
# FASTAPI SETUP
# ============================================================================

app = FastAPI(
    title="SAR Platform - Core API",
    description="Search & Rescue operations management system",
    version="1.0.0"
)

# Enable CORS for mobile apps and field devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = SARDatabaseManager()
logger = logging.getLogger("SARIntakeAPI")

# ============================================================================
# PYDANTIC MODELS (Request/Response schemas)
# ============================================================================

class IntakeCallRequest(BaseModel):
    """Initial intake call - the first form"""
    # Caller info
    caller_name: str
    caller_phone: str
    caller_relationship: Optional[str] = None  # family, friend, witness, leo
    
    # Incident
    incident_type: str  # person_missing, vessel_missing, etc
    incident_description: str
    incident_date: str  # YYYY-MM-DD
    incident_time: str  # HH:MM:SS
    
    # Missing person/vessel
    subject_name: str
    subject_age: Optional[int] = None
    subject_gender: Optional[str] = None
    subject_photo_url: Optional[str] = None
    subject_description: str  # "5'10", brown hair, blue eyes, wearing..."
    
    # Vessel-specific
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None  # sailboat, speedboat, cargo, etc
    vessel_length_m: Optional[float] = None
    vessel_color: Optional[str] = None
    vessel_registration: Optional[str] = None
    
    # Last known
    last_known_lat: Optional[float] = None
    last_known_lon: Optional[float] = None
    last_known_location_description: str  # "Pier at State Park"
    last_known_time: str  # YYYY-MM-DD HH:MM:SS
    
    # Conditions
    weather_description: Optional[str] = None
    water_temp_c: Optional[float] = None
    water_conditions: Optional[str] = None
    wind_speed_kmh: Optional[float] = None
    
    # Subject specifics
    medical_conditions: Optional[List[str]] = None
    medications: Optional[str] = None
    survival_skills: Optional[str] = None
    equipment_with_subject: Optional[List[str]] = None
    
    # Urgency factors
    subject_is_child: bool = False
    subject_has_medical_condition: bool = False
    high_risk_behavior: Optional[str] = None
    
    # Contact info
    family_contact_phone: Optional[str] = None
    family_contact_name: Optional[str] = None
    government_liaison_needed: bool = False

class CaseResponse(BaseModel):
    """Response when case is created"""
    case_id: str
    case_number: str
    status: str
    priority_level: int
    subject_name: str
    incident_time: str
    last_known_position: Optional[Dict[str, float]]
    next_steps: List[str]

class ResourceListResponse(BaseModel):
    """Available resources for a case"""
    available_count: int
    by_type: Dict[str, int]
    assets: List[Dict[str, Any]]

class TaskAssignmentRequest(BaseModel):
    """Assign task to asset"""
    case_id: str
    asset_id: str
    asset_type: str
    task_type: str  # sonar_search, drone_search, k9_search, etc
    
    search_zone_lat: Optional[float] = None
    search_zone_lon: Optional[float] = None
    search_zone_radius_nm: Optional[float] = 2.0
    search_pattern: str = "grid"  # grid, circular, sweep
    
    estimated_duration_minutes: int = 120
    priority: int = 1

class FindingReport(BaseModel):
    """Field team reports a finding"""
    case_id: str
    task_id: Optional[str] = None
    finding_type: str  # debris, personal_item, target, remains
    
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[int] = None
    location_description: str = ""
    
    description: str
    confidence_pct: float = 50.0
    
    photos: Optional[List[str]] = None  # File paths or URLs
    measurement_notes: Optional[str] = None
    
    reported_by: str  # Person ID or name

class StatusUpdateRequest(BaseModel):
    """Task status update from field"""
    task_id: str
    status: str  # in_progress, paused, complete
    progress_pct: float = 0.0
    
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
    
    message: Optional[str] = None
    has_findings: bool = False
    problems: Optional[str] = None

# ============================================================================
# INTAKE ENDPOINTS
# ============================================================================

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint - used by monitoring systems
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/intake/new_case")
async def create_case_from_intake(call: IntakeCallRequest) -> CaseResponse:
    """
    Process intake call and create case
    This is the PRIMARY entry point for SAR operations
    """
    try:
        logger.info(f"New intake call for {call.subject_name}")
        
        # Determine priority
        priority = 3  # default normal
        if call.subject_is_child:
            priority = 1  # critical
        elif call.subject_has_medical_condition:
            priority = 2  # high
        
        # Determine case type
        case_type = CaseType.PERSON_MISSING.value
        if call.vessel_name:
            case_type = CaseType.VESSEL_MISSING.value
        
        # Create case
        case = Case(
            case_type=case_type,
            case_name=f"{call.subject_name} ({call.incident_type})",
            status=CaseStatus.INTAKE.value,
            priority_level=priority,
            
            incident_description=call.incident_description,
            incident_date=call.incident_date,
            incident_time=call.incident_time,
            reported_date=datetime.now(timezone.utc).date().isoformat(),
            reported_time=datetime.now(timezone.utc).time().isoformat(),
            
            last_known_location_lat=call.last_known_lat,
            last_known_location_lon=call.last_known_lon,
            last_known_location_description=call.last_known_location_description,
            last_known_time=datetime.fromisoformat(f"{call.incident_date}T{call.incident_time}"),
            last_seen_by=call.caller_name,
            
            weather_conditions={
                "description": call.weather_description,
                "wind_speed_kmh": call.wind_speed_kmh
            },
            water_conditions={
                "temp_c": call.water_temp_c,
                "conditions": call.water_conditions
            },
            terrain_description=call.water_conditions or "water" if call.vessel_name else "unknown"
        )
        
        # Create subject
        subject = Subject(
            case_id=case.id,
            full_name=call.subject_name,
            age=call.subject_age,
            gender=call.subject_gender,
            usual_clothing=call.subject_description,
            
            # Vessel info
            vessel_name=call.vessel_name,
            vessel_type=call.vessel_type,
            vessel_length_m=call.vessel_length_m,
            vessel_color=call.vessel_color,
            vessel_registration=call.vessel_registration,
            
            # Medical
            medical_conditions=call.medical_conditions or [],
            medications_required=call.medications,
            survival_skills=call.survival_skills,
            equipment_with_subject=call.equipment_with_subject or []
        )
        case.subject_id = subject.id
        
        # Create caller contact
        caller_contact = Contact(
            case_id=case.id,
            contact_type="requester",
            name=call.caller_name,
            phone=call.caller_phone,
            relationship_to_subject=call.caller_relationship
        )
        case.primary_contact_id = caller_contact.id
        
        # Create family contact if provided
        if call.family_contact_phone:
            family_contact = Contact(
                case_id=case.id,
                contact_type="family_member",
                name=call.family_contact_name or "Family",
                phone=call.family_contact_phone,
                notify_on_status_change=True,
                notify_on_finding=True,
                notify_on_resolution=True
            )
            case.family_contact_id = family_contact.id
        
        # Auto-assign incident coordinator (would be from system user)
        # For now, leave empty - human will assign
        
        # Save to database
        try:
            case_id = db.create_case(case)
            
            # Generate case number
            case_num = f"SAR-{datetime.now().year}-{case_id[:6].upper()}"
            conn = db._get_connection()
            conn.execute('UPDATE cases SET case_number = ? WHERE id = ?', (case_num, case_id))
            conn.commit()
            conn.close()
            
            # Log intake action
            log_entry = IncidentLogEntry(
                case_id=case_id,
                action_type="case_created",
                action_description=f"Case created from intake call",
                actor_name=call.caller_name,
                summary=f"Case {case_num} opened: {call.subject_name}",
                details=call.incident_description
            )
            db.log_incident_action(log_entry)
            
            # Determine next steps
            next_steps = [
                "Assign incident coordinator",
                "Define search zones based on incident details",
                "Contact government liaison (if water incident)",
                "Deploy initial resources",
                "Begin active search operations"
            ]
            
            if priority == 1:
                next_steps.insert(0, "CRITICAL: Activate full team immediately")
            
            response = CaseResponse(
                case_id=case_id,
                case_number=case_num,
                status="intake",
                priority_level=priority,
                subject_name=call.subject_name,
                incident_time=call.incident_time,
                last_known_position={
                    "lat": call.last_known_lat,
                    "lon": call.last_known_lon
                } if call.last_known_lat and call.last_known_lon else None,
                next_steps=next_steps
            )
            
            logger.info(f"Case created: {case_num}")
            return response
        
        except Exception as e:
            logger.error(f"Error saving case: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in intake: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid intake request: {str(e)}")

# ============================================================================
# CASE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/cases/{case_id}")
async def get_case_details(case_id: str):
    """Get complete case information"""
    try:
        case = db.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return {
            "case": case.__dict__,
            "status": "success"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving case: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cases")
async def list_active_cases():
    """Get all active cases"""
    try:
        cases = db.get_active_cases()
        return {
            "count": len(cases),
            "cases": [c.__dict__ for c in cases],
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/cases/{case_id}/status")
async def update_case_status(case_id: str, new_status: str):
    """Update case status"""
    try:
        # Validate status
        valid_statuses = [s.value for s in CaseStatus]
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
        
        db.update_case_status(case_id, new_status)
        
        # Log the status change
        log_entry = IncidentLogEntry(
            case_id=case_id,
            action_type="status_change",
            action_description=f"Case status changed to {new_status}",
            summary=f"Status: {new_status}",
            details=f"Case transitioned to {new_status} status"
        )
        db.log_incident_action(log_entry)
        
        return {"status": "success", "case_id": case_id, "new_status": new_status}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RESOURCE MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/resources/available")
async def get_available_resources(asset_type: Optional[str] = None) -> ResourceListResponse:
    """Get available SAR resources"""
    try:
        assets = db.get_available_assets(asset_type)
        
        by_type = {}
        for asset in assets:
            asset_type = asset.asset_type
            by_type[asset_type] = by_type.get(asset_type, 0) + 1
        
        return ResourceListResponse(
            available_count=len(assets),
            by_type=by_type,
            assets=[{
                "id": a.id,
                "name": a.name,
                "type": a.asset_type,
                "organization": a.organization_id,
                "operator": a.primary_operator_id,
                "capabilities": a.capabilities,
                "location": {
                    "lat": a.current_location_lat,
                    "lon": a.current_location_lon
                } if a.current_location_lat else None,
                "range_nm": a.max_range_nm,
                "duration_hours": a.max_duration_hours
            } for a in assets]
        )
    
    except Exception as e:
        logger.error(f"Error retrieving resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resources/register")
async def register_asset(asset_data: Dict[str, Any]):
    """Register new asset in system"""
    try:
        asset = Asset(**asset_data)
        asset_id = db.create_asset(asset)
        
        return {
            "status": "success",
            "asset_id": asset_id,
            "message": f"Asset {asset.name} registered"
        }
    
    except Exception as e:
        logger.error(f"Error registering asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/resources/{asset_id}/status")
async def update_asset_status(asset_id: str, 
                              status: str,
                              lat: Optional[float] = None,
                              lon: Optional[float] = None):
    """Update asset status and location"""
    try:
        valid_statuses = [s.value for s in AssetStatus]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        db.update_asset_status(asset_id, status, lat, lon)
        
        return {"status": "success", "asset_id": asset_id, "new_status": status}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TASK MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/tasks/create")
async def create_task(request: TaskAssignmentRequest):
    """Assign task to asset"""
    try:
        task = Task(
            case_id=request.case_id,
            task_type=request.task_type,
            assigned_asset_id=request.asset_id,
            search_zone_lat=request.search_zone_lat,
            search_zone_lon=request.search_zone_lon,
            search_zone_radius_nm=request.search_zone_radius_nm,
            search_pattern=request.search_pattern,
            estimated_duration_minutes=request.estimated_duration_minutes,
            priority=request.priority,
            reasoning=f"Assigned {request.asset_type} to search zone"
        )
        
        task_id = db.create_task(task)
        
        # Update asset status
        db.update_asset_status(request.asset_id, "deployed")
        
        # Log task creation
        log_entry = IncidentLogEntry(
            case_id=request.case_id,
            action_type="task_created",
            action_description=f"Task created: {request.task_type}",
            related_task_id=task_id,
            related_asset_id=request.asset_id,
            summary=f"Task assigned to {request.asset_type}",
            details=f"Task {task_id}: Search zone ({request.search_zone_lat}, {request.search_zone_lon})"
        )
        db.log_incident_action(log_entry)
        
        return {
            "status": "success",
            "task_id": task_id,
            "asset_id": request.asset_id,
            "message": "Task assigned"
        }
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cases/{case_id}/tasks")
async def get_case_tasks(case_id: str, status_filter: Optional[str] = None):
    """Get all tasks for a case"""
    try:
        tasks = db.get_tasks_for_case(case_id, status_filter)
        
        return {
            "case_id": case_id,
            "total": len(tasks),
            "tasks": [t.__dict__ for t in tasks],
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: str, update: StatusUpdateRequest):
    """Update task status from field"""
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task in database
        conn = db._get_connection()
        c = conn.cursor()
        
        c.execute('''
            UPDATE tasks SET status = ?, started_time = COALESCE(started_time, ?),
            latest_status_update = ?, latest_status_time = ?
            WHERE id = ?
        ''', (
            update.status,
            datetime.now(timezone.utc) if update.status == "in_progress" else None,
            update.message,
            datetime.now(timezone.utc),
            task_id
        ))
        
        conn.commit()
        conn.close()
        
        # Log update
        log_entry = IncidentLogEntry(
            case_id=task.case_id,
            action_type="status_update",
            action_description=f"Task update: {update.status}",
            related_task_id=task_id,
            location_lat=update.current_lat,
            location_lon=update.current_lon,
            summary=f"Task {task_id}: {update.status}",
            details=update.message or ""
        )
        db.log_incident_action(log_entry)
        
        return {
            "status": "success",
            "task_id": task_id,
            "task_status": update.status,
            "message": "Task updated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FINDINGS ENDPOINTS
# ============================================================================

@app.post("/api/findings/report")
async def report_finding(report: FindingReport):
    """Field team reports a finding"""
    try:
        finding = Finding(
            case_id=report.case_id,
            task_id=report.task_id,
            finding_type=report.finding_type,
            description=report.description,
            confidence_pct=report.confidence_pct,
            location_lat=report.latitude,
            location_lon=report.longitude,
            location_accuracy_m=report.accuracy_m,
            location_description=report.location_description,
            photo_paths=report.photos or [],
            measurement_notes=report.measurement_notes,
            found_time=datetime.now(timezone.utc),
            found_by_id=report.reported_by
        )
        
        finding_id = db.log_finding(finding)
        
        # Log finding
        log_entry = IncidentLogEntry(
            case_id=report.case_id,
            action_type="finding_logged",
            action_description=f"Finding reported: {report.finding_type}",
            related_task_id=report.task_id,
            related_finding_id=finding_id,
            location_lat=report.latitude,
            location_lon=report.longitude,
            summary=f"Finding: {report.finding_type} ({report.confidence_pct}% confidence)",
            details=report.description
        )
        db.log_incident_action(log_entry)
        
        return {
            "status": "success",
            "finding_id": finding_id,
            "confidence": report.confidence_pct,
            "message": "Finding logged"
        }
    
    except Exception as e:
        logger.error(f"Error logging finding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# HEALTH & INFO
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Check API health"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected"
    }

@app.get("/api/info")
async def system_info():
    """Get system information"""
    return {
        "name": "SAR Platform",
        "version": "1.0.0",
        "database_path": str(db.db_path),
        "endpoints": [
            "/api/intake/new_case",
            "/api/cases",
            "/api/cases/{case_id}",
            "/api/resources/available",
            "/api/tasks/create",
            "/api/findings/report"
        ]
    }

# ============================================================================
# SURVEY ENDPOINTS
# ============================================================================

# Import survey handler
from survey_handler import SurveyDatabase, SurveyResponse

# Initialize survey database
survey_db = SurveyDatabase()

class SurveySubmission(BaseModel):
    """Survey response submission"""
    primary_discipline: Optional[List[str]] = None
    organization_type: Optional[str] = None
    team_size: Optional[str] = None
    years_experience: Optional[str] = None
    operational_challenges: Optional[List[str]] = None
    current_tools_incident: Optional[List[str]] = None
    current_tools_data: Optional[List[str]] = None
    current_tools_comm: Optional[List[str]] = None
    desired_integrations: Optional[List[str]] = None
    incidents_per_year: Optional[str] = None
    intake_required_fields: Optional[List[str]] = None
    intake_format: Optional[str] = None
    desired_reports: Optional[List[str]] = None
    task_assignment_method: Optional[str] = None
    asset_tracking_priority: Optional[List[str]] = None
    task_update_preference: Optional[str] = None
    needs_offline_capability: Optional[str] = None
    findings_logging_method: Optional[str] = None
    findings_metadata_priority: Optional[List[str]] = None
    needs_confidence_scoring: Optional[str] = None
    network_capability: Optional[str] = None
    platform_preference: Optional[str] = None
    offline_sync_valuable: Optional[str] = None
    cesarops_usage: Optional[str] = None
    sonar_usage: Optional[str] = None
    sonar_challenge: Optional[str] = None
    drone_usage: Optional[str] = None
    drone_improvement: Optional[str] = None
    rollout_timeline: Optional[str] = None
    training_preference: Optional[List[str]] = None
    tech_skill_level: Optional[str] = None
    success_metrics: Optional[List[str]] = None
    adoption_blockers: Optional[List[str]] = None
    feature_difference_maker: Optional[str] = None
    test_scenario: Optional[str] = None
    other_feedback: Optional[str] = None
    contact_allowed: Optional[str] = None
    contact_name: Optional[str] = None
    contact_org: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_preference: Optional[List[str]] = None
    participation_willing: Optional[List[str]] = None
    pilot_timeline: Optional[str] = None

@app.post("/api/survey/submit")
async def submit_survey(survey: SurveySubmission):
    """Submit SAR Platform survey response"""
    try:
        response_id = survey_db.save_response(survey.dict())
        return {
            "status": "success",
            "response_id": response_id,
            "message": "Thank you for your feedback! Your response has been recorded."
        }
    except Exception as e:
        logging.error(f"Error saving survey response: {e}")
        raise HTTPException(status_code=500, detail="Failed to save survey response")

@app.get("/api/survey/stats")
async def get_survey_stats():
    """Get survey response statistics"""
    try:
        stats = survey_db.get_summary_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logging.error(f"Error getting survey stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get survey statistics")

@app.get("/api/survey/responses")
async def get_all_responses():
    """Get all survey responses (admin only in production)"""
    try:
        responses = survey_db.get_all_responses()
        return {
            "status": "success",
            "count": len(responses),
            "data": responses
        }
    except Exception as e:
        logging.error(f"Error retrieving survey responses: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve survey responses")

@app.get("/api/survey/export")
async def export_survey_responses():
    """Export all responses to CSV"""
    try:
        csv_path = survey_db.export_csv()
        return {
            "status": "success",
            "file": str(csv_path),
            "message": f"Exported {survey_db.get_response_count()} responses"
        }
    except Exception as e:
        logging.error(f"Error exporting survey responses: {e}")
        raise HTTPException(status_code=500, detail="Failed to export survey responses")

if __name__ == "__main__":
    import uvicorn
    import threading
    
    logging.basicConfig(level=logging.INFO)
    
    # Run on both ports: 8000 (primary) and 80 (fallback)
    # Port 80 requires admin/root privileges on Windows
    
    # Start server on port 8000 in main thread
    print("Starting SAR Platform API on port 8000...")
    
    # Try to start port 80 in background (optional, may require admin)
    def start_port_80():
        try:
            print("Attempting to start secondary listener on port 80...")
            uvicorn.run(app, host="0.0.0.0", port=80, log_level="info")
        except Exception as e:
            print(f"Could not bind to port 80 (requires admin): {e}")
    
    # Start port 80 listener in background thread
    port_80_thread = threading.Thread(target=start_port_80, daemon=True)
    port_80_thread.start()
    
    # Run primary server on port 8000 (blocking)
    uvicorn.run(app, host="0.0.0.0", port=8000)
