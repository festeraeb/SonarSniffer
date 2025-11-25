#!/usr/bin/env python3
"""
Post-Processing Dialog for SonarSniffer GUI
Provides user-friendly interface for geospatial exports (KML, MBTiles, DEM, etc.)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import logging
from typing import Dict, Callable, List, Optional
from dataclasses import dataclass
import numpy as np

from geospatial_exporter import (
    GeospatialExporter,
    SonarPoint,
    DetectedTarget,
    BathymetricProcessor,
    KMLGenerator,
    MBTilesGenerator,
)


# ============================================================================
# UNIT CONVERSION FUNCTIONS
# ============================================================================

class UnitConverter:
    """Convert between different measurement units"""
    
    @staticmethod
    def convert_depth(value: float, from_unit: str = "meters", to_unit: str = "feet") -> float:
        """Convert depth value between units"""
        if value is None or value == 0:
            return 0
        
        # Convert to meters first as base unit
        if from_unit == "meters":
            meters = value
        elif from_unit == "feet":
            meters = value / 3.28084
        elif from_unit == "fathoms":
            meters = value * 1.8288
        else:
            return value
        
        # Convert to target unit
        if to_unit == "meters":
            return meters
        elif to_unit == "feet":
            return meters * 3.28084
        elif to_unit == "fathoms":
            return meters / 1.8288
        else:
            return value
    
    @staticmethod
    def convert_speed(value: float, from_unit: str = "kmh", to_unit: str = "knots") -> float:
        """Convert speed value between units"""
        if value is None or value == 0:
            return 0
        
        # Convert to km/h first as base unit
        if from_unit == "kmh":
            kmh = value
        elif from_unit == "knots":
            kmh = value * 1.852
        elif from_unit == "mph":
            kmh = value * 1.60934
        else:
            return value
        
        # Convert to target unit
        if to_unit == "kmh":
            return kmh
        elif to_unit == "knots":
            return kmh / 1.852
        elif to_unit == "mph":
            return kmh / 1.60934
        else:
            return value


# ============================================================================
# TARGET DETECTION & EXTRACTION
# ============================================================================

def extract_targets_from_records(records: List[Dict], 
                                  confidence_threshold: float = 0.5,
                                  depth_unit: str = "feet") -> List[DetectedTarget]:
    """
    Extract and classify detected targets from sonar records.
    
    Analyzes depth, intensity, and spatial patterns to identify:
    - Rocks: High-intensity shallow anomalies
    - Wrecks: Large structures with distinctive patterns
    - Debris: Scattered small anomalies
    - Anomalies: Other noteworthy features
    
    Args:
        records: List of sonar record dictionaries
        confidence_threshold: Minimum confidence score (0.0-1.0)
        depth_unit: Unit to convert depth to (feet, meters, fathoms)
        
    Returns:
        List of DetectedTarget objects
    """
    if not records:
        return []
    
    targets = []
    
    # Convert records to numpy array for analysis
    # Handle both dict and object attributes
    def get_attr(obj, *names, default=0):
        """Get attribute from object or dict, trying multiple names."""
        for name in names:
            if isinstance(obj, dict):
                val = obj.get(name)
            else:
                val = getattr(obj, name, None)
            if val is not None:
                return val
        return default
    
    depths = np.array([get_attr(rec, 'depth', 'depth_m', default=0) for rec in records])
    intensities = np.array([get_attr(rec, 'intensity', default=0) for rec in records])
    lats = np.array([get_attr(rec, 'latitude', 'lat', default=0) for rec in records])
    lons = np.array([get_attr(rec, 'longitude', 'lon', default=0) for rec in records])
    timestamps = np.array([get_attr(rec, 'timestamp', 'offset', default=i) for i, rec in enumerate(records)])
    
    if len(depths) == 0:
        return []
    
    # Normalize intensity to 0-1 range
    intensity_min, intensity_max = intensities.min(), intensities.max()
    if intensity_max > intensity_min:
        normalized_intensity = (intensities - intensity_min) / (intensity_max - intensity_min)
    else:
        normalized_intensity = np.zeros_like(intensities)
    
    # Detect anomalies using statistical methods
    mean_depth = depths.mean()
    std_depth = depths.std()
    mean_intensity = normalized_intensity.mean()
    std_intensity = normalized_intensity.std()
    
    # Find significant deviations from the mean
    depth_anomalies = np.abs(depths - mean_depth) > (2 * std_depth)
    intensity_anomalies = np.abs(normalized_intensity - mean_intensity) > (2 * std_intensity)
    
    # Classify targets based on characteristics
    for i in range(len(records)):
        rec = records[i]
        
        # Calculate confidence based on anomaly strength
        depth_score = abs(depths[i] - mean_depth) / (std_depth + 0.1)
        intensity_score = abs(normalized_intensity[i] - mean_intensity) / (std_intensity + 0.1)
        
        # Combined anomaly score
        anomaly_score = min(1.0, (depth_score + intensity_score) / 2.0)
        
        if anomaly_score < confidence_threshold:
            continue
        
        # Classify target type
        if depths[i] < mean_depth - std_depth and normalized_intensity[i] > 0.7:
            # Shallow with high intensity = likely rock
            target_type = 'rock'
            confidence = min(1.0, intensity_score * 0.9)
        elif std_depth > 0 and abs(depths[i] - mean_depth) > (3 * std_depth):
            # Very large depth deviation = possible wreck structure
            target_type = 'wreck'
            confidence = min(1.0, depth_score * 0.8)
        elif normalized_intensity[i] > 0.8 and depth_anomalies[i]:
            # Both intensity and depth anomaly = debris field
            target_type = 'debris'
            confidence = min(1.0, (intensity_score + depth_score) / 2.0 * 0.75)
        else:
            # Generic anomaly
            target_type = 'anomaly'
            confidence = anomaly_score * 0.6
        
        # Skip if confidence too low
        if confidence < confidence_threshold:
            continue
        
        # Estimate target size (based on intensity spread)
        size_estimate = max(0.5, min(100.0, normalized_intensity[i] * 50.0))
        
        # Convert depth to user's selected unit
        converted_depth = UnitConverter.convert_depth(
            float(depths[i]),
            from_unit="meters",
            to_unit=depth_unit
        )
        
        # Create target object
        target = DetectedTarget(
            latitude=float(lats[i]),
            longitude=float(lons[i]),
            depth=converted_depth,
            target_type=target_type,
            confidence=float(confidence),
            size_estimate=float(size_estimate),
        )
        
        targets.append(target)
    
    # Remove duplicate/clustered targets (keep strongest in each cluster)
    if targets:
        targets = _cluster_nearby_targets(targets, cluster_radius_m=50.0)
    
    return targets


def _cluster_nearby_targets(targets: List[DetectedTarget], 
                           cluster_radius_m: float = 50.0) -> List[DetectedTarget]:
    """
    Remove duplicate targets by clustering nearby detections.
    
    Within each cluster, keeps the target with highest confidence.
    
    Args:
        targets: List of detected targets
        cluster_radius_m: Clustering radius in meters (approximate)
        
    Returns:
        Deduplicated target list
    """
    if not targets:
        return []
    
    # Convert radius from meters to degrees (rough approximation at 40°N)
    # 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 85 km at 40°N
    cluster_radius_deg = cluster_radius_m / 111000.0
    
    clustered = []
    used = set()
    
    # Sort by confidence (highest first)
    sorted_targets = sorted(targets, key=lambda t: t.confidence, reverse=True)
    
    for i, target in enumerate(sorted_targets):
        if i in used:
            continue
        
        # Start new cluster with this target
        clustered.append(target)
        used.add(i)
        
        # Mark nearby targets as used (duplicates)
        for j in range(i + 1, len(sorted_targets)):
            if j in used:
                continue
            
            other = sorted_targets[j]
            lat_diff = abs(target.latitude - other.latitude)
            lon_diff = abs(target.longitude - other.longitude)
            
            if lat_diff < cluster_radius_deg and lon_diff < cluster_radius_deg:
                used.add(j)
    
    return clustered


@dataclass
class PostProcessingOptions:
    """Configuration for post-processing exports"""
    generate_kml: bool = True
    generate_mbtiles: bool = True
    generate_dem: bool = True
    contour_interval: float = 5.0
    include_targets: bool = False
    basename: str = "sonar_survey"
    output_dir: Path = None
    depth_unit: str = "feet"  # feet, meters, fathoms
    speed_unit: str = "knots"  # knots (nautical mph), mph (statute), kmh


class PostProcessingDialog:
    """Dialog window for post-processing options"""
    
    def __init__(self, parent, records: List[Dict], on_complete: Callable = None, output_dir: str = None):
        """
        Initialize post-processing dialog
        
        Args:
            parent: Parent Tkinter widget
            records: List of sonar records from processing
            on_complete: Callback function when export completes
            output_dir: Directory for processing output (passed from preprocessing)
        """
        self.parent = parent
        self.records = records
        self.on_complete = on_complete
        self.exporting = False
        self.processing_output_dir = output_dir  # Store the preprocessing output directory
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Post-Processing Options")
        self.dialog.geometry("600x700")
        self.dialog.resizable(True, True)
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(1, weight=1)
        
        # Build UI
        self._build_ui()
        
    def _build_ui(self):
        """Build the dialog UI"""
        
        # Header
        header_frame = ttk.Frame(self.dialog)
        header_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        header_frame.columnconfigure(0, weight=1)
        
        title = ttk.Label(header_frame, text="🗺️ Advanced Geospatial Post-Processing", 
                         font=('Helvetica', 12, 'bold'))
        title.grid(row=0, column=0, sticky='w')
        
        desc = ttk.Label(header_frame, 
                        text=f"Advanced exports: bathymetric KML, web maps, 3D elevation models\n"
                              f"Processing {len(self.records)} sonar records with depth analysis",
                        font=('Helvetica', 9), foreground='#666')
        desc.grid(row=1, column=0, sticky='w', pady=(5, 0))
        
        # Main content with scrollbar
        content_frame = ttk.Frame(self.dialog)
        content_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        canvas = tk.Canvas(content_frame, highlightthickness=0, bg='white')
        scrollbar = ttk.Scrollbar(content_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # ====== EXPORT FORMAT OPTIONS ======
        
        format_frame = ttk.LabelFrame(scrollable_frame, text="Export Formats", padding="10")
        format_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        format_frame.columnconfigure(0, weight=1)
        
        self.var_kml = tk.BooleanVar(value=True)
        self.var_mbtiles = tk.BooleanVar(value=True)
        self.var_dem = tk.BooleanVar(value=True)
        
        kml_check = ttk.Checkbutton(format_frame, text="📍 KML Bathymetry (Depth Contours)", 
                                    variable=self.var_kml)
        kml_check.grid(row=0, column=0, sticky='w', pady=5)
        kml_info = ttk.Label(format_frame, text="Bathymetric surfaces, depth contours, and sonar points for Google Earth",
                            font=('Helvetica', 8), foreground='#666')
        kml_info.grid(row=1, column=0, sticky='w', padx=(20, 0), pady=(0, 10))
        
        mbtiles_check = ttk.Checkbutton(format_frame, text="🗺️ MBTiles (Web Map Tiles)", 
                                        variable=self.var_mbtiles)
        mbtiles_check.grid(row=2, column=0, sticky='w', pady=5)
        mbtiles_info = ttk.Label(format_frame, text="Tile pyramid for web mapping (Leaflet, etc.)",
                                font=('Helvetica', 8), foreground='#666')
        mbtiles_info.grid(row=3, column=0, sticky='w', padx=(20, 0), pady=(0, 10))
        
        dem_check = ttk.Checkbutton(format_frame, text="🏔️ DEM (Digital Elevation Model GeoTIFF)", 
                                    variable=self.var_dem)
        dem_check.grid(row=4, column=0, sticky='w', pady=5)
        dem_info = ttk.Label(format_frame, text="3D elevation grid for GIS software and 3D visualization",
                            font=('Helvetica', 8), foreground='#666')
        dem_info.grid(row=5, column=0, sticky='w', padx=(20, 0), pady=(0, 0))
        
        # ====== BATHYMETRIC OPTIONS ======
        
        bath_frame = ttk.LabelFrame(scrollable_frame, text="Bathymetric Options", padding="10")
        bath_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        bath_frame.columnconfigure(1, weight=1)
        
        ttk.Label(bath_frame, text="Contour Interval (meters):").grid(row=0, column=0, sticky='w', pady=5)
        self.contour_spinbox = ttk.Spinbox(bath_frame, from_=0.5, to=50, increment=0.5, width=10)
        self.contour_spinbox.set(5.0)
        self.contour_spinbox.grid(row=0, column=1, sticky='w', pady=5)
        
        contour_info = ttk.Label(bath_frame, 
                                text="Spacing between depth contour lines. Smaller = more detail but slower",
                                font=('Helvetica', 8), foreground='#666')
        contour_info.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # ====== UNIT CONVERSION ======
        
        units_frame = ttk.LabelFrame(scrollable_frame, text="Units & Display", padding="10")
        units_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        units_frame.columnconfigure(1, weight=1)
        
        ttk.Label(units_frame, text="Depth Unit:").grid(row=0, column=0, sticky='w', pady=5)
        self.depth_unit_var = tk.StringVar(value="feet")
        depth_combo = ttk.Combobox(units_frame, textvariable=self.depth_unit_var, 
                                   values=["feet", "meters", "fathoms"], state='readonly', width=15)
        depth_combo.grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(units_frame, text="Speed Unit:").grid(row=1, column=0, sticky='w', pady=5)
        self.speed_unit_var = tk.StringVar(value="knots")
        speed_combo = ttk.Combobox(units_frame, textvariable=self.speed_unit_var, 
                                   values=["knots", "mph", "kmh"], state='readonly', width=15)
        speed_combo.grid(row=1, column=1, sticky='w', pady=5)
        
        units_info = ttk.Label(units_frame, 
                              text="Convert depth and speed values in HTML output",
                              font=('Helvetica', 8), foreground='#666')
        units_info.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 0))
        
        # ====== TARGET DETECTION ======
        
        target_frame = ttk.LabelFrame(scrollable_frame, text="Target Detection", padding="10")
        target_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
        target_frame.columnconfigure(0, weight=1)
        
        self.var_include_targets = tk.BooleanVar(value=False)
        target_check = ttk.Checkbutton(target_frame, 
                                      text="Include Detected Targets in KML", 
                                      variable=self.var_include_targets)
        target_check.grid(row=0, column=0, sticky='w', pady=5)
        
        target_info = ttk.Label(target_frame, 
                               text="Classify and mark rocks, wrecks, and anomalies in output (requires detection)",
                               font=('Helvetica', 8), foreground='#666')
        target_info.grid(row=1, column=0, sticky='w', pady=(0, 0))
        
        # ====== TIER 1 ENHANCEMENTS ======
        
        enhance_frame = ttk.LabelFrame(scrollable_frame, text="Image Enhancements (Tier 1)", padding="10")
        enhance_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=5)
        enhance_frame.columnconfigure(0, weight=1)
        
        self.var_histogram = tk.BooleanVar(value=False)
        hist_check = ttk.Checkbutton(enhance_frame, 
                                     text="📈 Histogram Equalization", 
                                     variable=self.var_histogram)
        hist_check.grid(row=0, column=0, sticky='w', pady=5)
        
        hist_info = ttk.Label(enhance_frame, 
                             text="Enhances contrast across entire dynamic range (slower, better for dark/bright images)",
                             font=('Helvetica', 8), foreground='#666')
        hist_info.grid(row=1, column=0, sticky='w', pady=(0, 5))
        
        self.var_morphology = tk.BooleanVar(value=False)
        morph_check = ttk.Checkbutton(enhance_frame, 
                                      text="🧹 Morphological Denoise", 
                                      variable=self.var_morphology)
        morph_check.grid(row=2, column=0, sticky='w', pady=5)
        
        morph_info = ttk.Label(enhance_frame, 
                              text="Removes noise using erosion/dilation (slowest, best for noisy sonar)",
                              font=('Helvetica', 8), foreground='#666')
        morph_info.grid(row=3, column=0, sticky='w', pady=(0, 5))
        
        self.var_adaptive = tk.BooleanVar(value=True)
        adapt_check = ttk.Checkbutton(enhance_frame, 
                                      text="🎨 Adaptive Contrast", 
                                      variable=self.var_adaptive)
        adapt_check.grid(row=4, column=0, sticky='w', pady=5)
        
        adapt_info = ttk.Label(enhance_frame, 
                              text="Local contrast enhancement (fast, good for balanced improvement)",
                              font=('Helvetica', 8), foreground='#666')
        adapt_info.grid(row=5, column=0, sticky='w', pady=(0, 0))
        
        # ====== FAMILY VIEWER & SHARING ======
        
        family_frame = ttk.LabelFrame(scrollable_frame, text="Family Viewer & Sharing", padding="10")
        family_frame.grid(row=4, column=0, sticky='ew', padx=5, pady=5)
        family_frame.columnconfigure(0, weight=1)
        
        self.var_family_viewer = tk.BooleanVar(value=True)
        family_check = ttk.Checkbutton(family_frame, 
                                      text="📱 Generate Family-Friendly Web Interface", 
                                      variable=self.var_family_viewer)
        family_check.grid(row=0, column=0, sticky='w', pady=5)
        
        family_info = ttk.Label(family_frame, 
                               text="Creates beautiful HTML pages for families to view survey results",
                               font=('Helvetica', 8), foreground='#666')
        family_info.grid(row=1, column=0, sticky='w', pady=(0, 10))
        
        self.var_launch_viewer = tk.BooleanVar(value=True)
        launch_check = ttk.Checkbutton(family_frame, 
                                      text="🚀 Launch Viewer Server (port 8080)", 
                                      variable=self.var_launch_viewer)
        launch_check.grid(row=2, column=0, sticky='w', pady=5)
        
        launch_info = ttk.Label(family_frame, 
                               text="Opens web server for local/network access (0.0.0.0:8080)",
                               font=('Helvetica', 8), foreground='#666')
        launch_info.grid(row=3, column=0, sticky='w', pady=(0, 10))
        
        self.var_tunnel = tk.BooleanVar(value=False)
        tunnel_check = ttk.Checkbutton(family_frame, 
                                      text="🌐 Setup Remote Tunnel (for families far away)", 
                                      variable=self.var_tunnel)
        tunnel_check.grid(row=4, column=0, sticky='w', pady=5)
        
        tunnel_info = ttk.Label(family_frame, 
                               text="Enables public access via ngrok/Cloudflare/SSH (requires external tool)",
                               font=('Helvetica', 8), foreground='#666')
        tunnel_info.grid(row=5, column=0, sticky='w', pady=(0, 10))
        
        ttk.Label(family_frame, text="Tunnel Type:").grid(row=6, column=0, sticky='w', pady=5)
        self.tunnel_type_var = tk.StringVar(value="localhost_run")
        tunnel_combo = ttk.Combobox(family_frame, textvariable=self.tunnel_type_var,
                                   values=["localhost_run", "ngrok", "cloudflare", "serveo", "tailscale"],
                                   state='readonly', width=20)
        tunnel_combo.grid(row=7, column=0, sticky='w', pady=5)
        
        # ====== OUTPUT SETTINGS ======
        
        output_frame = ttk.LabelFrame(scrollable_frame, text="Output Settings", padding="10")
        output_frame.grid(row=5, column=0, sticky='ew', padx=5, pady=5)
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky='w', pady=5)
        
        # Use the preprocessing output directory passed from sonar_gui.py
        default_output = str(Path.home() / "SonarSniffer_Output")
        if self.processing_output_dir:
            # Use the directory passed from preprocessing
            default_output = self.processing_output_dir
        else:
            # Fallback to parent's output directory if available
            try:
                if hasattr(self.parent, 'output_dir'):
                    default_output = self.parent.output_dir.get()
            except:
                pass
        
        self.output_var = tk.StringVar(value=default_output)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var)
        output_entry.grid(row=0, column=1, sticky='ew', padx=(5, 5), pady=5)
        
        browse_btn = ttk.Button(output_frame, text="Browse...", 
                               command=self._browse_output_dir)
        browse_btn.grid(row=0, column=2, pady=5)
        
        ttk.Label(output_frame, text="Filename Base:").grid(row=1, column=0, sticky='w', pady=5)
        self.basename_var = tk.StringVar(value="sonar_survey")
        basename_entry = ttk.Entry(output_frame, textvariable=self.basename_var)
        basename_entry.grid(row=1, column=1, columnspan=2, sticky='ew', padx=(5, 0), pady=5)
        
        # ====== PROGRESS ======
        
        progress_frame = ttk.LabelFrame(scrollable_frame, text="Progress", padding="10")
        progress_frame.grid(row=6, column=0, sticky='ew', padx=5, pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky='ew', pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready to export", 
                                     font=('Helvetica', 9), foreground='#666')
        self.status_label.grid(row=1, column=0, sticky='w', pady=5)
        
        # ====== BUTTONS ======
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=10)
        button_frame.columnconfigure(1, weight=1)
        
        export_btn = ttk.Button(button_frame, text="▶ Export All", 
                               command=self._start_export)
        export_btn.grid(row=0, column=0, sticky='w', padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", 
                                    command=self.dialog.destroy)
        self.cancel_btn.grid(row=0, column=2, sticky='e', padx=5)
        
    def _browse_output_dir(self):
        """Open directory browser dialog"""
        dir_path = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_var.get()
        )
        if dir_path:
            self.output_var.set(dir_path)
    
    def _start_export(self):
        """Start export in background thread"""
        if self.exporting:
            messagebox.showwarning("Export In Progress", "Export is already running")
            return
        
        # Validate at least one format is selected
        if not (self.var_kml.get() or self.var_mbtiles.get() or self.var_dem.get()):
            messagebox.showwarning("No Formats Selected", 
                                 "Please select at least one export format")
            return
        
        # Validate output directory
        output_dir = Path(self.output_var.get())
        if not output_dir.parent.exists():
            messagebox.showerror("Invalid Directory", 
                               f"Parent directory does not exist:\n{output_dir.parent}")
            return
        
        # Start export in thread
        self.exporting = True
        self.cancel_btn.config(state='disabled')
        export_thread = threading.Thread(target=self._do_export, daemon=True)
        export_thread.start()
    
    def _do_export(self):
        """Perform export (runs in background thread)"""
        try:
            # Create options
            options = PostProcessingOptions(
                generate_kml=self.var_kml.get(),
                generate_mbtiles=self.var_mbtiles.get(),
                generate_dem=self.var_dem.get(),
                contour_interval=float(self.contour_spinbox.get()),
                include_targets=self.var_include_targets.get(),
                basename=self.basename_var.get(),
                output_dir=Path(self.output_var.get()),
            )
            
            # Convert records to SonarPoint objects
            self.parent.after(0, lambda: self._update_status("Converting records...", 0))
            
            sonar_points = []
            for i, rec in enumerate(self.records):
                # Handle both dict and object attributes
                def get_attr(obj, *names, default=0):
                    """Get attribute from object or dict, trying multiple names."""
                    for name in names:
                        if isinstance(obj, dict):
                            val = obj.get(name)
                        else:
                            val = getattr(obj, name, None)
                        if val is not None:
                            return val
                    return default
                
                # Get raw depth in meters (RSD files are in meters)
                raw_depth = get_attr(rec, 'depth', 'depth_m', default=0)
                
                # Convert depth to user's selected unit
                converted_depth = UnitConverter.convert_depth(
                    raw_depth, 
                    from_unit="meters",
                    to_unit=self.depth_unit_var.get()
                )
                
                point = SonarPoint(
                    latitude=get_attr(rec, 'latitude', 'lat', default=0),
                    longitude=get_attr(rec, 'longitude', 'lon', default=0),
                    depth=converted_depth,
                    timestamp=get_attr(rec, 'timestamp', 'offset', default=i),
                    confidence=get_attr(rec, 'confidence', default=1.0),
                    channel=get_attr(rec, 'channel', 'ch', default=0),
                    frequency=get_attr(rec, 'frequency', default=200.0),
                )
                sonar_points.append(point)
                
                progress = (i / len(self.records)) * 10
                self.parent.after(0, lambda p=progress: self._update_status(
                    f"Converting record {i+1}/{len(self.records)}", p))
            
            # Create exporter
            self.parent.after(0, lambda: self._update_status("Initializing exporter...", 10))
            exporter = GeospatialExporter(options.output_dir)
            
            # Extract targets if requested
            targets = None
            if options.include_targets:
                self.parent.after(0, lambda: self._update_status("Extracting targets from sonar data...", 15))
                targets = extract_targets_from_records(
                    self.records, 
                    confidence_threshold=0.5,
                    depth_unit=self.depth_unit_var.get()
                )
                self.parent.after(0, lambda: self._update_status(
                    f"Found {len(targets)} potential targets", 18))
            
            # Export
            self.parent.after(0, lambda: self._update_status("Exporting data...", 20))
            
            results = exporter.export_all(
                sonar_points=sonar_points,
                targets=targets,  # Now extracts targets from records
                basename=options.basename,
                contour_interval=options.contour_interval,
                generate_mbtiles=options.generate_mbtiles,
                generate_dem=options.generate_dem,
                depth_unit=self.depth_unit_var.get(),
            )
            
            # Generate family viewer if enabled
            if self.var_family_viewer.get():
                self.parent.after(0, lambda: self._update_status("Generating family viewer...", 70))
                try:
                    from gui_integration_layer import FamilyViewerIntegration
                    
                    viewer_integration = FamilyViewerIntegration(
                        str(options.output_dir),
                        survey_name=options.basename
                    )
                    viewer_integration.generate_viewer(self.records)
                    self.parent.after(0, lambda: self._update_status("Family viewer generated", 80))
                    results['family_viewer'] = str(options.output_dir / 'family_viewer_output')
                except Exception as e:
                    self.parent.after(0, lambda msg=str(e): self._update_status(f"Family viewer failed: {msg}", 80))
            
            # Launch viewer server if enabled
            if self.var_launch_viewer.get() and self.var_family_viewer.get():
                self.parent.after(0, lambda: self._update_status("Launching viewer server...", 85))
                try:
                    from gui_integration_layer import TunnelIntegration
                    
                    server = TunnelIntegration(local_port=8080)
                    if server.launch_server(str(options.output_dir)):
                        self.parent.after(0, lambda: self._update_status("Server running on port 8080", 90))
                        results['server'] = "http://localhost:8080"
                    else:
                        self.parent.after(0, lambda: self._update_status("Server launch failed", 90))
                except Exception as e:
                    self.parent.after(0, lambda msg=str(e): self._update_status(f"Server launch failed: {msg}", 90))
            
            # Setup tunnel if enabled
            if self.var_tunnel.get() and self.var_family_viewer.get():
                self.parent.after(0, lambda: self._update_status("Setting up remote tunnel...", 95))
                try:
                    from gui_integration_layer import TunnelIntegration
                    
                    tunnel = TunnelIntegration(local_port=8080)
                    success, url = tunnel.setup_tunnel(self.tunnel_type_var.get())
                    if success and url:
                        self.parent.after(0, lambda: self._update_status(f"Tunnel ready: {url}", 98))
                        results['tunnel_url'] = url
                    else:
                        self.parent.after(0, lambda: self._update_status("Tunnel setup skipped (not available)", 98))
                except Exception as e:
                    self.parent.after(0, lambda msg=str(e): self._update_status(f"Tunnel setup skipped: {msg}", 98))
            
            # Success
            self.parent.after(0, lambda: self._export_complete(results))
            
        except Exception as e:
            error_msg = str(e)
            self.parent.after(0, lambda msg=error_msg: self._export_failed(msg))
    
    def _update_status(self, message: str, progress: float):
        """Update progress display (called from main thread)"""
        try:
            self.status_label.config(text=message)
            self.progress_var.set(progress)
        except:
            pass  # Dialog may have been destroyed
    
    def _export_complete(self, results: Dict[str, Path]):
        """Export completed successfully"""
        self.exporting = False
        self.cancel_btn.config(state='normal')
        self.progress_var.set(100)
        self.status_label.config(text="✓ Export complete!", foreground='#2ecc71')
        
        # Build message
        msg = "Export completed successfully!\n\nGenerated files:\n"
        for fmt, path in results.items():
            if fmt not in ['family_viewer', 'server', 'tunnel_url']:
                msg += f"  • {fmt.upper()}: {path.name}\n"
        
        msg += "\nFiles are ready for:\n"
        msg += "  • Google Earth (KML)\n"
        msg += "  • Web mapping (MBTiles)\n"
        msg += "  • GIS analysis (DEM)\n"
        
        # Add family viewer info
        if results.get('family_viewer'):
            msg += "\n✓ Family Viewer Generated\n"
            msg += f"  Location: {Path(results['family_viewer']).name}/\n"
        
        if results.get('server'):
            msg += f"\n✓ Viewer Server Running\n"
            msg += f"  URL: {results['server']}/\n"
        
        if results.get('tunnel_url'):
            msg += f"\n✓ Remote Access Ready\n"
            msg += f"  URL: {results['tunnel_url']}/\n"
            msg += f"  (Share with families away from command center)\n"
        
        messagebox.showinfo("Export Complete", msg)
        
        # Call completion callback if provided
        if self.on_complete:
            self.on_complete(results)
    
    def _export_failed(self, error: str):
        """Export failed"""
        self.exporting = False
        self.cancel_btn.config(state='normal')
        self.status_label.config(text=f"✗ Export failed: {error}", foreground='#e74c3c')
        messagebox.showerror("Export Failed", f"Export failed:\n{error}")


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == '__main__':
    # Create sample records
    sample_records = [
        {
            'latitude': 40.0 + i * 0.0001,
            'longitude': -75.0 + i * 0.0001,
            'depth': 10 + (i % 50),
            'timestamp': i,
            'confidence': 0.8 + (i % 20) * 0.01,
            'channel': i % 2,
            'frequency': 200.0,
        }
        for i in range(100)
    ]
    
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide root window
    
    # Create dialog
    def on_export_complete(results):
        print(f"\nExport completed: {results}")
    
    dialog = PostProcessingDialog(root, sample_records, on_export_complete)
    
    root.mainloop()
