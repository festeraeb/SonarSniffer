#!/usr/bin/env python3
"""
SonarSniffer License Validation Module
Validates license keys and enforces trial period restrictions.
Integrates with main SonarSniffer application.

Trial licenses: 30-day limit from first run
Commercial licenses: Perpetual or subscription-based
"""

import json
import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict
import sys


class LicenseValidator:
    """Validates and manages SonarSniffer licenses."""
    
    PRODUCT_ID = "SNIFFER"
    CONFIG_DIR = Path.home() / ".sonarsniffer"
    LICENSE_FILE = CONFIG_DIR / "license.json"
    TRIAL_DAYS = 30
    
    def __init__(self):
        """Initialize the license validator."""
        self.CONFIG_DIR.mkdir(exist_ok=True)
        self.license_data = self.load_license()
    
    def load_license(self) -> Optional[Dict]:
        """Load license from disk if it exists."""
        if self.LICENSE_FILE.exists():
            try:
                with open(self.LICENSE_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def save_license(self, license_key: str, license_info: Dict):
        """Save license to disk."""
        license_info['license_key'] = license_key
        license_info['installed_date'] = datetime.datetime.now().isoformat()
        
        with open(self.LICENSE_FILE, 'w') as f:
            json.dump(license_info, f, indent=2)
        
        self.license_data = license_info
    
    def validate_license_format(self, license_key: str) -> bool:
        """
        Validate that a key has the correct format.
        
        Args:
            license_key: The license key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        parts = license_key.split('-')
        if len(parts) != 5:
            return False
        
        if parts[0] != self.PRODUCT_ID:
            return False
        
        for i in range(1, 5):
            if len(parts[i]) != 5 or not parts[i].isalnum():
                return False
        
        return True
    
    def is_trial_expired(self) -> Tuple[bool, Optional[str]]:
        """
        Check if trial license has expired.
        
        Returns:
            (is_expired, message)
        """
        if not self.license_data:
            return False, None
        
        license_type = self.license_data.get('type')
        if license_type != 'TRIAL':
            return False, None
        
        installed_str = self.license_data.get('installed_date')
        if not installed_str:
            return False, None
        
        try:
            installed_date = datetime.datetime.fromisoformat(installed_str)
            expiration_date = installed_date + datetime.timedelta(days=self.TRIAL_DAYS)
            now = datetime.datetime.now()
            
            if now > expiration_date:
                return True, f"Trial license expired on {expiration_date.strftime('%Y-%m-%d')}"
            
            days_remaining = (expiration_date - now).days
            return False, f"{days_remaining} days remaining in trial"
        
        except ValueError:
            return False, None
    
    def is_commercial_expired(self) -> Tuple[bool, Optional[str]]:
        """
        Check if commercial subscription has expired.
        
        Returns:
            (is_expired, message)
        """
        if not self.license_data:
            return False, None
        
        license_type = self.license_data.get('type')
        if license_type != 'COMMERCIAL':
            return False, None
        
        expiration_str = self.license_data.get('expiration')
        
        # Perpetual licenses never expire
        if expiration_str == 'PERPETUAL':
            return False, "Perpetual commercial license"
        
        if not expiration_str:
            return False, None
        
        try:
            expiration_date = datetime.datetime.fromisoformat(expiration_str)
            now = datetime.datetime.now()
            
            if now > expiration_date:
                return True, f"Commercial license expired on {expiration_date.strftime('%Y-%m-%d')}"
            
            days_remaining = (expiration_date - now).days
            return False, f"{days_remaining} days remaining"
        
        except ValueError:
            return False, None
    
    def check_license(self) -> Tuple[bool, str]:
        """
        Check if SonarSniffer can run with current license.
        
        Returns:
            (can_run, message)
        """
        # No license installed - run in trial mode
        if not self.license_data:
            return True, "Running in 30-day trial mode. Install a license to continue past trial period."
        
        license_type = self.license_data.get('type')
        
        if license_type == 'TRIAL':
            is_expired, message = self.is_trial_expired()
            if is_expired:
                return False, f"Trial period expired. {message}\n\nPurchase a commercial license to continue using SonarSniffer.\nProceeds fund CesarOps SAR platform development."
            return True, message
        
        elif license_type == 'COMMERCIAL':
            is_expired, message = self.is_commercial_expired()
            if is_expired:
                return False, f"Commercial license expired. {message}\n\nRenew your license to continue using SonarSniffer."
            return True, message
        
        return False, "Invalid or unknown license type"
    
    def install_license_key(self, license_key: str) -> Tuple[bool, str]:
        """
        Install a new license key.
        
        Args:
            license_key: The license key to install
            
        Returns:
            (success, message)
        """
        if not self.validate_license_format(license_key):
            return False, f"Invalid license key format: {license_key}"
        
        # For now, we trust the key format. In production, you'd validate against a server
        license_info = {
            'type': 'TRIAL' if 'TRIAL' in license_key else 'COMMERCIAL',
            'license_key': license_key
        }
        
        self.save_license(license_key, license_info)
        
        if license_info['type'] == 'TRIAL':
            return True, f"Trial license installed. Valid for {self.TRIAL_DAYS} days from first run."
        else:
            return True, "Commercial license installed successfully."
    
    def get_license_status(self) -> Dict:
        """Get comprehensive license status."""
        if not self.license_data:
            return {
                'status': 'TRIAL_MODE',
                'message': 'No license installed. Running in 30-day trial mode.',
                'installed': False
            }
        
        license_type = self.license_data.get('type')
        
        if license_type == 'TRIAL':
            is_expired, message = self.is_trial_expired()
            return {
                'status': 'EXPIRED' if is_expired else 'TRIAL_ACTIVE',
                'type': 'TRIAL',
                'customer': self.license_data.get('customer', 'Unknown'),
                'installed': True,
                'installed_date': self.license_data.get('installed_date'),
                'message': message,
                'can_run': not is_expired
            }
        
        elif license_type == 'COMMERCIAL':
            is_expired, message = self.is_commercial_expired()
            return {
                'status': 'EXPIRED' if is_expired else 'ACTIVE',
                'type': 'COMMERCIAL',
                'license_type': self.license_data.get('license_type', 'UNKNOWN'),
                'customer': self.license_data.get('customer', 'Unknown'),
                'installed': True,
                'installed_date': self.license_data.get('installed_date'),
                'message': message,
                'can_run': not is_expired
            }
        
        return {
            'status': 'UNKNOWN',
            'message': 'Unknown license type',
            'installed': False
        }


def main():
    """Quick test/status check."""
    validator = LicenseValidator()
    status = validator.get_license_status()
    
    print("\n" + "="*60)
    print("SonarSniffer License Status")
    print("="*60)
    
    for key, value in status.items():
        print(f"{key:20s}: {value}")
    
    print()


if __name__ == '__main__':
    main()
