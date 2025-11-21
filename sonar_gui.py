#!/usr/bin/env python3
"""
SonarSniffer GUI - Desktop application for sonar data processing
SonarSniffer by NautiDog Sailing
Sniffing out sonar targets like a vizsla on birds
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime
from io import StringIO
import contextlib
import numpy as np
import time
import multiprocessing
import psutil

# Rust/CUDA acceleration
from python_cuda_bridge import encode_with_fallback
from cuda_bridge import get_cuda_bridge

# Add workspace to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Suppress stdout/stderr during imports to hide debug output
_capture = StringIO()
with contextlib.redirect_stdout(_capture), contextlib.redirect_stderr(_capture):
    try:
        # Import generation detector for automatic parser selection
        from rsd_format_detector import auto_select_parser, detect_rsd_generation
        
        # Import both parsers - will select appropriate one based on file generation
        from engine_classic_varstruct import parse_rsd_records_classic as parse_rsd_records_gen1
        from engine_nextgen_syncfirst import parse_rsd_records_nextgen as parse_rsd_records_gen2
        
        # Set a default parser (Gen1 for backwards compatibility)
        parse_rsd_records_fast = parse_rsd_records_gen1
        
        from manufacturer_parsers.navico_parser import NavicoParser
        from sonar_data_structures import SonarParseResult
        PARSER_AVAILABLE = True
    except Exception as e:
        PARSER_AVAILABLE = False
        PARSER_ERROR = str(e)

# Store captured debug output (can be logged if needed)
_import_debug = _capture.getvalue()

# ============================================================================
# CHECKPOINT MANAGER - For resumable processing
# ============================================================================

class CheckpointManager:
    """Manages checkpoints for resumable processing"""
    
    def __init__(self, checkpoint_dir=None):
        """Initialize checkpoint manager"""
        if checkpoint_dir is None:
            checkpoint_dir = str(Path.home() / '.sonarsnifer_checkpoints')
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def get_checkpoint_path(self, file_path):
        """Get checkpoint file path for a given input file"""
        file_hash = hash(str(Path(file_path).resolve()))
        return self.checkpoint_dir / f"checkpoint_{abs(file_hash)}.json"
    
    def save_checkpoint(self, file_path, stage, data):
        """Save processing checkpoint
        
        Args:
            file_path: Input RSD file path
            stage: Processing stage (e.g., 'parsed', 'mosaicked', 'enhanced')
            data: Data dict to save (will be JSON serialized)
        """
        import json
        checkpoint_path = self.get_checkpoint_path(file_path)
        
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'file_path': str(file_path),
            'file_size': Path(file_path).stat().st_size,
            'stage': stage,
            'data': data,
        }
        
        try:
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint, f, default=str, indent=2)
            return True
        except Exception as e:
            print(f"Checkpoint save failed: {e}")
            return False
    
    def load_checkpoint(self, file_path):
        """Load processing checkpoint if available
        
        Returns:
            Checkpoint dict or None if not found/invalid
        """
        import json
        checkpoint_path = self.get_checkpoint_path(file_path)
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint = json.load(f)
            
            # Verify the checkpoint is for the same file
            if checkpoint['file_path'] != str(file_path):
                return None
            
            return checkpoint
        except Exception as e:
            print(f"Checkpoint load failed: {e}")
            return None
    
    def delete_checkpoint(self, file_path):
        """Delete checkpoint after successful completion"""
        checkpoint_path = self.get_checkpoint_path(file_path)
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
                return True
            except:
                return False
        return True

# ============================================================================
# TIER 1 IMAGE ENHANCEMENT FUNCTIONS
# ============================================================================

def enhance_histogram_equalization(image):
    """Apply histogram equalization to improve contrast.
    
    Args:
        image: numpy array (grayscale or will be converted)
        
    Returns:
        enhanced image as uint8 array
    """
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Calculate histogram
    hist, _ = np.histogram(image, bins=256, range=(0, 256))
    cdf = np.cumsum(hist)
    cdf_normalized = cdf * 255 / cdf[-1]  # Normalize to 0-255
    
    # Apply mapping
    enhanced = cdf_normalized[image]
    return enhanced.astype(np.uint8)


def enhance_morphological_denoise(image, kernel_size=5):
    """Apply morphological operations (open/close) to denoise.
    
    Reduces speckle noise while preserving edges.
    
    Args:
        image: numpy array (grayscale)
        kernel_size: size of morphological kernel (odd number)
        
    Returns:
        denoised image as uint8 array
    """
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Create kernel
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    
    # Opening: erosion followed by dilation (removes small noise)
    from scipy import ndimage
    eroded = ndimage.binary_erosion(image > 128, structure=kernel).astype(np.uint8) * 255
    opened = ndimage.binary_dilation(eroded > 128, structure=kernel).astype(np.uint8) * 255
    
    # Closing: dilation followed by erosion (fills small holes)
    dilated = ndimage.binary_dilation(image > 128, structure=kernel).astype(np.uint8) * 255
    closed = ndimage.binary_erosion(dilated > 128, structure=kernel).astype(np.uint8) * 255
    
    # Combine opening and closing
    result = np.maximum(opened, closed)
    return result.astype(np.uint8)


def enhance_adaptive_contrast(image, window_size=32):
    """Apply adaptive thresholding for local contrast enhancement.
    
    Better than global contrast stretching for varying water conditions.
    
    Args:
        image: numpy array (grayscale)
        window_size: local window size for adaptation
        
    Returns:
        enhanced image as uint8 array
    """
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    h, w = image.shape
    result = np.zeros_like(image)
    
    # Process image in windows
    for y in range(0, h, window_size):
        for x in range(0, w, window_size):
            # Define window bounds
            y_end = min(y + window_size, h)
            x_end = min(x + window_size, w)
            
            # Extract window
            window = image[y:y_end, x:x_end]
            
            # Calculate local stats
            local_mean = np.mean(window)
            local_std = np.std(window)
            
            # Normalize and scale to 0-255
            if local_std > 1:
                normalized = (window - local_mean) / local_std * 64 + 128
                normalized = np.clip(normalized, 0, 255)
            else:
                normalized = window
            
            result[y:y_end, x:x_end] = normalized.astype(np.uint8)
    
    return result


def apply_sonar_enhancements(image, use_histogram=True, use_morphology=True, use_adaptive=True, cuda_bridge=None):
    """Apply selected enhancement pipeline to sonar imagery with GPU acceleration.
    
    Args:
        image: numpy array (grayscale uint8)
        use_histogram: apply histogram equalization
        use_morphology: apply morphological denoising
        use_adaptive: apply adaptive contrast
        cuda_bridge: optional CUDA bridge for GPU acceleration
        
    Returns:
        enhanced image as uint8 array
    """
    enhanced = image.copy().astype(np.float32)
    
    if use_histogram:
        if cuda_bridge is not None:
            try:
                # Try GPU acceleration first
                enhanced = cuda_bridge.histogram_equalize(enhanced.astype(np.uint8))
            except Exception:
                # Fall back to CPU if GPU fails
                enhanced = enhance_histogram_equalization(enhanced.astype(np.uint8))
        else:
            enhanced = enhance_histogram_equalization(enhanced.astype(np.uint8))
    
    if use_morphology:
        try:
            enhanced = enhance_morphological_denoise(enhanced.astype(np.uint8))
        except ImportError:
            pass  # scipy not available, skip
    
    if use_adaptive:
        enhanced = enhance_adaptive_contrast(enhanced.astype(np.uint8))
    
    return np.clip(enhanced, 0, 255).astype(np.uint8)


def apply_colormap_to_image(image, colormap_name='jet', mirror_horizontal=False):
    """Apply matplotlib colormap to grayscale image and optionally mirror it.
    
    Args:
        image: uint8 grayscale array
        colormap_name: name of matplotlib colormap (jet, viridis, plasma, etc.)
        mirror_horizontal: if True, flip image horizontally (for left side-scan)
        
    Returns:
        RGB image as uint8 array with shape (H, W, 3)
    """
    import matplotlib
    import matplotlib.colors as mcolors
    
    # Map custom colormap names to actual matplotlib colormaps
    colormap_mapping = {
        'amber': 'YlOrBr',           # Yellow -> Orange -> Brown (looks amber)
        'amber_light': 'YlOrBr_r',   # Reversed for light to bright orange
        'amber_dark': 'Oranges_r',   # Oranges reversed for dark to bright
    }
    
    # Resolve custom colormap names to matplotlib colormaps
    matplotlib_colormap = colormap_mapping.get(colormap_name, colormap_name)
    
    # Mirror if needed (for channel 4 / port side)
    if mirror_horizontal:
        image = np.fliplr(image)
    
    # Normalize to 0-1
    norm = mcolors.Normalize(vmin=0, vmax=255)
    
    # Get colormap using non-deprecated API (matplotlib 3.7+)
    try:
        cmap = matplotlib.colormaps[matplotlib_colormap]
    except (KeyError, AttributeError):
        # Fallback for older matplotlib versions or if colormap not found
        try:
            cmap = matplotlib.cm.get_cmap(matplotlib_colormap)
        except (ValueError, AttributeError):
            cmap = matplotlib.cm.get_cmap('jet')
    
    # Apply colormap (returns RGBA, we want RGB)
    colored = cmap(norm(image))
    
    # Convert to uint8 RGB (drop alpha channel)
    rgb = (colored[:, :, :3] * 255).astype(np.uint8)
    
    return rgb


def build_single_frame(frame_data):
    """
    Build a single video frame from sonar rows using smooth block stitching.
    
    This function is designed to be called in parallel via ThreadPoolExecutor.
    For dual-channel data (port + starboard), rows are pre-combined horizontally
    with proper orientation (port flipped left, starboard normal right).
    
    Uses block-based stitching with interpolation to eliminate flickering
    caused by hard row transitions.
    
    Args:
        frame_data: tuple of (frame_index, rows, row_channels, frame_h, frame_w, 
                             color_scheme, enhance_histogram, enhance_morphology, 
                             enhance_adaptive, cuda_bridge)
    
    Returns:
        tuple of (frame_index, img_rgb) where img_rgb is the colored frame
    """
    try:
        (i, rows, row_channels, frame_h, frame_w, color_scheme, 
         enhance_histogram, enhance_morphology, enhance_adaptive, cuda_bridge) = frame_data
        
        # Build slab from rows using smooth interpolation
        start = max(0, i - frame_h + 1)
        slab = rows[start:i+1]
        
        # Stack into image
        img = np.zeros((frame_h, frame_w), dtype=np.uint8)
        h = len(slab)
        
        if h > 0:
            # Use smooth interpolation to blend rows
            stacked = np.vstack(slab).astype(np.float32)
            
            # Apply vertical smoothing to eliminate hard row boundaries
            if h > 1:
                # Apply Gaussian filter vertically for smoothness
                from scipy.ndimage import gaussian_filter1d
                stacked = gaussian_filter1d(stacked, sigma=0.5, axis=0)
            
            img[-h:, :] = np.clip(stacked, 0, 255).astype(np.uint8)
        
        # Apply enhancements (with GPU if available)
        img = apply_sonar_enhancements(
            img,
            use_histogram=enhance_histogram,
            use_morphology=enhance_morphology,
            use_adaptive=enhance_adaptive,
            cuda_bridge=cuda_bridge
        )
        
        # Apply colormap
        # For combined dual-channel rows, don't apply channel-specific mirroring
        # (mirroring already done during row combination)
        current_channel = row_channels[i] if i < len(row_channels) else None
        mirror = (current_channel == 4) and (current_channel != 'combined')
        img_rgb = apply_colormap_to_image(img, colormap_name=color_scheme, mirror_horizontal=mirror)
        
        return (i, img_rgb)
    except Exception as e:
        print(f"Error building frame {frame_data[0]}: {str(e)}")
        return (frame_data[0], None)


class SonarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SonarSniffer - Sonar Data Processor")
        self.root.geometry("1400x900")
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.setup_colors()
        
        # Initialize checkpoint manager for resumable processing
        self.checkpoint_manager = CheckpointManager()
        
        # State variables
        self.current_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.home() / "SonarSniffer_Output"))
        self.last_output_dir = str(Path.home() / "SonarSniffer_Output")  # Remember last used directory
        self.processing = False
        self.cancel_requested = False
        
        # Processing options
        self.color_scheme = tk.StringVar(value="Jet (Blue->Red)")  # Store display name, not key
        self.include_csv = tk.BooleanVar(value=True)  # Auto-export CSV
        self.include_json = tk.BooleanVar(value=False)  # Auto-export JSON
        self.include_waterfall = tk.BooleanVar(value=True)
        self.include_video = tk.BooleanVar(value=True)
        self.include_kml = tk.BooleanVar(value=False)
        self.normalize_depth = tk.BooleanVar(value=True)
        self.include_mbtiles = tk.BooleanVar(value=False)
        self.auto_launch_map = tk.BooleanVar(value=True)
        
        # Water column detection and removal options
        self.detect_water_column = tk.BooleanVar(value=True)  # Auto-detect and align water column
        self.remove_water_column = tk.BooleanVar(value=False)  # Remove water column from video
        self.water_column_sensitivity = tk.DoubleVar(value=0.85)  # Detection sensitivity (0.0-1.0)
        
        # ============ ADVANCED ENHANCEMENTS ============
        # PBR Rendering options
        self.enable_pbr = tk.BooleanVar(value=False)
        self.pbr_mode = tk.StringVar(value="SIMPLE")  # SIMPLE, ENHANCED, PBR_METALLIC, ACOUSTIC, DIFFERENTIAL
        self.pbr_quality = tk.StringVar(value="HIGH")  # LOW, MEDIUM, HIGH
        
        # Radiometric Corrections
        self.enable_agc = tk.BooleanVar(value=False)  # Automatic Gain Control
        self.agc_sensitivity = tk.DoubleVar(value=0.5)  # 0.0-1.0
        self.enable_denoise = tk.BooleanVar(value=False)  # ML-based denoising
        self.denoise_strength = tk.DoubleVar(value=0.5)  # 0.0-1.0
        self.enable_destrip = tk.BooleanVar(value=False)  # Remove seam artifacts
        
        # Metadata Overlay
        self.enable_metadata_overlay = tk.BooleanVar(value=False)
        self.show_range_markers = tk.BooleanVar(value=True)
        self.show_center_cursor = tk.BooleanVar(value=True)
        self.show_scale_bar = tk.BooleanVar(value=True)
        self.show_gps_overlay = tk.BooleanVar(value=False)
        self.show_depth_overlay = tk.BooleanVar(value=False)
        
        # Target Detection
        self.enable_target_detection = tk.BooleanVar(value=False)
        self.target_detection_sensitivity = tk.DoubleVar(value=0.5)  # 0.0-1.0
        
        # Coordinate Overlay
        self.enable_coordinate_overlay = tk.BooleanVar(value=False)
        self.coordinate_viewer_type = tk.StringVar(value="Static")  # Static or HTML
        
        # Data loading for post-processing
        self.loaded_data = None  # Pre-parsed CSV/JSON data
        self.data_source_label = None  # Will reference the label in advanced tab
        
        # Rust/CUDA acceleration
        self.cuda = None  # Initialize lazily on first use
        
        # Image enhancement options moved to post-processing dialog
        
        # Color schemes for waterfall/video
        self.color_schemes = {
            "jet": "Jet (Blue->Red)",
            "viridis": "Viridis (Dark->Bright)",
            "plasma": "Plasma (Purple->Yellow)",
            "inferno": "Inferno (Black->Yellow)",
            "magma": "Magma (Black->White)",
            "cividis": "Cividis (Blue->Yellow, colorblind-friendly)",
            "turbo": "Turbo (Multi-color spectrum)",
            "twilight": "Twilight (Cyclic)",
            "hot": "Hot (Black->Red->Yellow)",
            "cool": "Cool (Cyan->Magenta)",
            "spring": "Spring (Magenta->Yellow)",
            "summer": "Summer (Green->Yellow)",
            "autumn": "Autumn (Red->Yellow)",
            "winter": "Winter (Blue->Cyan)",
            "gray": "Grayscale (B&W)",
            "amber": "Amber (Orange->Yellow)",
            "amber_light": "Amber Light (Light->Bright Orange)",
            "amber_dark": "Amber Dark (Dark Brown->Orange)",
        }
        
        # Create reverse lookup: display name -> key
        self.color_schemes_reverse = {v: k for k, v in self.color_schemes.items()}
        
        # Build UI
        self.build_ui()
        self.check_parser()
        
    def setup_colors(self):
        """Configure application color scheme"""
        self.style.configure('Title.TLabel', font=('Helvetica', 14, 'bold'))
        self.style.configure('Header.TLabel', font=('Helvetica', 11, 'bold'))
        self.style.configure('Info.TLabel', font=('Helvetica', 9))
        self.style.configure('Success.TLabel', foreground='#2ecc71', font=('Helvetica', 9, 'bold'))
        self.style.configure('Error.TLabel', foreground='#e74c3c', font=('Helvetica', 9, 'bold'))
        self.style.configure('Warning.TLabel', foreground='#f39c12', font=('Helvetica', 9, 'bold'))
        
    def build_ui(self):
        """Construct the complete user interface"""
        # Configure root window for proper resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create a vertical PanedWindow to hold tabs and button bar
        paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashwidth=5, bg='#f0f0f0')
        paned.grid(row=0, column=0, sticky='nsew')
        
        # Create notebook (tabs) for Basic and Advanced processing
        notebook_frame = ttk.Frame(paned)
        paned.add(notebook_frame, height=750, stretch="always")
        notebook_frame.columnconfigure(0, weight=1)
        notebook_frame.rowconfigure(0, weight=1)
        
        notebook = ttk.Notebook(notebook_frame)
        notebook.grid(row=0, column=0, sticky='nsew')
        
        # Create Basic tab
        basic_tab = self._create_basic_tab(notebook)
        notebook.add(basic_tab, text="🔧 Basic Processing")
        
        # Create Advanced tab
        advanced_tab = self._create_advanced_tab(notebook)
        notebook.add(advanced_tab, text="🚀 Advanced Enhancements")
        
        # Create fixed button bar as lower pane in PanedWindow (never hidden)
        button_frame = ttk.Frame(paned)
        paned.add(button_frame, height=110, stretch="never")  # Fixed height, won't shrink below this
        button_frame.columnconfigure(0, weight=1)
        
        self._create_action_buttons(button_frame)
    
    def _create_basic_tab(self, notebook):
        """Create the Basic Processing tab"""
        # Canvas with scrollbar for scrollable content
        content_frame = ttk.Frame(notebook)
        canvas = tk.Canvas(content_frame, bg='white', highlightthickness=0)
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
        
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Main frame inside scrollable area with padding
        main_frame = scrollable_frame
        main_frame.columnconfigure(0, weight=1)
        
        # Add padding to main frame
        padded_main = ttk.Frame(main_frame, padding="10")
        padded_main.grid(row=0, column=0, sticky='nsew')
        padded_main.columnconfigure(0, weight=1)
        main_frame = padded_main
        
        # Title
        title = ttk.Label(main_frame, text="🐕 SonarSniffer", style='Title.TLabel')
        title.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 5))
        
        # Tagline
        tagline = ttk.Label(main_frame, text="Sniffing out sonar targets like a vizsla on birds", style='Subtitle.TLabel', foreground='#666666')
        tagline.grid(row=1, column=0, columnspan=4, sticky='w', pady=(0, 15))
        
        # File selection panel
        file_frame = ttk.LabelFrame(main_frame, text="📁 File Selection", padding="10")
        file_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="Selected File:", style='Header.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(file_frame, textvariable=self.current_file, style='Info.TLabel', 
                 foreground='#3498db').grid(row=0, column=1, sticky='ew', padx=(10, 10))
        
        ttk.Button(file_frame, text="Browse...", command=self.select_file).grid(row=0, column=2, padx=5)
        ttk.Button(file_frame, text="Clear", command=self.clear_file).grid(row=0, column=3, padx=5)
        
        # Output directory panel
        output_frame = ttk.LabelFrame(main_frame, text="📂 Output Directory", padding="10")
        output_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Output Folder:", style='Header.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(output_frame, textvariable=self.output_dir, style='Info.TLabel', 
                 foreground='#2ecc71').grid(row=0, column=1, sticky='ew', padx=(10, 10))
        
        ttk.Button(output_frame, text="Browse...", command=self.select_output_dir).grid(row=0, column=2, padx=5)
        ttk.Button(output_frame, text="Clear", command=self.clear_output_dir).grid(row=0, column=3, padx=5)
        
        # Processing options panel
        options_frame = ttk.LabelFrame(main_frame, text="⚙️ Processing Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=(0, 10))
        options_frame.columnconfigure(4, weight=1)
        
        # Row 1: Color scheme and video/waterfall options
        ttk.Label(options_frame, text="Color Scheme:", style='Header.TLabel').grid(row=0, column=0, sticky='w', padx=5)
        color_combo = ttk.Combobox(options_frame, textvariable=self.color_scheme, 
                                   values=list(self.color_schemes.values()), state='readonly', width=25)
        color_combo.grid(row=0, column=1, padx=5, sticky='ew')
        
        # Video and waterfall checkboxes
        ttk.Checkbutton(options_frame, text="📺 Include Video Data", 
                       variable=self.include_video).grid(row=0, column=2, padx=10, sticky='w')
        ttk.Checkbutton(options_frame, text="📊 Include Waterfall Data", 
                       variable=self.include_waterfall).grid(row=0, column=3, padx=10, sticky='w')
        
        # Row 2: CSV/JSON export options
        ttk.Checkbutton(options_frame, text="📄 Export CSV", 
                       variable=self.include_csv).grid(row=1, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))
        ttk.Checkbutton(options_frame, text="📋 Export JSON", 
                       variable=self.include_json).grid(row=1, column=2, columnspan=2, padx=10, sticky='w', pady=(10, 0))
        
        # Row 3: KML and MBTiles options
        ttk.Checkbutton(options_frame, text="🗺️ Generate KML Trackline", 
                       variable=self.include_kml).grid(row=2, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))
        ttk.Checkbutton(options_frame, text="📏 Normalize Depth", 
                       variable=self.normalize_depth).grid(row=2, column=2, columnspan=2, padx=10, sticky='w', pady=(10, 0))
        
        # Row 4: MBTiles and water column options
        ttk.Checkbutton(options_frame, text="🌐 Generate MBTiles (Web Map)", 
                       variable=self.include_mbtiles).grid(row=3, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))
        ttk.Checkbutton(options_frame, text="🚀 Auto-launch Map", 
                       variable=self.auto_launch_map).grid(row=3, column=2, columnspan=2, padx=10, sticky='w', pady=(10, 0))
        
        # Row 5: Water column detection and removal options
        ttk.Checkbutton(options_frame, text="💧 Detect & Align Water Column", 
                       variable=self.detect_water_column).grid(row=4, column=0, columnspan=2, padx=5, sticky='w', pady=(10, 0))
        ttk.Checkbutton(options_frame, text="❌ Remove Water Column from Video", 
                       variable=self.remove_water_column).grid(row=4, column=2, columnspan=2, padx=10, sticky='w', pady=(10, 0))
        
        # Progress panel
        progress_frame = ttk.LabelFrame(main_frame, text="⏳ Processing Progress", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=4, sticky='nsew', pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        progress_frame.rowconfigure(2, weight=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 10))
        
        # Status labels
        ttk.Label(progress_frame, text="Status:", style='Header.TLabel').grid(row=1, column=0, sticky='w')
        self.status_label = ttk.Label(progress_frame, text="Ready", style='Info.TLabel')
        self.status_label.grid(row=1, column=1, sticky='w', padx=10)
        
        # Stats row
        ttk.Label(progress_frame, text="Records:", style='Header.TLabel').grid(row=2, column=0, sticky='w')
        self.records_label = ttk.Label(progress_frame, text="0", style='Info.TLabel', foreground='#3498db')
        self.records_label.grid(row=2, column=1, sticky='w', padx=10)
        
        ttk.Label(progress_frame, text="Time:", style='Header.TLabel').grid(row=3, column=0, sticky='w')
        self.time_label = ttk.Label(progress_frame, text="0s", style='Info.TLabel', foreground='#3498db')
        self.time_label.grid(row=3, column=1, sticky='w', padx=10)
        
        # Results panel with scrolled text
        results_frame = ttk.LabelFrame(main_frame, text="📊 Results & Output", padding="10")
        results_frame.grid(row=5, column=0, columnspan=4, sticky='nsew')
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Scrolled text for results
        self.results_text = scrolledtext.ScrolledText(results_frame, height=12, width=120, 
                                                      wrap=tk.WORD, font=('Courier', 9))
        self.results_text.grid(row=0, column=0, sticky='nsew')
        
        # Configure text tags for styling
        self.results_text.tag_config('header', foreground='#2c3e50', font=('Courier', 9, 'bold'))
        self.results_text.tag_config('success', foreground='#2ecc71', font=('Courier', 9, 'bold'))
        self.results_text.tag_config('error', foreground='#e74c3c', font=('Courier', 9, 'bold'))
        self.results_text.tag_config('info', foreground='#3498db', font=('Courier', 9))
        self.results_text.tag_config('warning', foreground='#f39c12', font=('Courier', 9, 'bold'))
        self.results_text.tag_config('option', foreground='#9b59b6', font=('Courier', 9, 'bold'))
        
        # Clear results button at bottom
        clear_frame = ttk.Frame(main_frame)
        clear_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(10, 0))
        clear_frame.columnconfigure(1, weight=1)
        
        ttk.Button(clear_frame, text="🗑 Clear Results", command=self.clear_results).grid(row=0, column=0, padx=5)
        
        return content_frame
    
    def _create_advanced_tab(self, notebook):
        """Create the Advanced Enhancements tab"""
        # Canvas with scrollbar
        content_frame = ttk.Frame(notebook)
        canvas = tk.Canvas(content_frame, bg='white', highlightthickness=0)
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
        
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_frame = scrollable_frame
        main_frame.columnconfigure(0, weight=1)
        
        # Padding
        padded_main = ttk.Frame(main_frame, padding="10")
        padded_main.grid(row=0, column=0, sticky='nsew')
        padded_main.columnconfigure(0, weight=1)
        main_frame = padded_main
        
        # Title
        title = ttk.Label(main_frame, text="🚀 Advanced Enhancements", style='Title.TLabel')
        title.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 15))
        
        # ============ DATA LOADING SECTION ============
        data_frame = ttk.LabelFrame(main_frame, text="📂 Data Source", padding="15")
        data_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 15))
        data_frame.columnconfigure(1, weight=1)
        
        # Status indicator
        ttk.Label(data_frame, text="Current Data:", style='Header.TLabel').grid(row=0, column=0, sticky='w', padx=10)
        self.data_source_label = ttk.Label(data_frame, text="No data loaded", style='Info.TLabel', 
                                          foreground='#e74c3c')
        self.data_source_label.grid(row=0, column=1, sticky='w', padx=10)
        
        # Load CSV/JSON button (only visible if no fresh data)
        load_btn = ttk.Button(data_frame, text="📂 Load CSV/JSON", command=self.load_parsed_data)
        load_btn.grid(row=0, column=2, padx=10)
        
        ttk.Label(data_frame, text="Load pre-parsed CSV or JSON files for post-processing enhancements",
                 style='Info.TLabel', foreground='#666666').grid(row=1, column=0, columnspan=3, sticky='w', pady=(10, 0))
        
        # Store reference to data source label for updates
        self.advanced_tab_data_status = data_frame
        
        # ============ PBR RENDERING SECTION ============
        pbr_frame = ttk.LabelFrame(main_frame, text="🔬 PBR (Physically-Based) Rendering", padding="15")
        pbr_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 15))
        pbr_frame.columnconfigure(1, weight=1)
        pbr_frame.columnconfigure(3, weight=1)
        
        ttk.Checkbutton(pbr_frame, text="✓ Enable PBR Rendering", 
                       variable=self.enable_pbr).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))
        
        # Rendering Mode selection
        ttk.Label(pbr_frame, text="Rendering Mode:", style='Header.TLabel').grid(row=1, column=0, sticky='w', padx=10)
        pbr_mode_combo = ttk.Combobox(pbr_frame, textvariable=self.pbr_mode,
                                      values=["SIMPLE", "ENHANCED", "PBR_METALLIC", "ACOUSTIC", "DIFFERENTIAL"],
                                      state='readonly', width=20)
        pbr_mode_combo.grid(row=1, column=1, padx=10, sticky='ew')
        
        # Quality level
        ttk.Label(pbr_frame, text="Quality Level:", style='Header.TLabel').grid(row=1, column=2, sticky='w', padx=10)
        pbr_quality_combo = ttk.Combobox(pbr_frame, textvariable=self.pbr_quality,
                                         values=["LOW", "MEDIUM", "HIGH"],
                                         state='readonly', width=15)
        pbr_quality_combo.grid(row=1, column=3, padx=10, sticky='ew')
        
        # Info text
        info_text = ("PBR rendering uses Fresnel-Schlick reflection equations and physical material properties "
                    "to create highly realistic acoustic material visualization. Supports differential rendering "
                    "for enhanced target contrast.")
        ttk.Label(pbr_frame, text=info_text, style='Info.TLabel', wraplength=800,
                 foreground='#666666').grid(row=2, column=0, columnspan=4, sticky='w', pady=(10, 0))
        
        # ============ RADIOMETRIC CORRECTIONS ============
        radio_frame = ttk.LabelFrame(main_frame, text="📊 Radiometric Corrections", padding="15")
        radio_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(0, 15))
        radio_frame.columnconfigure(1, weight=1)
        radio_frame.columnconfigure(3, weight=1)
        
        # Row 1: AGC
        ttk.Checkbutton(radio_frame, text="✓ Automatic Gain Control (AGC)", 
                       variable=self.enable_agc).grid(row=0, column=0, columnspan=2, sticky='w', padx=10)
        ttk.Label(radio_frame, text="Sensitivity:", style='Info.TLabel').grid(row=0, column=2, sticky='e', padx=10)
        
        agc_scale = ttk.Scale(radio_frame, from_=0.0, to=1.0, variable=self.agc_sensitivity, orient='horizontal')
        agc_scale.grid(row=0, column=3, padx=10, sticky='ew')
        
        self.agc_value_label = ttk.Label(radio_frame, text=f"{self.agc_sensitivity.get():.2f}",
                                        style='Info.TLabel', foreground='#3498db')
        self.agc_value_label.grid(row=0, column=4, padx=5)
        agc_scale.configure(command=lambda v: self.agc_value_label.config(text=f"{float(v):.2f}"))
        
        # Row 2: Denoising
        ttk.Checkbutton(radio_frame, text="✓ ML-Based Denoising", 
                       variable=self.enable_denoise).grid(row=1, column=0, columnspan=2, sticky='w', padx=10, pady=(10, 0))
        ttk.Label(radio_frame, text="Strength:", style='Info.TLabel').grid(row=1, column=2, sticky='e', padx=10, pady=(10, 0))
        
        denoise_scale = ttk.Scale(radio_frame, from_=0.0, to=1.0, variable=self.denoise_strength, orient='horizontal')
        denoise_scale.grid(row=1, column=3, padx=10, sticky='ew', pady=(10, 0))
        
        self.denoise_value_label = ttk.Label(radio_frame, text=f"{self.denoise_strength.get():.2f}",
                                            style='Info.TLabel', foreground='#3498db')
        self.denoise_value_label.grid(row=1, column=4, padx=5, pady=(10, 0))
        denoise_scale.configure(command=lambda v: self.denoise_value_label.config(text=f"{float(v):.2f}"))
        
        # Row 3: Destripping
        ttk.Checkbutton(radio_frame, text="✓ Remove Seam Artifacts (Destripping)", 
                       variable=self.enable_destrip).grid(row=2, column=0, columnspan=4, sticky='w', padx=10, pady=(10, 0))
        
        # Info text
        info_text2 = ("Advanced radiometric processing improves sonar image quality by correcting gain variations, "
                     "removing noise while preserving detail, and eliminating seam artifacts from adjacent ping lines.")
        ttk.Label(radio_frame, text=info_text2, style='Info.TLabel', wraplength=800,
                 foreground='#666666').grid(row=3, column=0, columnspan=5, sticky='w', pady=(10, 0))
        
        # ============ METADATA OVERLAY ============
        meta_frame = ttk.LabelFrame(main_frame, text="📍 Metadata Overlay", padding="15")
        meta_frame.grid(row=3, column=0, columnspan=4, sticky='ew', pady=(0, 15))
        meta_frame.columnconfigure(2, weight=1)
        
        ttk.Checkbutton(meta_frame, text="✓ Enable Metadata Overlay", 
                       variable=self.enable_metadata_overlay).grid(row=0, column=0, columnspan=4, sticky='w', padx=10, pady=(0, 10))
        
        # Row 1: Range markers and cursor
        ttk.Checkbutton(meta_frame, text="📏 Range Markers (m)", 
                       variable=self.show_range_markers).grid(row=1, column=0, columnspan=2, sticky='w', padx=10)
        ttk.Checkbutton(meta_frame, text="⊕ Center Cursor", 
                       variable=self.show_center_cursor).grid(row=1, column=2, columnspan=2, sticky='w', padx=10)
        
        # Row 2: Scale bar and depth
        ttk.Checkbutton(meta_frame, text="━ Scale Bar", 
                       variable=self.show_scale_bar).grid(row=2, column=0, columnspan=2, sticky='w', padx=10, pady=(10, 0))
        ttk.Checkbutton(meta_frame, text="🌊 Depth Overlay (m)", 
                       variable=self.show_depth_overlay).grid(row=2, column=2, columnspan=2, sticky='w', padx=10, pady=(10, 0))
        
        # Row 3: GPS
        ttk.Checkbutton(meta_frame, text="📡 GPS/Location Data", 
                       variable=self.show_gps_overlay).grid(row=3, column=0, columnspan=4, sticky='w', padx=10, pady=(10, 0))
        
        # Info text
        info_text3 = ("Real-time metadata overlay renders navigation data, range indicators, and depth information "
                     "directly onto the sonar video for enhanced situational awareness.")
        ttk.Label(meta_frame, text=info_text3, style='Info.TLabel', wraplength=800,
                 foreground='#666666').grid(row=4, column=0, columnspan=4, sticky='w', pady=(10, 0))
        
        # ============ TARGET DETECTION ============
        target_frame = ttk.LabelFrame(main_frame, text="🎯 Target Detection & Marking", padding="15")
        target_frame.grid(row=4, column=0, columnspan=4, sticky='ew', pady=(0, 15))
        target_frame.columnconfigure(2, weight=1)
        
        ttk.Checkbutton(target_frame, text="✓ Enable Target Detection", 
                       variable=self.enable_target_detection).grid(row=0, column=0, columnspan=4, sticky='w', padx=10, pady=(0, 10))
        
        # Sensitivity slider
        ttk.Label(target_frame, text="Detection Sensitivity:").grid(row=1, column=0, sticky='w', padx=10)
        ttk.Scale(target_frame, from_=0, to=1, orient='horizontal',
                 variable=self.target_detection_sensitivity).grid(row=1, column=1, columnspan=2, sticky='ew', padx=5)
        ttk.Label(target_frame, text="0=Low  1=High", font=('Helvetica', 8),
                 foreground='#666').grid(row=1, column=3, sticky='w', padx=5)
        
        # Info text
        info_text4 = ("Automatically detects rocks, wrecks, and other hard targets in sonar imagery using "
                     "multi-scale blob detection and statistical anomaly analysis. Results are marked with "
                     "confidence scores and classified by target type (rock/wreck/anomaly).")
        ttk.Label(target_frame, text=info_text4, style='Info.TLabel', wraplength=800,
                 foreground='#666666').grid(row=2, column=0, columnspan=4, sticky='w', pady=(10, 0))
        
        # ============ COORDINATE OVERLAY ============
        coord_frame = ttk.LabelFrame(main_frame, text="🗺️ Coordinate Display Overlay", padding="15")
        coord_frame.grid(row=5, column=0, columnspan=4, sticky='ew', pady=(0, 15))
        coord_frame.columnconfigure(2, weight=1)
        
        ttk.Checkbutton(coord_frame, text="✓ Enable Coordinate Overlay", 
                       variable=self.enable_coordinate_overlay).grid(row=0, column=0, columnspan=4, sticky='w', padx=10, pady=(0, 10))
        
        # Viewer type
        ttk.Label(coord_frame, text="Display Mode:").grid(row=1, column=0, sticky='w', padx=10)
        coord_combo = ttk.Combobox(coord_frame, textvariable=self.coordinate_viewer_type,
                                  values=["Static", "HTML"], state='readonly', width=15)
        coord_combo.grid(row=1, column=1, sticky='w', padx=5)
        
        coord_help = ttk.Label(coord_frame, text="Static: PNG with grid overlay   |   HTML: Interactive viewer",
                              font=('Helvetica', 8), foreground='#666')
        coord_help.grid(row=1, column=2, columnspan=2, sticky='w', padx=5)
        
        # Info text
        info_text5 = ("Adds interactive coordinate grid showing latitude, longitude, and depth at any cursor position. "
                     "Supports both static image overlays with embedded grid and dynamic HTML viewers for exploration.")
        ttk.Label(coord_frame, text=info_text5, style='Info.TLabel', wraplength=800,
                 foreground='#666666').grid(row=2, column=0, columnspan=4, sticky='w', pady=(10, 0))
        
        # ============ EXECUTE BUTTON ============
        execute_frame = ttk.Frame(main_frame)
        execute_frame.grid(row=6, column=0, columnspan=4, sticky='ew', pady=(20, 0))
        execute_frame.columnconfigure(0, weight=1)
        
        style = ttk.Style()
        style.configure('Execute.TButton', font=('Helvetica', 13, 'bold'), padding=12)
        
        self.execute_enhancement_btn = ttk.Button(execute_frame, text="▶ EXECUTE ENHANCEMENTS",
                                                 command=self.execute_enhancements,
                                                 style='Execute.TButton')
        self.execute_enhancement_btn.grid(row=0, column=0, padx=20, sticky='ew', ipady=20)
        
        # Notes section
        notes_frame = ttk.LabelFrame(main_frame, text="💡 Enhancement Information", padding="15")
        notes_frame.grid(row=7, column=0, columnspan=4, sticky='ew', pady=(20, 0))
        notes_frame.columnconfigure(0, weight=1)
        
        notes_text = scrolledtext.ScrolledText(notes_frame, height=8, width=100, wrap=tk.WORD,
                                              font=('Courier', 9), bg='#f9f9f9')
        notes_text.grid(row=0, column=0, sticky='nsew')
        notes_frame.rowconfigure(0, weight=1)
        
        notes_content = """ENHANCEMENT FEATURES:

PBR RENDERING: Uses physically-based reflection models with Fresnel-Schlick equations to simulate realistic
acoustic material interactions. Supports 5 rendering modes with automatic material classification.

RADIOMETRIC CORRECTIONS: Processes sonar data to improve image quality by correcting gain variations (AGC),
removing speckle noise via machine learning (Denoise), and eliminating acquisition artifacts (Destrip).

METADATA OVERLAY: Renders navigation, depth, and location data directly onto video frames for enhanced
situational awareness during playback and analysis.

Enhancements are applied automatically during video generation when "Execute Enhancements" is clicked.
Results are saved to the output directory alongside processed waterfall and video files."""
        
        notes_text.insert('1.0', notes_content)
        notes_text.config(state='disabled')
        
        return content_frame
    
    def _create_action_buttons(self, button_frame):
        """Create the action button bar"""
        button_bar = ttk.LabelFrame(button_frame, text="⚡ Action Controls", padding="15")
        button_bar.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)
        button_bar.columnconfigure(2, weight=1)
        
        # Make buttons larger and more visible
        style = ttk.Style()
        style.configure('Large.TButton', font=('Helvetica', 12, 'bold'), padding=10)
        
        self.process_btn = ttk.Button(button_bar, text="▶▶ PROCESS FILE", command=self.start_processing, style='Large.TButton')
        self.process_btn.grid(row=0, column=0, padx=20, pady=10, sticky='ew', ipadx=20, ipady=15)
        
        self.post_process_btn = ttk.Button(button_bar, text="🗺️ POST-PROCESS (KML/MBTiles)", command=self.show_post_processing, state='disabled', style='Large.TButton')
        self.post_process_btn.grid(row=0, column=1, padx=20, pady=10, sticky='ew', ipadx=20, ipady=15)
        
        self.cancel_btn = ttk.Button(button_bar, text="⏹ CANCEL", command=self.cancel_processing, state='disabled', style='Large.TButton')
        self.cancel_btn.grid(row=0, column=2, padx=20, pady=10, sticky='ew', ipadx=20, ipady=15)
    
    def execute_enhancements(self):
        """Execute the selected enhancements on processed data"""
        if not self.last_results or not self.last_results.get('records'):
            messagebox.showwarning("Warning", "No processed data available. Please process an RSD file first.")
            return
        
        enhancement_summary = []
        
        if self.enable_pbr.get():
            enhancement_summary.append(f"• PBR Rendering: {self.pbr_mode.get()} mode ({self.pbr_quality.get()} quality)")
        
        if self.enable_agc.get():
            enhancement_summary.append(f"• AGC: Sensitivity {self.agc_sensitivity.get():.2f}")
        
        if self.enable_denoise.get():
            enhancement_summary.append(f"• Denoising: Strength {self.denoise_strength.get():.2f}")
        
        if self.enable_destrip.get():
            enhancement_summary.append("• Destripping: Enabled")
        
        if self.enable_metadata_overlay.get():
            overlay_items = []
            if self.show_range_markers.get():
                overlay_items.append("Range Markers")
            if self.show_center_cursor.get():
                overlay_items.append("Center Cursor")
            if self.show_scale_bar.get():
                overlay_items.append("Scale Bar")
            if self.show_gps_overlay.get():
                overlay_items.append("GPS Data")
            if self.show_depth_overlay.get():
                overlay_items.append("Depth Info")
            
            if overlay_items:
                enhancement_summary.append(f"• Metadata Overlay: {', '.join(overlay_items)}")
        
        if not enhancement_summary:
            messagebox.showinfo("Info", "No enhancements selected")
            return
        
        msg = "The following enhancements will be applied:\n\n"
        msg += "\n".join(enhancement_summary)
        msg += "\n\nThis will create enhanced versions of video and waterfall output."
        
        result = messagebox.askokcancel("Confirm Enhancements", msg)
        if result:
            # Run enhancements in background thread
            thread = threading.Thread(target=self._apply_enhancements_thread, args=(
                self.last_results,
            ), daemon=True)
            thread.start()
    
    def _apply_enhancements_thread(self, results):
        """Background thread: Apply enhancements to video and waterfall"""
        try:
            self.log_header("\n" + "="*70)
            self.log_header("ENHANCEMENT PROCESSING")
            self.log_header("="*70)
            
            records_data = results.get('records', [])
            video_path = results.get('video_path')
            mosaic_paths = results.get('mosaic_paths', [])
            output_dir = self.output_dir.get().strip() or str(Path.home() / 'SonarSniffer_Output')
            
            self.log_info(f"Processing {len(records_data)} records with enhancements...")
            
            # Apply metadata overlay to video if enabled
            if self.enable_metadata_overlay.get() and video_path and Path(video_path).exists():
                self.log_header("\nApplying Metadata Overlays to Video...")
                try:
                    from video_metadata_overlay import VideoMetadataIntegrator
                    import cv2
                    import numpy as np
                    from pathlib import Path
                    
                    # Initialize overlay integrator
                    # Need to get video dimensions first
                    cap = cv2.VideoCapture(str(video_path))
                    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    
                    integrator = VideoMetadataIntegrator(frame_height, frame_width)
                    
                    # Process video frame by frame
                    enhanced_frames = []
                    cap = cv2.VideoCapture(str(video_path))
                    frame_count = 0
                    
                    self.log_info(f"Processing video frames with metadata overlay...")
                    
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        
                        # Map frame number to nearest record
                        frame_idx = min(frame_count, len(records_data) - 1)
                        record = records_data[frame_idx] if frame_idx < len(records_data) else None
                        
                        if record:
                            # Apply metadata overlay
                            frame = integrator.add_metadata_to_frame(
                                frame,
                                record,
                                frame_count,
                                show_range_markers=self.show_range_markers.get(),
                                show_center_cursor=self.show_center_cursor.get(),
                                show_scale_bar=self.show_scale_bar.get()
                            )
                        
                        enhanced_frames.append(frame)
                        frame_count += 1
                    
                    cap.release()
                    
                    # Write enhanced video if we have frames
                    if enhanced_frames:
                        output_path = Path(output_dir) / f"{Path(video_path).stem}_enhanced.mp4"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        fps = cv2.VideoCapture(str(video_path)).get(cv2.CAP_PROP_FPS)
                        out = cv2.VideoWriter(str(output_path), fourcc, fps, 
                                            (frame_width, frame_height))
                        
                        for frame in enhanced_frames:
                            out.write(frame)
                        
                        out.release()
                        self.log_success(f"✓ Enhanced video created: {output_path.name}")
                    else:
                        self.log_warning("No frames to write to enhanced video")
                except Exception as e:
                    self.log_warning(f"Metadata overlay skipped: {e}")
            
            # Apply PBR rendering to mosaic if enabled
            if self.enable_pbr.get() and mosaic_paths:
                self.log_header("\nApplying PBR Rendering...")
                try:
                    from pbr_sonar_renderer import PBRSonarRenderer
                    import numpy as np
                    from PIL import Image
                    
                    renderer = PBRSonarRenderer(
                        frame_height=480,
                        frame_width=480,
                        mounting_angle_deg=0.0,
                        beam_angle_deg=17.0,
                        frequency_khz=200.0
                    )
                    
                    for mosaic_path in mosaic_paths:
                        if Path(mosaic_path).exists():
                            try:
                                # Load the mosaic image
                                mosaic_img = Image.open(mosaic_path)
                                mosaic_array = np.array(mosaic_img).astype(np.uint8)
                                
                                # Handle grayscale or RGB
                                if len(mosaic_array.shape) == 2:
                                    sonar_frame = mosaic_array
                                elif mosaic_array.shape[2] >= 3:
                                    sonar_frame = np.mean(mosaic_array[:, :, :3], axis=2).astype(np.uint8)
                                else:
                                    sonar_frame = mosaic_array[:, :, 0]
                                
                                # Apply PBR differential rendering
                                rendered = renderer.render_differential_frame(
                                    sonar_frame,
                                    depth_map=None,
                                    material_map=None,
                                    use_pbr=True
                                )
                                
                                # Save rendered mosaic
                                output_path = Path(output_dir) / f"{Path(mosaic_path).stem}_pbr.png"
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                rendered_img = Image.fromarray(rendered)
                                rendered_img.save(str(output_path))
                                
                                self.log_success(f"✓ PBR-rendered mosaic: {output_path.name}")
                            except Exception as frame_error:
                                self.log_warning(f"PBR rendering failed for {Path(mosaic_path).name}: {frame_error}")
                except Exception as e:
                    self.log_warning(f"PBR rendering skipped: {e}")
            
            # Apply radiometric corrections if enabled
            if (self.enable_agc.get() or self.enable_denoise.get() or self.enable_destrip.get()) and mosaic_paths:
                self.log_header("\nApplying Radiometric Corrections...")
                try:
                    from radiometric_corrections import RadiometricCorrector
                    import numpy as np
                    from PIL import Image
                    
                    corrector = RadiometricCorrector()
                    
                    for mosaic_path in mosaic_paths:
                        if Path(mosaic_path).exists():
                            try:
                                # Load the mosaic image
                                mosaic_img = Image.open(mosaic_path)
                                mosaic_array = np.array(mosaic_img).astype(np.uint8)
                                
                                # Handle grayscale or RGB
                                if len(mosaic_array.shape) == 2:
                                    sonar_frame = mosaic_array
                                elif mosaic_array.shape[2] >= 3:
                                    sonar_frame = np.mean(mosaic_array[:, :, :3], axis=2).astype(np.uint8)
                                else:
                                    sonar_frame = mosaic_array[:, :, 0]
                                
                                # Build corrections dictionary based on user selections
                                corrections = {
                                    'beam_angle': False,  # No range data available
                                    'agc': self.enable_agc.get(),
                                    'denoise': self.enable_denoise.get(),
                                    'destrip': self.enable_destrip.get(),
                                    'footprint': False,  # No depth data available
                                }
                                
                                # Apply corrections
                                corrected = corrector.apply_full_correction(
                                    sonar_frame,
                                    range_samples=None,
                                    depth_m=10.0,
                                    range_max_m=50.0,
                                    corrections=corrections
                                )
                                
                                # Save corrected mosaic
                                output_path = Path(output_dir) / f"{Path(mosaic_path).stem}_corrected.png"
                                output_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                corrected_img = Image.fromarray(corrected)
                                corrected_img.save(str(output_path))
                                
                                self.log_success(f"✓ Radiometrically corrected: {output_path.name}")
                            except Exception as frame_error:
                                self.log_warning(f"Radiometric correction failed for {Path(mosaic_path).name}: {frame_error}")
                except Exception as e:
                    self.log_warning(f"Radiometric corrections skipped: {e}")
            
            # Apply target detection if enabled
            if self.enable_target_detection.get() and mosaic_paths:
                self.log_header("\nDetecting Targets (Rocks, Wrecks, Anomalies)...")
                try:
                    from target_detection import TargetDetector, TargetMarker
                    
                    detector = TargetDetector(sensitivity=self.target_detection_sensitivity.get())
                    
                    for mosaic_path in mosaic_paths:
                        if Path(mosaic_path).exists():
                            try:
                                # Load mosaic
                                mosaic_img = Image.open(mosaic_path)
                                mosaic_array = np.array(mosaic_img).astype(np.uint8)
                                
                                # Handle grayscale or RGB
                                if len(mosaic_array.shape) == 2:
                                    sonar_gray = mosaic_array
                                    sonar_rgb = cv2.cvtColor(mosaic_array, cv2.COLOR_GRAY2BGR)
                                elif mosaic_array.shape[2] >= 3:
                                    sonar_gray = np.mean(mosaic_array[:, :, :3], axis=2).astype(np.uint8)
                                    sonar_rgb = mosaic_array[:, :, :3]
                                else:
                                    sonar_gray = mosaic_array[:, :, 0]
                                    sonar_rgb = cv2.cvtColor(sonar_gray, cv2.COLOR_GRAY2BGR)
                                
                                # Detect targets
                                targets = detector.detect_targets(sonar_gray)
                                
                                if targets:
                                    # Mark targets on image
                                    marked = TargetMarker.mark_targets(
                                        sonar_rgb, 
                                        targets,
                                        show_confidence=True,
                                        show_intensity=True
                                    )
                                    
                                    # Save marked image
                                    output_path = Path(output_dir) / f"{Path(mosaic_path).stem}_targets.png"
                                    output_path.parent.mkdir(parents=True, exist_ok=True)
                                    
                                    marked_img = Image.fromarray(cv2.cvtColor(marked, cv2.COLOR_BGR2RGB))
                                    marked_img.save(str(output_path))
                                    
                                    self.log_success(f"✓ Detected {len(targets)} targets: {output_path.name}")
                                else:
                                    self.log_info(f"No targets detected in {Path(mosaic_path).name}")
                            except Exception as frame_error:
                                self.log_warning(f"Target detection failed for {Path(mosaic_path).name}: {frame_error}")
                except Exception as e:
                    self.log_warning(f"Target detection skipped: {e}")
            
            # Apply coordinate overlay if enabled
            if self.enable_coordinate_overlay.get() and mosaic_paths:
                self.log_header("\nApplying Coordinate Overlays...")
                try:
                    from coordinate_overlay import add_coordinate_overlay, GeoReference
                    
                    # Get georeferencing from records if available
                    if records_data:
                        # Extract bounds from records
                        lats = [r.get('lat', 0) for r in records_data if isinstance(r, dict)]
                        lons = [r.get('lon', 0) for r in records_data if isinstance(r, dict)]
                        depths = [r.get('depth_m', 0) for r in records_data if isinstance(r, dict)]
                        
                        if lats and lons:
                            geo_ref = GeoReference(
                                lat_min=min(lats),
                                lat_max=max(lats),
                                lon_min=min(lons),
                                lon_max=max(lons),
                                depth_min=min(depths) if depths else 0,
                                depth_max=max(depths) if depths else 100,
                                center_lat=np.mean(lats),
                                center_lon=np.mean(lons)
                            )
                        else:
                            # Default georeferencing
                            geo_ref = GeoReference(
                                lat_min=40.0, lat_max=41.0,
                                lon_min=-74.0, lon_max=-73.0,
                                depth_min=0, depth_max=100
                            )
                    else:
                        # Default georeferencing
                        geo_ref = GeoReference(
                            lat_min=40.0, lat_max=41.0,
                            lon_min=-74.0, lon_max=-73.0,
                            depth_min=0, depth_max=100
                        )
                    
                    # Determine viewer type
                    viewer_type = self.coordinate_viewer_type.get().lower().replace(' ', '_')
                    
                    for mosaic_path in mosaic_paths:
                        if Path(mosaic_path).exists():
                            try:
                                output_path = add_coordinate_overlay(
                                    str(mosaic_path),
                                    geo_ref,
                                    viewer_type=viewer_type,
                                    title=f"Sonar Image - {Path(mosaic_path).stem}"
                                )
                                
                                self.log_success(f"✓ Coordinate overlay: {Path(output_path).name}")
                            except Exception as frame_error:
                                self.log_warning(f"Coordinate overlay failed for {Path(mosaic_path).name}: {frame_error}")
                except Exception as e:
                    self.log_warning(f"Coordinate overlay skipped: {e}")
            
            self.log_header("\n" + "="*70)
            self.log_success("✓ Enhancement processing complete")
            self.log_header("="*70)
            
        except Exception as e:
            self.log_error(f"Enhancement error: {e}")
            self.log_error(traceback.format_exc())
    
    def load_parsed_data(self):
        """Load pre-parsed CSV or JSON files for post-processing"""
        file_types = [
            ("Parsed Data Files", "*.csv *.json"),
            ("CSV Files", "*.csv"),
            ("JSON Files", "*.json"),
            ("All Files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Load Parsed Sonar Data",
            filetypes=file_types,
            initialdir=str(Path.home() / "Downloads")
        )
        
        if filename:
            try:
                # Determine file type and load accordingly
                file_ext = Path(filename).suffix.lower()
                
                if file_ext == '.csv':
                    # Load CSV data
                    import pandas as pd
                    data = pd.read_csv(filename)
                    data_type = f"CSV ({len(data)} rows)"
                    self.loaded_data = data
                    
                elif file_ext == '.json':
                    # Load JSON data
                    import json
                    with open(filename, 'r') as f:
                        data = json.load(f)
                    
                    # Handle both dict and list formats
                    if isinstance(data, dict):
                        data_type = f"JSON (dict with {len(data)} keys)"
                    elif isinstance(data, list):
                        data_type = f"JSON ({len(data)} records)"
                    else:
                        data_type = "JSON (unknown format)"
                    
                    self.loaded_data = data
                
                else:
                    messagebox.showerror("Error", f"Unsupported file type: {file_ext}")
                    return
                
                # Update status label
                filename_short = Path(filename).name
                self.data_source_label.config(
                    text=f"✓ Loaded: {filename_short} ({data_type})",
                    foreground='#2ecc71'
                )
                
                self.log_success(f"✓ Data loaded: {filename_short}")
                self.log_info(f"  Type: {data_type}")
                self.log_info(f"  Path: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                self.log_error(f"Error loading file: {str(e)}")
    
    def _check_rust_available(self) -> bool:
        """Check if Rust encoder is available without blocking"""
        try:
            from python_cuda_bridge import RustEncoderBridge
            bridge = RustEncoderBridge()
            return bridge.available
        except Exception:
            return False
    
    def _check_cuda_available(self) -> bool:
        """Check if CUDA is available without blocking"""
        try:
            from cuda_bridge import get_cuda_bridge
            cuda = get_cuda_bridge()
            return cuda is not None and cuda.device_available
        except Exception:
            return False
        
    def check_parser(self):
        """Check if parser is available"""
        if not PARSER_AVAILABLE:
            self.log_error(f"Parser unavailable: {PARSER_ERROR}")
            self.process_btn.config(state='disabled')
        else:
            self.log_info("✓ RSD Parser loaded successfully")
    
    def select_file(self):
        """Open file browser to select sonar file (RSD, SLG, SL2, SL3, etc.)"""
        filename = filedialog.askopenfilename(
            title="Select Sonar File",
            filetypes=[
                ("All Sonar Files", "*.RSD *.slg *.sl2 *.sl3 *.dat *.son *.idx *.jsf *.svlog *.sdf"),
                ("Garmin RSD", "*.RSD"),
                ("Navico SLG", "*.slg"),
                ("Navico SL2", "*.sl2"),
                ("Navico SL3", "*.sl3"),
                ("Humminbird DAT", "*.dat"),
                ("Humminbird SON", "*.son"),
                ("Humminbird IDX", "*.idx"),
                ("EdgeTech JSF", "*.jsf"),
                ("Cerulean SVLOG", "*.svlog"),
                ("Klein SDF", "*.sdf"),
                ("All Files", "*.*")
            ],
            initialdir=str(Path.home() / "Downloads")
        )
        
        if filename:
            self.current_file.set(filename)
            self.log_info(f"✓ File selected: {Path(filename).name}")
    
    def clear_file(self):
        """Clear selected file"""
        self.current_file.set("")
        self.log_info("File selection cleared")
    
    def select_output_dir(self):
        """Open directory browser to select output folder"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.last_output_dir or str(Path.home())
        )
        
        if directory:
            self.output_dir.set(directory)
            self.last_output_dir = directory  # Remember this directory
            self.log_info(f"✓ Output directory selected: {directory}")
    
    def clear_output_dir(self):
        """Reset output directory to default"""
        default_dir = str(Path.home() / "SonarSniffer_Output")
        self.output_dir.set(default_dir)
        self.log_info(f"Output directory reset to: {default_dir}")
    
    def clear_results(self):
        """Clear results display"""
        self.results_text.delete('1.0', tk.END)
        self.records_label.config(text="0")
        self.time_label.config(text="0s")
    
    def start_processing(self):
        """Start file processing in background thread"""
        file_path = self.current_file.get().strip()
        
        if not file_path:
            messagebox.showwarning("No File Selected", "Please select an RSD file first")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", f"File does not exist: {file_path}")
            return
        
        if not PARSER_AVAILABLE:
            messagebox.showerror("Parser Error", "RSD parser is not available")
            return
        
        # Reset state
        self.processing = True
        self.cancel_requested = False
        self.process_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.clear_results()
        
        # Start processing thread
        thread = threading.Thread(target=self.process_file_thread, args=(file_path,), daemon=True)
        thread.start()
    
    def cancel_processing(self):
        """Request cancellation of ongoing processing"""
        self.cancel_requested = True
        self.cancel_btn.config(state='disabled')
        self.log_warning("Cancellation requested...")
    
    def process_file_thread(self, file_path):
        """Background thread: Process RSD file"""
        try:
            # Initialize Rust/CUDA acceleration
            rust_available = self._check_rust_available()
            cuda_available = self._check_cuda_available()
            
            if rust_available:
                self.log_success("✓ Rust encoder available - video will be faster")
            else:
                self.log_info("ℹ Using Python encoder (Rust not available)")
            
            if cuda_available:
                self.log_success("✓ GPU acceleration available - image processing will be faster")
            else:
                self.log_info("ℹ Using CPU image processing (GPU not available)")
            
            start_time = datetime.now()
            file_size = os.path.getsize(file_path)
            filename = Path(file_path).name
            
            # Get processing options
            selected_scheme = self.color_scheme.get()
            # Try to find the key by looking up the display name in the reverse dictionary
            color_scheme_key = self.color_schemes_reverse.get(selected_scheme, "jet")
            # If not found, it might be a direct key (fallback)
            if color_scheme_key not in self.color_schemes:
                color_scheme_key = "jet"
            
            # Update UI - file info
            self.update_status(f"Processing: {filename}")
            self.log_header(f"\n{'='*70}")
            self.log_header(f"RSD File Processing Report")
            self.log_header(f"{'='*70}")
            self.log_info(f"Filename: {filename}")
            self.log_info(f"Path: {file_path}")
            self.log_info(f"File Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
            self.log_info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Log processing options
            self.log_info("")
            self.log_header("Processing Options:")
            self.log_option(f"  Color Scheme: {self.color_scheme.get()}")
            self.log_option(f"  Include Video: {self.include_video.get()}")
            self.log_option(f"  Include Waterfall: {self.include_waterfall.get()}")
            self.log_option(f"  Export CSV: {self.include_csv.get()}")
            self.log_option(f"  Export JSON: {self.include_json.get()}")
            self.log_option(f"  Generate KML Trackline: {self.include_kml.get()}")
            self.log_option(f"  Generate MBTiles: {self.include_mbtiles.get()}")
            self.log_option(f"  Auto-launch Map: {self.auto_launch_map.get()}")
            self.log_option(f"  Normalize Depth: {self.normalize_depth.get()}")
            
            self.log_info("")
            
            self.progress.start()
            
            # Initialize CUDA bridge for GPU acceleration
            try:
                self.cuda = get_cuda_bridge()
                if self.cuda is not None and self.cuda.device_available:
                    self.log_success("✓ GPU acceleration initialized")
            except Exception as e:
                self.log_info(f"GPU acceleration unavailable: {e}")
                self.cuda = None
            
            # Parse records with debug output suppressed
            record_count = 0
            error_count = 0
            records_data = []
            
            self.log_header("Parsing Records...")
            self.log_info("")
            
            # Detect file format and parse accordingly using universal parser
            file_ext = Path(file_path).suffix.lower()
            self.log_info(f"File format detected: {file_ext}")
            
            # Suppress debug output from parser
            _old_stdout = sys.stdout
            _old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            try:
                # First try universal parser for all manufacturers
                if file_ext in ['.slg', '.sl2', '.sl3', '.dat', '.son', '.idx', '.jsf', '.svlog', '.sdf']:
                    # Multi-manufacturer formats
                    from universal_sonar_parser import parse_sonar_file
                    
                    if file_ext in ['.slg', '.sl2', '.sl3']:
                        format_name = "Navico"
                    elif file_ext in ['.dat', '.son', '.idx']:
                        format_name = "Humminbird"
                    elif file_ext == '.jsf':
                        format_name = "EdgeTech"
                    elif file_ext == '.svlog':
                        format_name = "Cerulean"
                    elif file_ext == '.sdf':
                        format_name = "Klein"
                    else:
                        format_name = "Unknown"
                    
                    self.log_info(f"Parsing {format_name} format ({file_ext}) file...")
                    result = parse_sonar_file(file_path)
                    
                    # Check for errors
                    if result.errors:
                        for error in result.errors:
                            self.log_error(f"  Parser error: {error}")
                    
                    # Convert parsed records to standard format
                    if hasattr(result, 'records') and result.records:
                        for rec in result.records:
                            record_count += 1
                            # Create a record object similar to RSD records
                            if isinstance(rec, dict):
                                sonar_data = rec.get('sonar_data', b'')
                                record = type('Record', (), {
                                    'offset': rec.get('offset', 0),
                                    'ch': rec.get('channel_type', rec.get('ch', 0)),
                                    'lat': rec.get('latitude', rec.get('lat', 0)),
                                    'lon': rec.get('longitude', rec.get('lon', 0)),
                                    'depth': rec.get('depth_m', rec.get('depth', 0)),
                                    'sonar_size': len(sonar_data),
                                    'sonar_data': sonar_data,  # Store actual sonar data for non-RSD formats
                                    'sonar_ofs': rec.get('offset', 0),  # File offset (for RSD compatibility)
                                })()
                            else:
                                record = rec  # Already in correct format
                            records_data.append(record)
                            
                            # Update progress every 500 records
                            if record_count % 500 == 0:
                                elapsed = (datetime.now() - start_time).total_seconds()
                                self.update_records(record_count)
                                self.update_time(elapsed)
                                self.log_info(f"  Processed {record_count:,} records ({elapsed:.1f}s)")
                else:
                    # Default to Garmin RSD format - auto-detect generation
                    rsd_gen = detect_rsd_generation(file_path)
                    
                    # Select appropriate parser based on file generation
                    if rsd_gen == 'gen2':
                        parser_to_use = parse_rsd_records_gen2
                        gen_label = "Gen2 (UHD)"
                    elif rsd_gen == 'gen3':
                        parser_to_use = parse_rsd_records_gen2
                        gen_label = "Gen3 (UHD2)"
                    elif rsd_gen == 'gen1':
                        parser_to_use = parse_rsd_records_gen1
                        gen_label = "Gen1 (Legacy)"
                    else:
                        # Default to Gen2 (modern files are usually UHD)
                        parser_to_use = parse_rsd_records_gen2
                        gen_label = "Auto-detected (UHD)"
                    
                    self.log_info(f"Parsing Garmin RSD file ({gen_label})...")
                    for record in parser_to_use(file_path):
                        if self.cancel_requested:
                            break
                        
                        record_count += 1
                        records_data.append(record)
                        
                        # Update progress every 5000 records
                        if record_count % 5000 == 0:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            self.update_records(record_count)
                            self.update_time(elapsed)
                            self.log_info(f"  Processed {record_count:,} records ({elapsed:.1f}s)")
            finally:
                sys.stdout = _old_stdout
                sys.stderr = _old_stderr
            
            if self.cancel_requested:
                self.log_warning("Processing cancelled by user")
                elapsed = (datetime.now() - start_time).total_seconds()
            else:
                elapsed = (datetime.now() - start_time).total_seconds()
            
            # Calculation phase
            self.progress.stop()
            self.log_info("")
            self.log_header("Processing Complete!")
            self.log_header(f"{'='*70}")
            self.log_success(f"✓ Successfully parsed {record_count:,} records")
            self.log_info(f"Processing time: {elapsed:.2f} seconds")
            if record_count > 0:
                self.log_info(f"Records per second: {record_count/elapsed:.0f}")
            
            # Detailed statistics
            self.log_info("")
            self.log_header("Summary Statistics:")
            self.log_info(f"  Total Records: {record_count:,}")
            self.log_info(f"  File Size: {file_size:,} bytes")
            self.log_info(f"  Processing Duration: {elapsed:.3f} seconds")
            self.log_info(f"  Throughput: {(file_size / (1024*1024)) / elapsed:.2f} MB/s")
            
            # Extract and display statistics from records
            if records_data:
                self.log_info("")
                self.log_header("Data Statistics:")
                channels = set()
                depths = []
                for rec in records_data:
                    # Handle both 'ch' and 'channel_id' attribute names
                    if hasattr(rec, 'ch'):
                        channels.add(rec.ch)
                    elif hasattr(rec, 'channel_id'):
                        channels.add(rec.channel_id)
                    if hasattr(rec, 'depth'):
                        depths.append(rec.depth)
                    elif hasattr(rec, 'depth_m'):
                        depths.append(rec.depth_m)
                
                if channels:
                    self.log_info(f"  Channels Found: {sorted(channels)}")
                if depths:
                    self.log_info(f"  Depth Range: {min(depths):.3f}m to {max(depths):.3f}m")
                    self.log_info(f"  Average Depth: {sum(depths)/len(depths):.3f}m")
            
            # Show first few records as sample
            if records_data:
                self.log_info("")
                self.log_header("Sample Records (first 5):")
                for i, record in enumerate(records_data[:5], 1):
                    self.log_info(f"  Record {i}: {record}")
            
            # Generate video/waterfall if enabled
            video_path = None
            if self.include_video.get():
                output_dir = self.output_dir.get().strip()
                video_path = self.generate_video_waterfall(file_path, records_data, output_dir, 
                                                           color_scheme=color_scheme_key)
                # Save checkpoint after video generation
                if video_path:
                    self.checkpoint_manager.save_checkpoint(
                        file_path, 'video_complete',
                        {'video_path': str(video_path), 'record_count': record_count}
                    )
                    self.log_success(f"✓ Checkpoint saved - video complete")
            
            # Generate georeferenced mosaic if enabled (for KML/mbtiles)
            mosaic_paths = None
            if self.include_waterfall.get():
                output_dir = self.output_dir.get().strip()
                mosaic_paths = self.generate_georeferenced_mosaic(file_path, records_data, output_dir,
                                                                  color_scheme=color_scheme_key)
                # Save checkpoint after mosaic generation
                if mosaic_paths:
                    self.checkpoint_manager.save_checkpoint(
                        file_path, 'mosaic_complete',
                        {'mosaic_paths': [str(p) for p in mosaic_paths], 'record_count': record_count}
                    )
                    self.log_success(f"✓ Checkpoint saved - mosaic complete")
            
            # Export options summary
            self.log_info("")
            self.log_header("Export Options:")
            self.log_option(f"  CSV Export: {self.include_csv.get()}")
            self.log_option(f"  JSON Export: {self.include_json.get()}")
            self.log_option(f"  Color Scheme: {color_scheme_key} ({self.color_scheme.get()})")
            self.log_option(f"  Video Output: {'Yes' if self.include_video.get() else 'No'}" + (f" → {Path(video_path).name}" if video_path else ""))
            self.log_option(f"  Mosaic Output: {'Yes' if self.include_waterfall.get() else 'No'}" + (f" ({len(mosaic_paths)} channels)" if mosaic_paths else ""))
            self.log_option(f"  KML Map: {'Yes' if self.include_kml.get() else 'No'}")
            self.log_option(f"  MBTiles/Leaflet: {'Yes (auto-launch: ' + ('Yes' if self.auto_launch_map.get() else 'No') + ')' if self.include_mbtiles.get() else 'No'}")
            
            self.log_info("")
            self.log_header(f"{'='*70}")
            
            self.update_records(record_count)
            self.update_time(elapsed)
            self.update_status("✓ Complete", success=True)
            
            # Store results for later reference
            self.last_results = {
                'filename': filename,
                'file_path': file_path,
                'record_count': record_count,
                'processing_time': elapsed,
                'file_size': file_size,
                'records': records_data,
                'timestamp': start_time,
                'color_scheme': color_scheme_key,
                'include_csv': self.include_csv.get(),
                'include_json': self.include_json.get(),
                'include_video': self.include_video.get(),
                'include_waterfall': self.include_waterfall.get(),
                'include_kml': self.include_kml.get(),
                'include_mbtiles': self.include_mbtiles.get(),
                'auto_launch_map': self.auto_launch_map.get(),
                'normalize_depth': self.normalize_depth.get(),
                'video_path': video_path,
                'mosaic_paths': mosaic_paths,
            }
            
            # Auto-export files based on checkboxes
            try:
                output_dir = self.output_dir.get().strip() or str(Path.home() / 'SonarSniffer_Output')
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                
                # Generate filename stem from input file
                file_stem = Path(file_path).stem
                
                # Auto-export CSV if enabled
                if self.include_csv.get():
                    self._export_csv_auto(records_data, output_dir, file_stem, file_path)
                
                # Auto-export JSON if enabled
                if self.include_json.get():
                    self._export_json_auto(records_data, output_dir, file_stem, file_path)
                
                # Auto-generate Survey HTML report
                try:
                    from survey_html_generator import generate_survey_report
                    survey_path = generate_survey_report(records_data, file_stem, output_dir)
                    if survey_path:
                        self.log_success(f"✓ Survey report generated: {Path(survey_path).name}")
                except Exception as e:
                    self.log_warning(f"Could not generate survey report: {e}")
                
                # Auto-export KML if enabled and mosaic was generated
                if self.include_kml.get() and mosaic_paths:
                    self._export_kml_auto(records_data, mosaic_paths, output_dir, file_stem)
                
                # Auto-export MBTiles if enabled and mosaic was generated
                if self.include_mbtiles.get() and mosaic_paths:
                    try:
                        from mbtiles_generator import generate_mbtiles
                        result = generate_mbtiles(records_data, file_stem, output_dir)
                        if result:
                            self.log_success(f"✓ MBTiles generated: {Path(result['mbtiles_path']).name} ({result['tile_count']} tiles)")
                            if result['html_path'] and result['html_path'].exists():
                                self.log_success(f"✓ Map HTML created: {Path(result['html_path']).name}")
                    except Exception as e:
                        self.log_error(f"MBTiles generation error: {e}")
                    
                    # Auto-launch map if enabled
                    if self.auto_launch_map.get():
                        map_path = Path(output_dir) / f"{file_stem}_map.html"
                        if map_path.exists():
                            import webbrowser
                            webbrowser.open(str(map_path))
                
                # Delete checkpoint after successful completion
                if self.checkpoint_manager.delete_checkpoint(file_path):
                    self.log_success("✓ Processing checkpoint cleared")
            
            except Exception as e:
                self.log_error(f"Auto-export error: {str(e)}")
            
        except Exception as e:
            self.progress.stop()
            error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
            self.log_error(f"Error during processing: {error_msg}")
            self.update_status("✗ Error", error=True)
            messagebox.showerror("Processing Error", str(e))
        
        finally:
            self.processing = False
            self.cancel_requested = False  # Reset cancel flag for next run
            self.process_btn.config(state='normal')
            self.cancel_btn.config(state='disabled')
            # Enable post-processing button if we have results
            if hasattr(self, 'last_results') and self.last_results and self.last_results.get('records'):
                self.post_process_btn.config(state='normal')
            else:
                self.post_process_btn.config(state='disabled')
    
    def update_status(self, text, success=False, error=False):
        """Update status label"""
        self.root.after(0, lambda: self.status_label.config(
            text=text,
            style='Success.TLabel' if success else ('Error.TLabel' if error else 'Info.TLabel')
        ))
    
    def update_records(self, count):
        """Update record count display"""
        self.root.after(0, lambda: self.records_label.config(text=f"{count:,}"))
    
    def update_time(self, seconds):
        """Update elapsed time display"""
        mins = int(seconds // 60)
        secs = seconds % 60
        time_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"
        self.root.after(0, lambda: self.time_label.config(text=time_str))
    
    def log_header(self, text):
        """Log header text"""
        self.root.after(0, lambda: self._do_log(text, 'header'))
    
    def log_success(self, text):
        """Log success text"""
        self.root.after(0, lambda: self._do_log(text, 'success'))
    
    def log_info(self, text):
        """Log info text"""
        self.root.after(0, lambda: self._do_log(text, 'info'))
    
    def log_error(self, text):
        """Log error text"""
        self.root.after(0, lambda: self._do_log(text, 'error'))
    
    def log_warning(self, text):
        """Log warning text"""
        self.root.after(0, lambda: self._do_log(text, 'warning'))
    
    def log_option(self, text):
        """Log option text (purple)"""
        self.root.after(0, lambda: self._do_log(text, 'option'))
    
    def _do_log(self, text, tag='info'):
        """Actually write to text widget"""
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, text + '\n', tag)
        self.results_text.see(tk.END)
        self.results_text.config(state='normal')
    
    def generate_video_waterfall(self, file_path, records_data, output_dir=None, color_scheme='jet'):
        """
        Generate waterfall video from sonar payload data with streaming memory management.
        Uses StreamingVideoEncoder when memory would exceed limits to prevent OOM crashes.
        """
        if not output_dir:
            output_dir = Path(file_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        filename_stem = Path(file_path).stem
        video_path = output_dir / f"{filename_stem}_waterfall.mp4"
        
        try:
            self.log_info("")
            self.log_header("Generating Video/Waterfall...")
            self.log_info(f"Processing {len(records_data)} records for waterfall frames")
            self.log_info(f"Filtering for side-scan channels only (4=Port, 5=Starboard)")
            self.log_info(f"Using memory-aware encoding (will stream frames if needed)")
            
            # Extract sonar payloads from records (side-scan channels 4 and 5 only)
            # Note: Process ALL records, not just first 600, to get complete side-scan data
            rows = []
            row_channels = []  # Track which channel each row came from
            rsd_file = Path(file_path)
            
            # DIAGNOSTIC: Count records by channel AND check for sonar data
            ch_counts = {}
            ch_has_sonar = {}
            ch_sonar_sizes = {}
            for rec in records_data:
                # Handle both 'ch' and 'channel_id' attribute names
                ch = getattr(rec, 'ch', None) or getattr(rec, 'channel_id', None)
                ch_counts[ch] = ch_counts.get(ch, 0) + 1
                
                # Check if this record has valid sonar data
                sonar_size = getattr(rec, 'sonar_size', 0)
                sonar_ofs = getattr(rec, 'sonar_ofs', None)
                has_sonar = (sonar_size and sonar_size > 0 and sonar_ofs is not None)
                
                if has_sonar:
                    ch_has_sonar[ch] = ch_has_sonar.get(ch, 0) + 1
                    ch_sonar_sizes[ch] = ch_sonar_sizes.get(ch, [])
                    ch_sonar_sizes[ch].append(sonar_size)
            
            self.log_info(f"Record distribution by channel: {ch_counts}")
            self.log_info(f"Records WITH valid sonar data: {ch_has_sonar}")
            
            # Debug: Show sample record details
            if records_data:
                self.log_info(f"Sample record (index 0):")
                rec = records_data[0]
                ch = getattr(rec, 'ch', None) or getattr(rec, 'channel_id', None)
                self.log_info(f"  ch={ch}, sonar_size={getattr(rec, 'sonar_size', 'N/A')}, sonar_ofs={getattr(rec, 'sonar_ofs', 'N/A')}, lat={getattr(rec, 'lat', 'N/A')}, lon={getattr(rec, 'lon', 'N/A')}")
            
            # Check if channels 4/5 have ANY sonar data
            ch4_sonar = ch_has_sonar.get(4, 0)
            ch5_sonar = ch_has_sonar.get(5, 0)
            total_sidescan_sonar = ch4_sonar + ch5_sonar
            self.log_info(f"Side-scan sonar data: Ch4={ch4_sonar} records, Ch5={ch5_sonar} records, Total={total_sidescan_sonar}")
            
            # Determine which channels to use for side-scan (use channels with sonar data)
            # Prefer channels 4/5 (standard side-scan), but fall back to any channel with sonar data
            if total_sidescan_sonar > 0:
                side_scan_channels = [4, 5]
                self.log_info(f"Using standard side-scan channels: {side_scan_channels}")
            else:
                # No data in channels 4/5, use whichever channel has the most sonar data
                side_scan_channels = [max(ch_has_sonar, key=ch_has_sonar.get)] if ch_has_sonar else []
                if side_scan_channels:
                    self.log_warning(f"No data in channels 4/5, using channel {side_scan_channels[0]} instead (has {ch_has_sonar[side_scan_channels[0]]} records with sonar data)")
            
            # Extract sonar rows with filtering
            # Track channel 4 (port) and channel 5 (starboard) separately for side-by-side display
            extracted_count = 0
            skipped_wrong_channel = 0
            skipped_no_sonar = 0
            skipped_read_error = 0
            
            ch4_rows = []  # Port side (left)
            ch5_rows = []  # Starboard side (right)
            
            # Open file for RSD records that need to be read from disk
            f = None
            try:
                f = open(rsd_file, 'rb')
            except Exception as e:
                self.log_warning(f"Could not open file for reading (will use embedded sonar data if available): {e}")
            
            for rec_idx, rec in enumerate(records_data):
                if self.cancel_requested:
                    self.log_warning("Video generation cancelled")
                    if f:
                        f.close()
                    return None
                
                # Handle both 'ch' and 'channel_id' attribute names
                ch = getattr(rec, 'ch', None) or getattr(rec, 'channel_id', None)
                
                # Check if record has sonar data
                if not hasattr(rec, 'sonar_size') or not rec.sonar_size or rec.sonar_size <= 0:
                    skipped_no_sonar += 1
                    continue
                
                try:
                    # Try to get sonar data from embedded source first (non-RSD formats)
                    if hasattr(rec, 'sonar_data') and rec.sonar_data:
                        data = rec.sonar_data if isinstance(rec.sonar_data, bytes) else bytes(rec.sonar_data)
                    # Fall back to reading from file offset (RSD format)
                    elif f and hasattr(rec, 'sonar_ofs') and rec.sonar_ofs is not None:
                        f.seek(rec.sonar_ofs)
                        data = f.read(rec.sonar_size)
                    else:
                        skipped_no_sonar += 1
                        continue
                    
                    if len(data) == 0:
                        skipped_read_error += 1
                        continue

                    
                    # Convert bytes to uint8 array
                    arr = np.frombuffer(data, dtype=np.uint8)
                    
                    if arr.size == 0:
                        continue
                    
                    # Resample to target width for side-by-side display
                    # Each channel gets half the frame width for side-by-side display
                    target_w = 480  # Half of 960 for dual-channel display
                    if arr.size < 16:
                        # Pad small rows
                        row = np.pad(arr, (0, max(0, target_w - arr.size)), constant_values=0).astype(np.uint8)
                    elif arr.size != target_w:
                        # Resample using interpolation
                        row = np.interp(np.linspace(0, arr.size-1, target_w), np.arange(arr.size), arr).astype(np.uint8)
                    else:
                        row = arr
                    
                    # Store in appropriate channel list
                    if ch == 4:
                        ch4_rows.append(row)
                    elif ch == 5:
                        ch5_rows.append(row)
                    else:
                        # For other channels, append to rows directly (single-channel mode)
                        rows.append(row)
                        row_channels.append(ch)
                    
                    extracted_count += 1
                    
                    if extracted_count % 50 == 0:
                        self.log_info(f"  Extracted {extracted_count} records (Ch4: {len(ch4_rows)}, Ch5: {len(ch5_rows)})")
                
                except Exception as e:
                    skipped_read_error += 1
                    self.log_warning(f"  Skipping record {rec_idx}: {str(e)[:50]}")
                    continue
            
            # Close file if it was opened
            if f:
                f.close()
            
            # Detect water column and apply alignment if enabled
            remover = None
            aligner = None
            mounting_config = None
            
            if self.detect_water_column.get() and (ch4_rows or ch5_rows):
                try:
                    from water_column_detector import (
                        WaterColumnDetector, WaterColumnRemover, DualChannelAligner
                    )
                    
                    detector = WaterColumnDetector(sensitivity=0.85)
                    
                    # Analyze mounting configuration
                    if ch4_rows and ch5_rows:
                        mounting_config = detector.detect_mounting_orientation(ch4_rows, ch5_rows)
                        self.log_info(f"Water column analysis:")
                        self.log_info(f"  Detected orientation: {mounting_config['orientation']}")
                        self.log_info(f"  Confidence: {mounting_config['confidence']:.1%}")
                        if 'port_stats' in mounting_config and mounting_config['port_stats'].get('detected'):
                            self.log_info(f"  Port water column: {mounting_config['port_stats']['avg_position']:.0f}px avg")
                        if 'starboard_stats' in mounting_config and mounting_config['starboard_stats'].get('detected'):
                            self.log_info(f"  Starboard water column: {mounting_config['starboard_stats']['avg_position']:.0f}px avg")
                    
                    if self.remove_water_column.get():
                        remover = WaterColumnRemover(detector)
                        self.log_info(f"Water column removal enabled (will mask detected water column)")
                    
                    if ch4_rows and ch5_rows:
                        aligner = DualChannelAligner(detector)
                    
                except ImportError as e:
                    self.log_warning(f"Water column detection unavailable: {e}")
            
            # Combine channel 4 and 5 into side-by-side rows with optional alignment
            # Port (Ch4) on left, Starboard (Ch5) on right
            if ch4_rows and ch5_rows:
                self.log_info(f"Combining dual-channel data: Ch4={len(ch4_rows)} rows, Ch5={len(ch5_rows)} rows")
                # Use the minimum count to ensure matching pairs
                paired_count = min(len(ch4_rows), len(ch5_rows))
                
                for i in range(paired_count):
                    port_row = ch4_rows[i].copy()
                    starboard_row = ch5_rows[i].copy()
                    
                    # Apply water column removal if enabled
                    if remover:
                        port_row = remover.mask_water_column(port_row)
                        starboard_row = remover.mask_water_column(starboard_row)
                    
                    # Apply alignment if available
                    if aligner:
                        port_row, starboard_row, metadata = aligner.align_channels(
                            port_row, starboard_row, auto_flip_port=True
                        )
                    else:
                        # Default: flip port horizontally to show water column pointing inward
                        port_row = np.fliplr(port_row)
                    
                    # Combine side-by-side: port on left, starboard on right
                    combined_row = np.hstack((port_row, starboard_row))
                    rows.append(combined_row)
                    row_channels.append('combined')
                
                self.log_info(f"Created {paired_count} combined dual-channel frames")
            elif ch4_rows:
                self.log_info(f"Using Port channel (Ch4) only: {len(ch4_rows)} rows")
                for i, row in enumerate(ch4_rows):
                    if remover:
                        row = remover.mask_water_column(row)
                    rows.append(row)
                row_channels.extend([4] * len(ch4_rows))
            elif ch5_rows:
                self.log_info(f"Using Starboard channel (Ch5) only: {len(ch5_rows)} rows")
                for i, row in enumerate(ch5_rows):
                    if remover:
                        row = remover.mask_water_column(row)
                    rows.append(row)
                row_channels.extend([5] * len(ch5_rows))
            
            # Log extraction summary
            self.log_info(f"Extraction summary:")
            self.log_info(f"  Successfully extracted: {extracted_count} rows")
            self.log_info(f"  Skipped (wrong channel): {skipped_wrong_channel}")
            self.log_info(f"  Skipped (no sonar data): {skipped_no_sonar}")
            self.log_info(f"  Skipped (read error): {skipped_read_error}")
            
            if not rows:
                self.log_error(f"❌ NO SONAR DATA EXTRACTED! Extracted count = {len(rows)}")
                self.log_error(f"Total records processed: {len(records_data)}")
                self.log_error(f"Check if:")
                self.log_error(f"  1. File actually contains side-scan sonar (channels 4/5)")
                self.log_error(f"  2. Records have sonar_size and sonar_ofs attributes")
                self.log_error(f"  3. File offsets are correct")
                return None
            
            self.log_success(f"✓ Extracted {len(rows)} waterfall frames")
            
            # Stack rows into frames (sliding window)
            frame_h = 480
            frame_w = rows[0].size
            
            # Memory diagnostic
            try:
                import psutil
                process = psutil.Process(os.getpid())
                mem_info = process.memory_info()
                mem_percent = process.memory_percent()
                frame_size_mb = (frame_h * frame_w * 3) / (1024 * 1024)  # RGB frame
                estimated_total_mb = (len(rows) * frame_size_mb) + (mem_info.rss / (1024 * 1024))
                self.log_info(f"Memory diagnostics:")
                self.log_info(f"  Current usage: {mem_percent:.1f}% ({mem_info.rss / (1024**3):.2f}GB)")
                self.log_info(f"  Per-frame size: {frame_size_mb:.2f}MB")
                self.log_info(f"  Estimated total if all frames buffered: {estimated_total_mb:.1f}MB")
                if estimated_total_mb > 3000:  # > 3GB - too much
                    self.log_warning(f"  ⚠️  CRITICAL: High memory usage! Using STREAMING mode (Rust encoder required)")
                    use_streaming = True
                else:
                    use_streaming = False
            except ImportError:
                use_streaming = False  # psutil not available, use normal mode
            
            self.log_info(f"Building {len(rows)} video frames ({frame_w}x{frame_h}) - using smooth interpolation to eliminate flickering...")
            self.log_info(f"Note: Applying Gaussian smoothing between rows + image enhancements...")
            if use_streaming:
                self.log_info(f"Mode: STREAMING (write frames directly to encoder, no buffering)")
            
            # Create progress tracker for real-time metrics
            class FrameProgressTracker:
                """Track frame building progress with real-time metrics"""
                def __init__(self, total_frames):
                    self.total = total_frames
                    self.completed = 0
                    self.failed = 0
                    self.start_time = time.time()
                    self.frame_times = []
                
                def update(self, frame_idx=None, success=True):
                    """Update progress with new completion"""
                    if success:
                        self.completed += 1
                    else:
                        self.failed += 1
                    
                    # Track frame processing time
                    elapsed = time.time() - self.start_time
                    self.frame_times.append(elapsed)
                    
                    return self.get_stats()
                
                def get_stats(self):
                    """Get current statistics"""
                    elapsed = time.time() - self.start_time
                    if self.completed > 0:
                        avg_frame_time = elapsed / self.completed
                        remaining_frames = self.total - self.completed
                        estimated_remaining = remaining_frames * avg_frame_time
                        fps = self.completed / max(elapsed, 0.001)
                    else:
                        avg_frame_time = 0
                        estimated_remaining = 0
                        fps = 0
                    
                    return {
                        'completed': self.completed,
                        'failed': self.failed,
                        'total': self.total,
                        'elapsed': elapsed,
                        'estimated_remaining': estimated_remaining,
                        'avg_frame_time': avg_frame_time,
                        'fps': fps,
                        'percent': (self.completed / max(self.total, 1)) * 100
                    }
                
                def log_progress(self, log_func):
                    """Log progress with pretty formatting"""
                    stats = self.get_stats()
                    percent = stats['percent']
                    completed = stats['completed']
                    total = stats['total']
                    fps = stats['fps']
                    remaining_sec = stats['estimated_remaining']
                    
                    # Format remaining time
                    if remaining_sec > 60:
                        remaining_str = f"{remaining_sec/60:.1f}m"
                    else:
                        remaining_str = f"{remaining_sec:.1f}s"
                    
                    # Progress bar
                    bar_width = 30
                    filled = int(bar_width * percent / 100)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    
                    log_func(
                        f"  Progress: [{bar}] {percent:5.1f}% "
                        f"({completed}/{total} frames, {fps:.1f} fps, ~{remaining_str} remaining)"
                    )
            
            progress_tracker = FrameProgressTracker(len(rows))
            
            # Use ThreadPoolExecutor for parallel frame building
            # Number of workers = CPU count (limited to 4-8 for memory efficiency)
            max_workers = min(multiprocessing.cpu_count(), 4)  # Reduced to 4 workers
            frames_dict = {}
            
            # ⚠️ MEMORY CRITICAL: Build frames but stream to encoder IMMEDIATELY to avoid OOM
            # Don't accumulate all frames in memory at once
            
            try:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Prepare frame data for parallel processing
                    frame_tasks = [
                        (i, rows, row_channels, frame_h, frame_w, color_scheme,
                         False, False, False,  # Tier 1 enhancements now in post-processing
                         self.cuda)
                        for i in range(len(rows))
                    ]
                    
                    # Submit all tasks
                    futures = {
                        executor.submit(build_single_frame, task): task[0]
                        for task in frame_tasks
                    }
                    
                    # Collect results as they complete
                    completed = 0
                    for future in as_completed(futures):
                        if self.cancel_requested:
                            self.log_warning("Video generation cancelled")
                            executor.shutdown(wait=False)
                            return None
                        
                        try:
                            frame_idx, img_rgb = future.result()
                            if img_rgb is not None:
                                frames_dict[frame_idx] = img_rgb
                                progress_tracker.update(frame_idx, success=True)
                            else:
                                progress_tracker.update(frame_idx, success=False)
                            completed += 1
                            
                            # Log detailed progress every 50 frames
                            if completed % 50 == 0:
                                progress_tracker.log_progress(self.log_info)
                        except Exception as e:
                            progress_tracker.update(frame_idx=futures[future], success=False)
                            self.log_warning(f"  Failed to build frame: {str(e)[:50]}")
                            completed += 1
                    
                    # Final progress report
                    stats = progress_tracker.get_stats()
                    self.log_success(
                        f"✓ Frame building complete: {stats['completed']}/{stats['total']} frames built "
                        f"({stats['failed']} failed) in {stats['elapsed']:.1f}s ({stats['fps']:.1f} fps)"
                    )
                
                # Sort frames by index to maintain order
                frames = [frames_dict[i] for i in sorted(frames_dict.keys()) if i in frames_dict]
                
                if not frames:
                    self.log_error("❌ No frames were successfully built")
                    return None
                
                self.log_success(f"✓ Collected {len(frames)} frames into memory (total {sum(f.nbytes for f in frames) / (1024**2):.1f}MB)")
                
            except Exception as e:
                self.log_warning(f"Parallel frame building failed, falling back to serial: {str(e)[:50]}")
                # Fall back to serial processing with tracking
                frames = []
                for i, _ in enumerate(rows):
                    if self.cancel_requested:
                        self.log_warning("Video generation cancelled")
                        return None
                    
                    start = max(0, i - frame_h + 1)
                    slab = rows[start:i+1]
                    
                    # Build image of height frame_h
                    img = np.zeros((frame_h, frame_w), dtype=np.uint8)
                    h = len(slab)
                    if h > 0:
                        stacked = np.vstack(slab).astype(np.float32)
                        
                        # Apply vertical smoothing to eliminate hard row boundaries
                        if h > 1:
                            from scipy.ndimage import gaussian_filter1d
                            stacked = gaussian_filter1d(stacked, sigma=0.5, axis=0)
                        
                        img[-h:, :] = np.clip(stacked, 0, 255).astype(np.uint8)
                    
                    # Apply enhancements
                    img = apply_sonar_enhancements(
                        img,
                        use_histogram=False,  # Tier 1 enhancements now in post-processing
                        use_morphology=False,
                        use_adaptive=False,
                        cuda_bridge=self.cuda
                    )
                    
                    # Determine if we need to mirror this row (channel 4 = port/left side)
                    current_channel = row_channels[i] if i < len(row_channels) else None
                    mirror = (current_channel == 4)
                    
                    # Apply colormap and optionally mirror
                    img_rgb = apply_colormap_to_image(img, colormap_name=color_scheme, mirror_horizontal=mirror)
                    frames.append(img_rgb)
                    
                    # Progress tracking and logging every 50 frames
                    progress_tracker.update(i, success=True)
                    if (i + 1) % 50 == 0:
                        progress_tracker.log_progress(self.log_info)
                
                # Final progress report
                stats = progress_tracker.get_stats()
                self.log_success(
                    f"✓ Frame building complete (serial fallback): {stats['completed']}/{stats['total']} frames "
                    f"in {stats['elapsed']:.1f}s"
                )
            
            self.log_success(f"✓ Built {len(frames)} video frames (enhanced, using parallel processing)")

            # Video encoding with professional FFmpeg encoder
            self.log_info("")
            self.log_header("Video Encoding (Professional)")
            
            try:
                from professional_video_encoder import encode_professional_video
                
                # Use FFmpeg with automatic GPU detection
                self.log_info(f"Using FFmpeg encoder with GPU acceleration detection...")
                
                success, output_file, elapsed = encode_professional_video(
                    frames=frames,
                    output_path=str(video_path),
                    fps=30,
                    bitrate='5000k',
                    use_gpu=True,
                    log_func=self.log_info
                )
                
                # Clear frames from memory
                frames.clear()
                del frames
                
                if success and Path(output_file).exists():
                    self.log_success(f"Video successfully encoded: {Path(output_file).name}")
                    return output_file
                else:
                    self.log_error(f"Video encoding failed")
                    return None
            
            except Exception as e:
                self.log_warning(f"Professional encoder error: {str(e)[:80]}, using fallback...")
                
                # Fallback to direct OpenCV encoding
                try:
                    import cv2
                    
                    self.log_info("Using fallback OpenCV encoder...")
                    
                    # Try MJPEG first (most reliable), then try others
                    codecs_to_try = [
                        ('MJPG', '.avi'),
                        ('DIVX', '.avi'),
                        ('XVID', '.avi'),
                    ]
                    
                    output_path = video_path
                    success = False
                    
                    for codec_code, ext in codecs_to_try:
                        try:
                            # Adjust file extension if needed
                            if output_path.suffix != ext:
                                output_path = output_path.with_suffix(ext)
                            
                            fourcc = cv2.VideoWriter_fourcc(*codec_code)
                            out = cv2.VideoWriter(str(output_path), fourcc, 30.0, (frame_w, frame_h))
                            
                            if not out.isOpened():
                                self.log_warning(f"Codec {codec_code} not available, trying next...")
                                continue
                            
                            self.log_info(f"Using codec: {codec_code}")
                            
                            # Encode all frames
                            for fidx, frame in enumerate(frames):
                                if self.cancel_requested:
                                    out.release()
                                    self.log_warning("Video encoding cancelled")
                                    return None
                                
                                # Convert to BGR
                                if len(frame.shape) == 2:
                                    frame_bgr = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_GRAY2BGR)
                                else:
                                    frame_bgr = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_RGB2BGR)
                                
                                out.write(frame_bgr)
                                
                                if (fidx + 1) % 100 == 0:
                                    self.log_info(f"  Wrote {fidx + 1}/{len(frames)} frames")
                            
                            out.release()
                            success = True
                            break
                        
                        except Exception as e:
                            self.log_warning(f"Codec {codec_code} failed: {str(e)[:50]}")
                            continue
                    
                    frames.clear()
                    
                    if success and output_path.exists():
                        file_size = output_path.stat().st_size / (1024 * 1024)
                        self.log_success(f"✓ Video encoded: {file_size:.1f}MB")
                        return str(output_path)
                    else:
                        self.log_error("❌ Video encoding failed with all available codecs")
                        return None
                
                except Exception as e:
                    self.log_error(f"❌ Fallback encoding error: {str(e)}")
                    import traceback
                    self.log_error(traceback.format_exc())
                    return None

        
        except Exception as e:
            self.log_error(f"Video generation error: {str(e)}")
            self.log_error(traceback.format_exc())
            return None
    
    def generate_georeferenced_mosaic(self, file_path, records_data, output_dir=None, color_scheme='jet'):
        """Generate georeferenced sonar mosaic images for KML/mbtiles overlay"""
        if not output_dir:
            output_dir = Path(file_path).parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        filename_stem = Path(file_path).stem
        
        try:
            self.log_info("")
            self.log_header("Generating Georeferenced Mosaic...")
            self.log_info(f"Processing {len(records_data)} records for mosaic")
            
            # Group records by channel
            channels = {}
            ch_has_sonar_mosaic = {}
            for rec in records_data:
                # Handle both 'ch' and 'channel_id' attribute names
                ch = getattr(rec, 'ch', None) or getattr(rec, 'channel_id', 0)
                if ch not in channels:
                    channels[ch] = []
                channels[ch].append(rec)
                
                # Track which channels have sonar data
                if hasattr(rec, 'sonar_size') and rec.sonar_size and rec.sonar_size > 0:
                    ch_has_sonar_mosaic[ch] = ch_has_sonar_mosaic.get(ch, 0) + 1
            
            self.log_info(f"Found {len(channels)} channel(s): {sorted(channels.keys())}")
            self.log_info(f"Channels with sonar data: {ch_has_sonar_mosaic}")
            
            mosaic_paths = {}
            rsd_file = Path(file_path)
            
            # Determine which channels to use for side-scan
            # Prefer channels 4/5 (standard side-scan), but fall back to any channel with sonar data
            side_scan_channels_mosaic = []
            if 4 in ch_has_sonar_mosaic or 5 in ch_has_sonar_mosaic:
                side_scan_channels_mosaic = [ch for ch in [4, 5] if ch in ch_has_sonar_mosaic]
                self.log_info(f"Using standard side-scan channels for mosaic: {side_scan_channels_mosaic}")
            else:
                # No data in channels 4/5, use whichever channel has sonar data
                side_scan_channels_mosaic = sorted([ch for ch in ch_has_sonar_mosaic.keys()])
                if side_scan_channels_mosaic:
                    self.log_warning(f"No data in channels 4/5, using channel(s) {side_scan_channels_mosaic} instead for mosaic")
            
            # Generate mosaic for each side-scan channel
            for ch, recs in sorted(channels.items()):
                # Skip non-side-scan channels
                if ch not in side_scan_channels_mosaic:
                    self.log_info(f"Skipping Channel {ch} (not selected for mosaic)")
                    continue
                
                if self.cancel_requested:
                    self.log_warning("Mosaic generation cancelled")
                    return None
                
                # Diagnostic: Check how many records have sonar data
                recs_with_sonar = sum(1 for r in recs if (hasattr(r, 'sonar_size') and r.sonar_size and r.sonar_size > 0 and
                                                           hasattr(r, 'sonar_ofs') and r.sonar_ofs is not None))
                self.log_info(f"\nProcessing Channel {ch}: {len(recs)} total records, {recs_with_sonar} with sonar data")

                
                # Extract sonar rows with GPS coordinates for georeferencing
                rows = []
                positions = []  # (lat, lon, depth)
                extracted_count = 0
                skipped_no_sonar = 0
                skipped_no_gps = 0
                skipped_read_error = 0
                
                # Open file for RSD records that need to be read from disk
                f = None
                try:
                    f = open(rsd_file, 'rb')
                except Exception as e:
                    self.log_warning(f"Could not open file for reading (will use embedded sonar data if available): {e}")
                
                # Process ALL records for this channel (not just first 600)
                for rec_idx, rec in enumerate(recs):
                    if not hasattr(rec, 'sonar_size') or not rec.sonar_size or rec.sonar_size <= 0:
                        skipped_no_sonar += 1
                        continue
                    if not hasattr(rec, 'lat') or not hasattr(rec, 'lon'):
                        skipped_no_gps += 1
                        continue
                    
                    try:
                        # Try to get sonar data from embedded source first (non-RSD formats)
                        if hasattr(rec, 'sonar_data') and rec.sonar_data:
                            data = rec.sonar_data if isinstance(rec.sonar_data, bytes) else bytes(rec.sonar_data)
                        # Fall back to reading from file offset (RSD format)
                        elif f and hasattr(rec, 'sonar_ofs') and rec.sonar_ofs is not None:
                            f.seek(rec.sonar_ofs)
                            data = f.read(rec.sonar_size)
                        else:
                            skipped_no_sonar += 1
                            continue
                        
                        if len(data) == 0:
                            skipped_read_error += 1
                            continue
                        
                        # Convert to uint8 array
                        arr = np.frombuffer(data, dtype=np.uint8)
                        
                        if arr.size == 0:
                            skipped_read_error += 1
                            continue
                        
                        # Resample to standard width
                        target_w = 1920
                        if arr.size < 16:
                            row = np.pad(arr, (0, max(0, target_w - arr.size)), constant_values=0).astype(np.uint8)
                        elif arr.size != target_w:
                            row = np.interp(np.linspace(0, arr.size-1, target_w), np.arange(arr.size), arr).astype(np.uint8)
                        else:
                            row = arr
                        
                        rows.append(row)
                        positions.append((rec.lat, rec.lon, getattr(rec, 'depth', 0)))
                        extracted_count += 1
                    
                    except Exception as e:
                        skipped_read_error += 1
                        continue
                
                # Close file if it was opened
                if f:
                    f.close()
                
                # Log extraction summary for this channel
                self.log_info(f"  Extraction summary for Channel {ch}:")
                self.log_info(f"    Extracted: {extracted_count} rows")
                self.log_info(f"    Skipped (no sonar data): {skipped_no_sonar}")
                self.log_info(f"    Skipped (no GPS): {skipped_no_gps}")
                self.log_info(f"    Skipped (read error): {skipped_read_error}")
                
                if not rows or not positions:
                    self.log_error(f"❌ No sonar data for channel {ch} - cannot create mosaic")
                    continue
                
                self.log_info(f"  Extracted {len(rows)} mosaic rows")
                
                # Stack rows into mosaic image
                img = np.vstack(rows).astype(np.uint8)
                h, w = img.shape
                
                # Tier 1 enhancements moved to post-processing dialog
                img = apply_sonar_enhancements(
                    img,
                    use_histogram=False,  # Disabled in main processing
                    use_morphology=False,
                    use_adaptive=False,
                    cuda_bridge=self.cuda
                )
                
                # Apply colormap and optionally mirror for channel 4 (port side)
                mirror = (ch == 4)
                img_rgb = apply_colormap_to_image(img, colormap_name=color_scheme, mirror_horizontal=mirror)
                
                # Calculate geographic bounds
                lats = [p[0] for p in positions]
                lons = [p[1] for p in positions]
                min_lat, max_lat = min(lats), max(lats)
                min_lon, max_lon = min(lons), max(lons)
                
                self.log_info(f"  Bounds: lat [{min_lat:.6f}, {max_lat:.6f}], lon [{min_lon:.6f}, {max_lon:.6f}]")
                self.log_info(f"  Image size: {w}x{h} pixels (enhanced)")

                
                # Save as GeoTIFF if available, otherwise PNG with world file
                try:
                    import rasterio
                    from rasterio.transform import from_bounds
                    
                    # Create GeoTIFF
                    mosaic_path = output_dir / f"{filename_stem}_ch{ch}_mosaic.tif"
                    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, w, h)
                    
                    with rasterio.open(
                        mosaic_path, 'w',
                        driver='GTiff',
                        height=h, width=w,
                        count=3, dtype=img_rgb.dtype,
                        transform=transform,
                        crs='EPSG:4326'
                    ) as dst:
                        dst.write(img_rgb[:,:,0], 1)
                        dst.write(img_rgb[:,:,1], 2)
                        dst.write(img_rgb[:,:,2], 3)
                    
                    self.log_success(f"✓ GeoTIFF mosaic: {mosaic_path.name}")
                    mosaic_paths[ch] = ('geotiff', str(mosaic_path))
                
                except ImportError:
                    # Fallback: Save PNG with world file
                    try:
                        import cv2
                        mosaic_path = output_dir / f"{filename_stem}_ch{ch}_mosaic.png"
                        cv2.imwrite(str(mosaic_path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
                        
                        # Write world file (.pgw)
                        world_path = output_dir / f"{filename_stem}_ch{ch}_mosaic.pgw"
                        pixel_width = (max_lon - min_lon) / w
                        pixel_height = (max_lat - min_lat) / h
                        
                        with open(world_path, 'w') as f:
                            f.write(f"{pixel_width}\n")
                            f.write("0\n")
                            f.write("0\n")
                            f.write(f"{-pixel_height}\n")
                            f.write(f"{min_lon}\n")
                            f.write(f"{max_lat}\n")
                        
                        self.log_success(f"✓ PNG mosaic + world file: {mosaic_path.name}")
                        mosaic_paths[ch] = ('png', str(mosaic_path), str(world_path), (min_lat, max_lat, min_lon, max_lon))
                    
                    except Exception as e:
                        self.log_error(f"PNG export failed: {str(e)}")
                        continue
            
            if not mosaic_paths:
                self.log_warning("No mosaic images generated")
                return None
            
            self.log_success(f"✓ Generated {len(mosaic_paths)} mosaic image(s)")
            return mosaic_paths
        
        except Exception as e:
            self.log_error(f"Mosaic generation error: {str(e)}")
            self.log_error(traceback.format_exc())
            return None
    
    def show_post_processing(self):
        """Show post-processing dialog for geospatial exports"""
        if not hasattr(self, 'last_results') or not self.last_results:
            messagebox.showwarning("No Data", "Please process a file first")
            return
        
        records = self.last_results.get('records', [])
        if not records:
            messagebox.showwarning("No Data", "No records available for post-processing")
            return
        
        # Convert records to dictionaries if needed
        records_list = []
        for rec in records:
            if isinstance(rec, dict):
                records_list.append(rec)
            else:
                # Convert object to dictionary
                rec_dict = {}
                # Map common attribute names (lat/lon from RSDRecord, latitude/longitude alternatives)
                for attr_pair in [('latitude', 'lat'), ('longitude', 'lon'), ('depth', 'depth_m'), 
                                  ('timestamp', 'offset'), ('confidence', 'conf'), ('channel', 'ch'), 
                                  ('frequency', 'freq')]:
                    for attr_name in attr_pair:
                        if hasattr(rec, attr_name):
                            rec_dict[attr_pair[0]] = getattr(rec, attr_name)
                            break
                # Also preserve the original attribute names in case post-processing needs them
                for attr in ['lat', 'lon', 'depth_m', 'beam_deg', 'pitch_deg', 'roll_deg', 'heave_m', 'tx_ofs_m', 'rx_ofs_m']:
                    if hasattr(rec, attr) and attr not in rec_dict.values():
                        rec_dict[attr] = getattr(rec, attr)
                records_list.append(rec_dict)
        
        # Import post-processing dialog
        try:
            from post_processing_dialog import PostProcessingDialog
            
            def on_export_complete(results):
                """Callback when post-processing completes"""
                self.log_success("✓ Post-processing complete!")
                for fmt, path in results.items():
                    self.log_info(f"  {fmt.upper()}: {path.name}")
            
            # Get current output directory and pass it to post-processing
            output_dir = self.output_dir.get().strip() or str(Path.home() / "SonarSniffer_Output")
            
            # Show dialog
            dialog = PostProcessingDialog(self.root, records_list, on_export_complete, output_dir=output_dir)
            
        except ImportError as e:
            messagebox.showerror("Import Error", 
                               f"Could not load post-processing module:\n{str(e)}\n\n"
                               "Make sure geospatial_exporter.py and post_processing_dialog.py are in the same directory")
    
    def export_csv(self, default_name):
        """Export results to CSV"""
        output_dir = self.output_dir.get().strip() or str(Path.home())
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = filedialog.asksaveasfilename(
            title="Save Results As CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile=f"{default_name}.csv",
            initialdir=output_dir
        )
        
        if not filename:
            return
        
        try:
            import csv
            results = self.last_results
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header with metadata
                writer.writerow(['SonarSniffer Processing Report - CSV Export'])
                writer.writerow([''])
                writer.writerow(['Processing Metadata'])
                writer.writerow(['Filename', results['filename']])
                writer.writerow(['File Path', results['file_path']])
                writer.writerow(['Processing Time (s)', f"{results['processing_time']:.3f}"])
                writer.writerow(['Total Records', results['record_count']])
                writer.writerow(['File Size (bytes)', results['file_size']])
                writer.writerow(['Timestamp', results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([''])
                
                # Processing options
                writer.writerow(['Processing Options'])
                writer.writerow(['Color Scheme', results.get('color_scheme', 'N/A')])
                writer.writerow(['Include Video', results.get('include_video', 'N/A')])
                writer.writerow(['Include Waterfall', results.get('include_waterfall', 'N/A')])
                writer.writerow(['Normalize Depth', results.get('normalize_depth', 'N/A')])
                writer.writerow(['Generate KML', results.get('include_kml', 'N/A')])
                writer.writerow([''])
                writer.writerow(['Records Data'])
                
                # Write records
                if results['records']:
                    writer.writerow(['Record Number', 'Data', 'Channel', 'Depth', 'Latitude', 'Longitude'])
                    for i, record in enumerate(results['records'], 1):
                        ch = getattr(record, 'ch', 'N/A')
                        depth = getattr(record, 'depth', 'N/A')
                        lat = getattr(record, 'lat', 'N/A')
                        lon = getattr(record, 'lon', 'N/A')
                        writer.writerow([i, str(record), ch, depth, lat, lon])
            
            self.log_success(f"✓ CSV exported to: {filename}")
            messagebox.showinfo("Export Successful", f"CSV saved to:\n{filename}")
            
        except Exception as e:
            self.log_error(f"CSV export failed: {str(e)}")
            messagebox.showerror("Export Error", str(e))
    
    def export_json(self, default_name):
        """Export results to JSON"""
        output_dir = self.output_dir.get().strip() or str(Path.home())
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = filedialog.asksaveasfilename(
            title="Save Results As JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile=f"{default_name}.json",
            initialdir=output_dir
        )
        
        if not filename:
            return
        
        try:
            import json
            results = self.last_results
            
            # Prepare JSON structure
            json_data = {
                'metadata': {
                    'filename': results['filename'],
                    'file_path': results['file_path'],
                    'processing_time': results['processing_time'],
                    'total_records': results['record_count'],
                    'file_size': results['file_size'],
                    'timestamp': results['timestamp'].isoformat()
                },
                'options': {
                    'color_scheme': results.get('color_scheme', 'N/A'),
                    'include_video': results.get('include_video', False),
                    'include_waterfall': results.get('include_waterfall', False),
                    'normalize_depth': results.get('normalize_depth', False),
                    'include_kml': results.get('include_kml', False)
                },
                'records': [str(rec) for rec in results['records'][:100]]  # First 100 records
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
            
            self.log_success(f"✓ JSON exported to: {filename}")
            messagebox.showinfo("Export Successful", f"JSON saved to:\n{filename}")
            
        except Exception as e:
            self.log_error(f"JSON export failed: {str(e)}")
            messagebox.showerror("Export Error", str(e))
    
    def export_kml(self, default_name):
        """Export results to KML (Google Earth format) with mosaic overlays"""
        if not self.last_results.get('include_kml', False):
            messagebox.showwarning("KML Disabled", "KML generation was not enabled in processing options")
            return
        
        output_dir = self.output_dir.get().strip() or str(Path.home())
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = filedialog.asksaveasfilename(
            title="Save Results As KML",
            defaultextension=".kml",
            filetypes=[("KML Files", "*.kml"), ("All Files", "*.*")],
            initialfile=f"{default_name}.kml",
            initialdir=output_dir
        )
        
        if not filename:
            return
        
        try:
            results = self.last_results
            
            # Create KML structure
            kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>SonarSniffer Sonar Data</name>
    <description>Exported from {}</description>
    <Style id="sonar_style">
      <IconStyle>
        <scale>0.6</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/ms/icons/blue-dot.png</href>
        </Icon>
      </IconStyle>
    </Style>
'''.format(results['filename'])
            
            # Add mosaic overlays if available
            mosaic_paths = results.get('mosaic_paths')
            if mosaic_paths:
                kml_content += '  <Folder>\n    <name>Sonar Mosaic Overlays</name>\n'
                
                for ch, mosaic_info in sorted(mosaic_paths.items()):
                    if mosaic_info[0] == 'png':
                        # PNG + world file format
                        mosaic_path = mosaic_info[1]
                        bounds = mosaic_info[3]  # (min_lat, max_lat, min_lon, max_lon)
                        min_lat, max_lat, min_lon, max_lon = bounds
                        
                        # Use relative path if same directory
                        mosaic_file = Path(mosaic_path).name
                        
                        kml_content += f'''    <GroundOverlay>
      <name>Channel {ch} Sonar Mosaic</name>
      <description>Sidescan sonar mosaic for channel {ch}</description>
      <Icon>
        <href>{mosaic_file}</href>
      </Icon>
      <LatLonBox>
        <north>{max_lat}</north>
        <south>{min_lat}</south>
        <east>{max_lon}</east>
        <west>{min_lon}</west>
      </LatLonBox>
    </GroundOverlay>
'''
                    elif mosaic_info[0] == 'geotiff':
                        # GeoTIFF format
                        mosaic_path = mosaic_info[1]
                        mosaic_file = Path(mosaic_path).name
                        
                        kml_content += f'''    <GroundOverlay>
      <name>Channel {ch} Sonar Mosaic (GeoTIFF)</name>
      <description>Georeferenced sidescan sonar mosaic for channel {ch}</description>
      <Icon>
        <href>{mosaic_file}</href>
      </Icon>
    </GroundOverlay>
'''
                
                kml_content += '  </Folder>\n'
            
            # Add track points folder
            kml_content += '  <Folder>\n    <name>Sonar Track Points</name>\n'
            
            # Add placemarks for records with coordinates
            for i, record in enumerate(results['records'][:1000], 1):  # Limit to 1000 for performance
                if hasattr(record, 'lat') and hasattr(record, 'lon'):
                    depth = getattr(record, 'depth', 0)
                    ch = getattr(record, 'ch', 0)
                    kml_content += f'''    <Placemark>
      <name>Record {i}</name>
      <description>Channel: {ch}, Depth: {depth:.3f}m</description>
      <styleUrl>#sonar_style</styleUrl>
      <Point>
        <coordinates>{record.lon},{record.lat},0</coordinates>
      </Point>
    </Placemark>
'''
            
            kml_content += '''  </Folder>
  </Document>
</kml>'''
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(kml_content)
            
            # Copy mosaic files to same directory if PNG format
            if mosaic_paths:
                for ch, mosaic_info in sorted(mosaic_paths.items()):
                    if mosaic_info[0] == 'png':
                        import shutil
                        mosaic_path = Path(mosaic_info[1])
                        world_path = Path(mosaic_info[2])
                        dest_dir = Path(filename).parent
                        
                        # Copy mosaic and world file
                        shutil.copy2(mosaic_path, dest_dir / mosaic_path.name)
                        shutil.copy2(world_path, dest_dir / world_path.name)
            
            self.log_success(f"✓ KML exported to: {filename}")
            msg = f"KML saved to:\n{filename}\nOpen in Google Earth Pro"
            if mosaic_paths:
                msg += f"\n\nIncludes {len(mosaic_paths)} sonar mosaic overlay(s)"
            messagebox.showinfo("Export Successful", msg)
            
        except Exception as e:
            self.log_error(f"KML export failed: {str(e)}")
            messagebox.showerror("Export Error", str(e))
    
    def export_mbtiles(self, default_name):
        """Export results as mbtiles with interactive Leaflet.js viewer"""
        output_dir = self.output_dir.get().strip() or str(Path.home())
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        filename = filedialog.asksaveasfilename(
            title="Save Results As MBTiles Map",
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")],
            initialfile=f"{default_name}_map.html",
            initialdir=output_dir
        )
        
        if not filename:
            return
        
        try:
            import json
            results = self.last_results
            records = results['records']
            
            # Filter records with GPS coordinates
            valid_records = [r for r in records if hasattr(r, 'lat') and hasattr(r, 'lon')]
            
            if not valid_records:
                self.log_warning("No records with GPS coordinates found for mbtiles export")
                messagebox.showwarning("No GPS Data", "No records with GPS coordinates found")
                return
            
            # Calculate bounds
            lats = [r.lat for r in valid_records if hasattr(r, 'lat')]
            lons = [r.lon for r in valid_records if hasattr(r, 'lon')]
            
            if not lats or not lons:
                messagebox.showwarning("No GPS Data", "Cannot determine map bounds")
                return
            
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            
            # Prepare marker data
            markers = []
            for i, record in enumerate(valid_records[:500]):  # Limit to 500 for performance
                depth = getattr(record, 'depth', 0)
                ch = getattr(record, 'ch', 0)
                temp = getattr(record, 'temp', 0)
                
                # Color based on depth (gradient)
                if depth > 100:
                    color = '#d62728'  # red
                elif depth > 50:
                    color = '#ff7f0e'  # orange
                elif depth > 20:
                    color = '#ffdd57'  # yellow
                else:
                    color = '#2ca02c'  # green
                
                markers.append({
                    'lat': record.lat,
                    'lon': record.lon,
                    'depth': round(depth, 2),
                    'channel': int(ch),
                    'temp': round(temp, 1),
                    'color': color
                })
            
            # Create HTML with Leaflet.js
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SonarSniffer Map - {results['filename']}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: #f0f0f0; }}
        #map {{ height: 100vh; width: 100%; }}
        .info {{ 
            padding: 6px 8px; 
            background: white; 
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            line-height: 18px;
            color: #555;
        }}
        .info h4 {{ margin: 0 0 5px 0; color: #333; }}
        .legend {{
            background: white;
            border-radius: 5px;
            padding: 10px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            line-height: 18px;
            color: #555;
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.7;
            border-radius: 50%;
        }}
        .controls {{
            position: fixed;
            top: 10px;
            left: 50px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            z-index: 1000;
            max-width: 300px;
        }}
        .controls h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #333; }}
        .stat {{ font-size: 12px; color: #666; margin: 2px 0; }}
        .stat-value {{ font-weight: bold; color: #333; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="controls">
        <h3>📊 Map Info</h3>
        <div class="stat">File: <span class="stat-value">{results['filename']}</span></div>
        <div class="stat">Records: <span class="stat-value">{len(valid_records)}</span></div>
        <div class="stat">Bounds: <span class="stat-value">{min_lat:.4f}°, {min_lon:.4f}°</span></div>
        <div class="stat">Color Scheme: <span class="stat-value">{results.get('color_scheme', 'Default')}</span></div>
    </div>
    
    <script>
        // Initialize map
        var map = L.map('map').setView([{center_lat}, {center_lon}], 12);
        
        // Add base layers
        var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }});
        
        // NOAA Nautical Charts (raster tiles)
        var noaa = L.tileLayer('https://tileservice.charts.noaa.gov/tiles/raster/oct/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© NOAA Charts',
            maxZoom: 16
        }});
        
        // GEBCO Bathymetry (optional)
        var gebco = L.tileLayer('https://www.gebco.net/data_and_products/gridded_bathymetry_data/gebco_2023/gebco_2023_n90.0_s-90.0_w-180.0_e180.0_bedrock.tid/GEBCO_2023.tid/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© GEBCO',
            maxZoom: 15
        }});
        
        osm.addTo(map);
        
        var baseMaps = {{
            "OpenStreetMap": osm,
            "NOAA Charts": noaa
        }};
        
        // Add sonar mosaic overlays if available
        var overlayMaps = {{}};
        var mosaic_paths = {json.dumps({str(ch): path[1] for ch, path in (results.get('mosaic_paths', {}).items() if results.get('mosaic_paths') else [])} if results.get('mosaic_paths') else {})};
        
        for (var ch in mosaic_paths) {{
            var mosaic_url = mosaic_paths[ch];
            if (mosaic_url.endsWith('.png')) {{
                // PNG with world file - use ImageOverlay
                overlayMaps['Sonar Mosaic Ch' + ch] = L.imageOverlay(mosaic_url, [[{min_lat}, {min_lon}], [{max_lat}, {max_lon}]], {{opacity: 0.7}});
            }} else {{
                // GeoTIFF - would need special handling
                overlayMaps['Sonar Mosaic Ch' + ch + ' (GeoTIFF)'] = L.tileLayer(mosaic_url, {{opacity: 0.7}});
            }}
        }}
        
        var layerControl = L.control.layers(baseMaps, overlayMaps, {{position: 'topright'}});
        layerControl.addTo(map);
        
        // Add markers
        var markers = {json.dumps(markers)};
        
        markers.forEach(function(marker, index) {{
            var circle = L.circleMarker([marker.lat, marker.lon], {{
                radius: 5,
                fillColor: marker.color,
                color: '#333',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.7
            }});
            
            var popup = '<strong>Record ' + (index + 1) + '</strong><br/>' +
                        'Depth: ' + marker.depth + 'm<br/>' +
                        'Channel: ' + marker.channel + '<br/>' +
                        'Temp: ' + marker.temp + '°C<br/>' +
                        'Lat: ' + marker.lat.toFixed(4) + '°<br/>' +
                        'Lon: ' + marker.lon.toFixed(4) + '°';
            
            circle.bindPopup(popup);
            circle.addTo(map);
        }});
        
        // Fit bounds
        if (markers.length > 0) {{
            var group = new L.featureGroup();
            markers.forEach(function(m) {{
                group.addLayer(L.circleMarker([m.lat, m.lon], {{radius: 1}}));
            }});
            map.fitBounds(group.getBounds(), {{padding: [50, 50]}});
        }}
        
        // Legend
        var legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function(map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML += '<i style="background: #2ca02c"></i> Shallow (&lt;20m)<br/>';
            div.innerHTML += '<i style="background: #ffdd57"></i> Moderate (20-50m)<br/>';
            div.innerHTML += '<i style="background: #ff7f0e"></i> Deep (50-100m)<br/>';
            div.innerHTML += '<i style="background: #d62728"></i> Very Deep (&gt;100m)';
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>'''
            
            # Write HTML file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.log_success(f"✓ MBTiles map exported to: {filename}")
            self.log_info(f"📍 Map contains {len(markers)} sonar markers with NOAA chart overlay")
            
            # Auto-launch if enabled
            if self.auto_launch_map.get():
                import webbrowser
                webbrowser.open('file://' + os.path.abspath(filename))
                self.log_success("✓ Map opened in default browser")
            
            messagebox.showinfo("Export Successful", 
                              f"Interactive map saved to:\n{filename}\n\n"
                              f"Markers: {len(markers)}\n"
                              f"Map includes NOAA nautical charts")
            
        except Exception as e:
            self.log_error(f"MBTiles export failed: {str(e)}")
            messagebox.showerror("Export Error", str(e))
    
    def export_all(self, default_name):
        """Export to all formats"""
        output_dir = self.output_dir.get().strip() or str(Path.home())
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        folder = filedialog.askdirectory(
            title="Select folder to save all formats",
            initialdir=output_dir
        )
        if not folder:
            return
        
        try:
            # Temporarily change export format and export each
            self.log_info(f"Exporting to all formats in: {folder}")
            
            # CSV
            csv_file = os.path.join(folder, f"{default_name}.csv")
            self._export_to_file('csv', csv_file)
            
            # JSON
            json_file = os.path.join(folder, f"{default_name}.json")
            self._export_to_file('json', json_file)
            
            # KML
            kml_file = os.path.join(folder, f"{default_name}.kml")
            self._export_to_file('kml', kml_file)
            
            # MBTiles (interactive map)
            if self.last_results.get('include_mbtiles', False):
                mbtiles_file = os.path.join(folder, f"{default_name}_map.html")
                self._export_to_file('mbtiles', mbtiles_file)
            
            self.log_success(f"✓ All formats exported to: {folder}")
            messagebox.showinfo("Export Successful", f"All formats saved to:\n{folder}")
            
        except Exception as e:
            self.log_error(f"Multi-format export failed: {str(e)}")
            messagebox.showerror("Export Error", str(e))
    
    def _export_csv_auto(self, records_data, output_dir, file_stem, file_path):
        """Auto-export results to CSV without file dialog"""
        filepath = Path(output_dir) / f"{file_stem}_results.csv"
        
        try:
            import csv
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header with metadata
                writer.writerow(['SonarSniffer Processing Report - CSV Export'])
                writer.writerow([''])
                writer.writerow(['Processing Metadata'])
                writer.writerow(['Filename', Path(file_path).name])
                writer.writerow(['File Path', file_path])
                writer.writerow(['Processing Time (s)', f"{self.last_results['processing_time']:.3f}"])
                writer.writerow(['Total Records', self.last_results['record_count']])
                writer.writerow(['File Size (bytes)', self.last_results['file_size']])
                writer.writerow(['Timestamp', self.last_results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([''])
                
                # Processing options
                writer.writerow(['Processing Options'])
                writer.writerow(['Color Scheme', self.last_results.get('color_scheme', 'N/A')])
                writer.writerow(['Include Video', self.last_results.get('include_video', 'N/A')])
                writer.writerow(['Include Waterfall', self.last_results.get('include_waterfall', 'N/A')])
                writer.writerow(['Normalize Depth', self.last_results.get('normalize_depth', 'N/A')])
                writer.writerow(['Generate KML', self.last_results.get('include_kml', 'N/A')])
                writer.writerow([''])
                writer.writerow(['Records Data'])
                
                # Write records
                if records_data:
                    writer.writerow(['Record Number', 'Data', 'Channel', 'Depth', 'Latitude', 'Longitude'])
                    for i, record in enumerate(records_data, 1):
                        ch = getattr(record, 'ch', getattr(record, 'channel_id', 'N/A'))
                        depth = getattr(record, 'depth', getattr(record, 'depth_m', 'N/A'))
                        lat = getattr(record, 'lat', 'N/A')
                        lon = getattr(record, 'lon', 'N/A')
                        writer.writerow([i, str(record), ch, depth, lat, lon])
            
            self.log_success(f"✓ CSV exported to: {filepath}")
            
        except Exception as e:
            self.log_error(f"CSV export failed: {str(e)}")
    
    def _export_json_auto(self, records_data, output_dir, file_stem, file_path):
        """Auto-export results to JSON without file dialog"""
        filepath = Path(output_dir) / f"{file_stem}_results.json"
        
        try:
            import json
            
            data = {
                'metadata': {
                    'filename': Path(file_path).name,
                    'file_path': file_path,
                    'processing_time_seconds': self.last_results['processing_time'],
                    'total_records': self.last_results['record_count'],
                    'file_size_bytes': self.last_results['file_size'],
                    'timestamp': self.last_results['timestamp'].isoformat(),
                },
                'options': {
                    'color_scheme': self.last_results.get('color_scheme', 'N/A'),
                    'include_video': self.last_results.get('include_video', False),
                    'include_waterfall': self.last_results.get('include_waterfall', False),
                    'normalize_depth': self.last_results.get('normalize_depth', False),
                    'include_kml': self.last_results.get('include_kml', False),
                },
                'records': []
            }
            
            # Convert records to JSON-serializable format
            for i, record in enumerate(records_data, 1):
                ch = getattr(record, 'ch', getattr(record, 'channel_id', None))
                depth = getattr(record, 'depth', getattr(record, 'depth_m', None))
                lat = getattr(record, 'lat', None)
                lon = getattr(record, 'lon', None)
                
                data['records'].append({
                    'index': i,
                    'channel': ch,
                    'depth': depth,
                    'latitude': lat,
                    'longitude': lon,
                })
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.log_success(f"✓ JSON exported to: {filepath}")
            
        except Exception as e:
            self.log_error(f"JSON export failed: {str(e)}")
    
    def _export_kml_auto(self, records_data, mosaic_paths, output_dir, file_stem):
        """Auto-export KML trackline without file dialog (vessel path and overlays)"""
        try:
            import simplekml
            
            self.log_info("Generating KML trackline (vessel path and mosaic overlays)...")
            
            kml = simplekml.Kml()
            
            # Add folder for data points
            data_folder = kml.newfolder(name="Data Points")
            
            # Add each record as a point
            for i, record in enumerate(records_data, 1):
                lat = getattr(record, 'lat', None)
                lon = getattr(record, 'lon', None)
                depth = getattr(record, 'depth', getattr(record, 'depth_m', None))
                ch = getattr(record, 'ch', getattr(record, 'channel_id', None))
                
                if lat and lon:
                    point = data_folder.newpoint(name=f"Record {i}", coords=[(lon, lat)])
                    point.description = f"Channel: {ch}, Depth: {depth}m"
            
            # Add folder for mosaic overlays if available
            if mosaic_paths:
                overlay_folder = kml.newfolder(name="Mosaic Overlays")
                
                # mosaic_paths is a dict {channel: (format, path, world_path, bounds)}
                for ch, mosaic_info in mosaic_paths.items():
                    try:
                        if isinstance(mosaic_info, tuple) and len(mosaic_info) >= 2:
                            mosaic_path = mosaic_info[1]  # Get the actual path
                        else:
                            mosaic_path = str(mosaic_info)
                        
                        if Path(mosaic_path).exists():
                            overlay_name = f"Channel {ch} Mosaic"
                            ground_overlay = overlay_folder.newgroundoverlay(name=overlay_name)
                            ground_overlay.icon.href = f"file:///{mosaic_path}"
                    except Exception as e:
                        self.log_warning(f"Could not add mosaic overlay for channel {ch}: {e}")
                        continue
            
            filepath = Path(output_dir) / f"{file_stem}_trackline.kml"
            kml.save(str(filepath))
            
            self.log_success(f"✓ KML Trackline exported to: {filepath}")
            self.log_info("  TIP: For bathymetric KML with depth contours, use the Post-Processing dialog")
            
        except ImportError:
            self.log_error("KML export requires 'simplekml' package")
        except Exception as e:
            self.log_error(f"KML export failed: {str(e)}")
            self.log_error(traceback.format_exc())
    
    def _export_mbtiles_auto(self, records_data, mosaic_paths, output_dir, file_stem):
        """Auto-export MBTiles without file dialog"""
        try:
            import sqlite3
            from PIL import Image
            import numpy as np
            
            filepath = Path(output_dir) / f"{file_stem}_tiles.mbtiles"
            
            # Create MBTiles database
            conn = sqlite3.connect(str(filepath))
            cursor = conn.cursor()
            
            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    name TEXT,
                    value TEXT
                )
            ''')
            
            # Insert metadata
            metadata = [
                ('name', f'Sonar {file_stem}'),
                ('format', 'png'),
                ('minzoom', '0'),
                ('maxzoom', '14'),
                ('bounds', '-180,-85,180,85'),
                ('type', 'overlay'),
            ]
            
            cursor.executemany('INSERT INTO metadata VALUES (?, ?)', metadata)
            
            # Create tiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tiles (
                    zoom_level INTEGER,
                    tile_column INTEGER,
                    tile_row INTEGER,
                    tile_data BLOB
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.log_success(f"✓ MBTiles exported to: {filepath}")
            
            # Create HTML viewer
            html_filepath = Path(output_dir) / f"{file_stem}_map.html"
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sonar Map - {file_stem}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ height: 100%; margin: 0; padding: 0; }}
        #map {{ height: 100%; }}
        .info {{ padding: 6px 8px; font: 14px/16px Arial, Helvetica, sans-serif; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map('map').setView([0, 0], 2);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Add sonar points
        const sonarData = {records_data[:100]};  // Show first 100 records
        sonarData.forEach((rec, idx) => {{
            if (rec.latitude && rec.longitude) {{
                L.circleMarker([rec.latitude, rec.longitude], {{
                    radius: 3,
                    fillColor: '#3388ff',
                    color: '#000',
                    weight: 0.5,
                    opacity: 1,
                    fillOpacity: 0.8
                }}).addTo(map).bindPopup(`Record ${{idx + 1}}<br/>Depth: ${{rec.depth}}m<br/>Channel: ${{rec.channel}}`);
            }}
        }});
    </script>
</body>
</html>
"""
            
            with open(html_filepath, 'w') as f:
                f.write(html_content)
            
            self.log_success(f"✓ Web map created: {html_filepath}")
            
        except Exception as e:
            self.log_error(f"MBTiles export failed: {str(e)}")
    
    def _export_to_file(self, format_type, filepath):
        """Helper to export to specific file"""
        if format_type == 'csv':
            self.export_csv(os.path.splitext(filepath)[0])
        elif format_type == 'json':
            self.export_json(os.path.splitext(filepath)[0])
        elif format_type == 'kml':
            self.export_kml(os.path.splitext(filepath)[0])
        elif format_type == 'mbtiles':
            self.export_mbtiles(os.path.splitext(filepath)[0])


def main():
    root = tk.Tk()
    app = SonarGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
