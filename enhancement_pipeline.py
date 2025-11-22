#!/usr/bin/env python3
"""
Integration layer for baseline enhancements
Applies baseline enhancements automatically during mosaic generation
"""

from baseline_enhancements import BaselineEnhancer
from pathlib import Path as PathlibPath
import numpy as np
from PIL import Image
from typing import Optional, Tuple


class EnhancementPipeline:
    """Manages enhancement pipeline - baseline automatic, secondary optional"""
    
    def __init__(self):
        """Initialize enhancement pipeline"""
        self.baseline_enhancer = BaselineEnhancer()
    
    @staticmethod
    def apply_baseline_to_mosaic(mosaic_path: str, output_base_dir: str, 
                                 create_backup: bool = False) -> Tuple[bool, str]:
        """
        Apply baseline enhancements to mosaic and save as default version
        
        Args:
            mosaic_path: Path to original mosaic
            output_base_dir: Base output directory
            create_backup: Whether to keep original as '_original.png'
            
        Returns:
            (success, enhanced_mosaic_path)
        """
        try:
            # Create output filename
            mosaic_filename = PathlibPath(mosaic_path).stem
            output_path = PathlibPath(output_base_dir) / f"{mosaic_filename}_enhanced.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Apply baseline enhancements
            success = BaselineEnhancer.apply_to_mosaic(
                mosaic_path, 
                str(output_path),
                create_sidecar=True
            )
            
            # Optionally create backup of original
            if create_backup and success:
                backup_path = PathlibPath(output_base_dir) / f"{mosaic_filename}_original.png"
                import shutil
                shutil.copy2(mosaic_path, backup_path)
            
            return success, str(output_path)
        except Exception as e:
            print(f"Error in baseline enhancement pipeline: {e}")
            return False, mosaic_path
    
    @staticmethod
    def should_apply_baseline(mosaic_path: str) -> bool:
        """Check if mosaic hasn't already been enhanced"""
        path = PathlibPath(mosaic_path)
        return '_enhanced' not in path.name and '_original' not in path.name
    
    @staticmethod
    def get_enhancement_info() -> dict:
        """Get information about baseline enhancements"""
        return {
            'name': 'Automatic Baseline Enhancement',
            'description': 'Optimal sonar image quality without user configuration',
            'techniques': [
                'Contrast Stretching (2-98 percentile)',
                'Adaptive Histogram Equalization (CLAHE)',
                'Gentle Edge Enhancement (Unsharp Mask)',
                'Bilateral Denoising'
            ],
            'auto_applied': True,
            'optional_secondary': [
                'Automatic Gain Control (AGC)',
                'Physically-Based Rendering (PBR)',
                'Automated Target Detection',
                'Coordinate/Reference Overlays'
            ]
        }


class SecondaryEnhancementApplier:
    """Applies optional secondary enhancements after baseline processing"""
    
    def __init__(self):
        """Initialize secondary enhancement applier"""
        pass
    
    @staticmethod
    def apply_agc(mosaic_array: np.ndarray, sensitivity: float = 0.5) -> np.ndarray:
        """
        Apply Automatic Gain Control
        
        Args:
            mosaic_array: Input sonar image
            sensitivity: AGC sensitivity (0.0-1.0)
            
        Returns:
            AGC-corrected image
        """
        try:
            from radiometric_corrections import RadiometricCorrector
            
            corrector = RadiometricCorrector()
            corrected = corrector.apply_full_correction(
                mosaic_array,
                range_samples=None,
                depth_m=10.0,
                range_max_m=50.0,
                corrections={
                    'agc': True,
                    'denoise': False,
                    'destrip': False,
                    'beam_angle': False,
                    'footprint': False
                }
            )
            return corrected
        except Exception as e:
            print(f"AGC enhancement failed: {e}")
            return mosaic_array
    
    @staticmethod
    def apply_pbr(mosaic_array: np.ndarray, mode: str = 'DIFFERENTIAL') -> np.ndarray:
        """
        Apply Physically-Based Rendering
        
        Args:
            mosaic_array: Input sonar image
            mode: PBR mode (DIFFERENTIAL recommended for sonar)
            
        Returns:
            PBR-rendered image
        """
        try:
            from pbr_sonar_renderer import PBRSonarRenderer
            
            renderer = PBRSonarRenderer(
                frame_height=480,
                frame_width=480,
                mounting_angle_deg=0.0,
                beam_angle_deg=17.0,
                frequency_khz=200.0
            )
            
            # Handle different array shapes
            if len(mosaic_array.shape) == 3:
                sonar_frame = np.mean(mosaic_array[:, :, :3], axis=2).astype(np.uint8)
            else:
                sonar_frame = mosaic_array.astype(np.uint8)
            
            rendered = renderer.render_differential_frame(
                sonar_frame,
                depth_map=None,
                material_map=None,
                use_pbr=True
            )
            return rendered
        except Exception as e:
            print(f"PBR enhancement failed: {e}")
            return mosaic_array
    
    @staticmethod
    def apply_target_detection(mosaic_array: np.ndarray, 
                              sensitivity: float = 0.5) -> Tuple[np.ndarray, list]:
        """
        Apply automated target detection
        
        Args:
            mosaic_array: Input sonar image
            sensitivity: Detection sensitivity (0.0-1.0)
            
        Returns:
            (marked_image, detected_targets_list)
        """
        try:
            from target_detection import TargetDetector, TargetMarker
            import cv2
            
            detector = TargetDetector(sensitivity=sensitivity)
            
            # Convert to grayscale if needed
            if len(mosaic_array.shape) == 3:
                gray = cv2.cvtColor(mosaic_array, cv2.COLOR_RGB2GRAY)
                rgb = mosaic_array[:, :, :3]
            else:
                gray = mosaic_array
                rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
            # Detect targets
            targets = detector.detect_targets(gray)
            
            # Mark targets if found
            if targets:
                marked = TargetMarker.mark_targets(
                    rgb,
                    targets,
                    show_confidence=True,
                    show_intensity=True
                )
                return marked, targets
            else:
                return rgb, []
        except Exception as e:
            print(f"Target detection failed: {e}")
            return mosaic_array, []


def create_enhancement_summary(enhancements_applied: dict) -> str:
    """Create a summary of applied enhancements"""
    summary = "Enhancement Pipeline Summary\n"
    summary += "="*50 + "\n\n"
    summary += "BASELINE (Automatic):\n"
    summary += "  ✓ Contrast Stretching\n"
    summary += "  ✓ Adaptive Histogram Equalization\n"
    summary += "  ✓ Edge Enhancement\n"
    summary += "  ✓ Bilateral Denoising\n\n"
    summary += "SECONDARY (Optional):\n"
    
    for name, applied in enhancements_applied.items():
        if applied:
            summary += f"  ✓ {name}\n"
        else:
            summary += f"  ✗ {name}\n"
    
    return summary
