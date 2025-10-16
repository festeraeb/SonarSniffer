#!/usr/bin/env python3
"""
Advanced Video Export System - Waterfall + Full Video with Color Patterns
Competing with SonarTRX video capabilities
"""

import numpy as np
import cv2
import os
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

@dataclass
class VideoExportSettings:
    """Video export configuration"""
    output_path: str
    width: int = 1920
    height: int = 1080
    fps: float = 2.0  # Realistic default for sonar survey playback
    codec: str = "mp4v"
    color_scheme: str = "traditional"
    waterfall_mode: bool = True
    full_video_mode: bool = False
    overlay_charts: bool = False
    include_telemetry: bool = True

    @staticmethod
    def calculate_realistic_fps(survey_speed_kts: float, ping_rate_hz: float = 20.0) -> float:
        """
        Calculate realistic video fps based on survey speed and ping rate.
        
        For realistic playback, the video should show survey progression at actual speed.
        If we want 1 meter of survey distance per second of video time, then:
        fps = ping_rate / (speed_mps / 1.0)
        
        Args:
            survey_speed_kts: Survey speed in knots
            ping_rate_hz: Sonar ping rate in Hz (default 20 Hz)
            
        Returns:
            Realistic fps for video playback
        """
        if survey_speed_kts <= 0:
            return 2.0  # Default fallback
            
        # Convert knots to m/s (1 knot = 0.514444 m/s)
        speed_mps = survey_speed_kts * 0.514444
        
        # Calculate fps for 1 meter per second video progression
        realistic_fps = ping_rate_hz / (speed_mps / 1.0)
        
        # Clamp to reasonable range (0.5 to 10 fps)
        return max(0.5, min(10.0, realistic_fps))

class ColorSchemeManager:
    """Manage different color schemes like SonarTRX"""
    
    @staticmethod
    def get_available_schemes() -> Dict[str, str]:
        return {
            "traditional": "Classic sonar colors (blue to red)",
            "grayscale": "Black and white traditional",
            "thermal": "Heat map style (black/red/yellow/white)",
            "rainbow": "Full spectrum rainbow",
            "ocean": "Blue-green ocean theme", 
            "high_contrast": "High contrast for deep water",
            "fishfinder": "Traditional fish finder colors",
            "scientific": "Scientific visualization palette"
        }
    
    @staticmethod
    def get_colormap(scheme: str) -> np.ndarray:
        """Get 256-entry colormap for given scheme"""
        
        if scheme == "traditional":
            # Classic sonar: dark blue -> cyan -> yellow -> red
            colors = [
                [0, 0, 0.2],      # Dark blue
                [0, 0, 0.8],      # Blue  
                [0, 0.8, 0.8],    # Cyan
                [0.8, 0.8, 0],    # Yellow
                [0.8, 0, 0],      # Red
                [1, 1, 1]         # White (strong returns)
            ]
        elif scheme == "grayscale":
            # Simple grayscale
            colors = [[0, 0, 0], [1, 1, 1]]
            
        elif scheme == "thermal":
            # Heat map style
            colors = [
                [0, 0, 0],        # Black
                [0.5, 0, 0],      # Dark red
                [1, 0, 0],        # Red
                [1, 0.5, 0],      # Orange
                [1, 1, 0],        # Yellow
                [1, 1, 1]         # White
            ]
        elif scheme == "rainbow":
            # Full spectrum
            colors = [
                [0.5, 0, 1],      # Purple
                [0, 0, 1],        # Blue
                [0, 1, 1],        # Cyan
                [0, 1, 0],        # Green
                [1, 1, 0],        # Yellow
                [1, 0.5, 0],      # Orange
                [1, 0, 0]         # Red
            ]
        elif scheme == "ocean":
            # Ocean theme
            colors = [
                [0, 0, 0.1],      # Deep blue
                [0, 0.2, 0.4],    # Ocean blue
                [0, 0.5, 0.7],    # Medium blue
                [0.2, 0.7, 0.5],  # Blue-green
                [0.5, 0.8, 0.3],  # Green
                [1, 1, 0.8]       # Light yellow
            ]
        elif scheme == "high_contrast":
            # High contrast for deep water
            colors = [
                [0, 0, 0],        # Black
                [0, 0, 0.3],      # Dark blue
                [1, 1, 0],        # Bright yellow
                [1, 0, 0],        # Bright red
                [1, 1, 1]         # White
            ]
        elif scheme == "fishfinder":
            # Traditional fish finder
            colors = [
                [0, 0, 0],        # Black (no return)
                [0, 0, 1],        # Blue (weak)
                [0, 1, 0],        # Green (medium)
                [1, 1, 0],        # Yellow (strong)
                [1, 0, 0]         # Red (very strong)
            ]
        elif scheme == "scientific":
            # Scientific visualization
            colors = [
                [0.1, 0.1, 0.4],  # Dark blue
                [0.2, 0.4, 0.8],  # Blue
                [0.4, 0.8, 0.4],  # Green
                [0.8, 0.8, 0.2],  # Yellow
                [0.8, 0.4, 0.2],  # Orange
                [0.6, 0.2, 0.2]   # Dark red
            ]
        else:
            # Default to traditional
            colors = [[0, 0, 0.2], [0, 0, 0.8], [0, 0.8, 0.8], [0.8, 0.8, 0], [0.8, 0, 0], [1, 1, 1]]
        
        # Interpolate to 256 entries
        colors = np.array(colors)
        indices = np.linspace(0, len(colors)-1, 256)
        
        colormap = np.zeros((256, 3))
        for i in range(256):
            idx = indices[i]
            idx_floor = int(np.floor(idx))
            idx_ceil = min(idx_floor + 1, len(colors)-1)
            alpha = idx - idx_floor
            
            colormap[i] = colors[idx_floor] * (1-alpha) + colors[idx_ceil] * alpha
        
        return (colormap * 255).astype(np.uint8)
    
    def get_color_scheme(self, scheme_name: str) -> Dict:
        """Get a specific color scheme configuration"""
        from matplotlib.colors import LinearSegmentedColormap
        
        # Get the color scheme
        if scheme_name == "traditional":
            colors = [[0, 0, 0.2], [0, 0, 0.8], [0, 0.8, 0.8], [0.8, 0.8, 0], [0.8, 0, 0], [1, 1, 1]]
        elif scheme_name == "thermal":
            colors = [[0, 0, 0], [0.5, 0, 0], [1, 0, 0], [1, 0.5, 0], [1, 1, 0], [1, 1, 1]]
        elif scheme_name == "rainbow":
            colors = [[0.5, 0, 1], [0, 0, 1], [0, 1, 1], [0, 1, 0], [1, 1, 0], [1, 0.5, 0], [1, 0, 0]]
        elif scheme_name == "ocean":
            colors = [[0, 0, 0.1], [0, 0.2, 0.4], [0, 0.5, 0.7], [0.2, 0.7, 0.5], [0.5, 0.8, 0.3], [1, 1, 0.8]]
        elif scheme_name == "high_contrast":
            colors = [[0, 0, 0], [0, 0, 0.3], [1, 1, 0], [1, 0, 0]]
        elif scheme_name == "fishfinder":
            colors = [[0, 0, 0.2], [1, 1, 0], [1, 0.5, 0], [1, 0, 0]]
        elif scheme_name == "scientific":
            colors = [[0.1, 0.1, 0.4], [0.2, 0.4, 0.8], [0.4, 0.8, 0.4], [0.8, 0.4, 0.2], [0.6, 0.2, 0.2]]
        elif scheme_name == "grayscale":
            colors = [[0, 0, 0], [1, 1, 1]]
        else:
            colors = [[0, 0, 0.2], [0, 0, 0.8], [0, 0.8, 0.8], [0.8, 0.8, 0], [0.8, 0, 0], [1, 1, 1]]
        
        return {
            'name': scheme_name.title() + ' Color Scheme',
            'colors': colors,
            'matplotlib_cmap': LinearSegmentedColormap.from_list(scheme_name, colors)
        }

class AdvancedVideoExporter:
    """Advanced video export with multiple modes and color schemes"""
    
    def __init__(self, settings: VideoExportSettings):
        self.settings = settings
        self.color_manager = ColorSchemeManager()
        self.writer = None
        self.colormap = self.color_manager.get_colormap(settings.color_scheme)
        
    def create_waterfall_frame(self, sonar_data: np.ndarray, 
                              telemetry: Dict = None) -> np.ndarray:
        """Create a waterfall-style frame"""
        height, width = self.settings.height, self.settings.width
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        if sonar_data is not None and len(sonar_data) > 0:
            # Normalize sonar data to 0-255
            normalized = ((sonar_data - sonar_data.min()) / 
                         (sonar_data.max() - sonar_data.min() + 1e-8) * 255).astype(np.uint8)
            
            # Apply colormap
            colored_data = self.colormap[normalized]
            
            # Resize to fit frame
            resized = cv2.resize(colored_data, (width, height//2))
            frame[:height//2] = resized
        
        # Add telemetry overlay if requested
        if self.settings.include_telemetry and telemetry:
            self._add_telemetry_overlay(frame, telemetry)
            
        return frame
    
    def create_full_video_frame(self, sonar_data: np.ndarray, 
                               bathymetry: np.ndarray = None,
                               telemetry: Dict = None) -> np.ndarray:
        """Create a full video frame with multiple views"""
        height, width = self.settings.height, self.settings.width
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Split frame into sections
        waterfall_height = height // 2
        map_height = height - waterfall_height
        
        # Top half: waterfall view
        if sonar_data is not None:
            waterfall_section = self.create_waterfall_frame(sonar_data)[:waterfall_height]
            frame[:waterfall_height] = waterfall_section
        
        # Bottom half: bathymetric map or other view
        if bathymetry is not None:
            map_section = self._create_map_section(bathymetry, map_height, width)
            frame[waterfall_height:] = map_section
        
        # Add telemetry overlay
        if self.settings.include_telemetry and telemetry:
            self._add_telemetry_overlay(frame, telemetry)
            
        return frame
    
    def _create_map_section(self, bathymetry: np.ndarray, 
                           height: int, width: int) -> np.ndarray:
        """Create bathymetric map section"""
        map_frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        if bathymetry.size > 0:
            # Normalize bathymetry data
            normalized = ((bathymetry - bathymetry.min()) / 
                         (bathymetry.max() - bathymetry.min() + 1e-8) * 255).astype(np.uint8)
            
            # Apply colormap
            colored_bathy = self.colormap[normalized]
            
            # Resize to fit
            resized = cv2.resize(colored_bathy, (width, height))
            map_frame = resized
            
        return map_frame
    
    def _add_telemetry_overlay(self, frame: np.ndarray, telemetry: Dict):
        """Add telemetry data overlay to frame"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        color = (255, 255, 255)  # White text
        thickness = 2
        
        # Position text in top-left corner
        y_offset = 30
        line_height = 25
        
        if 'depth_m' in telemetry:
            depth_text = f"Depth: {telemetry['depth_m']:.1f}m"
            cv2.putText(frame, depth_text, (10, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
            
        if 'speed_kts' in telemetry:
            speed_text = f"Speed: {telemetry['speed_kts']:.1f} kts"
            cv2.putText(frame, speed_text, (10, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
            
        if 'course_deg' in telemetry:
            course_text = f"Course: {telemetry['course_deg']:.0f}°"
            cv2.putText(frame, course_text, (10, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
            
        if 'water_temp_c' in telemetry:
            temp_text = f"Temp: {telemetry['water_temp_c']:.1f}°C"
            cv2.putText(frame, temp_text, (10, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
            
        # Add timestamp in bottom-right
        if 'timestamp' in telemetry:
            timestamp_text = telemetry['timestamp']
            text_size = cv2.getTextSize(timestamp_text, font, font_scale, thickness)[0]
            x_pos = frame.shape[1] - text_size[0] - 10
            y_pos = frame.shape[0] - 10
            cv2.putText(frame, timestamp_text, (x_pos, y_pos), font, font_scale, color, thickness)
    
    def export_video(self, sonar_records: List[Dict], 
                    progress_callback: Optional[Callable] = None) -> str:
        """Export complete video from sonar records"""
        
        if not sonar_records:
            raise ValueError("No sonar records to export")
        
        output_path = Path(self.settings.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*self.settings.codec)
        self.writer = cv2.VideoWriter(
            str(output_path), fourcc, float(self.settings.fps),
            (self.settings.width, self.settings.height)
        )
        
        if not self.writer.isOpened():
            raise RuntimeError(f"Could not open video writer for {output_path}")
        
        total_records = len(sonar_records)
        
        for i, record in enumerate(sonar_records):
            try:
                # Extract sonar data (placeholder - would need actual sonar samples)
                sonar_data = np.random.random((100, 512))  # Placeholder
                
                # Extract telemetry
                telemetry = {
                    'depth_m': record.get('depth_m', 0),
                    'speed_kts': record.get('speed_kts', 0), 
                    'course_deg': record.get('course_deg', 0),
                    'water_temp_c': record.get('water_temp_c', 0),
                    'timestamp': record.get('timestamp', '')
                }
                
                # Create frame based on mode
                if self.settings.waterfall_mode:
                    frame = self.create_waterfall_frame(sonar_data, telemetry)
                elif self.settings.full_video_mode:
                    # Create bathymetry data (placeholder)
                    bathymetry = np.random.random((50, 50))
                    frame = self.create_full_video_frame(sonar_data, bathymetry, telemetry)
                else:
                    frame = self.create_waterfall_frame(sonar_data, telemetry)
                
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self.writer.write(frame_bgr)
                
                # Progress callback
                if progress_callback:
                    progress = (i + 1) / total_records * 100
                    progress_callback(progress, f"Processed {i+1}/{total_records} frames")
                    
            except Exception as e:
                print(f"Error processing frame {i}: {e}")
                continue
        
        self.writer.release()
        
        return str(output_path)

def test_color_schemes():
    """Test all available color schemes"""
    manager = ColorSchemeManager()
    schemes = manager.get_available_schemes()
    
    print("Available color schemes:")
    for name, desc in schemes.items():
        print(f"  {name}: {desc}")
        
    # Create sample image with all schemes
    test_data = np.linspace(0, 255, 256).astype(np.uint8)
    test_data = np.tile(test_data, (50, 1))
    
    fig, axes = plt.subplots(len(schemes), 1, figsize=(12, 2*len(schemes)))
    
    for i, scheme_name in enumerate(schemes.keys()):
        colormap = manager.get_colormap(scheme_name)
        colored_data = colormap[test_data]
        
        axes[i].imshow(colored_data, aspect='auto')
        axes[i].set_title(f"{scheme_name}: {schemes[scheme_name]}")
        axes[i].set_xticks([])
        axes[i].set_yticks([])
    
    plt.tight_layout()
    plt.savefig("color_schemes_preview.png", dpi=150, bbox_inches='tight')
    print("Color scheme preview saved as 'color_schemes_preview.png'")

if __name__ == "__main__":
    # Test the color schemes
    test_color_schemes()
    
    # Example usage
    settings = VideoExportSettings(
        output_path="test_video.mp4",
        color_scheme="thermal",
        waterfall_mode=True,
        include_telemetry=True
    )
    
    exporter = AdvancedVideoExporter(settings)
    print(f"Video exporter initialized with {settings.color_scheme} color scheme")