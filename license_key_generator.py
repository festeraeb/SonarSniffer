#!/usr/bin/env python3
"""
SonarSniffer License Key Generator
Generates trial and commercial license keys for SonarSniffer installations.
Revenue from license sales funds CesarOps SAR platform development.

Format: SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX
- Trial keys: 30-day expiration from first run
- Commercial keys: Perpetual or subscription-based
"""

import hashlib
import datetime
import secrets
from typing import Tuple, Dict
import json
from pathlib import Path


class LicenseKeyGenerator:
    """Generate and validate SonarSniffer license keys."""
    
    PRODUCT_ID = "SNIFFER"
    TRIAL_DAYS = 30
    VERSION = "1.0"
    
    def __init__(self):
        """Initialize the license key generator."""
        self.generated_keys_file = Path("generated_licenses.json")
        self.load_generated_keys()
    
    def load_generated_keys(self):
        """Load previously generated keys from file."""
        if self.generated_keys_file.exists():
            with open(self.generated_keys_file, 'r') as f:
                self.generated_keys = json.load(f)
        else:
            self.generated_keys = {}
    
    def save_generated_keys(self):
        """Save generated keys to file."""
        with open(self.generated_keys_file, 'w') as f:
            json.dump(self.generated_keys, f, indent=2)
    
    def generate_trial_key(self, customer_name: str = "TRIAL") -> str:
        """
        Generate a 30-day trial license key.
        
        Args:
            customer_name: Name of customer/team using trial
            
        Returns:
            License key in format: SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX
        """
        # Create a seed from product ID, trial marker, and random data
        trial_marker = "TRIAL"
        random_suffix = secrets.token_hex(8)
        seed = f"{self.PRODUCT_ID}{trial_marker}{customer_name}{random_suffix}"
        
        # Generate hash-based segments
        hash_obj = hashlib.sha256(seed.encode())
        hex_digest = hash_obj.hexdigest()
        
        # Create 4 segments of 5 characters each
        segments = []
        for i in range(4):
            start = i * 5
            end = start + 5
            segment = hex_digest[start:end].upper()[:5]
            # Ensure segment is exactly 5 chars
            segment = (segment + "0" * 5)[:5]
            segments.append(segment)
        
        license_key = f"{self.PRODUCT_ID}-{'-'.join(segments)}"
        
        # Record the generated key
        key_data = {
            "type": "TRIAL",
            "customer": customer_name,
            "generated_date": datetime.datetime.now().isoformat(),
            "expiration": (datetime.datetime.now() + datetime.timedelta(days=self.TRIAL_DAYS)).isoformat(),
            "days_valid": self.TRIAL_DAYS
        }
        
        self.generated_keys[license_key] = key_data
        self.save_generated_keys()
        
        return license_key
    
    def generate_commercial_key(self, customer_name: str, license_type: str = "PERPETUAL") -> str:
        """
        Generate a commercial license key.
        
        Args:
            customer_name: Name of customer/organization
            license_type: PERPETUAL, ANNUAL, or MONTHLY
            
        Returns:
            License key in format: SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX
        """
        # Create a seed from product ID, commercial marker, and customer
        commercial_marker = "COMM"
        random_suffix = secrets.token_hex(8)
        seed = f"{self.PRODUCT_ID}{commercial_marker}{customer_name}{random_suffix}"
        
        # Generate hash-based segments
        hash_obj = hashlib.sha256(seed.encode())
        hex_digest = hash_obj.hexdigest()
        
        # Create 4 segments of 5 characters each
        segments = []
        for i in range(4):
            start = i * 5
            end = start + 5
            segment = hex_digest[start:end].upper()[:5]
            segment = (segment + "0" * 5)[:5]
            segments.append(segment)
        
        license_key = f"{self.PRODUCT_ID}-{'-'.join(segments)}"
        
        # Determine expiration based on license type
        if license_type == "PERPETUAL":
            expiration_date = "PERPETUAL"
            days_valid = None
        elif license_type == "ANNUAL":
            expiration_date = (datetime.datetime.now() + datetime.timedelta(days=365)).isoformat()
            days_valid = 365
        elif license_type == "MONTHLY":
            expiration_date = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
            days_valid = 30
        else:
            raise ValueError(f"Unknown license type: {license_type}")
        
        # Record the generated key
        key_data = {
            "type": "COMMERCIAL",
            "license_type": license_type,
            "customer": customer_name,
            "generated_date": datetime.datetime.now().isoformat(),
            "expiration": expiration_date,
            "days_valid": days_valid
        }
        
        self.generated_keys[license_key] = key_data
        self.save_generated_keys()
        
        return license_key
    
    def get_key_info(self, license_key: str) -> Dict:
        """
        Get information about a generated key.
        
        Args:
            license_key: The license key to look up
            
        Returns:
            Dictionary with key information or None if not found
        """
        return self.generated_keys.get(license_key)
    
    def list_all_keys(self):
        """Display all generated keys."""
        if not self.generated_keys:
            print("No license keys generated yet.")
            return
        
        print("\n" + "="*70)
        print("GENERATED LICENSE KEYS - SonarSniffer")
        print("="*70)
        
        for key, info in self.generated_keys.items():
            print(f"\nKey: {key}")
            print(f"  Type: {info.get('type', 'UNKNOWN')}")
            print(f"  Customer: {info.get('customer', 'N/A')}")
            print(f"  Generated: {info.get('generated_date', 'N/A')}")
            print(f"  Expiration: {info.get('expiration', 'N/A')}")
            if info.get('license_type'):
                print(f"  License Type: {info.get('license_type')}")
            print()
    
    def validate_key_format(self, license_key: str) -> bool:
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


def main():
    """Command-line interface for license key generation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SonarSniffer License Key Generator - Funds CesarOps SAR Platform Development"
    )
    parser.add_argument(
        'action',
        choices=['trial', 'commercial', 'list', 'info'],
        help='Action to perform'
    )
    parser.add_argument(
        '--customer',
        type=str,
        help='Customer/organization name'
    )
    parser.add_argument(
        '--type',
        choices=['PERPETUAL', 'ANNUAL', 'MONTHLY'],
        default='PERPETUAL',
        help='Commercial license type (default: PERPETUAL)'
    )
    parser.add_argument(
        '--key',
        type=str,
        help='License key to look up'
    )
    
    args = parser.parse_args()
    
    generator = LicenseKeyGenerator()
    
    if args.action == 'trial':
        customer = args.customer or "TRIAL_USER"
        key = generator.generate_trial_key(customer)
        print(f"\n✓ Trial License Key Generated (30 days):")
        print(f"  {key}")
        print(f"  Customer: {customer}")
        print(f"  Expiration: {(datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')}")
        print("\n  Note: This key expires 30 days from first installation.")
        print("  Funding SAR platform development: https://cesarops.org\n")
    
    elif args.action == 'commercial':
        if not args.customer:
            print("Error: --customer required for commercial licenses")
            return
        key = generator.generate_commercial_key(args.customer, args.type)
        print(f"\n✓ Commercial License Key Generated ({args.type}):")
        print(f"  {key}")
        print(f"  Customer: {args.customer}")
        print(f"  Type: {args.type}")
        
        if args.type == "PERPETUAL":
            print(f"  Valid: Forever")
        else:
            days = 365 if args.type == "ANNUAL" else 30
            print(f"  Expires: {(datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')}")
        
        print("\n  Thank you for supporting SAR operations!")
        print("  100% of proceeds fund CesarOps search and rescue platform.\n")
    
    elif args.action == 'list':
        generator.list_all_keys()
    
    elif args.action == 'info':
        if not args.key:
            print("Error: --key required for info lookup")
            return
        
        info = generator.get_key_info(args.key)
        if info:
            print(f"\nLicense Key Information: {args.key}")
            print(json.dumps(info, indent=2))
        else:
            print(f"License key not found: {args.key}")


if __name__ == '__main__':
    main()
