-- SAR Platform Core Database Schema
-- SQLite3 implementation
-- Version 1.0 - Foundation tables only (extensible for modules)

-- ============================================================================
-- ORGANIZATIONS & CONTACTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,  -- 'volunteer_sar', 'coast_guard', 'fire_dept', 'police', 'k9_unit', 'drone_team', 'dive_team', 'multi_discipline'
    jurisdiction TEXT,  -- 'Great Lakes', 'Lake Michigan', 'Cook County', etc
    
    -- Contact
    primary_contact_id TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    
    -- Location
    station_lat REAL,
    station_lon REAL,
    station_address TEXT,
    
    -- Operational
    is_active INTEGER DEFAULT 1,  -- 1=active, 0=inactive
    response_capability TEXT,  -- comma-separated: 'water_search', 'land_search', 'k9', 'drone', 'dive', 'air'
    avg_response_time_minutes INTEGER,  -- typical deployment time
    service_area TEXT,  -- JSON region description
    
    -- Resource capacity
    typical_personnel_available INTEGER,
    maximum_personnel_available INTEGER,
    assets_owned TEXT,  -- JSON array of asset types/counts
    
    -- System info
    uses_platform INTEGER DEFAULT 0,  -- 1=yes, 0=prospective
    admin_contact_id TEXT,  -- who manages account in system
    
    FOREIGN KEY(primary_contact_id) REFERENCES persons(id),
    FOREIGN KEY(admin_contact_id) REFERENCES persons(id)
);

CREATE TABLE IF NOT EXISTS persons (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    full_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    radio_callsign TEXT,
    
    -- Role & affiliation
    organization_id TEXT,
    role TEXT,  -- 'coordinator', 'k9_handler', 'boat_operator', 'drone_pilot', 'diver', 'volunteer', 'family_member', 'leo', 'government_liaison'
    
    -- Credentials
    certifications TEXT,  -- JSON array: ['SAR_certified', 'CPR', 'Swift_Water_Rescue', 'K9_Handler']
    specializations TEXT,  -- JSON array: ['water_search', 'land_search', 'night_operations']
    years_experience INTEGER,
    
    -- Status
    availability_status TEXT DEFAULT 'available',  -- 'available', 'deployed', 'fatigued', 'unavailable'
    last_deployed TIMESTAMP,
    deployments_this_month INTEGER DEFAULT 0,
    total_hours_this_month INTEGER DEFAULT 0,
    
    -- Background
    address TEXT,
    date_of_birth DATE,
    
    -- System
    is_active INTEGER DEFAULT 1,
    
    FOREIGN KEY(organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT NOT NULL,
    contact_type TEXT,  -- 'family_member', 'requester', 'government_liaison', 'friend', 'witness'
    
    person_id TEXT,  -- link to persons table if they're a known contact
    
    -- Direct contact info
    name TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    relationship_to_subject TEXT,  -- for family: 'parent', 'spouse', 'sibling', etc
    
    -- Relationship to subject
    subject_id TEXT,  -- for family members, link to subject record
    
    -- Notification preferences
    notify_on_status_change INTEGER DEFAULT 1,  -- 1=yes, 0=no
    notify_on_finding INTEGER DEFAULT 1,
    notify_on_resolution INTEGER DEFAULT 1,
    contact_method_preference TEXT,  -- 'phone', 'email', 'sms'
    
    -- Tracking
    last_contact_time TIMESTAMP,
    last_contact_notes TEXT,
    contact_quality TEXT,  -- 'excellent', 'good', 'poor', 'unreliable'  (emotional state, reliability)
    
    -- Internal notes
    reliability_notes TEXT,  -- "Gets emotional, provide updates carefully"
    
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(person_id) REFERENCES persons(id),
    FOREIGN KEY(subject_id) REFERENCES subjects(id)
);

-- ============================================================================
-- CASE MANAGEMENT CORE
-- ============================================================================

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    intake_time TIMESTAMP,
    
    -- Identification
    case_number TEXT UNIQUE,  -- human-readable identifier
    case_name TEXT,  -- "Rosa Missing Vessel"
    case_type TEXT NOT NULL,  -- 'person_missing', 'vessel_missing', 'aircraft_missing', 'water_rescue'
    
    -- Status
    status TEXT DEFAULT 'active',  -- 'intake', 'active', 'suspended', 'closed_found', 'closed_presumed_lost', 'closed_other'
    priority_level INTEGER DEFAULT 3,  -- 1=critical (child, medical), 2=high (adult), 3=normal, 4=low
    
    -- Subject information
    subject_id TEXT,  -- link to subjects table for details
    
    -- Incident details
    incident_description TEXT,  -- Free-form what happened
    incident_date DATE,
    incident_time TIME,
    reported_date DATE,
    reported_time TIME,
    time_in_condition_hours INTEGER,  -- How long subject exposed
    
    -- Last known information
    last_known_location_lat REAL,
    last_known_location_lon REAL,
    last_known_location_description TEXT,  -- "Pier at State Park"
    last_known_time TIMESTAMP,
    position_confidence_m INTEGER,  -- Estimated GPS error radius in meters
    last_seen_by TEXT,  -- Name or entity
    
    -- Environmental conditions at incident
    weather_conditions TEXT,  -- JSON: {wind_kmh, direction, temp_c, visibility_m, conditions}
    water_conditions TEXT,  -- JSON: {temp_c, wave_height_m, current_speed_kts, current_direction}
    terrain_description TEXT,  -- 'lake_water', 'ocean', 'river', 'forest', 'mountain', 'urban'
    
    -- Contacts
    primary_contact_id TEXT,  -- Person who reported/called in
    family_contact_id TEXT,  -- Primary family liaison
    government_liaison_id TEXT,  -- Coast Guard, State Police, etc
    media_liaison_id TEXT,  -- Who handles press
    incident_coordinator_id TEXT,  -- Who's running SAR operation
    
    -- Resources
    lead_organization_id TEXT,
    assisting_organizations TEXT,  -- JSON array of org IDs
    
    -- Intelligence & Prediction
    search_zones TEXT,  -- JSON array of predicted zones
    search_zones_generated_by TEXT,  -- 'CESAROPS', 'expert_judgment', 'other_model'
    search_zones_confidence REAL,  -- Overall confidence (0-1)
    
    -- Coverage tracking
    search_zones_completed INTEGER DEFAULT 0,
    search_zones_in_progress INTEGER DEFAULT 0,
    area_searched_sq_nm REAL DEFAULT 0,
    estimated_total_search_area_sq_nm REAL,
    
    -- Findings
    findings_count INTEGER DEFAULT 0,
    high_confidence_findings INTEGER DEFAULT 0,
    
    -- Resolution
    outcome TEXT,  -- 'found_alive', 'found_deceased', 'presumed_lost', 'gave_up', 'resolved_other'
    resolution_date TIMESTAMP,
    resolution_location_lat REAL,
    resolution_location_lon REAL,
    resolution_notes TEXT,
    
    -- Post-incident
    lessons_learned TEXT,
    admin_notes TEXT,
    
    FOREIGN KEY(subject_id) REFERENCES subjects(id),
    FOREIGN KEY(primary_contact_id) REFERENCES contacts(id),
    FOREIGN KEY(family_contact_id) REFERENCES contacts(id),
    FOREIGN KEY(government_liaison_id) REFERENCES persons(id),
    FOREIGN KEY(media_liaison_id) REFERENCES persons(id),
    FOREIGN KEY(incident_coordinator_id) REFERENCES persons(id),
    FOREIGN KEY(lead_organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT NOT NULL,
    
    -- Identity
    full_name TEXT NOT NULL,
    age INTEGER,
    date_of_birth DATE,
    gender TEXT,  -- 'male', 'female', 'other'
    
    -- Physical description
    height_cm INTEGER,
    weight_kg INTEGER,
    hair_color TEXT,
    eye_color TEXT,
    distinguishing_marks TEXT,  -- Scars, tattoos, etc
    usual_clothing TEXT,
    photo_path TEXT,  -- File path to photo
    
    -- For vessels
    vessel_name TEXT,
    vessel_type TEXT,  -- 'sailboat', 'speedboat', 'cargo_ship', 'fishing_vessel'
    vessel_length_m REAL,
    vessel_width_m REAL,
    vessel_depth_m REAL,
    vessel_material TEXT,  -- 'fiberglass', 'steel', 'wood'
    vessel_color TEXT,
    vessel_buoyancy_kg REAL,  -- If known
    vessel_registration TEXT,  -- Hull number, IMO, etc
    vessel_radio_callsign TEXT,  -- VHF designation
    
    -- Medical
    medical_conditions TEXT,  -- JSON array: ['diabetic', 'heart_condition', 'medication_dependent']
    medications_required TEXT,  -- What meds does subject take
    allergies TEXT,
    mobility_limitations TEXT,  -- "Uses wheelchair", "Partial paralysis"
    mental_health_notes TEXT,  -- "Depression", "Dementia"
    suicide_risk TEXT,  -- 'no', 'low', 'moderate', 'high'
    
    -- Behavioral
    typical_behavior TEXT,  -- For lost persons
    survival_skills TEXT,  -- Swimming ability, outdoor experience
    equipment_with_subject TEXT,  -- GPS, PLB, life jacket, etc
    
    -- Known patterns
    has_returned_before INTEGER DEFAULT 0,  -- For lost persons
    previous_incident TEXT,  -- Description of prior disappearance
    
    FOREIGN KEY(case_id) REFERENCES cases(id)
);

-- ============================================================================
-- ASSETS & RESOURCES
-- ============================================================================

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Identification
    asset_type TEXT NOT NULL,  -- 'k9_unit', 'boat', 'drone', 'vehicle', 'diver_team', 'aircraft'
    name TEXT NOT NULL,  -- "Max" (K9), "SeaHawk" (boat)
    asset_number TEXT,  -- Human-readable ID
    
    -- Organization
    organization_id TEXT NOT NULL,
    primary_operator_id TEXT,
    
    -- Status
    status TEXT DEFAULT 'available',  -- 'available', 'deployed', 'returning', 'fatigued', 'maintenance', 'unavailable'
    current_location_lat REAL,
    current_location_lon REAL,
    current_location_time TIMESTAMP,
    current_position_accuracy_m INTEGER,  -- GPS accuracy
    
    -- Operational state
    deployments_today INTEGER DEFAULT 0,
    hours_deployed_today REAL DEFAULT 0,
    last_deployment_start TIMESTAMP,
    last_deployment_end TIMESTAMP,
    fuel_level_pct REAL,  -- For vehicles/boats
    battery_level_pct REAL,  -- For drones, etc
    
    -- Capabilities
    capabilities TEXT,  -- JSON array: ['surface_search', 'night_ops', 'sonar', 'video_stream']
    max_range_nm REAL,  -- Operating range in nautical miles
    max_duration_hours REAL,  -- Max operational time per deployment
    specialized_equipment TEXT,  -- JSON: {sonar: true, thermal_camera: true}
    
    -- Constraints & requirements
    environmental_limits TEXT,  -- JSON: {max_wave_height: 3, min_water_temp: 5}
    personnel_required INTEGER,  -- How many people to operate
    support_vehicle_needed INTEGER,  -- 1=yes, 0=no
    maintenance_requirements TEXT,  -- "Rest 4 hrs after 2 hrs deployment"
    
    -- Tracking
    gps_device_id TEXT,  -- Serial number if tracked via GPS
    radio_channel TEXT,  -- VHF freq or radio channel
    call_sign TEXT,  -- Radio designation
    
    -- Maintenance
    maintenance_status TEXT DEFAULT 'operational',  -- 'operational', 'needs_service', 'in_repair'
    last_maintenance_date DATE,
    next_maintenance_due DATE,
    inspection_notes TEXT,
    
    -- Ownership & costs
    acquisition_date DATE,
    acquisition_cost_usd INTEGER,
    operational_cost_per_hour_usd REAL,  -- For cost analysis
    
    FOREIGN KEY(organization_id) REFERENCES organizations(id),
    FOREIGN KEY(primary_operator_id) REFERENCES persons(id)
);

-- ============================================================================
-- TASKS & OPERATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT NOT NULL,
    task_number TEXT,  -- "Task 1", "Task 2" for human reference
    
    -- Type & status
    task_type TEXT,  -- 'sonar_search', 'drone_search', 'k9_search', 'diver_deployment', 'shore_search', 'coordination'
    status TEXT DEFAULT 'assigned',  -- 'assigned', 'in_progress', 'paused', 'complete', 'cancelled'
    
    -- Assignment
    assigned_asset_id TEXT,
    assigned_personnel_ids TEXT,  -- JSON array of person IDs
    assigned_by_id TEXT,
    assigned_time TIMESTAMP,
    estimated_duration_minutes INTEGER,
    
    -- Search specifics
    search_zone_lat REAL,
    search_zone_lon REAL,
    search_zone_radius_nm REAL,
    search_zone_polygon TEXT,  -- GeoJSON if not circular
    search_pattern TEXT,  -- 'grid', 'circular_spiral', 'sweep', 'random', 'sonar_trackline'
    priority INTEGER,  -- 1=highest, for task ordering
    reasoning TEXT,  -- Why this zone (e.g., "Zone A from CESAROPS prediction")
    
    -- Success criteria
    success_criteria TEXT,  -- Free-form: "No high-confidence targets found" vs "Visual confirmation of target"
    minimum_coverage_pct REAL DEFAULT 90,  -- % of zone that must be covered
    
    -- Execution tracking
    started_time TIMESTAMP,
    estimated_completion_time TIMESTAMP,
    actual_completion_time TIMESTAMP,
    
    -- Results
    result_summary TEXT,
    targets_found INTEGER DEFAULT 0,
    high_confidence_targets INTEGER DEFAULT 0,  -- confidence > 80%
    coverage_achieved_pct REAL,
    
    -- Resource tracking
    fuel_consumed_liters REAL,
    personnel_hours REAL,
    equipment_used TEXT,  -- JSON array
    cost_incurred_usd REAL,
    
    -- Field data
    sonar_data_files TEXT,  -- JSON array of file paths
    photos_collected INTEGER DEFAULT 0,
    photo_path_pattern TEXT,  -- Directory where photos saved
    gps_trackline_path TEXT,  -- KML of coverage path
    video_file_path TEXT,  -- Drone/boat video
    
    -- Communication log
    status_update_count INTEGER DEFAULT 0,
    latest_status_update TEXT,
    latest_status_time TIMESTAMP,
    
    -- Notes
    field_notes TEXT,
    problems_encountered TEXT,
    recommendations TEXT,
    
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(assigned_asset_id) REFERENCES assets(id),
    FOREIGN KEY(assigned_by_id) REFERENCES persons(id)
);

CREATE TABLE IF NOT EXISTS task_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    task_id TEXT NOT NULL,
    updated_by_id TEXT,  -- Person who gave update
    update_time TIMESTAMP,
    
    status TEXT,  -- Current task status
    progress_pct REAL,  -- % complete
    location_lat REAL,  -- Where they are now
    location_lon REAL,
    
    message TEXT,  -- Update text
    has_findings INTEGER DEFAULT 0,  -- 1=new findings reported
    
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(updated_by_id) REFERENCES persons(id)
);

-- ============================================================================
-- FINDINGS & INTELLIGENCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT NOT NULL,
    task_id TEXT,  -- Which task found this
    
    finding_type TEXT,  -- 'debris', 'personal_item', 'vessel_part', 'remains', 'footprint', 'clothing', 'other'
    description TEXT,
    confidence_pct REAL,  -- How certain is this a finding? (0-100)
    
    -- Location
    location_lat REAL,
    location_lon REAL,
    location_accuracy_m INTEGER,  -- GPS error radius
    location_description TEXT,  -- "50m south of dock"
    
    -- Timing
    found_time TIMESTAMP,
    found_by_id TEXT,
    
    -- Evidence
    evidence_collected INTEGER DEFAULT 0,  -- 1=yes, 0=no
    evidence_storage_location TEXT,  -- Where it's being kept
    evidence_notes TEXT,
    
    -- Documentation
    photo_paths TEXT,  -- JSON array of file paths
    measurement_notes TEXT,  -- Size, weight, condition
    
    -- Analysis
    initial_assessment TEXT,  -- Quick evaluation
    expert_analysis TEXT,  -- Detailed examination
    matches_subject INTEGER DEFAULT 0,  -- 1=yes, 0=no, null=unknown
    
    -- Resolution
    contributes_to_resolution INTEGER DEFAULT 0,  -- 1=yes, 0=no
    
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(found_by_id) REFERENCES persons(id)
);

-- ============================================================================
-- PREDICTIONS & INTELLIGENCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT NOT NULL,
    
    -- Model info
    model_name TEXT,  -- 'CESAROPS', 'lost_person_behavior', 'drift_ballistic'
    model_version TEXT,
    generated_time TIMESTAMP,
    
    -- Zone
    zone_lat REAL,
    zone_lon REAL,
    zone_radius_nm REAL,
    zone_polygon TEXT,  -- GeoJSON if not circular
    
    -- Confidence
    confidence_pct REAL,  -- 0-100
    confidence_reasoning TEXT,  -- Why this confidence level
    
    -- Metadata
    reasoning TEXT,  -- Why this prediction (inputs used, logic)
    input_parameters TEXT,  -- JSON of what went into model
    assumptions TEXT,  -- What did we assume
    
    -- For drift predictions specifically
    predicted_sinking_location_lat REAL,  -- Where object ends up
    predicted_sinking_location_lon REAL,
    predicted_sinking_time_hours INTEGER,  -- How long to sink
    predicted_debris_field_radius_nm REAL,
    
    -- Validity
    is_superseded INTEGER DEFAULT 0,  -- 1=newer prediction available
    superseded_by_id TEXT,  -- Link to newer prediction
    
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(superseded_by_id) REFERENCES predictions(id)
);

-- ============================================================================
-- COMMUNICATIONS & LOGGING
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT,  -- May be null for general messages
    sender_id TEXT NOT NULL,
    
    -- Recipients (can be individual or group)
    recipient_ids TEXT,  -- JSON array of person IDs
    recipient_org_ids TEXT,  -- JSON array of org IDs (broadcast to whole org)
    
    -- Content
    priority TEXT DEFAULT 'normal',  -- 'critical', 'high', 'normal', 'low'
    message_type TEXT,  -- 'alert', 'update', 'query', 'coordination', 'status'
    subject TEXT,
    body TEXT,
    
    -- Delivery
    delivery_method TEXT,  -- 'radio', 'sms', 'email', 'app', 'phone'
    delivery_time TIMESTAMP,
    is_broadcast INTEGER DEFAULT 0,  -- 1=broadcast to all relevant
    
    -- Metadata
    attachments TEXT,  -- JSON array of file paths
    location_context_lat REAL,  -- Where message applies
    location_context_lon REAL,
    
    -- Read receipts
    read_by_ids TEXT,  -- JSON array of person IDs
    read_times TEXT,  -- JSON mapping of person_id -> timestamp
    
    -- Radio-specific
    radio_channel TEXT,  -- If sent via radio
    radio_recording_path TEXT,  -- Audio file if available
    
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(sender_id) REFERENCES persons(id)
);

CREATE TABLE IF NOT EXISTS incident_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    case_id TEXT NOT NULL,
    action_time TIMESTAMP,
    
    -- Action classification
    action_type TEXT,  -- 'task_created', 'resource_deployed', 'finding_logged', 'status_update', 'decision', 'resource_released'
    action_description TEXT,
    
    -- Actor & context
    actor_id TEXT,  -- Person performing action
    actor_name TEXT,  -- Backup if person record not available
    
    -- Details by type
    related_task_id TEXT,
    related_asset_id TEXT,
    related_finding_id TEXT,
    
    -- Location context
    location_lat REAL,
    location_lon REAL,
    
    -- Full text for chronology
    summary TEXT,  -- Human-readable summary for incident timeline
    details TEXT,  -- Extended notes
    
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(actor_id) REFERENCES persons(id),
    FOREIGN KEY(related_task_id) REFERENCES tasks(id),
    FOREIGN KEY(related_asset_id) REFERENCES assets(id),
    FOREIGN KEY(related_finding_id) REFERENCES findings(id)
);

-- ============================================================================
-- INDEXING (for query performance)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_created ON cases(created_at);
CREATE INDEX IF NOT EXISTS idx_cases_incident_coord ON cases(incident_coordinator_id);

CREATE INDEX IF NOT EXISTS idx_tasks_case ON tasks(case_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_asset ON tasks(assigned_asset_id);

CREATE INDEX IF NOT EXISTS idx_assets_org ON assets(organization_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);

CREATE INDEX IF NOT EXISTS idx_findings_case ON findings(case_id);
CREATE INDEX IF NOT EXISTS idx_findings_task ON findings(task_id);
CREATE INDEX IF NOT EXISTS idx_findings_confidence ON findings(confidence_pct);

CREATE INDEX IF NOT EXISTS idx_messages_case ON messages(case_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);

CREATE INDEX IF NOT EXISTS idx_incident_log_case ON incident_log(case_id);
CREATE INDEX IF NOT EXISTS idx_incident_log_time ON incident_log(action_time);

CREATE INDEX IF NOT EXISTS idx_predictions_case ON predictions(case_id);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions(confidence_pct);
