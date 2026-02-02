"""
CESARops - Great Lakes Search and Rescue Drift Modeling System

A comprehensive drift modeling system combining OpenDrift Lagrangian particle tracking
with machine learning enhancements for offline-capable SAR operations across all five
Great Lakes (Michigan, Erie, Huron, Ontario, Superior).

Author: CESAROPS Development Team
Version: 2.0.0-beta
License: Proprietary
"""

__version__ = "2.0.0-beta"
__author__ = "CESAROPS Development Team"
__license__ = "Proprietary"

# Core ML and drift correction modules
try:
    from .ml_pipeline import DriftCorrectionPipeline, EnhancedDriftSimulator

    ML_PIPELINE_AVAILABLE = True
except ImportError:
    ML_PIPELINE_AVAILABLE = False

# Geospatial export modules
try:
    from .geospatial_export import (
        GeoTIFFGenerator,
        KMLNetworkLinkGenerator,
        DriftSimulationExporter,
    )

    GEOSPATIAL_EXPORT_AVAILABLE = True
except ImportError:
    GEOSPATIAL_EXPORT_AVAILABLE = False

# Incremental loading for memory efficiency
try:
    from .incremental_loading import (
        StreamingDataLoader,
        ChunkedDataProcessor,
        ProgressiveDataLoader,
    )

    INCREMENTAL_LOADING_AVAILABLE = True
except ImportError:
    INCREMENTAL_LOADING_AVAILABLE = False

__all__ = [
    "DriftCorrectionPipeline",
    "EnhancedDriftSimulator",
    "GeoTIFFGenerator",
    "KMLNetworkLinkGenerator",
    "DriftSimulationExporter",
    "StreamingDataLoader",
    "ChunkedDataProcessor",
    "ProgressiveDataLoader",
    "ML_PIPELINE_AVAILABLE",
    "GEOSPATIAL_EXPORT_AVAILABLE",
    "INCREMENTAL_LOADING_AVAILABLE",
]
