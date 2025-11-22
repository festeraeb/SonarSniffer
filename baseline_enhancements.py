#!/usr/bin/env python3
"""
Baseline Enhancements - Applied during raw data processing
These are the "always-on" best-practice enhancements for sonar images
"""

import numpy as np
from PIL import Image
import cv2
from typing import Optional, Tuple


class BaselineEnhancer:
    """Applies baseline enhancements during data processing"""
    
    def __init__(self):
        """Initialize baseline enhancer"""
        pass
    
    @staticmethod
    def apply_baseline_enhancements(sonar_frame: np.ndarray) -> np.ndarray:
        """
        Apply baseline enhancements to sonar frame
        Includes: contrast stretching, adaptive filtering, edge enhancement
        
        Args:
            sonar_frame: Input sonar image (grayscale or RGB)
            
        Returns:
            Enhanced sonar image
        """
        # Convert to grayscale if RGB
        if len(sonar_frame.shape) == 3:
            gray = cv2.cvtColor(sonar_frame, cv2.COLOR_RGB2GRAY)
        else:
            gray = sonar_frame.copy()
        
        # 1. Contrast stretching (best-all-around for sonar)
        gray = BaselineEnhancer._contrast_stretch(gray)
        
        # 2. Adaptive histogram equalization for local contrast
        gray = BaselineEnhancer._adaptive_contrast(gray)
        
        # 3. Gentle edge enhancement for target visibility
        gray = BaselineEnhancer._edge_enhance(gray, strength=0.3)
        
        # 4. Noise reduction (light bilateral filter)
        gray = cv2.bilateralFilter(gray, 5, 50, 50)
        
        # 5. Normalize to uint8
        gray = np.uint8(np.clip(gray, 0, 255))
        
        return gray
    
    @staticmethod
    def _contrast_stretch(img: np.ndarray, percentile_low: float = 2.0, 
                         percentile_high: float = 98.0) -> np.ndarray:
        """Contrast stretching using percentile clipping"""
        vmin = np.percentile(img, percentile_low)
        vmax = np.percentile(img, percentile_high)
        
        if vmax > vmin:
            stretched = ((img - vmin) / (vmax - vmin) * 255.0)
        else:
            stretched = img.copy()
        
        return np.clip(stretched, 0, 255)
    
    @staticmethod
    def _adaptive_contrast(img: np.ndarray, clip_limit: float = 2.0, 
                          tile_size: int = 8) -> np.ndarray:
        """Adaptive histogram equalization for local contrast"""
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
        enhanced = clahe.apply(np.uint8(img))
        return enhanced
    
    @staticmethod
    def _edge_enhance(img: np.ndarray, strength: float = 0.3) -> np.ndarray:
        """Gentle edge enhancement using unsharp masking"""
        if strength <= 0:
            return img
        
        # Unsharp mask
        blur = cv2.GaussianBlur(img, (5, 5), 0)
        enhanced = cv2.addWeighted(img, 1 + strength, blur, -strength, 0)
        
        return enhanced
    
    @staticmethod
    def apply_to_mosaic(mosaic_path: str, output_path: str, 
                       create_sidecar: bool = True) -> bool:
        """
        Apply baseline enhancements to mosaic image and save
        
        Args:
            mosaic_path: Path to input mosaic
            output_path: Path for enhanced mosaic
            create_sidecar: Whether to create sidecar info file
            
        Returns:
            True if successful
        """
        try:
            # Load mosaic
            mosaic_img = Image.open(mosaic_path)
            mosaic_array = np.array(mosaic_img)
            
            # Apply baseline enhancements
            enhanced = BaselineEnhancer.apply_baseline_enhancements(mosaic_array)
            
            # Save enhanced version
            enhanced_img = Image.fromarray(enhanced)
            enhanced_img.save(output_path)
            
            # Create sidecar metadata if requested
            if create_sidecar:
                sidecar_path = output_path.replace('.png', '_baseline.json')
                import json
                metadata = {
                    'enhancement': 'baseline',
                    'type': 'contrast_stretch + adaptive_contrast + edge_enhance + denoise',
                    'parameters': {
                        'contrast_percentile_low': 2.0,
                        'contrast_percentile_high': 98.0,
                        'adaptive_clip_limit': 2.0,
                        'adaptive_tile_size': 8,
                        'edge_strength': 0.3,
                        'bilateral_d': 5,
                        'bilateral_sigma_color': 50,
                        'bilateral_sigma_space': 50
                    }
                }
                with open(sidecar_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error applying baseline enhancements: {e}")
            return False


class SecondaryEnhancementOptions:
    """Optional secondary enhancements for users who want specific processing"""
    
    # Map enhancement names to their implementations
    ENHANCEMENT_OPTIONS = {
        'agc_enhanced': {
            'name': 'Automatic Gain Control (AGC)',
            'description': 'Adaptive gain for uniform brightness across range',
            'category': 'radiometric'
        },
        'denoise_ml': {
            'name': 'ML Denoising',
            'description': 'Deep learning based noise reduction',
            'category': 'radiometric'
        },
        'pbr_rendering': {
            'name': 'Physically-Based Rendering',
            'description': 'Advanced material property visualization',
            'category': 'rendering'
        },
        'target_detection': {
            'name': 'Automated Target Detection',
            'description': 'Identify rocks, wrecks, and anomalies',
            'category': 'analysis'
        },
        'coordinate_overlay': {
            'name': 'Coordinate Overlay',
            'description': 'Geospatial reference grid',
            'category': 'reference'
        },
        'metadata_overlay': {
            'name': 'Metadata Overlay',
            'description': 'Range markers, depth, GPS info',
            'category': 'reference'
        }
    }
    
    @staticmethod
    def get_available_enhancements() -> dict:
        """Get all available secondary enhancements"""
        return SecondaryEnhancementOptions.ENHANCEMENT_OPTIONS
    
    @staticmethod
    def get_by_category(category: str) -> dict:
        """Get enhancements by category"""
        options = SecondaryEnhancementOptions.ENHANCEMENT_OPTIONS
        return {k: v for k, v in options.items() if v['category'] == category}
