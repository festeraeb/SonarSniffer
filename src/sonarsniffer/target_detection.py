"""
Advanced Target Detection and Classification System
for Search and Rescue (SAR) and Wreck Hunting Applications

This module implements ML-based target recognition for:
- Wreck detection and classification
- Vehicle/car detection (submerged)
- Human body detection (SAR operations)
- Anomaly detection for unknown objects
- Bottom composition analysis
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import cv2
from PIL import Image
import json
import sqlite3
from datetime import datetime
import math

# ML libraries
try:
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available, using basic algorithms")

try:
    import scipy.ndimage as ndimage
    from scipy.spatial.distance import cdist
    from scipy.signal import find_peaks, savgol_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available, reduced functionality")

@dataclass
class TargetSignature:
    """Signature characteristics for different target types"""
    name: str
    size_range: Tuple[float, float]  # min, max size in meters
    aspect_ratio_range: Tuple[float, float]  # min, max aspect ratio
    echo_strength_range: Tuple[float, float]  # min, max relative echo strength
    shape_complexity: float  # 0-1, simple to complex
    shadow_characteristics: str  # "sharp", "diffuse", "none"
    typical_depth_range: Tuple[float, float]  # typical depth range
    context_clues: List[str]  # environmental context

class TargetDetector:
    """Advanced target detection and classification system"""
    
    def __init__(self, rsd_path: str, csv_path: str):
        self.rsd_path = Path(rsd_path)
        self.csv_path = Path(csv_path)
        self.records_df = None
        self.sonar_cache = {}
        
        # Target signatures database
        self.target_signatures = self._init_target_signatures()
        
        # Detection parameters
        self.noise_threshold = 0.1
        self.min_target_size = 0.5  # meters
        self.max_target_size = 100.0  # meters
        self.shadow_detection_sensitivity = 0.7
        
        # Results storage
        self.detected_targets = []
        self.anomalies = []
        self.bottom_classifications = []
        
    def _init_target_signatures(self) -> Dict[str, TargetSignature]:
        """Initialize target signature database"""
        signatures = {
            'shipwreck_large': TargetSignature(
                name="Large Shipwreck",
                size_range=(20.0, 200.0),
                aspect_ratio_range=(2.0, 8.0),
                echo_strength_range=(0.7, 1.0),
                shape_complexity=0.8,
                shadow_characteristics="sharp",
                typical_depth_range=(10.0, 200.0),
                context_clues=["debris_field", "linear_features", "multiple_echoes"]
            ),
            'shipwreck_small': TargetSignature(
                name="Small Vessel/Boat",
                size_range=(5.0, 25.0),
                aspect_ratio_range=(2.0, 5.0),
                echo_strength_range=(0.6, 0.9),
                shape_complexity=0.6,
                shadow_characteristics="sharp",
                typical_depth_range=(2.0, 50.0),
                context_clues=["single_target", "boat_shaped"]
            ),
            'vehicle_car': TargetSignature(
                name="Submerged Vehicle",
                size_range=(3.0, 8.0),
                aspect_ratio_range=(1.5, 3.0),
                echo_strength_range=(0.5, 0.8),
                shape_complexity=0.4,
                shadow_characteristics="diffuse",
                typical_depth_range=(1.0, 30.0),
                context_clues=["rectangular", "near_shore", "road_access"]
            ),
            'human_body': TargetSignature(
                name="Human Body",
                size_range=(0.3, 2.0),
                aspect_ratio_range=(0.3, 3.0),
                echo_strength_range=(0.2, 0.6),
                shape_complexity=0.3,
                shadow_characteristics="diffuse",
                typical_depth_range=(0.5, 50.0),
                context_clues=["small_target", "soft_echo", "isolated"]
            ),
            'debris_field': TargetSignature(
                name="Debris Field",
                size_range=(5.0, 100.0),
                aspect_ratio_range=(0.5, 10.0),
                echo_strength_range=(0.3, 0.8),
                shape_complexity=0.9,
                shadow_characteristics="multiple",
                typical_depth_range=(1.0, 200.0),
                context_clues=["scattered", "multiple_targets", "varied_sizes"]
            ),
            'geological_feature': TargetSignature(
                name="Rock Formation",
                size_range=(1.0, 50.0),
                aspect_ratio_range=(0.8, 5.0),
                echo_strength_range=(0.8, 1.0),
                shape_complexity=0.7,
                shadow_characteristics="sharp",
                typical_depth_range=(0.5, 500.0),
                context_clues=["natural_shape", "hard_echo", "irregular"]
            )
        }
        return signatures
    
    def load_data(self):
        """Load sonar data from CSV file"""
        print(f"Loading sonar data from {self.csv_path}")
        
        try:
            self.records_df = pd.read_csv(self.csv_path)
            print(f"Loaded {len(self.records_df)} records")
            
            # Filter to only records with sonar data
            sonar_records = self.records_df[
                (self.records_df['sonar_ofs'].notna()) & 
                (self.records_df['sonar_size'] > 0) &
                (self.records_df['channel_id'].notna())
            ]
            
            print(f"Found {len(sonar_records)} records with sonar data")
            print(f"Channels available: {sorted(sonar_records['channel_id'].unique())}")
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def extract_sonar_data(self, record) -> Optional[np.ndarray]:
        """Extract sonar data payload from RSD file"""
        if pd.isna(record['sonar_ofs']) or pd.isna(record['sonar_size']):
            return None
            
        cache_key = (record['sonar_ofs'], record['sonar_size'])
        if cache_key in self.sonar_cache:
            return self.sonar_cache[cache_key]
        
        try:
            with open(self.rsd_path, 'rb') as f:
                f.seek(int(record['sonar_ofs']))
                payload = f.read(int(record['sonar_size']))
                
            if payload:
                # Convert to intensity values
                sonar_data = np.frombuffer(payload, dtype=np.uint8).astype(np.float32) / 255.0
                self.sonar_cache[cache_key] = sonar_data
                return sonar_data
                
        except Exception as e:
            print(f"Error reading sonar data: {e}")
            
        return None
    
    def detect_targets_in_ping(self, sonar_data: np.ndarray, record) -> List[Dict]:
        """Detect potential targets in a single sonar ping"""
        if sonar_data is None or len(sonar_data) == 0:
            return []
        
        targets = []
        
        # Smooth the data to reduce noise
        if SCIPY_AVAILABLE and len(sonar_data) > 5:
            smoothed = savgol_filter(sonar_data, min(5, len(sonar_data)//2*2+1), 2)
        else:
            # Simple moving average fallback
            window = 3
            smoothed = np.convolve(sonar_data, np.ones(window)/window, mode='same')
        
        # Detect peaks (potential targets)
        if SCIPY_AVAILABLE:
            peaks, properties = find_peaks(
                smoothed, 
                height=self.noise_threshold,
                distance=5,  # Minimum distance between peaks
                width=2      # Minimum width of peaks
            )
        else:
            # Simple peak detection fallback
            peaks = []
            for i in range(1, len(smoothed) - 1):
                if (smoothed[i] > smoothed[i-1] and 
                    smoothed[i] > smoothed[i+1] and 
                    smoothed[i] > self.noise_threshold):
                    peaks.append(i)
            peaks = np.array(peaks)
            properties = {'widths': np.ones(len(peaks)) * 3}
        
        for i, peak_idx in enumerate(peaks):
            # Calculate target characteristics
            peak_value = smoothed[peak_idx]
            
            # Estimate target size based on beam angle and sample position
            beam_angle = record.get('beam_deg', -20.0)  # Default sidescan angle
            sample_rate = record.get('sample_cnt', 2048)
            range_resolution = 0.01  # Approximate range resolution in meters
            
            # Convert sample index to range
            target_range = peak_idx * range_resolution * (sample_rate / len(sonar_data))
            
            # Estimate target width
            if SCIPY_AVAILABLE and 'widths' in properties:
                width_samples = properties['widths'][i] if i < len(properties['widths']) else 3
            else:
                width_samples = 3
            
            target_width = width_samples * range_resolution * (sample_rate / len(sonar_data))
            
            # Look for shadow behind target
            shadow_start = min(peak_idx + int(width_samples), len(smoothed) - 1)
            shadow_end = min(shadow_start + 10, len(smoothed))
            
            if shadow_end > shadow_start:
                shadow_region = smoothed[shadow_start:shadow_end]
                shadow_strength = 1.0 - np.mean(shadow_region) / (peak_value + 1e-6)
            else:
                shadow_strength = 0.0
            
            target = {
                'ping_id': record.get('seq', 0),
                'channel_id': record.get('channel_id', 0),
                'timestamp': record.get('time_ms', 0),
                'lat': record.get('lat'),
                'lon': record.get('lon'),
                'depth': record.get('depth_m', 0),
                'target_range': target_range,
                'target_width': target_width,
                'echo_strength': peak_value,
                'shadow_strength': shadow_strength,
                'sample_idx': peak_idx,
                'beam_angle': beam_angle,
                'raw_sonar_data': sonar_data.tolist()  # Store for later analysis
            }
            
            targets.append(target)
        
        return targets
    
    def classify_target_cluster(self, cluster_targets: List[Dict]) -> Dict:
        """Classify a cluster of targets across multiple pings"""
        if not cluster_targets:
            return {'classification': 'unknown', 'confidence': 0.0}
        
        # Calculate cluster characteristics
        ranges = [t['target_range'] for t in cluster_targets]
        widths = [t['target_width'] for t in cluster_targets]
        echo_strengths = [t['echo_strength'] for t in cluster_targets]
        shadow_strengths = [t['shadow_strength'] for t in cluster_targets]
        
        cluster_size = max(ranges) - min(ranges) if len(ranges) > 1 else np.mean(widths)
        aspect_ratio = cluster_size / np.mean(widths) if np.mean(widths) > 0 else 1.0
        avg_echo_strength = np.mean(echo_strengths)
        avg_shadow_strength = np.mean(shadow_strengths)
        
        # Calculate shape complexity (variation in echo strengths)
        shape_complexity = np.std(echo_strengths) / (np.mean(echo_strengths) + 1e-6)
        
        # Determine shadow characteristics
        if avg_shadow_strength > 0.5:
            shadow_type = "sharp"
        elif avg_shadow_strength > 0.2:
            shadow_type = "diffuse"
        else:
            shadow_type = "none"
        
        # Calculate depth context
        depths = [t['depth'] for t in cluster_targets if t['depth'] is not None]
        avg_depth = np.mean(depths) if depths else 0.0
        
        # Score against each target signature
        best_match = None
        best_score = 0.0
        scores = {}
        
        for sig_name, signature in self.target_signatures.items():
            score = 0.0
            factors = 0
            
            # Size match
            if signature.size_range[0] <= cluster_size <= signature.size_range[1]:
                score += 1.0
            else:
                # Penalty for size mismatch
                size_penalty = min(
                    abs(cluster_size - signature.size_range[0]) / signature.size_range[0],
                    abs(cluster_size - signature.size_range[1]) / signature.size_range[1]
                )
                score += max(0, 1.0 - size_penalty)
            factors += 1
            
            # Aspect ratio match
            if signature.aspect_ratio_range[0] <= aspect_ratio <= signature.aspect_ratio_range[1]:
                score += 1.0
            else:
                ar_penalty = min(
                    abs(aspect_ratio - signature.aspect_ratio_range[0]) / signature.aspect_ratio_range[0],
                    abs(aspect_ratio - signature.aspect_ratio_range[1]) / signature.aspect_ratio_range[1]
                )
                score += max(0, 1.0 - ar_penalty)
            factors += 1
            
            # Echo strength match
            if signature.echo_strength_range[0] <= avg_echo_strength <= signature.echo_strength_range[1]:
                score += 1.0
            else:
                echo_penalty = min(
                    abs(avg_echo_strength - signature.echo_strength_range[0]),
                    abs(avg_echo_strength - signature.echo_strength_range[1])
                )
                score += max(0, 1.0 - echo_penalty * 2)
            factors += 1
            
            # Shadow characteristics match
            if shadow_type == signature.shadow_characteristics:
                score += 1.0
            elif signature.shadow_characteristics == "multiple":
                score += 0.5  # Partial match for complex targets
            factors += 1
            
            # Depth range match
            if signature.typical_depth_range[0] <= avg_depth <= signature.typical_depth_range[1]:
                score += 0.5
            factors += 0.5
            
            # Shape complexity match
            complexity_diff = abs(shape_complexity - signature.shape_complexity)
            score += max(0, 1.0 - complexity_diff) * 0.5
            factors += 0.5
            
            final_score = score / factors if factors > 0 else 0.0
            scores[sig_name] = final_score
            
            if final_score > best_score:
                best_score = final_score
                best_match = sig_name
        
        return {
            'classification': best_match,
            'confidence': best_score,
            'all_scores': scores,
            'characteristics': {
                'size': cluster_size,
                'aspect_ratio': aspect_ratio,
                'echo_strength': avg_echo_strength,
                'shadow_strength': avg_shadow_strength,
                'shape_complexity': shape_complexity,
                'shadow_type': shadow_type,
                'depth': avg_depth
            }
        }
    
    def cluster_targets_spatial(self, targets: List[Dict]) -> List[List[Dict]]:
        """Group targets that are spatially close (same object across pings)"""
        if not targets:
            return []
        
        # Extract spatial features for clustering
        features = []
        for target in targets:
            lat = target.get('lat', 0.0) or 0.0
            lon = target.get('lon', 0.0) or 0.0
            range_m = target.get('target_range', 0.0)
            
            # Convert lat/lon to approximate meters for clustering
            lat_m = lat * 111320  # Approximate meters per degree latitude
            lon_m = lon * 111320 * math.cos(math.radians(lat))
            
            features.append([lat_m, lon_m, range_m])
        
        features = np.array(features)
        
        if SKLEARN_AVAILABLE and len(features) > 2:
            # Use DBSCAN for spatial clustering
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # DBSCAN parameters tuned for sonar targets
            clustering = DBSCAN(eps=0.3, min_samples=2).fit(features_scaled)
            labels = clustering.labels_
        else:
            # Simple distance-based clustering fallback
            labels = np.zeros(len(features))
            cluster_id = 0
            assigned = set()
            
            for i in range(len(features)):
                if i in assigned:
                    continue
                    
                current_cluster = []
                for j in range(i, len(features)):
                    if j in assigned:
                        continue
                    
                    # Calculate distance
                    dist = np.sqrt(np.sum((features[i] - features[j])**2))
                    if dist < 5.0:  # 5 meter threshold
                        labels[j] = cluster_id
                        assigned.add(j)
                        current_cluster.append(j)
                
                if current_cluster:
                    cluster_id += 1
        
        # Group targets by cluster
        clusters = {}
        for i, label in enumerate(labels):
            if label == -1:  # Noise in DBSCAN
                label = f"noise_{i}"
            
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(targets[i])
        
        return list(clusters.values())
    
    def detect_anomalies(self, targets: List[Dict]) -> List[Dict]:
        """Detect unusual targets that don't match known signatures"""
        if not targets or not SKLEARN_AVAILABLE:
            return []
        
        # Extract features for anomaly detection
        features = []
        for target in targets:
            feature_vector = [
                target.get('target_range', 0.0),
                target.get('target_width', 0.0),
                target.get('echo_strength', 0.0),
                target.get('shadow_strength', 0.0),
                target.get('depth', 0.0) or 0.0
            ]
            features.append(feature_vector)
        
        features = np.array(features)
        
        if len(features) < 10:
            return []  # Need minimum samples for anomaly detection
        
        # Use Isolation Forest for anomaly detection
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        anomaly_labels = iso_forest.fit_predict(features)
        
        anomalies = []
        for i, label in enumerate(anomaly_labels):
            if label == -1:  # Anomaly
                anomaly = targets[i].copy()
                anomaly['anomaly_score'] = iso_forest.decision_function([features[i]])[0]
                anomalies.append(anomaly)
        
        return anomalies
    
    def analyze_bottom_composition(self, records_sample: pd.DataFrame) -> Dict:
        """Analyze bottom composition and characteristics"""
        compositions = []
        
        for _, record in records_sample.iterrows():
            sonar_data = self.extract_sonar_data(record)
            if sonar_data is None:
                continue
            
            # Analyze bottom characteristics
            # Look at the latter part of the sonar return (bottom)
            bottom_start = int(len(sonar_data) * 0.7)
            bottom_data = sonar_data[bottom_start:]
            
            if len(bottom_data) > 10:
                # Calculate bottom characteristics
                avg_intensity = np.mean(bottom_data)
                intensity_var = np.var(bottom_data)
                roughness = np.mean(np.abs(np.diff(bottom_data)))
                
                # Classify bottom type
                if avg_intensity > 0.7 and roughness > 0.1:
                    bottom_type = "rocky"
                elif avg_intensity > 0.5 and intensity_var > 0.05:
                    bottom_type = "mixed"
                elif avg_intensity < 0.3:
                    bottom_type = "soft_mud"
                else:
                    bottom_type = "sand"
                
                compositions.append({
                    'lat': record.get('lat'),
                    'lon': record.get('lon'),
                    'depth': record.get('depth_m'),
                    'bottom_type': bottom_type,
                    'intensity': avg_intensity,
                    'roughness': roughness,
                    'variance': intensity_var
                })
        
        return {
            'samples': compositions,
            'summary': self._summarize_bottom_types(compositions)
        }
    
    def _summarize_bottom_types(self, compositions: List[Dict]) -> Dict:
        """Summarize bottom type distribution"""
        if not compositions:
            return {}
        
        types = [c['bottom_type'] for c in compositions]
        from collections import Counter
        type_counts = Counter(types)
        
        total = len(types)
        summary = {
            'total_samples': total,
            'type_distribution': {k: v/total for k, v in type_counts.items()},
            'dominant_type': type_counts.most_common(1)[0][0] if type_counts else 'unknown'
        }
        
        return summary
    
    def run_full_analysis(self) -> Dict:
        """Run complete target detection and classification analysis"""
        print("Starting comprehensive target analysis...")
        
        if not self.load_data():
            return {'error': 'Failed to load data'}
        
        # Step 1: Detect targets in individual pings
        print("Step 1: Detecting targets in individual pings...")
        all_targets = []
        
        sonar_records = self.records_df[
            (self.records_df['sonar_ofs'].notna()) & 
            (self.records_df['sonar_size'] > 0)
        ].head(1000)  # Limit for testing
        
        for idx, record in sonar_records.iterrows():
            sonar_data = self.extract_sonar_data(record)
            if sonar_data is not None:
                ping_targets = self.detect_targets_in_ping(sonar_data, record)
                all_targets.extend(ping_targets)
        
        print(f"Found {len(all_targets)} potential targets across {len(sonar_records)} pings")
        
        # Step 2: Cluster targets spatially
        print("Step 2: Clustering targets spatially...")
        target_clusters = self.cluster_targets_spatial(all_targets)
        print(f"Grouped into {len(target_clusters)} spatial clusters")
        
        # Step 3: Classify each cluster
        print("Step 3: Classifying target clusters...")
        classified_targets = []
        for cluster in target_clusters:
            if len(cluster) >= 2:  # Require multiple detections for confidence
                classification = self.classify_target_cluster(cluster)
                classified_targets.append({
                    'targets': cluster,
                    'classification': classification
                })
        
        # Step 4: Detect anomalies
        print("Step 4: Detecting anomalies...")
        anomalies = self.detect_anomalies(all_targets)
        
        # Step 5: Analyze bottom composition
        print("Step 5: Analyzing bottom composition...")
        bottom_analysis = self.analyze_bottom_composition(sonar_records.sample(min(200, len(sonar_records))))
        
        # Compile results
        results = {
            'summary': {
                'total_pings_analyzed': len(sonar_records),
                'raw_targets_detected': len(all_targets),
                'spatial_clusters': len(target_clusters),
                'classified_targets': len(classified_targets),
                'anomalies_detected': len(anomalies),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'classified_targets': classified_targets,
            'anomalies': anomalies,
            'bottom_analysis': bottom_analysis,
            'target_signatures_used': list(self.target_signatures.keys())
        }
        
        return results

def save_analysis_results(results: Dict, output_path: str):
    """Save analysis results to JSON and SQLite database"""
    output_dir = Path(output_path)
    output_dir.mkdir(exist_ok=True)
    
    # Save to JSON
    json_path = output_dir / "target_analysis_results.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save to SQLite database
    db_path = output_dir / "target_analysis.db"
    conn = sqlite3.connect(db_path)
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS classified_targets (
            id INTEGER PRIMARY KEY,
            classification TEXT,
            confidence REAL,
            size_m REAL,
            lat REAL,
            lon REAL,
            depth_m REAL,
            target_count INTEGER,
            characteristics TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY,
            lat REAL,
            lon REAL,
            depth_m REAL,
            target_range REAL,
            echo_strength REAL,
            anomaly_score REAL,
            timestamp INTEGER
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bottom_composition (
            id INTEGER PRIMARY KEY,
            lat REAL,
            lon REAL,
            depth_m REAL,
            bottom_type TEXT,
            intensity REAL,
            roughness REAL
        )
    ''')
    
    # Insert classified targets
    for target_group in results.get('classified_targets', []):
        targets = target_group['targets']
        classification = target_group['classification']
        
        if targets:
            avg_lat = np.mean([t.get('lat', 0) for t in targets if t.get('lat')])
            avg_lon = np.mean([t.get('lon', 0) for t in targets if t.get('lon')])
            avg_depth = np.mean([t.get('depth', 0) for t in targets if t.get('depth')])
            
            conn.execute('''
                INSERT INTO classified_targets 
                (classification, confidence, size_m, lat, lon, depth_m, target_count, characteristics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                classification['classification'],
                classification['confidence'],
                classification['characteristics'].get('size', 0),
                avg_lat,
                avg_lon,
                avg_depth,
                len(targets),
                json.dumps(classification['characteristics'])
            ))
    
    # Insert anomalies
    for anomaly in results.get('anomalies', []):
        conn.execute('''
            INSERT INTO anomalies 
            (lat, lon, depth_m, target_range, echo_strength, anomaly_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            anomaly.get('lat', 0),
            anomaly.get('lon', 0),
            anomaly.get('depth', 0),
            anomaly.get('target_range', 0),
            anomaly.get('echo_strength', 0),
            anomaly.get('anomaly_score', 0),
            anomaly.get('timestamp', 0)
        ))
    
    # Insert bottom composition data
    for sample in results.get('bottom_analysis', {}).get('samples', []):
        conn.execute('''
            INSERT INTO bottom_composition 
            (lat, lon, depth_m, bottom_type, intensity, roughness)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            sample.get('lat', 0),
            sample.get('lon', 0),
            sample.get('depth', 0),
            sample['bottom_type'],
            sample['intensity'],
            sample['roughness']
        ))
    
    conn.commit()
    conn.close()
    
    print(f"Results saved to {json_path} and {db_path}")

if __name__ == "__main__":
    # Test with available data
    rsd_path = "126SV-UHD2-GT54.RSD"
    csv_path = "outputs/records.csv"
    
    if Path(rsd_path).exists() and Path(csv_path).exists():
        detector = TargetDetector(rsd_path, csv_path)
        results = detector.run_full_analysis()
        
        save_analysis_results(results, "target_analysis_output")
        
        print("\n=== ANALYSIS COMPLETE ===")
        print(f"Analyzed {results['summary']['total_pings_analyzed']} pings")
        print(f"Detected {results['summary']['raw_targets_detected']} potential targets")
        print(f"Found {results['summary']['classified_targets']} classified target groups")
        print(f"Identified {results['summary']['anomalies_detected']} anomalies")
        
        # Print top classifications
        print("\n=== TARGET CLASSIFICATIONS ===")
        for i, target_group in enumerate(results['classified_targets'][:5]):
            classification = target_group['classification']
            print(f"{i+1}. {classification['classification']} "
                  f"(confidence: {classification['confidence']:.2f}, "
                  f"size: {classification['characteristics']['size']:.1f}m)")
    else:
        print(f"Required files not found: {rsd_path}, {csv_path}")
        print("Please run the parser first to generate CSV data.")


class SARTargetClassifier:
    """
    Search and Rescue Target Classification System
    Specialized for emergency response and body/vehicle recovery
    """
    
    def __init__(self):
        self.human_signatures = {
            'body_floating': {'size_range': (0.4, 2.0), 'density': 'low', 'shadow': 'minimal'},
            'body_submerged': {'size_range': (0.3, 1.8), 'density': 'medium', 'shadow': 'variable'},
            'life_vest': {'size_range': (0.2, 0.6), 'density': 'very_low', 'shadow': 'none'},
            'clothing': {'size_range': (0.1, 1.0), 'density': 'low', 'shadow': 'minimal'}
        }
        
        self.vehicle_signatures = {
            'car_small': {'size_range': (3.0, 4.5), 'aspect_ratio': (1.5, 2.2), 'shadow': 'strong'},
            'car_large': {'size_range': (4.5, 6.0), 'aspect_ratio': (1.8, 2.5), 'shadow': 'strong'},
            'motorcycle': {'size_range': (1.5, 2.5), 'aspect_ratio': (0.8, 1.2), 'shadow': 'medium'},
            'boat_small': {'size_range': (3.0, 8.0), 'aspect_ratio': (2.0, 4.0), 'shadow': 'variable'},
            'boat_large': {'size_range': (8.0, 30.0), 'aspect_ratio': (3.0, 6.0), 'shadow': 'strong'}
        }
        
        self.debris_patterns = {
            'scattered': 'Multiple small objects in loose pattern',
            'concentrated': 'Dense cluster of objects',
            'linear': 'Objects in line formation (current drag)',
            'circular': 'Objects in circular pattern (vortex/sink point)'
        }
    
    def classify_sar_targets(self, targets: List[Dict]) -> List[Dict]:
        """Classify targets for SAR operations with priority scoring"""
        classified = []
        
        for target in targets:
            sar_classification = self._analyze_sar_target(target)
            target['sar_analysis'] = sar_classification
            classified.append(target)
        
        # Sort by SAR priority
        classified.sort(key=lambda x: x['sar_analysis']['priority_score'], reverse=True)
        return classified
    
    def _analyze_sar_target(self, target: Dict) -> Dict:
        """Analyze single target for SAR characteristics"""
        size = target.get('size', 0)
        aspect_ratio = target.get('aspect_ratio', 1.0)
        shadow_strength = target.get('shadow_strength', 0)
        depth = target.get('depth', 0)
        
        analysis = {
            'classification': 'unknown',
            'priority': 'low',
            'priority_score': 0,
            'confidence': 0.0,
            'sar_notes': []
        }
        
        # Human body detection
        human_score = self._score_human_target(size, aspect_ratio, shadow_strength, depth)
        
        # Vehicle detection
        vehicle_score = self._score_vehicle_target(size, aspect_ratio, shadow_strength)
        
        # Debris detection
        debris_score = self._score_debris_target(size, shadow_strength)
        
        # Determine classification
        max_score = max(human_score, vehicle_score, debris_score)
        
        if human_score == max_score and human_score > 0.3:
            analysis['classification'] = 'potential_human'
            analysis['priority'] = 'high' if human_score > 0.7 else 'medium'
            analysis['priority_score'] = human_score * 100
            analysis['sar_notes'].append('Possible human remains or survivor')
            
        elif vehicle_score == max_score and vehicle_score > 0.4:
            analysis['classification'] = 'vehicle'
            analysis['priority'] = 'high' if vehicle_score > 0.8 else 'medium'
            analysis['priority_score'] = vehicle_score * 80
            analysis['sar_notes'].append('Vehicle detected - check for occupants')
            
        elif debris_score > 0.2:
            analysis['classification'] = 'debris'
            analysis['priority'] = 'medium' if debris_score > 0.5 else 'low'
            analysis['priority_score'] = debris_score * 40
            analysis['sar_notes'].append('Debris field - potential accident site')
        
        analysis['confidence'] = max_score
        
        # Add emergency response notes
        if depth < 3.0:
            analysis['sar_notes'].append('Shallow water - diver accessible')
        elif depth < 10.0:
            analysis['sar_notes'].append('Medium depth - specialized equipment needed')
        else:
            analysis['sar_notes'].append('Deep water - ROV/advanced recovery required')
        
        return analysis
    
    def _score_human_target(self, size: float, aspect_ratio: float, shadow: float, depth: float) -> float:
        """Score likelihood of human target"""
        score = 0.0
        
        # Size scoring
        if 0.3 <= size <= 2.0:
            score += 0.4
        elif 0.2 <= size <= 2.5:
            score += 0.2
        
        # Aspect ratio (humans roughly 1:3 to 1:6 when lying down)
        if 2.0 <= aspect_ratio <= 6.0:
            score += 0.3
        elif 1.5 <= aspect_ratio <= 8.0:
            score += 0.1
        
        # Shadow (humans create minimal shadows when submerged)
        if shadow < 0.3:
            score += 0.2
        
        # Depth preference (bodies often found in specific depth ranges)
        if 1.0 <= depth <= 15.0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_vehicle_target(self, size: float, aspect_ratio: float, shadow: float) -> float:
        """Score likelihood of vehicle target"""
        score = 0.0
        
        # Size scoring
        if 1.5 <= size <= 30.0:
            score += 0.4
        
        # Aspect ratio (vehicles are typically longer than wide)
        if 1.5 <= aspect_ratio <= 6.0:
            score += 0.3
        
        # Shadow (vehicles create strong shadows)
        if shadow > 0.5:
            score += 0.3
        
        return min(score, 1.0)
    
    def _score_debris_target(self, size: float, shadow: float) -> float:
        """Score likelihood of debris"""
        score = 0.0
        
        # Debris can be any size
        if 0.1 <= size <= 50.0:
            score += 0.3
        
        # Variable shadow characteristics
        score += 0.2
        
        return min(score, 1.0)


class WreckHuntingAnalyzer:
    """
    Wreck Hunting and Archaeological Analysis System
    Specialized for shipwreck detection and historical artifact identification
    """
    
    def __init__(self):
        self.wreck_signatures = {
            'modern_vessel': {
                'size_range': (10.0, 300.0),
                'materials': ['steel', 'aluminum', 'fiberglass'],
                'shadow_characteristics': 'strong_linear',
                'debris_pattern': 'concentrated'
            },
            'historical_vessel': {
                'size_range': (5.0, 100.0),
                'materials': ['wood', 'iron'],
                'shadow_characteristics': 'variable',
                'debris_pattern': 'scattered'
            },
            'aircraft': {
                'size_range': (8.0, 80.0),
                'materials': ['aluminum', 'steel'],
                'shadow_characteristics': 'geometric',
                'debris_pattern': 'impact_crater'
            }
        }
        
        self.hull_patterns = [
            'linear_structure',    # Intact hull
            'curved_profile',      # Ship's hull curve
            'compartmented',       # Multiple sections
            'debris_field',        # Broken apart
            'buried_partially',    # Partially buried
            'metal_anomaly'        # Strong metallic signature
        ]
    
    def analyze_wreck_potential(self, targets: List[Dict]) -> List[Dict]:
        """Analyze targets for wreck hunting potential"""
        wreck_candidates = []
        
        for target in targets:
            wreck_analysis = self._analyze_wreck_characteristics(target)
            if wreck_analysis['wreck_probability'] > 0.1:  # Only include potential wrecks
                target['wreck_analysis'] = wreck_analysis
                wreck_candidates.append(target)
        
        # Sort by wreck probability
        wreck_candidates.sort(key=lambda x: x['wreck_analysis']['wreck_probability'], reverse=True)
        return wreck_candidates
    
    def _analyze_wreck_characteristics(self, target: Dict) -> Dict:
        """Analyze target for wreck characteristics"""
        size = target.get('size', 0)
        aspect_ratio = target.get('aspect_ratio', 1.0)
        shadow_strength = target.get('shadow_strength', 0)
        depth = target.get('depth', 0)
        
        analysis = {
            'wreck_type': 'unknown',
            'wreck_probability': 0.0,
            'historical_significance': 'unknown',
            'material_composition': 'unknown',
            'excavation_difficulty': 'unknown',
            'wreck_notes': []
        }
        
        # Size-based classification
        if size >= 50.0:
            analysis['wreck_type'] = 'large_vessel'
            analysis['wreck_probability'] += 0.4
            analysis['wreck_notes'].append('Large vessel signature detected')
            
        elif size >= 15.0:
            analysis['wreck_type'] = 'medium_vessel'
            analysis['wreck_probability'] += 0.3
            analysis['wreck_notes'].append('Medium vessel or aircraft possible')
            
        elif size >= 5.0:
            analysis['wreck_type'] = 'small_vessel'
            analysis['wreck_probability'] += 0.2
            analysis['wreck_notes'].append('Small vessel or debris field')
        
        # Aspect ratio analysis
        if 3.0 <= aspect_ratio <= 8.0:
            analysis['wreck_probability'] += 0.3
            analysis['wreck_notes'].append('Ship-like proportions detected')
        
        # Shadow analysis (indicates material density)
        if shadow_strength > 0.7:
            analysis['material_composition'] = 'metallic'
            analysis['wreck_probability'] += 0.2
            analysis['wreck_notes'].append('Strong metallic signature')
        elif shadow_strength > 0.4:
            analysis['material_composition'] = 'dense_organic'
            analysis['wreck_probability'] += 0.1
            analysis['wreck_notes'].append('Dense material, possibly wood/composite')
        
        # Depth-based historical significance
        if depth > 50.0:
            analysis['historical_significance'] = 'high'
            analysis['excavation_difficulty'] = 'extreme'
            analysis['wreck_notes'].append('Deep water wreck - high historical value')
        elif depth > 20.0:
            analysis['historical_significance'] = 'medium'
            analysis['excavation_difficulty'] = 'difficult'
            analysis['wreck_notes'].append('Medium depth - specialized recovery needed')
        else:
            analysis['historical_significance'] = 'variable'
            analysis['excavation_difficulty'] = 'moderate'
            analysis['wreck_notes'].append('Shallow water - accessible for study')
        
        # Cap probability at 1.0
        analysis['wreck_probability'] = min(analysis['wreck_probability'], 1.0)
        
        return analysis
    
    def generate_excavation_plan(self, wreck_data: Dict) -> Dict:
        """Generate excavation and recovery plan for identified wreck"""
        plan = {
            'survey_methods': [],
            'equipment_needed': [],
            'timeline_estimate': 'unknown',
            'legal_considerations': [],
            'scientific_value': 'unknown'
        }
        
        wreck_analysis = wreck_data.get('wreck_analysis', {})
        depth = wreck_data.get('depth', 0)
        size = wreck_data.get('size', 0)
        
        # Survey methods based on depth and size
        if depth < 10:
            plan['survey_methods'].extend(['diving_survey', 'underwater_photography', 'hand_mapping'])
        elif depth < 30:
            plan['survey_methods'].extend(['ROV_survey', 'sonar_mapping', 'photogrammetry'])
        else:
            plan['survey_methods'].extend(['deep_ROV', 'multibeam_sonar', 'sub_operations'])
        
        # Equipment recommendations
        if wreck_analysis.get('material_composition') == 'metallic':
            plan['equipment_needed'].extend(['metal_detector', 'magnetometer', 'corrosion_analysis'])
        
        if size > 20:
            plan['equipment_needed'].extend(['crane_barge', 'heavy_lift_equipment'])
            plan['timeline_estimate'] = 'months_to_years'
        else:
            plan['timeline_estimate'] = 'weeks_to_months'
        
        # Legal considerations
        plan['legal_considerations'].extend([
            'archaeological_permit_required',
            'environmental_impact_assessment',
            'historical_registry_check'
        ])
        
        return plan


# Example usage for CESARops integration
def demo_cesarops_integration():
    """Demonstrate CESARops integration capabilities"""
    print("🎓 CESARops Target Detection Demo")
    print("=" * 40)
    
    # Initialize systems
    detector = TargetDetector()
    sar_classifier = SARTargetClassifier()
    wreck_analyzer = WreckHuntingAnalyzer()
    
    # Simulate some targets for demonstration
    sample_targets = [
        {'size': 1.7, 'aspect_ratio': 4.0, 'shadow_strength': 0.2, 'depth': 5.5, 'lat': 41.123, 'lon': -71.456},
        {'size': 4.2, 'aspect_ratio': 2.1, 'shadow_strength': 0.8, 'depth': 12.0, 'lat': 41.124, 'lon': -71.457},
        {'size': 25.5, 'aspect_ratio': 5.2, 'shadow_strength': 0.9, 'depth': 35.0, 'lat': 41.125, 'lon': -71.458},
    ]
    
    print("SAR Analysis:")
    sar_results = sar_classifier.classify_sar_targets(sample_targets)
    for i, result in enumerate(sar_results):
        analysis = result['sar_analysis']
        print(f"  Target {i+1}: {analysis['classification']} ({analysis['priority']} priority)")
        for note in analysis['sar_notes']:
            print(f"    • {note}")
    
    print("\nWreck Hunting Analysis:")
    wreck_results = wreck_analyzer.analyze_wreck_potential(sample_targets)
    for i, result in enumerate(wreck_results):
        analysis = result['wreck_analysis']
        print(f"  Target {i+1}: {analysis['wreck_type']} (probability: {analysis['wreck_probability']:.2f})")
        for note in analysis['wreck_notes']:
            print(f"    • {note}")


if __name__ == "__main__":
    # Run demonstration
    demo_cesarops_integration()