#!/usr/bin/env python3
"""
Radiometric Correction Enhancement - Advanced bathymetric data calibration
Handles sensor drift, temperature compensation, and intensity normalization
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrectionType(Enum):
    """Available radiometric correction methods"""
    LINEAR = "linear"  # Simple gain/offset
    POLYNOMIAL = "polynomial"  # Higher-order correction
    TEMPERATURE = "temperature"  # Temperature compensation
    INTENSITY_NORM = "intensity_normalization"
    GAIN_VARIATION = "gain_variation"


@dataclass
class SensorCalibration:
    """Sensor calibration parameters"""
    gain: float = 1.0  # Amplification factor
    offset: float = 0.0  # DC offset
    temperature_ref: float = 20.0  # Reference temperature (°C)
    temperature_coeff: float = 0.001  # Temperature coefficient
    intensity_baseline: float = 128.0  # Expected intensity at known distance
    distance_baseline: float = 100.0  # Distance for intensity baseline


@dataclass
class CorrectionResult:
    """Result from radiometric correction"""
    corrected_data: np.ndarray
    correction_type: CorrectionType
    parameters: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


class RadiometricCorrector:
    """
    Radiometric correction for bathymetric sonar data
    
    Handles:
    - Sensor gain/offset calibration
    - Temperature compensation
    - Beam intensity normalization
    - Temporal drift correction
    - Distance attenuation compensation
    """
    
    def __init__(self, calibration: SensorCalibration = None):
        self.calibration = calibration or SensorCalibration()
        self.correction_cache = {}
    
    def apply_linear_correction(self, data: np.ndarray) -> CorrectionResult:
        """
        Apply linear gain and offset correction
        
        Formula: corrected = (raw - offset) / gain
        
        Args:
            data: Raw sensor data
            
        Returns:
            CorrectionResult with corrected data
        """
        logger.info(f"Applying linear correction (gain={self.calibration.gain}, "
                   f"offset={self.calibration.offset})")
        
        # Avoid division by zero
        gain = self.calibration.gain if self.calibration.gain != 0 else 1.0
        
        corrected = (data - self.calibration.offset) / gain
        
        return CorrectionResult(
            corrected_data=corrected,
            correction_type=CorrectionType.LINEAR,
            parameters={
                "gain": gain,
                "offset": self.calibration.offset
            }
        )
    
    def apply_temperature_correction(self, data: np.ndarray,
                                   temperatures: np.ndarray) -> CorrectionResult:
        """
        Apply temperature-dependent correction
        
        Formula: corrected = raw * (1 + coeff * (T - T_ref))
        
        Args:
            data: Raw sensor data
            temperatures: Temperature measurements (°C)
            
        Returns:
            CorrectionResult with temperature-corrected data
        """
        logger.info(f"Applying temperature correction (ref={self.calibration.temperature_ref}°C, "
                   f"coeff={self.calibration.temperature_coeff})")
        
        if len(temperatures) != len(data):
            logger.warning(f"Temperature array length {len(temperatures)} != "
                          f"data length {len(data)}, truncating")
            temperatures = temperatures[:len(data)]
        
        # Temperature correction factor
        temp_delta = temperatures - self.calibration.temperature_ref
        correction_factor = 1.0 + (self.calibration.temperature_coeff * temp_delta)
        
        # Apply correction
        corrected = data * correction_factor
        
        return CorrectionResult(
            corrected_data=corrected,
            correction_type=CorrectionType.TEMPERATURE,
            parameters={
                "temperature_ref": self.calibration.temperature_ref,
                "temperature_coeff": self.calibration.temperature_coeff,
                "temperature_range": (np.min(temperatures), np.max(temperatures))
            }
        )
    
    def apply_intensity_normalization(self, intensities: np.ndarray,
                                     distances: np.ndarray) -> CorrectionResult:
        """
        Normalize beam intensities based on distance (spreading loss correction)
        
        Formula: normalized = intensity * (distance / distance_baseline)^2
        
        Args:
            intensities: Beam intensity data
            distances: Distance from sonar (m)
            
        Returns:
            CorrectionResult with normalized intensities
        """
        logger.info(f"Applying intensity normalization (baseline={self.calibration.intensity_baseline}@"
                   f"{self.calibration.distance_baseline}m)")
        
        if len(intensities) != len(distances):
            min_len = min(len(intensities), len(distances))
            intensities = intensities[:min_len]
            distances = distances[:min_len]
        
        # Avoid division by zero
        safe_distances = np.where(distances > 0, distances, 0.001)
        
        # Spreading loss correction: intensity ∝ 1/distance²
        # Normalize to baseline distance
        normalized = intensities * (safe_distances / self.calibration.distance_baseline) ** 2
        
        return CorrectionResult(
            corrected_data=normalized,
            correction_type=CorrectionType.INTENSITY_NORM,
            parameters={
                "intensity_baseline": self.calibration.intensity_baseline,
                "distance_baseline": self.calibration.distance_baseline,
                "distance_range": (np.min(distances), np.max(distances))
            }
        )
    
    def apply_polynomial_correction(self, data: np.ndarray,
                                   coefficients: np.ndarray) -> CorrectionResult:
        """
        Apply polynomial correction for non-linear sensor response
        
        Formula: corrected = c0 + c1*raw + c2*raw² + ... + cn*raw^n
        
        Args:
            data: Raw sensor data
            coefficients: Polynomial coefficients [c0, c1, c2, ...]
            
        Returns:
            CorrectionResult with polynomial-corrected data
        """
        logger.info(f"Applying polynomial correction (degree={len(coefficients)-1})")
        
        # Evaluate polynomial
        corrected = np.polyval(coefficients, data)
        
        return CorrectionResult(
            corrected_data=corrected,
            correction_type=CorrectionType.POLYNOMIAL,
            parameters={
                "polynomial_degree": len(coefficients) - 1,
                "coefficients": coefficients.tolist()
            }
        )
    
    def apply_gain_variation_correction(self, data: np.ndarray,
                                       gain_map: np.ndarray) -> CorrectionResult:
        """
        Apply spatially-varying gain correction
        
        Useful for correcting beam pattern variations across swath
        
        Args:
            data: Raw sensor data (samples x beams)
            gain_map: Gain correction per beam
            
        Returns:
            CorrectionResult with gain-corrected data
        """
        logger.info(f"Applying gain variation correction ({len(gain_map)} beams)")
        
        if data.ndim == 1:
            # Single beam
            corrected = data / gain_map[0] if gain_map[0] != 0 else data
        elif data.ndim == 2:
            # Multiple beams
            safe_gain_map = np.where(gain_map > 0, gain_map, 1.0)
            corrected = data / safe_gain_map[np.newaxis, :]
        else:
            logger.warning(f"Unexpected data shape {data.shape}, returning uncorrected")
            corrected = data
        
        return CorrectionResult(
            corrected_data=corrected,
            correction_type=CorrectionType.GAIN_VARIATION,
            parameters={
                "num_beams": len(gain_map),
                "gain_range": (np.min(gain_map), np.max(gain_map))
            }
        )
    
    def estimate_calibration_from_reference(self, raw_data: np.ndarray,
                                          reference_data: np.ndarray) -> SensorCalibration:
        """
        Estimate sensor calibration from raw vs reference data
        
        Uses least-squares fit: calibrated = (raw - offset) / gain
        
        Args:
            raw_data: Raw sensor measurements
            reference_data: Known-good reference measurements
            
        Returns:
            Estimated SensorCalibration
        """
        logger.info("Estimating calibration from reference data")
        
        # Linear regression to find gain and offset
        # Fit: reference = a * raw + b
        coeffs = np.polyfit(raw_data.ravel(), reference_data.ravel(), 1)
        
        gain = coeffs[0]
        offset = -coeffs[1] / gain if gain != 0 else 0
        
        error = np.mean(np.abs(reference_data - (raw_data - offset) / gain))
        
        logger.info(f"  Estimated gain: {gain:.4f}, offset: {offset:.2f}")
        logger.info(f"  Mean absolute error: {error:.4f}")
        
        new_calibration = SensorCalibration(
            gain=gain,
            offset=offset
        )
        
        return new_calibration
    
    def apply_temporal_drift_correction(self, data: np.ndarray,
                                       time_indices: np.ndarray,
                                       drift_rate: float = 0.1) -> CorrectionResult:
        """
        Correct for temporal sensor drift (drift over time)
        
        Formula: corrected = raw / (1 + drift_rate * time)
        
        Args:
            data: Sensor data over time
            time_indices: Time indices for each measurement
            drift_rate: Drift rate as fraction per time unit
            
        Returns:
            CorrectionResult with drift-corrected data
        """
        logger.info(f"Applying temporal drift correction (rate={drift_rate:.4f})")
        
        # Normalize time indices to start at 0
        time_norm = time_indices - np.min(time_indices)
        
        # Drift correction factor
        drift_factor = 1.0 + (drift_rate * time_norm)
        
        # Avoid division by zero
        safe_drift = np.where(drift_factor > 0, drift_factor, 1.0)
        
        corrected = data / safe_drift
        
        return CorrectionResult(
            corrected_data=corrected,
            correction_type=CorrectionType.LINEAR,  # Simplified
            parameters={
                "drift_rate": drift_rate,
                "time_span": float(np.max(time_indices) - np.min(time_indices))
            }
        )
    
    def chain_corrections(self, data: np.ndarray,
                         correction_sequence: list) -> CorrectionResult:
        """
        Apply multiple corrections in sequence
        
        Args:
            data: Input data
            correction_sequence: List of (correction_type, **kwargs) tuples
            
        Returns:
            Final CorrectionResult after all corrections
        """
        current_data = data.copy()
        all_params = {}
        
        for i, (corr_type, kwargs) in enumerate(correction_sequence):
            logger.info(f"Applying correction {i+1}/{len(correction_sequence)}: {corr_type}")
            
            if corr_type == "linear":
                result = self.apply_linear_correction(current_data)
            elif corr_type == "temperature":
                result = self.apply_temperature_correction(current_data, kwargs.get("temperatures"))
            elif corr_type == "intensity":
                result = self.apply_intensity_normalization(
                    current_data, kwargs.get("distances")
                )
            else:
                logger.warning(f"Unknown correction type: {corr_type}")
                continue
            
            current_data = result.corrected_data
            all_params[f"step_{i}"] = result.parameters
        
        return CorrectionResult(
            corrected_data=current_data,
            correction_type=CorrectionType.POLYNOMIAL,  # Simplified
            parameters=all_params,
            metadata={"num_corrections": len(correction_sequence)}
        )


class CorrectionQualityAssurance:
    """
    Validate and assess quality of radiometric corrections
    """
    
    @staticmethod
    def check_correction_validity(original: np.ndarray,
                                 corrected: np.ndarray) -> Dict:
        """
        Validate that correction is reasonable
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "is_valid": True,
            "issues": []
        }
        
        # Check for NaN/Inf
        if np.any(np.isnan(corrected)):
            results["issues"].append("Output contains NaN values")
            results["is_valid"] = False
        
        if np.any(np.isinf(corrected)):
            results["issues"].append("Output contains infinite values")
            results["is_valid"] = False
        
        # Check dynamic range (should not explode)
        original_range = np.nanmax(original) - np.nanmin(original)
        corrected_range = np.nanmax(corrected) - np.nanmin(corrected)
        
        if original_range > 0:
            range_ratio = corrected_range / original_range
            if range_ratio > 100:
                results["issues"].append(f"Dynamic range expanded 100x+ ({range_ratio:.0f}x)")
            elif range_ratio < 0.01:
                results["issues"].append(f"Dynamic range collapsed 100x+ ({range_ratio:.0f}x)")
        
        # Check distribution shift (should be reasonable)
        original_mean = np.nanmean(original)
        corrected_mean = np.nanmean(corrected)
        
        if original_mean > 0:
            mean_shift = abs(corrected_mean - original_mean) / original_mean
            if mean_shift > 10.0:
                results["issues"].append(f"Mean shifted by {mean_shift*100:.0f}%")
        
        return results
    
    @staticmethod
    def assess_correction_quality(original: np.ndarray,
                                 reference: np.ndarray,
                                 corrected: np.ndarray) -> float:
        """
        Assess quality of correction vs reference data
        
        Returns:
            Quality score (0-1, higher is better)
        """
        # Compute errors
        original_error = np.sqrt(np.mean((original - reference) ** 2))
        corrected_error = np.sqrt(np.mean((corrected - reference) ** 2))
        
        # Quality as improvement ratio
        if original_error > 0:
            quality = max(0.0, 1.0 - (corrected_error / original_error))
        else:
            quality = 0.5
        
        return quality


if __name__ == "__main__":
    # Example usage
    np.random.seed(42)
    
    # Simulate sonar data with issues
    raw_data = np.random.randint(0, 256, 1000).astype(float)
    
    # Create radiometric corrector
    calibration = SensorCalibration(
        gain=1.1,
        offset=5.0,
        temperature_ref=20.0,
        temperature_coeff=0.002
    )
    
    corrector = RadiometricCorrector(calibration)
    
    # Apply corrections
    print("Applying radiometric corrections...")
    
    # Linear correction
    result1 = corrector.apply_linear_correction(raw_data)
    print(f"Linear correction: {result1.corrected_data[:5]}")
    
    # Temperature correction
    temperatures = 20 + np.random.randn(1000) * 2
    result2 = corrector.apply_temperature_correction(raw_data, temperatures)
    print(f"Temperature correction applied: temp range {temperatures.min():.1f}-{temperatures.max():.1f}°C")
    
    # Intensity normalization
    distances = np.linspace(10, 200, 1000)
    result3 = corrector.apply_intensity_normalization(raw_data, distances)
    print(f"Intensity normalization: distance range {distances.min():.0f}-{distances.max():.0f}m")
    
    # Check quality
    print("\nValidation:")
    validation = CorrectionQualityAssurance.check_correction_validity(raw_data, result1.corrected_data)
    print(f"Valid: {validation['is_valid']}")
    if validation['issues']:
        for issue in validation['issues']:
            print(f"  - {issue}")
