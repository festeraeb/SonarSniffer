"""
SonarSniffer - Professional Marine Survey Analysis Software

A comprehensive tool for analyzing marine sonar data with AI-enhanced target detection,
web-based visualization, and professional reporting capabilities.

Author: NautiDog Inc.
Contact: festeraeb@yahoo.com
Version: 1.0.0-beta
"""

__version__ = "1.0.0-beta"
__author__ = "NautiDog Inc."
__email__ = "festeraeb@yahoo.com"
__license__ = "Proprietary"

from .license_manager import LicenseManager
from .sonar_parser import SonarParser
from .web_dashboard_generator import WebDashboardGenerator

__all__ = [
    "LicenseManager",
    "SonarParser",
    "WebDashboardGenerator",
]