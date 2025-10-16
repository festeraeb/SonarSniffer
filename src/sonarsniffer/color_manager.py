#!/usr/bin/env python3
"""Color management and visualization tools for RSD Studio."""
from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass

@dataclass
class ColorStop:
    position: int
    color: str

class ColorManager:
    """Handles color maps and real-time visualization."""
    
    def __init__(self):
        self._luts: Dict[str, np.ndarray] = {}
        self._init_colormaps()
    
    def _hex2rgb(self, h: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    
    def _create_colormap(self, stops: List[ColorStop]) -> np.ndarray:
        """Create a colormap from stops."""
        lut = np.zeros((256, 3), np.uint8)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i].position, stops[i].color
            p1, c1 = stops[i + 1].position, stops[i + 1].color
            
            r0, g0, b0 = self._hex2rgb(c0)
            r1, g1, b1 = self._hex2rgb(c1)
            
            span = max(1, p1 - p0)
            t = np.linspace(0, 1, span, endpoint=False, dtype=np.float32)
            
            lut[p0:p1, 0] = (r0 + (r1 - r0) * t).astype(np.uint8)
            lut[p0:p1, 1] = (g0 + (g1 - g0) * t).astype(np.uint8)
            lut[p0:p1, 2] = (b0 + (b1 - b0) * t).astype(np.uint8)
        
        # Fill remaining range with last color
        last = stops[-1]
        lut[last.position:] = np.array(self._hex2rgb(last.color), np.uint8)
        return lut
    
    def _init_colormaps(self):
        """Initialize built-in colormaps."""
        colormaps = {
            "grayscale": [
                ColorStop(0, "#000000"),
                ColorStop(255, "#ffffff")
            ],
            "amber": [
                ColorStop(0, "#000000"),
                ColorStop(40, "#2b1b00"),
                ColorStop(96, "#7a3e00"),
                ColorStop(180, "#f6a400"),
                ColorStop(255, "#fff5cc")
            ],
            "copper": [
                ColorStop(0, "#000000"),
                ColorStop(48, "#1a0e06"),
                ColorStop(110, "#5a2e15"),
                ColorStop(190, "#b36b2c"),
                ColorStop(255, "#ffd29c")
            ],
            "blue": [
                ColorStop(0, "#000000"),
                ColorStop(64, "#001a33"),
                ColorStop(140, "#004c99"),
                ColorStop(210, "#33aaff"),
                ColorStop(255, "#d6f0ff")
            ],
            "ice": [
                ColorStop(0, "#000000"),
                ColorStop(64, "#001a33"),
                ColorStop(170, "#66b2ff"),
                ColorStop(255, "#ffffff")
            ],
            "purple": [
                ColorStop(0, "#000000"),
                ColorStop(64, "#1a0033"),
                ColorStop(150, "#5a00a3"),
                ColorStop(210, "#c084ff"),
                ColorStop(255, "#ffe6ff")
            ],
            "fire": [
                ColorStop(0, "#000000"),
                ColorStop(50, "#330000"),
                ColorStop(120, "#990000"),
                ColorStop(200, "#ff6600"),
                ColorStop(255, "#ffff66")
            ],
            "viridis": [
                ColorStop(0, "#440154"),
                ColorStop(80, "#3b528b"),
                ColorStop(140, "#21918c"),
                ColorStop(200, "#5ec962"),
                ColorStop(255, "#fde725")
            ],
            "magma": [
                ColorStop(0, "#000004"),
                ColorStop(90, "#3b0f70"),
                ColorStop(150, "#8c2981"),
                ColorStop(200, "#de4968"),
                ColorStop(235, "#fca636"),
                ColorStop(255, "#fcfdbf")
            ],
            "inferno": [
                ColorStop(0, "#000004"),
                ColorStop(70, "#1f0c48"),
                ColorStop(135, "#5c1e76"),
                ColorStop(190, "#b63679"),
                ColorStop(225, "#ee7b51"),
                ColorStop(255, "#f6d746")
            ],
            # Add scientific colormaps
            "bathymetry": [
                ColorStop(0, "#000033"),
                ColorStop(64, "#000099"),
                ColorStop(128, "#0066cc"),
                ColorStop(192, "#00ffff"),
                ColorStop(255, "#ffffff")
            ],
            "depth": [
                ColorStop(0, "#08306b"),
                ColorStop(85, "#08519c"),
                ColorStop(170, "#2171b5"),
                ColorStop(255, "#4292c6")
            ]
        }
        
        for name, stops in colormaps.items():
            self._luts[name.lower()] = self._create_colormap(stops)
    
    def apply(self, data: np.ndarray, colormap: str = "grayscale") -> np.ndarray:
        """Apply colormap to data. Returns RGB uint8 array."""
        if data.ndim == 3 and data.shape[2] == 3:
            return data
            
        # Normalize float data to 0-255 range
        if data.dtype != np.uint8:
            data_f = data.astype(np.float32)
            mn, mx = np.nanmin(data_f), np.nanmax(data_f)
            if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
                data_f = np.clip(data_f, 0, 1)
            else:
                data_f = np.clip((data_f - mn) / (mx - mn), 0, 1)
            data = (data_f * 255 + 0.5).astype(np.uint8)
        
        # Apply colormap
        lut = self._luts.get(colormap.lower(), self._luts["grayscale"])
        return lut[data]
    
    def get_colormap_names(self) -> List[str]:
        """Get list of available colormap names."""
        return sorted(self._luts.keys())
    
    def add_colormap(self, name: str, stops: List[ColorStop]):
        """Add a custom colormap."""
        self._luts[name.lower()] = self._create_colormap(stops)