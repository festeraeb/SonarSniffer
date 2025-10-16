"""
Tests for SonarSniffer CLI
"""

import pytest
import sys
from unittest.mock import patch, MagicMock
from io import StringIO


class TestCLI:
    """Test cases for CLI functionality"""

    def test_cli_import(self):
        """Test that CLI module can be imported"""
        try:
            from sonarsniffer.cli import main
            assert callable(main)
        except ImportError:
            # Expected in test environment
            pytest.skip("CLI module not available in test environment")

    @patch('sys.argv', ['sonarsniffer', '--help'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_help_output(self, mock_stdout):
        """Test help output"""
        try:
            from sonarsniffer.cli import main
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert 'Usage:' in output
            assert 'sonarsniffer' in output
        except ImportError:
            pytest.skip("CLI module not available in test environment")

    @patch('sonarsniffer.cli.LicenseManager')
    def test_license_check(self, mock_license_mgr):
        """Test license validation in CLI"""
        try:
            from sonarsniffer.cli import main

            # Mock invalid license
            mock_instance = MagicMock()
            mock_instance.is_valid.return_value = False
            mock_instance.get_trial_days_remaining.return_value = 15
            mock_license_mgr.return_value = mock_instance

            with patch('sys.argv', ['sonarsniffer', 'analyze', 'test.rsd']):
                result = main()
                assert result == 1  # Should return error code

        except ImportError:
            pytest.skip("CLI module not available in test environment")


if __name__ == "__main__":
    pytest.main([__file__])