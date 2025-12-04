"""
Survey Response Handler for SAR Platform
Collects community feedback on platform features and design
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import uuid

DB_PATH = Path(__file__).parent / "sar_platform.db"

@dataclass
class SurveyResponse:
    """A single survey response from SAR team"""
    id: str
    submission_time: str
    
    # Section 1
    primary_discipline: str  # JSON array
    organization_type: str
    team_size: str
    years_experience: str
    
    # Section 2
    operational_challenges: str  # JSON array
    current_tools_incident: str  # JSON array
    current_tools_data: str  # JSON array
    current_tools_comm: str  # JSON array
    desired_integrations: str  # JSON array
    
    # Section 3
    incidents_per_year: str
    intake_required_fields: str  # JSON array
    intake_format: str
    desired_reports: str  # JSON array
    
    # Section 4
    task_assignment_method: str
    asset_tracking_priority: str  # JSON array
    task_update_preference: str
    needs_offline_capability: str
    
    # Section 5
    findings_logging_method: str
    findings_metadata_priority: str  # JSON array
    needs_confidence_scoring: str
    
    # Section 7
    network_capability: str
    platform_preference: str
    offline_sync_valuable: str
    
    # Section 8
    cesarops_usage: str
    sonar_usage: str
    sonar_challenge: Optional[str] = None
    drone_usage: str = ""
    drone_improvement: Optional[str] = None
    
    # Section 9
    rollout_timeline: str = ""
    training_preference: str = ""
    tech_skill_level: str = ""
    
    # Section 10
    success_metrics: str = ""  # JSON array
    adoption_blockers: str = ""  # JSON array
    
    # Section 11
    feature_difference_maker: Optional[str] = None
    test_scenario: Optional[str] = None
    other_feedback: Optional[str] = None
    
    # Section 12
    contact_allowed: str = ""
    contact_name: Optional[str] = None
    contact_org: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_preference: str = ""  # JSON array
    participation_willing: str = ""  # JSON array
    pilot_timeline: str = ""

class SurveyDatabase:
    """Handle survey responses database operations"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.create_table()
    
    def create_table(self):
        """Create survey_responses table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS survey_responses (
                id TEXT PRIMARY KEY,
                submission_time TEXT NOT NULL,
                
                primary_discipline TEXT,
                organization_type TEXT,
                team_size TEXT,
                years_experience TEXT,
                
                operational_challenges TEXT,
                current_tools_incident TEXT,
                current_tools_data TEXT,
                current_tools_comm TEXT,
                desired_integrations TEXT,
                
                incidents_per_year TEXT,
                intake_required_fields TEXT,
                intake_format TEXT,
                desired_reports TEXT,
                
                task_assignment_method TEXT,
                asset_tracking_priority TEXT,
                task_update_preference TEXT,
                needs_offline_capability TEXT,
                
                findings_logging_method TEXT,
                findings_metadata_priority TEXT,
                needs_confidence_scoring TEXT,
                
                network_capability TEXT,
                platform_preference TEXT,
                offline_sync_valuable TEXT,
                
                cesarops_usage TEXT,
                sonar_usage TEXT,
                sonar_challenge TEXT,
                drone_usage TEXT,
                drone_improvement TEXT,
                
                rollout_timeline TEXT,
                training_preference TEXT,
                tech_skill_level TEXT,
                
                success_metrics TEXT,
                adoption_blockers TEXT,
                
                feature_difference_maker TEXT,
                test_scenario TEXT,
                other_feedback TEXT,
                
                contact_allowed TEXT,
                contact_name TEXT,
                contact_org TEXT,
                contact_role TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                contact_preference TEXT,
                participation_willing TEXT,
                pilot_timeline TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_response(self, response_data: Dict[str, Any]) -> str:
        """Save survey response to database"""
        response_id = str(uuid.uuid4())
        submission_time = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Prepare data with defaults
        data = {
            'id': response_id,
            'submission_time': submission_time,
        }
        
        # Add all response fields
        for key, value in response_data.items():
            if isinstance(value, (list, dict)):
                data[key] = json.dumps(value)
            else:
                data[key] = value
        
        # Build INSERT statement
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data.keys()])
        values = tuple(data.values())
        
        cursor.execute(
            f'INSERT INTO survey_responses ({columns}) VALUES ({placeholders})',
            values
        )
        
        conn.commit()
        conn.close()
        
        return response_id
    
    def get_response(self, response_id: str) -> Optional[Dict]:
        """Get a single response by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM survey_responses WHERE id = ?', (response_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_responses(self) -> List[Dict]:
        """Get all survey responses"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM survey_responses ORDER BY submission_time DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_response_count(self) -> int:
        """Get total number of responses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM survey_responses')
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about responses"""
        responses = self.get_all_responses()
        
        if not responses:
            return {
                'total_responses': 0,
                'organizations': [],
                'disciplines': [],
                'team_sizes': []
            }
        
        organizations = {}
        disciplines = {}
        team_sizes = {}
        
        for response in responses:
            # Count organizations
            org = response.get('organization_type', 'Unknown')
            organizations[org] = organizations.get(org, 0) + 1
            
            # Count disciplines
            if response.get('primary_discipline'):
                try:
                    discs = json.loads(response['primary_discipline'])
                    for disc in discs:
                        disciplines[disc] = disciplines.get(disc, 0) + 1
                except:
                    pass
            
            # Count team sizes
            size = response.get('team_size', 'Unknown')
            team_sizes[size] = team_sizes.get(size, 0) + 1
        
        return {
            'total_responses': len(responses),
            'organizations': dict(sorted(organizations.items(), key=lambda x: x[1], reverse=True)),
            'disciplines': dict(sorted(disciplines.items(), key=lambda x: x[1], reverse=True)),
            'team_sizes': dict(sorted(team_sizes.items(), key=lambda x: x[1], reverse=True)),
        }
    
    def export_csv(self, output_path: Path = None) -> str:
        """Export all responses to CSV"""
        import csv
        
        if output_path is None:
            output_path = self.db_path.parent / "survey_responses.csv"
        
        responses = self.get_all_responses()
        
        if not responses:
            return str(output_path)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=responses[0].keys())
            writer.writeheader()
            writer.writerows(responses)
        
        return str(output_path)

if __name__ == "__main__":
    db = SurveyDatabase()
    print(f"Survey database ready at: {db.db_path}")
    stats = db.get_summary_stats()
    print(f"Total responses: {stats['total_responses']}")
