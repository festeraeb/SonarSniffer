"""
Block-Level Target Detection System
Integrated with RSD Studio Block Processing Pipeline

Focuses on detecting targets within sonar blocks rather than individual pings
for more efficient and contextually-aware target recognition.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import cv2
from PIL import Image
import json
from datetime import datetime
import math

# Import our existing block processing
try:
    from block_pipeline import BlockProcessor, RSDRecord
    BLOCK_PROCESSING_AVAILABLE = True
except ImportError:
    BLOCK_PROCESSING_AVAILABLE = False
    print("Warning: Block processing not available")

# ML libraries for target classification
try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available, using basic algorithms")

try:
    import scipy.ndimage as ndimage
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

@dataclass
class TargetCandidate:
    """A potential target detected in a sonar block"""
    block_index: int
    center_x: int
    center_y: int
    width: int
    height: int
    confidence: float
    target_type: str
    acoustic_shadow: bool
    size_meters: Optional[float]
    depth_meters: Optional[float]
    lat: Optional[float]
    lon: Optional[float]
    features: Dict[str, float]
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h

@dataclass
class BlockAnalysis:
    """Analysis results for a sonar block"""
    block_index: int
    targets: List[TargetCandidate]
    anomalies: List[Dict]
    bottom_type: str
    average_depth: float
    texture_analysis: Dict[str, float]
    acoustic_shadows: List[Tuple[int, int, int, int]]  # shadow regions

class BlockTargetDetector:
    """Block-level target detection for SAR and wreck hunting"""
    
    def __init__(self):
        self.target_signatures = self._load_target_signatures()
        self.detection_params = {
            'min_target_size': 5,  # minimum pixels
            'max_target_size': 200,  # maximum pixels  
            'shadow_ratio_threshold': 0.3,  # acoustic shadow indicator
            'anomaly_threshold': 0.1,  # isolation forest threshold
            'texture_window': 15,  # texture analysis window
            'edge_threshold': 50,  # edge detection threshold
        }
        
    def _load_target_signatures(self) -> Dict[str, Dict]:
        """Load target signature database"""
        return {
            'wreck_large': {
                'size_range': (10, 100),  # meters
                'aspect_ratio': (0.3, 3.0),
                'shadow_expected': True,
                'edge_strength': 'high',
                'keywords': ['ship', 'vessel', 'wreck', 'hull']
            },
            'wreck_small': {
                'size_range': (2, 15),
                'aspect_ratio': (0.5, 2.5),
                'shadow_expected': True,
                'edge_strength': 'medium',
                'keywords': ['boat', 'small craft', 'debris']
            },
            'vehicle_car': {
                'size_range': (3, 6),
                'aspect_ratio': (0.4, 0.8),
                'shadow_expected': True,
                'edge_strength': 'medium',
                'keywords': ['car', 'vehicle', 'automobile']
            },
            'human_body': {
                'size_range': (0.3, 2.0),
                'aspect_ratio': (0.2, 0.6),
                'shadow_expected': False,
                'edge_strength': 'low',
                'keywords': ['body', 'person', 'victim']
            },
            'debris_field': {
                'size_range': (1, 20),
                'aspect_ratio': (0.1, 5.0),
                'shadow_expected': False,
                'edge_strength': 'variable',
                'keywords': ['debris', 'scattered', 'field']
            }
        }
    
    def analyze_block(self, block_image: np.ndarray, block_metadata: Dict) -> BlockAnalysis:
        """
        Analyze a sonar block for targets and anomalies
        
        Args:
            block_image: Grayscale sonar block image (H x W)
            block_metadata: Block metadata including GPS, depth, etc.
            
        Returns:
            BlockAnalysis with detected targets and analysis
        """
        if len(block_image.shape) == 3:
            block_image = cv2.cvtColor(block_image, cv2.COLOR_RGB2GRAY)
        
        # Initialize analysis
        analysis = BlockAnalysis(
            block_index=block_metadata.get('block_index', 0),
            targets=[],
            anomalies=[],
            bottom_type='unknown',
            average_depth=block_metadata.get('avg_depth', 0),
            texture_analysis={},
            acoustic_shadows=[]
        )
        
        # 1. Detect acoustic shadows (often indicate targets)
        shadows = self._detect_acoustic_shadows(block_image)
        analysis.acoustic_shadows = shadows
        
        # 2. Edge detection for target outlines
        edges = self._detect_edges(block_image)
        
        # 3. Find potential target regions
        target_regions = self._find_target_regions(block_image, edges, shadows)
        
        # 4. Classify each target region
        for region in target_regions:
            target = self._classify_target_region(block_image, region, block_metadata)
            if target.confidence > 0.3:  # confidence threshold
                analysis.targets.append(target)
        
        # 5. Texture analysis for bottom type
        analysis.texture_analysis = self._analyze_texture(block_image)
        analysis.bottom_type = self._classify_bottom_type(analysis.texture_analysis)
        
        # 6. Anomaly detection
        if SKLEARN_AVAILABLE:
            anomalies = self._detect_block_anomalies(block_image)
            analysis.anomalies = anomalies
        
        return analysis
    
    def _detect_acoustic_shadows(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect acoustic shadow regions that indicate targets"""
        shadows = []
        
        # Find dark regions that could be shadows
        dark_threshold = np.percentile(image, 15)  # Bottom 15% of intensities
        dark_mask = image < dark_threshold
        
        # Find connected components
        if SCIPY_AVAILABLE:
            labeled, num_features = ndimage.label(dark_mask)
            
            for i in range(1, num_features + 1):
                component = (labeled == i)
                y_coords, x_coords = np.where(component)
                
                if len(y_coords) < 10:  # Too small
                    continue
                    
                x_min, x_max = x_coords.min(), x_coords.max()
                y_min, y_max = y_coords.min(), y_coords.max()
                
                width = x_max - x_min
                height = y_max - y_min
                
                # Shadow characteristics: elongated, dark
                if width > height * 1.5 and width > 10:
                    shadows.append((x_min, y_min, width, height))
        
        return shadows
    
    def _detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Detect edges that might indicate target boundaries"""
        # Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(image, (3, 3), 0)
        
        # Canny edge detection
        edges = cv2.Canny(blurred, 
                         self.detection_params['edge_threshold'], 
                         self.detection_params['edge_threshold'] * 2)
        
        return edges
    
    def _find_target_regions(self, image: np.ndarray, edges: np.ndarray, 
                           shadows: List[Tuple[int, int, int, int]]) -> List[Dict]:
        """Find regions that could contain targets"""
        regions = []
        
        # Find contours in edge image
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            
            # Filter by size
            if (area < self.detection_params['min_target_size'] or 
                area > self.detection_params['max_target_size']):
                continue
            
            # Calculate features
            aspect_ratio = w / h if h > 0 else 0
            extent = area / (w * h) if w > 0 and h > 0 else 0
            
            # Check for nearby acoustic shadow
            has_shadow = any(self._regions_overlap((x, y, w, h), shadow) for shadow in shadows)
            
            regions.append({
                'bbox': (x, y, w, h),
                'area': area,
                'aspect_ratio': aspect_ratio,
                'extent': extent,
                'has_shadow': has_shadow,
                'contour': contour
            })
        
        return regions
    
    def _classify_target_region(self, image: np.ndarray, region: Dict, 
                              metadata: Dict) -> TargetCandidate:
        """Classify a target region based on its characteristics"""
        x, y, w, h = region['bbox']
        
        # Extract region for analysis
        roi = image[y:y+h, x:x+w]
        
        # Calculate features
        features = {
            'area': region['area'],
            'aspect_ratio': region['aspect_ratio'],
            'extent': region['extent'],
            'has_shadow': region['has_shadow'],
            'mean_intensity': np.mean(roi),
            'std_intensity': np.std(roi),
            'contrast': np.max(roi) - np.min(roi),
        }
        
        # Calculate size in meters (approximate from pixel size and depth)
        depth = metadata.get('avg_depth', 10)
        pixel_size_m = self._estimate_pixel_size(depth)
        size_meters = math.sqrt(region['area']) * pixel_size_m
        
        # Match against target signatures
        best_match = 'unknown'
        best_confidence = 0.0
        
        for target_type, signature in self.target_signatures.items():
            confidence = self._calculate_match_confidence(features, signature, size_meters)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = target_type
        
        return TargetCandidate(
            block_index=metadata.get('block_index', 0),
            center_x=x + w // 2,
            center_y=y + h // 2,
            width=w,
            height=h,
            confidence=best_confidence,
            target_type=best_match,
            acoustic_shadow=region['has_shadow'],
            size_meters=size_meters,
            depth_meters=depth,
            lat=metadata.get('lat'),
            lon=metadata.get('lon'),
            features=features,
            bounding_box=(x, y, w, h)
        )
    
    def _calculate_match_confidence(self, features: Dict, signature: Dict, size_meters: float) -> float:
        """Calculate confidence that features match a target signature"""
        confidence = 0.0
        
        # Size match
        size_min, size_max = signature['size_range']
        if size_min <= size_meters <= size_max:
            confidence += 0.3
        elif size_meters < size_min * 2 or size_meters > size_max * 0.5:
            confidence += 0.1  # Partial credit for near matches
        
        # Aspect ratio match
        aspect_min, aspect_max = signature['aspect_ratio']
        if aspect_min <= features['aspect_ratio'] <= aspect_max:
            confidence += 0.2
        
        # Shadow expectation
        if signature['shadow_expected'] == features['has_shadow']:
            confidence += 0.2
        
        # Contrast/edge strength
        if signature['edge_strength'] == 'high' and features['contrast'] > 100:
            confidence += 0.15
        elif signature['edge_strength'] == 'medium' and 50 < features['contrast'] <= 100:
            confidence += 0.15
        elif signature['edge_strength'] == 'low' and features['contrast'] <= 50:
            confidence += 0.15
        
        # Shape regularity (extent)
        if features['extent'] > 0.5:  # More regular shapes
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def _estimate_pixel_size(self, depth_meters: float) -> float:
        """Estimate pixel size in meters based on depth and sonar characteristics"""
        # This is a rough approximation - would need calibration for specific sonar
        # Assuming typical sidescan sonar beam characteristics
        beam_angle_rad = math.radians(1.0)  # ~1 degree beam width
        pixel_size = depth_meters * beam_angle_rad
        return max(pixel_size, 0.1)  # Minimum 10cm per pixel
    
    def _regions_overlap(self, rect1: Tuple[int, int, int, int], 
                        rect2: Tuple[int, int, int, int]) -> bool:
        """Check if two rectangular regions overlap"""
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        
        return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)
    
    def _analyze_texture(self, image: np.ndarray) -> Dict[str, float]:
        """Analyze texture characteristics of the sonar image"""
        texture_metrics = {}
        
        # Calculate texture using GLCM-like measures
        # Standard deviation (roughness)
        texture_metrics['roughness'] = np.std(image)
        
        # Local variance (texture variation)
        kernel_size = self.detection_params['texture_window']
        if kernel_size < image.shape[0] and kernel_size < image.shape[1]:
            kernel = np.ones((kernel_size, kernel_size)) / (kernel_size ** 2)
            local_mean = cv2.filter2D(image.astype(np.float32), -1, kernel)
            local_variance = cv2.filter2D((image.astype(np.float32) - local_mean) ** 2, -1, kernel)
            texture_metrics['local_variance'] = np.mean(local_variance)
        else:
            texture_metrics['local_variance'] = 0.0
        
        # Edge density
        edges = cv2.Canny(image, 50, 150)
        texture_metrics['edge_density'] = np.sum(edges > 0) / edges.size
        
        # Intensity distribution
        texture_metrics['intensity_range'] = np.max(image) - np.min(image)
        texture_metrics['intensity_mean'] = np.mean(image)
        
        return texture_metrics
    
    def _classify_bottom_type(self, texture_analysis: Dict[str, float]) -> str:
        """Classify bottom type based on texture analysis"""
        roughness = texture_analysis.get('roughness', 0)
        edge_density = texture_analysis.get('edge_density', 0)
        
        if roughness < 20 and edge_density < 0.1:
            return 'mud/silt'
        elif roughness < 40 and edge_density < 0.2:
            return 'sand'
        elif roughness > 60 or edge_density > 0.3:
            return 'rock/debris'
        else:
            return 'mixed_sediment'
    
    def _detect_block_anomalies(self, image: np.ndarray) -> List[Dict]:
        """Detect anomalous regions using isolation forest"""
        if not SKLEARN_AVAILABLE:
            return []
        
        # Extract features from image patches
        patch_size = 16
        features = []
        positions = []
        
        for y in range(0, image.shape[0] - patch_size, patch_size // 2):
            for x in range(0, image.shape[1] - patch_size, patch_size // 2):
                patch = image[y:y+patch_size, x:x+patch_size]
                
                # Calculate patch features
                patch_features = [
                    np.mean(patch),
                    np.std(patch),
                    np.max(patch) - np.min(patch),
                    np.sum(cv2.Canny(patch, 50, 150) > 0)
                ]
                
                features.append(patch_features)
                positions.append((x, y))
        
        if len(features) < 10:
            return []
        
        # Detect anomalies
        features_array = np.array(features)
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features_array)
        
        isolation_forest = IsolationForest(contamination=self.detection_params['anomaly_threshold'])
        anomaly_labels = isolation_forest.fit_predict(features_scaled)
        
        # Extract anomalous regions
        anomalies = []
        for i, (pos, label) in enumerate(zip(positions, anomaly_labels)):
            if label == -1:  # Anomaly
                x, y = pos
                anomalies.append({
                    'position': (x, y),
                    'size': (patch_size, patch_size),
                    'anomaly_score': isolation_forest.score_samples([features_scaled[i]])[0]
                })
        
        return anomalies

class BlockTargetAnalysisEngine:
    """High-level engine for analyzing multiple blocks and tracking targets"""
    
    def __init__(self, block_processor: Optional[BlockProcessor] = None):
        self.detector = BlockTargetDetector()
        self.block_processor = block_processor
        self.target_database = []
        self.analysis_history = []
        
    def analyze_blocks_from_processor(self, left_channel: int, right_channel: int, 
                                    max_blocks: int = 100) -> List[BlockAnalysis]:
        """Analyze blocks from the block processor"""
        if not self.block_processor:
            raise ValueError("No block processor available")
        
        analyses = []
        block_count = 0
        
        # Process blocks from the block processor
        for result in self.block_processor.process_channel_pair(left_channel, right_channel):
            if block_count >= max_blocks:
                break
                
            # Convert block image to numpy array
            if result.get('image') is not None:
                if isinstance(result['image'], Image.Image):
                    block_image = np.array(result['image'])
                else:
                    block_image = result['image']
                
                # Create metadata
                metadata = {
                    'block_index': result.get('block_index', block_count),
                    'avg_depth': 10.0,  # Default depth - would get from records
                    'lat': None,
                    'lon': None
                }
                
                # Analyze this block
                analysis = self.detector.analyze_block(block_image, metadata)
                analyses.append(analysis)
                
                # Log significant findings
                if analysis.targets:
                    print(f"Block {analysis.block_index}: Found {len(analysis.targets)} targets")
                    for target in analysis.targets:
                        if target.confidence > 0.5:
                            print(f"  - {target.target_type}: {target.confidence:.2f} confidence")
                
            block_count += 1
        
        self.analysis_history.extend(analyses)
        return analyses
    
    def generate_sar_report(self, analyses: List[BlockAnalysis]) -> Dict:
        """Generate a SAR (Search and Rescue) report"""
        high_priority_targets = []
        potential_victims = []
        search_areas = []
        
        for analysis in analyses:
            for target in analysis.targets:
                if target.target_type == 'human_body' and target.confidence > 0.4:
                    potential_victims.append({
                        'block': analysis.block_index,
                        'position': (target.center_x, target.center_y),
                        'confidence': target.confidence,
                        'gps': (target.lat, target.lon) if target.lat else None
                    })
                elif target.confidence > 0.6:
                    high_priority_targets.append(target)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_blocks_analyzed': len(analyses),
            'potential_victims': potential_victims,
            'high_priority_targets': len(high_priority_targets),
            'search_recommendations': self._generate_search_recommendations(analyses)
        }
    
    def generate_wreck_report(self, analyses: List[BlockAnalysis]) -> Dict:
        """Generate a wreck hunting report"""
        wrecks = []
        debris_fields = []
        
        for analysis in analyses:
            for target in analysis.targets:
                if 'wreck' in target.target_type and target.confidence > 0.5:
                    wrecks.append({
                        'block': analysis.block_index,
                        'type': target.target_type,
                        'size_meters': target.size_meters,
                        'confidence': target.confidence,
                        'has_shadow': target.acoustic_shadow,
                        'gps': (target.lat, target.lon) if target.lat else None
                    })
                elif target.target_type == 'debris_field':
                    debris_fields.append(target)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_blocks_analyzed': len(analyses),
            'potential_wrecks': wrecks,
            'debris_fields': len(debris_fields),
            'wreck_hunting_recommendations': self._generate_wreck_recommendations(wrecks)
        }
    
    def _generate_search_recommendations(self, analyses: List[BlockAnalysis]) -> List[str]:
        """Generate search recommendations based on analysis"""
        recommendations = []
        
        # Count targets by type
        target_counts = {}
        for analysis in analyses:
            for target in analysis.targets:
                target_counts[target.target_type] = target_counts.get(target.target_type, 0) + 1
        
        if target_counts.get('human_body', 0) > 0:
            recommendations.append("Deploy ROV/divers to investigate potential victim locations")
        
        if target_counts.get('vehicle_car', 0) > 0:
            recommendations.append("Investigate vehicle signatures - may indicate accident scene")
        
        if target_counts.get('debris_field', 0) > 0:
            recommendations.append("Search debris fields systematically - may contain evidence")
        
        return recommendations
    
    def _generate_wreck_recommendations(self, wrecks: List[Dict]) -> List[str]:
        """Generate wreck hunting recommendations"""
        recommendations = []
        
        large_wrecks = [w for w in wrecks if w.get('size_meters', 0) > 20]
        small_wrecks = [w for w in wrecks if w.get('size_meters', 0) < 10]
        
        if large_wrecks:
            recommendations.append(f"Found {len(large_wrecks)} large wreck candidates - high priority for investigation")
        
        if small_wrecks:
            recommendations.append(f"Found {len(small_wrecks)} small craft signatures - potential fishing boats or debris")
        
        high_confidence = [w for w in wrecks if w['confidence'] > 0.7]
        if high_confidence:
            recommendations.append(f"{len(high_confidence)} high-confidence targets warrant immediate investigation")
        
        return recommendations

# Integration function for the GUI
def integrate_target_detection_with_gui():
    """Function to integrate target detection with the existing GUI"""
    integration_code = '''
    # Add this to studio_gui_engines_v3_14.py in the block processing section
    
    # Import target detection
    try:
        from block_target_detection import BlockTargetAnalysisEngine, BlockTargetDetector
        TARGET_DETECTION_AVAILABLE = True
    except ImportError:
        TARGET_DETECTION_AVAILABLE = False
    
    # Add target detection button to block processing frame
    if TARGET_DETECTION_AVAILABLE:
        ttk.Button(ch_frame, text="Analyze Targets", command=self._analyze_targets).pack(pady=2)
    
    # Add target analysis method
    def _analyze_targets(self):
        """Analyze blocks for targets and generate reports"""
        if not TARGET_DETECTION_AVAILABLE or not self.block_processor:
            messagebox.showwarning("Not Available", "Target detection not available")
            return
            
        # Create analysis engine
        engine = BlockTargetAnalysisEngine(self.block_processor)
        
        # Analyze blocks
        left_ch = self.left_channel.get()
        right_ch = self.right_channel.get()
        
        def analysis_job(on_progress, check_cancel):
            try:
                on_progress(10, "Analyzing blocks for targets...")
                analyses = engine.analyze_blocks_from_processor(left_ch, right_ch, max_blocks=50)
                
                on_progress(70, "Generating SAR report...")
                sar_report = engine.generate_sar_report(analyses)
                
                on_progress(85, "Generating wreck hunting report...")
                wreck_report = engine.generate_wreck_report(analyses)
                
                # Save reports
                output_dir = Path(self.last_output_csv_path).parent
                
                with open(output_dir / "sar_report.json", "w") as f:
                    json.dump(sar_report, f, indent=2)
                    
                with open(output_dir / "wreck_report.json", "w") as f:
                    json.dump(wreck_report, f, indent=2)
                
                on_progress(100, f"Target analysis complete - {len(analyses)} blocks analyzed")
                
                # Log results
                self._q.put(("log", f"=== TARGET ANALYSIS RESULTS ==="))
                self._q.put(("log", f"Blocks analyzed: {len(analyses)}"))
                self._q.put(("log", f"Potential victims: {len(sar_report['potential_victims'])}"))
                self._q.put(("log", f"Potential wrecks: {len(wreck_report['potential_wrecks'])}"))
                self._q.put(("log", f"Reports saved to: {output_dir}"))
                
            except Exception as e:
                on_progress(None, f"Error: {str(e)}")
                
        self._create_progress_bar("target_analysis", "Analyzing targets...")
        self.process_mgr.start_process("target_analysis", analysis_job)
    '''
    
    return integration_code

if __name__ == "__main__":
    # Test the block target detector
    print("Block-Level Target Detection System")
    print("For SAR and Wreck Hunting Applications")
    print("=" * 50)
    
    detector = BlockTargetDetector()
    print(f"Target signatures loaded: {list(detector.target_signatures.keys())}")
    print(f"Detection parameters: {detector.detection_params}")
    
    # Create a synthetic test block
    test_block = np.random.randint(0, 255, (100, 200), dtype=np.uint8)
    # Add a synthetic target (bright rectangle with shadow)
    test_block[40:50, 80:100] = 200  # Bright target
    test_block[40:50, 100:120] = 50  # Dark shadow
    
    metadata = {
        'block_index': 1,
        'avg_depth': 15.0,
        'lat': 45.5,
        'lon': -75.3
    }
    
    print(f"Analyzing test block...")
    analysis = detector.analyze_block(test_block, metadata)
    
    print(f"Results:")
    print(f"  Targets found: {len(analysis.targets)}")
    print(f"  Acoustic shadows: {len(analysis.acoustic_shadows)}")
    print(f"  Bottom type: {analysis.bottom_type}")
    print(f"  Anomalies: {len(analysis.anomalies)}")
    
    for i, target in enumerate(analysis.targets):
        print(f"  Target {i+1}: {target.target_type} (confidence: {target.confidence:.2f})")