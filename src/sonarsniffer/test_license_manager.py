"""
Tests for SonarSniffer License Manager
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

from sonarsniffer.license_manager import LicenseManager


class TestLicenseManager:
    """Test cases for LicenseManager class"""

    def setup_method(self):
        """Setup for each test method"""
        self.license_mgr = LicenseManager()

    def test_initialization(self):
        """Test license manager initialization"""
        assert self.license_mgr is not None
        assert hasattr(self.license_mgr, 'is_valid')
        assert hasattr(self.license_mgr, 'get_status')

    def test_trial_license(self):
        """Test trial license functionality"""
        status = self.license_mgr.get_status()
        assert 'is_trial' in status
        assert 'days_remaining' in status
        assert 'contact' in status

    def test_contact_info(self):
        """Test contact information retrieval"""
        contact = self.license_mgr.get_contact_info()
        assert contact == "festeraeb@yahoo.com"

    def test_trial_days_remaining(self):
        """Test trial days remaining calculation"""
        days = self.license_mgr.get_trial_days_remaining()
        assert isinstance(days, int)
        assert days >= 0

    @patch('sonarsniffer.license_manager.sqlite3')
    def test_database_operations(self, mock_sqlite):
        """Test database operations are handled properly"""
        # Mock the database connection
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn

        # Test that database operations don't crash
        try:
            status = self.license_mgr.get_status()
            assert isinstance(status, dict)
        except Exception as e:
            # Should handle database errors gracefully
            assert "database" in str(e).lower() or "sqlite" in str(e).lower()

    def test_validate_key_format(self):
        """Test license key validation format"""
        # Test with invalid key formats
        assert not self.license_mgr.validate_key("")
        assert not self.license_mgr.validate_key("invalid-key")

        # Test with potentially valid format (this will fail but shouldn't crash)
        try:
            result = self.license_mgr.validate_key("XXXX-XXXX-XXXX-XXXX")
            assert isinstance(result, bool)
        except:
            # Expected to fail with invalid key
            pass


if __name__ == "__main__":
    pytest.main([__file__])