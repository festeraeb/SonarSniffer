"""
SAR Platform - Core Data Models & Database Interface
Foundation layer for all case, resource, and task management
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import logging

# ============================================================================
# ENUMS
# ============================================================================

class CaseStatus(Enum):
    INTAKE = "intake"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED_FOUND = "closed_found"
    CLOSED_PRESUMED_LOST = "closed_presumed_lost"
    CLOSED_OTHER = "closed_other"

class CaseType(Enum):
    PERSON_MISSING = "person_missing"
    VESSEL_MISSING = "vessel_missing"
    AIRCRAFT_MISSING = "aircraft_missing"
    WATER_RESCUE = "water_rescue"

class TaskStatus(Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETE = "complete"
    CANCELLED = "cancelled"

class TaskType(Enum):
    SONAR_SEARCH = "sonar_search"
    DRONE_SEARCH = "drone_search"
    K9_SEARCH = "k9_search"
    DIVER_DEPLOYMENT = "diver_deployment"
    SHORE_SEARCH = "shore_search"
    VEHICLE_PATROL = "vehicle_patrol"
    COORDINATION = "coordination"

class AssetStatus(Enum):
    AVAILABLE = "available"
    DEPLOYED = "deployed"
    RETURNING = "returning"
    FATIGUED = "fatigued"
    MAINTENANCE = "maintenance"
    UNAVAILABLE = "unavailable"

class PersonRole(Enum):
    COORDINATOR = "coordinator"
    K9_HANDLER = "k9_handler"
    BOAT_OPERATOR = "boat_operator"
    DRONE_PILOT = "drone_pilot"
    DIVER = "diver"
    VOLUNTEER = "volunteer"
    FAMILY_MEMBER = "family_member"
    LEO = "leo"  # Law Enforcement Officer
    GOVERNMENT_LIAISON = "government_liaison"

# ============================================================================
# DATA CLASSES (Simplified Python models for API layer)
# ============================================================================

@dataclass
class Organization:
    """SAR team or partner agency"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    name: str = ""
    type: str = ""  # volunteer_sar, coast_guard, fire_dept, etc
    jurisdiction: str = ""
    
    phone: str = ""
    email: str = ""
    website: str = ""
    
    station_lat: Optional[float] = None
    station_lon: Optional[float] = None
    station_address: str = ""
    
    is_active: bool = True
    response_capability: List[str] = field(default_factory=list)
    avg_response_time_minutes: Optional[int] = None
    
    typical_personnel_available: Optional[int] = None
    maximum_personnel_available: Optional[int] = None
    
    uses_platform: bool = False

@dataclass
class Person:
    """Individual in the system"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    full_name: str = ""
    phone: str = ""
    email: str = ""
    radio_callsign: str = ""
    
    organization_id: Optional[str] = None
    role: str = ""  # From PersonRole enum
    
    certifications: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    years_experience: Optional[int] = None
    
    availability_status: str = "available"
    last_deployed: Optional[datetime] = None
    deployments_this_month: int = 0
    total_hours_this_month: int = 0
    
    is_active: bool = True

@dataclass
class Subject:
    """Missing person or vessel"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: str = ""
    full_name: str = ""
    age: Optional[int] = None
    gender: str = ""
    
    # Physical description
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    hair_color: str = ""
    eye_color: str = ""
    distinguishing_marks: str = ""
    usual_clothing: str = ""
    photo_path: Optional[str] = None
    
    # Vessel info
    vessel_name: str = ""
    vessel_type: str = ""
    vessel_length_m: Optional[float] = None
    vessel_material: str = ""
    vessel_color: str = ""
    vessel_registration: str = ""
    vessel_radio_callsign: str = ""
    
    # Medical
    medical_conditions: List[str] = field(default_factory=list)
    medications_required: str = ""
    allergies: str = ""
    mobility_limitations: str = ""
    
    # Behavioral
    survival_skills: str = ""
    equipment_with_subject: List[str] = field(default_factory=list)

@dataclass
class Contact:
    """Contact information for case (family, requester, etc)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: str = ""
    contact_type: str = ""  # family_member, requester, government_liaison
    
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    relationship_to_subject: str = ""
    
    notify_on_status_change: bool = True
    notify_on_finding: bool = True
    notify_on_resolution: bool = True
    contact_method_preference: str = "phone"
    
    last_contact_time: Optional[datetime] = None
    last_contact_notes: str = ""
    contact_quality: str = "good"  # excellent, good, poor, unreliable

@dataclass
class Case:
    """Central case file - CORE data structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    intake_time: Optional[datetime] = None
    
    # Identification
    case_number: str = ""  # e.g., "SAR-2025-0001"
    case_name: str = ""
    case_type: str = ""  # From CaseType enum
    
    # Status
    status: str = "intake"  # From CaseStatus enum
    priority_level: int = 3  # 1=critical, 2=high, 3=normal, 4=low
    
    # Subject
    subject_id: Optional[str] = None
    
    # Incident details
    incident_description: str = ""
    incident_date: Optional[str] = None  # YYYY-MM-DD
    incident_time: Optional[str] = None  # HH:MM:SS
    reported_date: Optional[str] = None
    reported_time: Optional[str] = None
    time_in_condition_hours: Optional[int] = None
    
    # Last known position
    last_known_location_lat: Optional[float] = None
    last_known_location_lon: Optional[float] = None
    last_known_location_description: str = ""
    last_known_time: Optional[datetime] = None
    position_confidence_m: int = 500  # Default ±500m error radius
    last_seen_by: str = ""
    
    # Environmental conditions
    weather_conditions: Dict[str, Any] = field(default_factory=dict)
    water_conditions: Dict[str, Any] = field(default_factory=dict)
    terrain_description: str = ""
    
    # Contacts
    primary_contact_id: Optional[str] = None
    family_contact_id: Optional[str] = None
    government_liaison_id: Optional[str] = None
    media_liaison_id: Optional[str] = None
    incident_coordinator_id: Optional[str] = None
    
    # Resources
    lead_organization_id: Optional[str] = None
    assisting_organizations: List[str] = field(default_factory=list)
    
    # Prediction
    search_zones: List[Dict] = field(default_factory=list)
    search_zones_generated_by: str = ""
    search_zones_confidence: Optional[float] = None
    
    # Coverage
    search_zones_completed: int = 0
    search_zones_in_progress: int = 0
    area_searched_sq_nm: float = 0.0
    estimated_total_search_area_sq_nm: Optional[float] = None
    
    # Findings
    findings_count: int = 0
    high_confidence_findings: int = 0
    
    # Resolution
    outcome: Optional[str] = None
    resolution_date: Optional[datetime] = None
    resolution_location_lat: Optional[float] = None
    resolution_location_lon: Optional[float] = None
    resolution_notes: str = ""
    
    # Post-incident
    lessons_learned: str = ""
    admin_notes: str = ""

@dataclass
class Asset:
    """Searchable resource (boat, drone, K9, etc)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Identification
    asset_type: str = ""  # k9_unit, boat, drone, vehicle, diver_team, aircraft
    name: str = ""
    asset_number: str = ""
    
    # Organization
    organization_id: str = ""
    primary_operator_id: Optional[str] = None
    
    # Status
    status: str = "available"  # From AssetStatus enum
    current_location_lat: Optional[float] = None
    current_location_lon: Optional[float] = None
    current_location_time: Optional[datetime] = None
    
    # Operational
    deployments_today: int = 0
    hours_deployed_today: float = 0.0
    last_deployment_start: Optional[datetime] = None
    last_deployment_end: Optional[datetime] = None
    fuel_level_pct: Optional[float] = None
    battery_level_pct: Optional[float] = None
    
    # Capabilities
    capabilities: List[str] = field(default_factory=list)
    max_range_nm: Optional[float] = None
    max_duration_hours: Optional[float] = None
    
    # Constraints
    personnel_required: int = 1
    support_vehicle_needed: bool = False
    maintenance_requirements: str = ""
    
    # Contact
    radio_channel: str = ""
    call_sign: str = ""
    
    # Maintenance
    maintenance_status: str = "operational"
    last_maintenance_date: Optional[str] = None
    next_maintenance_due: Optional[str] = None
    
    # Cost
    operational_cost_per_hour_usd: Optional[float] = None

@dataclass
class Task:
    """Atomic search action"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: str = ""
    task_number: str = ""  # "Task 1", "Task 2"
    
    # Type & status
    task_type: str = ""  # From TaskType enum
    status: str = "assigned"  # From TaskStatus enum
    
    # Assignment
    assigned_asset_id: Optional[str] = None
    assigned_personnel_ids: List[str] = field(default_factory=list)
    assigned_by_id: Optional[str] = None
    assigned_time: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    
    # Search specifics
    search_zone_lat: Optional[float] = None
    search_zone_lon: Optional[float] = None
    search_zone_radius_nm: Optional[float] = None
    search_pattern: str = ""  # grid, circular_spiral, sweep, random
    priority: int = 1
    reasoning: str = ""
    
    # Success criteria
    success_criteria: str = ""
    minimum_coverage_pct: float = 90.0
    
    # Execution
    started_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    actual_completion_time: Optional[datetime] = None
    
    # Results
    result_summary: str = ""
    targets_found: int = 0
    high_confidence_targets: int = 0
    coverage_achieved_pct: Optional[float] = None
    
    # Resource tracking
    fuel_consumed_liters: Optional[float] = None
    personnel_hours: float = 0.0
    equipment_used: List[str] = field(default_factory=list)
    cost_incurred_usd: Optional[float] = None
    
    # Data collected
    sonar_data_files: List[str] = field(default_factory=list)
    photos_collected: int = 0
    gps_trackline_path: Optional[str] = None
    video_file_path: Optional[str] = None
    
    # Notes
    field_notes: str = ""
    problems_encountered: str = ""
    recommendations: str = ""

@dataclass
class Finding:
    """Evidence of subject or debris"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: str = ""
    task_id: Optional[str] = None
    
    finding_type: str = ""  # debris, personal_item, vessel_part, remains, footprint
    description: str = ""
    confidence_pct: float = 50.0  # 0-100
    
    # Location
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_accuracy_m: Optional[int] = None
    location_description: str = ""
    
    # Timing
    found_time: Optional[datetime] = None
    found_by_id: Optional[str] = None
    
    # Evidence
    evidence_collected: bool = False
    evidence_storage_location: str = ""
    
    # Documentation
    photo_paths: List[str] = field(default_factory=list)
    measurement_notes: str = ""
    
    # Analysis
    initial_assessment: str = ""
    expert_analysis: str = ""
    matches_subject: Optional[bool] = None
    
    contributes_to_resolution: bool = False

@dataclass
class Prediction:
    """Intelligence/modeling output"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: str = ""
    
    model_name: str = ""  # CESAROPS, lost_person_behavior, drift_ballistic
    model_version: str = ""
    generated_time: Optional[datetime] = None
    
    # Zone
    zone_lat: Optional[float] = None
    zone_lon: Optional[float] = None
    zone_radius_nm: Optional[float] = None
    
    # Confidence
    confidence_pct: float = 50.0  # 0-100
    confidence_reasoning: str = ""
    
    # Details
    reasoning: str = ""
    input_parameters: Dict[str, Any] = field(default_factory=dict)
    assumptions: str = ""
    
    # Drift-specific
    predicted_sinking_location_lat: Optional[float] = None
    predicted_sinking_location_lon: Optional[float] = None
    predicted_sinking_time_hours: Optional[int] = None
    predicted_debris_field_radius_nm: Optional[float] = None
    
    is_superseded: bool = False
    superseded_by_id: Optional[str] = None

@dataclass
class Message:
    """Communication log entry"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: Optional[str] = None
    sender_id: str = ""
    
    recipient_ids: List[str] = field(default_factory=list)
    recipient_org_ids: List[str] = field(default_factory=list)
    
    priority: str = "normal"  # critical, high, normal, low
    message_type: str = ""  # alert, update, query, coordination
    subject: str = ""
    body: str = ""
    
    delivery_method: str = ""  # radio, sms, email, app, phone
    delivery_time: Optional[datetime] = None
    is_broadcast: bool = False
    
    attachments: List[str] = field(default_factory=list)
    
    read_by_ids: List[str] = field(default_factory=list)

@dataclass
class IncidentLogEntry:
    """Timestamped action log"""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    case_id: str = ""
    action_time: Optional[datetime] = None
    
    action_type: str = ""  # task_created, resource_deployed, finding_logged, status_update, decision
    action_description: str = ""
    
    actor_id: Optional[str] = None
    actor_name: str = ""
    
    related_task_id: Optional[str] = None
    related_asset_id: Optional[str] = None
    related_finding_id: Optional[str] = None
    
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    
    summary: str = ""
    details: str = ""

# ============================================================================
# DATABASE MANAGER
# ============================================================================

class SARDatabaseManager:
    """Central database interface for all SAR operations"""
    
    def __init__(self, db_path: Path = Path("sar_platform.db")):
        self.db_path = db_path
        self.logger = logging.getLogger("SARDatabase")
        
        # Initialize database with schema
        self._init_db()
    
    def _init_db(self):
        """Create database and all tables"""
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and execute schema
        schema_path = Path(__file__).parent / "database_schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = f.read()
            
            conn = sqlite3.connect(self.db_path)
            conn.executescript(schema)
            conn.commit()
            conn.close()
            self.logger.info(f"Database initialized: {self.db_path}")
    
    def _get_connection(self):
        """Get database connection with JSON support"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _serialize(self, obj: Any) -> str:
        """Convert dataclass to JSON for storage"""
        if isinstance(obj, dict):
            return json.dumps(obj)
        elif hasattr(obj, '__dataclass_fields__'):
            return json.dumps(asdict(obj), default=str)
        else:
            return json.dumps(obj, default=str)
    
    def _deserialize(self, json_str: str) -> Dict:
        """Convert JSON to dict"""
        if not json_str:
            return {}
        try:
            return json.loads(json_str)
        except:
            return {}
    
    # ========================================================================
    # CASE OPERATIONS
    # ========================================================================
    
    def create_case(self, case: Case) -> str:
        """Create new case, return case ID"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            case.intake_time = datetime.now(timezone.utc)
            
            c.execute('''
                INSERT INTO cases (
                    id, case_number, case_name, case_type, status, priority_level,
                    subject_id, incident_description, incident_date, incident_time,
                    reported_date, reported_time, time_in_condition_hours,
                    last_known_location_lat, last_known_location_lon,
                    last_known_location_description, last_known_time,
                    position_confidence_m, last_seen_by,
                    weather_conditions, water_conditions, terrain_description,
                    primary_contact_id, family_contact_id, government_liaison_id,
                    media_liaison_id, incident_coordinator_id,
                    lead_organization_id, assisting_organizations,
                    search_zones, search_zones_generated_by,
                    search_zones_confidence, area_searched_sq_nm,
                    estimated_total_search_area_sq_nm,
                    findings_count, high_confidence_findings,
                    outcome, resolution_date, resolution_location_lat,
                    resolution_location_lon, resolution_notes,
                    lessons_learned, admin_notes, intake_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?)
            ''', (
                case.id, case.case_number, case.case_name, case.case_type,
                case.status, case.priority_level, case.subject_id,
                case.incident_description, case.incident_date, case.incident_time,
                case.reported_date, case.reported_time, case.time_in_condition_hours,
                case.last_known_location_lat, case.last_known_location_lon,
                case.last_known_location_description, case.last_known_time,
                case.position_confidence_m, case.last_seen_by,
                self._serialize(case.weather_conditions),
                self._serialize(case.water_conditions),
                case.terrain_description,
                case.primary_contact_id, case.family_contact_id,
                case.government_liaison_id, case.media_liaison_id,
                case.incident_coordinator_id, case.lead_organization_id,
                self._serialize(case.assisting_organizations),
                self._serialize(case.search_zones),
                case.search_zones_generated_by, case.search_zones_confidence,
                case.area_searched_sq_nm, case.estimated_total_search_area_sq_nm,
                case.findings_count, case.high_confidence_findings,
                case.outcome, case.resolution_date,
                case.resolution_location_lat, case.resolution_location_lon,
                case.resolution_notes, case.lessons_learned, case.admin_notes,
                case.intake_time, case.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Case created: {case.id} ({case.case_name})")
            return case.id
        
        except Exception as e:
            self.logger.error(f"Error creating case: {e}")
            raise
    
    def get_case(self, case_id: str) -> Optional[Case]:
        """Retrieve case by ID"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('SELECT * FROM cases WHERE id = ?', (case_id,))
            row = c.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Convert to Case object
            case = Case(
                id=row['id'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                intake_time=datetime.fromisoformat(row['intake_time']) if row['intake_time'] else None,
                case_number=row['case_number'] or "",
                case_name=row['case_name'] or "",
                case_type=row['case_type'] or "",
                status=row['status'] or "intake",
                priority_level=row['priority_level'] or 3,
                subject_id=row['subject_id'],
                incident_description=row['incident_description'] or "",
                incident_date=row['incident_date'],
                incident_time=row['incident_time'],
                reported_date=row['reported_date'],
                reported_time=row['reported_time'],
                time_in_condition_hours=row['time_in_condition_hours'],
                last_known_location_lat=row['last_known_location_lat'],
                last_known_location_lon=row['last_known_location_lon'],
                last_known_location_description=row['last_known_location_description'] or "",
                last_known_time=datetime.fromisoformat(row['last_known_time']) if row['last_known_time'] else None,
                position_confidence_m=row['position_confidence_m'] or 500,
                last_seen_by=row['last_seen_by'] or "",
                weather_conditions=self._deserialize(row['weather_conditions']),
                water_conditions=self._deserialize(row['water_conditions']),
                terrain_description=row['terrain_description'] or "",
                primary_contact_id=row['primary_contact_id'],
                family_contact_id=row['family_contact_id'],
                government_liaison_id=row['government_liaison_id'],
                media_liaison_id=row['media_liaison_id'],
                incident_coordinator_id=row['incident_coordinator_id'],
                lead_organization_id=row['lead_organization_id'],
                assisting_organizations=self._deserialize(row['assisting_organizations']),
                search_zones=self._deserialize(row['search_zones']),
                search_zones_generated_by=row['search_zones_generated_by'] or "",
                search_zones_confidence=row['search_zones_confidence'],
                findings_count=row['findings_count'] or 0,
                high_confidence_findings=row['high_confidence_findings'] or 0,
                outcome=row['outcome'],
                resolution_date=datetime.fromisoformat(row['resolution_date']) if row['resolution_date'] else None,
                resolution_location_lat=row['resolution_location_lat'],
                resolution_location_lon=row['resolution_location_lon'],
                resolution_notes=row['resolution_notes'] or "",
                lessons_learned=row['lessons_learned'] or "",
                admin_notes=row['admin_notes'] or ""
            )
            
            return case
        
        except Exception as e:
            self.logger.error(f"Error retrieving case: {e}")
            return None
    
    def get_active_cases(self) -> List[Case]:
        """Get all active cases"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('SELECT id FROM cases WHERE status IN (?, ?)', ('intake', 'active'))
            rows = c.fetchall()
            conn.close()
            
            cases = []
            for row in rows:
                case = self.get_case(row['id'])
                if case:
                    cases.append(case)
            
            return cases
        
        except Exception as e:
            self.logger.error(f"Error retrieving active cases: {e}")
            return []
    
    def update_case_status(self, case_id: str, status: str):
        """Update case status"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('UPDATE cases SET status = ? WHERE id = ?', (status, case_id))
            conn.commit()
            conn.close()
            
            self.logger.info(f"Case {case_id} status updated to {status}")
        
        except Exception as e:
            self.logger.error(f"Error updating case status: {e}")
            raise
    
    def log_incident_action(self, entry: IncidentLogEntry):
        """Log an action to incident timeline"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO incident_log (
                    case_id, action_time, action_type, action_description,
                    actor_id, actor_name, related_task_id, related_asset_id,
                    related_finding_id, location_lat, location_lon,
                    summary, details, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.case_id,
                entry.action_time or datetime.now(timezone.utc),
                entry.action_type,
                entry.action_description,
                entry.actor_id,
                entry.actor_name,
                entry.related_task_id,
                entry.related_asset_id,
                entry.related_finding_id,
                entry.location_lat,
                entry.location_lon,
                entry.summary,
                entry.details,
                entry.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Incident action logged: {entry.action_type}")
        
        except Exception as e:
            self.logger.error(f"Error logging incident action: {e}")
            raise
    
    # ========================================================================
    # TASK OPERATIONS
    # ========================================================================
    
    def create_task(self, task: Task) -> str:
        """Create new task"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            task.assigned_time = datetime.now(timezone.utc)
            
            c.execute('''
                INSERT INTO tasks (
                    id, case_id, task_number, task_type, status,
                    assigned_asset_id, assigned_personnel_ids, assigned_by_id,
                    assigned_time, estimated_duration_minutes,
                    search_zone_lat, search_zone_lon, search_zone_radius_nm,
                    search_pattern, priority, reasoning,
                    success_criteria, minimum_coverage_pct,
                    started_time, estimated_completion_time, actual_completion_time,
                    result_summary, targets_found, high_confidence_targets,
                    coverage_achieved_pct, fuel_consumed_liters, personnel_hours,
                    equipment_used, cost_incurred_usd,
                    sonar_data_files, photos_collected, gps_trackline_path,
                    video_file_path, field_notes, problems_encountered,
                    recommendations, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id, task.case_id, task.task_number, task.task_type, task.status,
                task.assigned_asset_id, self._serialize(task.assigned_personnel_ids),
                task.assigned_by_id, task.assigned_time, task.estimated_duration_minutes,
                task.search_zone_lat, task.search_zone_lon, task.search_zone_radius_nm,
                task.search_pattern, task.priority, task.reasoning,
                task.success_criteria, task.minimum_coverage_pct,
                task.started_time, task.estimated_completion_time,
                task.actual_completion_time, task.result_summary,
                task.targets_found, task.high_confidence_targets,
                task.coverage_achieved_pct, task.fuel_consumed_liters,
                task.personnel_hours, self._serialize(task.equipment_used),
                task.cost_incurred_usd, self._serialize(task.sonar_data_files),
                task.photos_collected, task.gps_trackline_path,
                task.video_file_path, task.field_notes,
                task.problems_encountered, task.recommendations, task.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Task created: {task.id}")
            return task.id
        
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            raise
    
    def get_tasks_for_case(self, case_id: str, status_filter: Optional[str] = None) -> List[Task]:
        """Get all tasks for a case"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            if status_filter:
                c.execute('SELECT id FROM tasks WHERE case_id = ? AND status = ?',
                         (case_id, status_filter))
            else:
                c.execute('SELECT id FROM tasks WHERE case_id = ?', (case_id,))
            
            rows = c.fetchall()
            conn.close()
            
            tasks = []
            for row in rows:
                task = self.get_task(row['id'])
                if task:
                    tasks.append(task)
            
            return tasks
        
        except Exception as e:
            self.logger.error(f"Error retrieving tasks: {e}")
            return []
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = c.fetchone()
            conn.close()
            
            if not row:
                return None
            
            task = Task(
                id=row['id'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                case_id=row['case_id'] or "",
                task_number=row['task_number'] or "",
                task_type=row['task_type'] or "",
                status=row['status'] or "assigned",
                assigned_asset_id=row['assigned_asset_id'],
                assigned_personnel_ids=self._deserialize(row['assigned_personnel_ids']),
                assigned_by_id=row['assigned_by_id'],
                assigned_time=datetime.fromisoformat(row['assigned_time']) if row['assigned_time'] else None,
                estimated_duration_minutes=row['estimated_duration_minutes'],
                search_zone_lat=row['search_zone_lat'],
                search_zone_lon=row['search_zone_lon'],
                search_zone_radius_nm=row['search_zone_radius_nm'],
                search_pattern=row['search_pattern'] or "",
                priority=row['priority'] or 1,
                reasoning=row['reasoning'] or "",
                success_criteria=row['success_criteria'] or "",
                minimum_coverage_pct=row['minimum_coverage_pct'] or 90.0,
                started_time=datetime.fromisoformat(row['started_time']) if row['started_time'] else None,
                estimated_completion_time=datetime.fromisoformat(row['estimated_completion_time']) if row['estimated_completion_time'] else None,
                actual_completion_time=datetime.fromisoformat(row['actual_completion_time']) if row['actual_completion_time'] else None,
                result_summary=row['result_summary'] or "",
                targets_found=row['targets_found'] or 0,
                high_confidence_targets=row['high_confidence_targets'] or 0,
                coverage_achieved_pct=row['coverage_achieved_pct'],
                fuel_consumed_liters=row['fuel_consumed_liters'],
                personnel_hours=row['personnel_hours'] or 0.0,
                equipment_used=self._deserialize(row['equipment_used']),
                cost_incurred_usd=row['cost_incurred_usd'],
                sonar_data_files=self._deserialize(row['sonar_data_files']),
                photos_collected=row['photos_collected'] or 0,
                gps_trackline_path=row['gps_trackline_path'],
                video_file_path=row['video_file_path'],
                field_notes=row['field_notes'] or "",
                problems_encountered=row['problems_encountered'] or "",
                recommendations=row['recommendations'] or ""
            )
            
            return task
        
        except Exception as e:
            self.logger.error(f"Error retrieving task: {e}")
            return None
    
    # ========================================================================
    # ASSET OPERATIONS
    # ========================================================================
    
    def create_asset(self, asset: Asset) -> str:
        """Register asset in system"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO assets (
                    id, asset_type, name, asset_number, organization_id,
                    primary_operator_id, status, current_location_lat,
                    current_location_lon, current_location_time,
                    current_position_accuracy_m, deployments_today,
                    hours_deployed_today, last_deployment_start,
                    last_deployment_end, fuel_level_pct, battery_level_pct,
                    capabilities, max_range_nm, max_duration_hours,
                    specialized_equipment, environmental_limits,
                    personnel_required, support_vehicle_needed,
                    maintenance_requirements, gps_device_id, radio_channel,
                    call_sign, maintenance_status, last_maintenance_date,
                    next_maintenance_due, inspection_notes,
                    acquisition_date, acquisition_cost_usd,
                    operational_cost_per_hour_usd, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                asset.id, asset.asset_type, asset.name, asset.asset_number,
                asset.organization_id, asset.primary_operator_id, asset.status,
                asset.current_location_lat, asset.current_location_lon,
                asset.current_location_time, asset.current_position_accuracy_m,
                asset.deployments_today, asset.hours_deployed_today,
                asset.last_deployment_start, asset.last_deployment_end,
                asset.fuel_level_pct, asset.battery_level_pct,
                self._serialize(asset.capabilities), asset.max_range_nm,
                asset.max_duration_hours, self._serialize(asset.specialized_equipment),
                self._serialize(asset.environmental_limits),
                asset.personnel_required, asset.support_vehicle_needed,
                asset.maintenance_requirements, asset.gps_device_id,
                asset.radio_channel, asset.call_sign, asset.maintenance_status,
                asset.last_maintenance_date, asset.next_maintenance_due,
                asset.inspection_notes, None, None, asset.operational_cost_per_hour_usd,
                asset.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Asset created: {asset.id} ({asset.name})")
            return asset.id
        
        except Exception as e:
            self.logger.error(f"Error creating asset: {e}")
            raise
    
    def get_available_assets(self, asset_type: Optional[str] = None) -> List[Asset]:
        """Get all available assets, optionally filtered by type"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            if asset_type:
                c.execute(
                    'SELECT id FROM assets WHERE status = ? AND asset_type = ?',
                    ('available', asset_type)
                )
            else:
                c.execute('SELECT id FROM assets WHERE status = ?', ('available',))
            
            rows = c.fetchall()
            conn.close()
            
            assets = []
            for row in rows:
                asset = self.get_asset(row['id'])
                if asset:
                    assets.append(asset)
            
            return assets
        
        except Exception as e:
            self.logger.error(f"Error retrieving available assets: {e}")
            return []
    
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Retrieve asset by ID"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('SELECT * FROM assets WHERE id = ?', (asset_id,))
            row = c.fetchone()
            conn.close()
            
            if not row:
                return None
            
            asset = Asset(
                id=row['id'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                asset_type=row['asset_type'] or "",
                name=row['name'] or "",
                asset_number=row['asset_number'] or "",
                organization_id=row['organization_id'] or "",
                primary_operator_id=row['primary_operator_id'],
                status=row['status'] or "available",
                current_location_lat=row['current_location_lat'],
                current_location_lon=row['current_location_lon'],
                current_location_time=datetime.fromisoformat(row['current_location_time']) if row['current_location_time'] else None,
                deployments_today=row['deployments_today'] or 0,
                hours_deployed_today=row['hours_deployed_today'] or 0.0,
                last_deployment_start=datetime.fromisoformat(row['last_deployment_start']) if row['last_deployment_start'] else None,
                last_deployment_end=datetime.fromisoformat(row['last_deployment_end']) if row['last_deployment_end'] else None,
                fuel_level_pct=row['fuel_level_pct'],
                battery_level_pct=row['battery_level_pct'],
                capabilities=self._deserialize(row['capabilities']),
                max_range_nm=row['max_range_nm'],
                max_duration_hours=row['max_duration_hours'],
                personnel_required=row['personnel_required'] or 1,
                support_vehicle_needed=bool(row['support_vehicle_needed']),
                maintenance_requirements=row['maintenance_requirements'] or "",
                radio_channel=row['radio_channel'] or "",
                call_sign=row['call_sign'] or "",
                maintenance_status=row['maintenance_status'] or "operational",
                last_maintenance_date=row['last_maintenance_date'],
                next_maintenance_due=row['next_maintenance_due'],
                operational_cost_per_hour_usd=row['operational_cost_per_hour_usd']
            )
            
            return asset
        
        except Exception as e:
            self.logger.error(f"Error retrieving asset: {e}")
            return None
    
    def update_asset_status(self, asset_id: str, status: str,
                           location_lat: Optional[float] = None,
                           location_lon: Optional[float] = None):
        """Update asset status and location"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''
                UPDATE assets SET status = ?,
                current_location_lat = COALESCE(?, current_location_lat),
                current_location_lon = COALESCE(?, current_location_lon),
                current_location_time = ?
                WHERE id = ?
            ''', (status, location_lat, location_lon, datetime.now(timezone.utc), asset_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Asset {asset_id} status updated to {status}")
        
        except Exception as e:
            self.logger.error(f"Error updating asset status: {e}")
            raise
    
    # ========================================================================
    # FINDING OPERATIONS
    # ========================================================================
    
    def log_finding(self, finding: Finding) -> str:
        """Record a finding"""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO findings (
                    id, case_id, task_id, finding_type, description,
                    confidence_pct, location_lat, location_lon,
                    location_accuracy_m, location_description, found_time,
                    found_by_id, evidence_collected, evidence_storage_location,
                    evidence_notes, photo_paths, measurement_notes,
                    initial_assessment, expert_analysis, matches_subject,
                    contributes_to_resolution, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                finding.id, finding.case_id, finding.task_id,
                finding.finding_type, finding.description, finding.confidence_pct,
                finding.location_lat, finding.location_lon,
                finding.location_accuracy_m, finding.location_description,
                finding.found_time or datetime.now(timezone.utc),
                finding.found_by_id, finding.evidence_collected,
                finding.evidence_storage_location, finding.evidence_notes,
                self._serialize(finding.photo_paths), finding.measurement_notes,
                finding.initial_assessment, finding.expert_analysis,
                finding.matches_subject, finding.contributes_to_resolution,
                finding.created_at
            ))
            
            # Update case findings count
            c.execute('UPDATE cases SET findings_count = findings_count + 1 WHERE id = ?',
                     (finding.case_id,))
            
            if finding.confidence_pct > 80:
                c.execute('UPDATE cases SET high_confidence_findings = high_confidence_findings + 1 WHERE id = ?',
                         (finding.case_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Finding logged: {finding.id}")
            return finding.id
        
        except Exception as e:
            self.logger.error(f"Error logging finding: {e}")
            raise


# ============================================================================
# LOGGER SETUP
# ============================================================================

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('sar_platform.log'),
            logging.StreamHandler()
        ]
    )

if __name__ == "__main__":
    setup_logging()
    db = SARDatabaseManager()
    print(f"Database ready: {db.db_path}")
