"""
Search and Rescue Web Server - sonar_gui.py Integration Helper
================================================================

This module provides ready-to-use helper functions for integrating
the web server into sonar_gui.py with minimal code changes.

Usage in sonar_gui.py:

    # At top of file, add import:
    from sar_web_server_integration_helper import (
        ExportWithWebServer,
        get_share_link_dialog,
        create_web_server_config_dialog
    )
    
    # In your export button click handler:
    result = ExportWithWebServer.export_and_serve(
        parent_window=self,
        export_dir=self.output_dir,
        sonar_files=self.sonar_files,
        survey_metadata={
            'survey_id': 'SarOp-2025-11-25-001',
            'search_area': 'Monterey Canyon',
            'contact_info': 'John Smith (831-555-0123)'
        }
    )
    
    if result.success:
        show_share_link_dialog(
            parent=self,
            server=result.server,
            survey_id=result.survey_id
        )
"""

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

# Conditional imports - work even if PyQt5 not installed
try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QMessageBox, QSpinBox, QCheckBox, QGroupBox,
        QApplication, QProgressDialog
    )
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from sar_web_server import SARWebServerIntegration, SARWebServer

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of export with web server"""
    success: bool
    message: str
    server: Optional[SARWebServer] = None
    survey_id: Optional[str] = None
    share_url: Optional[str] = None
    error: Optional[Exception] = None


class ExportWithWebServer:
    """
    Helper class for exporting sonar data with automatic web server startup
    
    Designed for integration into sonar_gui.py
    """
    
    @staticmethod
    def export_and_serve(
        parent_window: Any,
        export_dir: str,
        sonar_files: list,
        survey_metadata: Dict[str, str],
        port: int = 8080,
        auto_open: bool = True
    ) -> ExportResult:
        """
        Export sonar data and start web server
        
        Args:
            parent_window: Qt parent window (for progress dialog)
            export_dir: Directory to export to
            sonar_files: List of sonar files to process
            survey_metadata: Dict with 'survey_id', 'search_area', 'contact_info'
            port: Server port (default 8080)
            auto_open: Auto-open browser (default True)
        
        Returns:
            ExportResult with success status and server reference
        
        Example:
            result = ExportWithWebServer.export_and_serve(
                parent_window=self,
                export_dir='output',
                sonar_files=['survey.rsd'],
                survey_metadata={
                    'survey_id': 'SarOp-2025-11-25-001',
                    'search_area': 'Monterey Canyon - 800m depth',
                    'contact_info': 'John Smith (831-555-0123)'
                }
            )
            
            if result.success:
                print(f"Share: {result.share_url}")
        """
        
        try:
            logger.info(f"Starting export with web server (port {port})")
            
            # Create server instance
            server = SARWebServerIntegration.create_from_export_result(
                export_dir=export_dir,
                survey_id=survey_metadata.get('survey_id'),
                search_area=survey_metadata.get('search_area'),
                contact_info=survey_metadata.get('contact_info'),
                port=port,
                auto_start=True  # Automatically starts
            )
            
            # Get share URL
            share_url = f"http://{server._get_local_ip()}:{port}"
            
            return ExportResult(
                success=True,
                message=f"Export complete. Web server running on port {port}",
                server=server,
                survey_id=survey_metadata.get('survey_id'),
                share_url=share_url
            )
        
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            return ExportResult(
                success=False,
                message=f"Export failed: {str(e)}",
                error=e
            )


class WebServerConfigDialog:
    """Create PyQt5 dialog for web server configuration"""
    
    @staticmethod
    def create_dialog(parent=None):
        """
        Create configuration dialog for web server options
        
        Returns PyQt5 dialog with controls for:
        - Enable/disable web server
        - Port selection
        - Allow external connections
        - Auto-open browser
        
        Example:
            dialog = WebServerConfigDialog.create_dialog(parent=main_window)
            if dialog.exec_() == QDialog.Accepted:
                config = dialog.get_config()
                # Use config...
        """
        
        if not HAS_PYQT5:
            logger.warning("PyQt5 not available, returning None")
            return None
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("Web Server Configuration")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Configure Web Server for Remote Viewing")
        header.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header)
        
        # Enable checkbox
        dialog.enable_server = QCheckBox("Enable web server after export")
        dialog.enable_server.setChecked(True)
        layout.addWidget(dialog.enable_server)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Server Port:"))
        dialog.port_spinbox = QSpinBox()
        dialog.port_spinbox.setRange(1024, 65535)
        dialog.port_spinbox.setValue(8080)
        port_layout.addWidget(dialog.port_spinbox)
        port_layout.addStretch()
        layout.addLayout(port_layout)
        
        # Allow external
        dialog.allow_external = QCheckBox(
            "Allow external connections (family/team on Wi-Fi)"
        )
        dialog.allow_external.setChecked(True)
        dialog.allow_external.setToolTip(
            "If checked, anyone on your local network can view the data.\n"
            "Uncheck if you want localhost-only access."
        )
        layout.addWidget(dialog.allow_external)
        
        # Auto-open browser
        dialog.auto_open_browser = QCheckBox("Auto-open browser after startup")
        dialog.auto_open_browser.setChecked(True)
        layout.addWidget(dialog.auto_open_browser)
        
        # Info box
        info = QLabel(
            "ℹ️  Web server allows family/team to view sonar data in any "
            "browser without installing software.\n\n"
            "Share the IP address shown after export. Works offline "
            "on same Wi-Fi network."
        )
        info.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Add method to get config
        def get_config():
            return {
                'enabled': dialog.enable_server.isChecked(),
                'port': dialog.port_spinbox.value(),
                'allow_external': dialog.allow_external.isChecked(),
                'auto_open_browser': dialog.auto_open_browser.isChecked()
            }
        
        dialog.get_config = get_config
        
        return dialog


class ShareLinkDialog:
    """Create PyQt5 dialog for sharing web server link"""
    
    @staticmethod
    def create_dialog(
        parent=None,
        share_url: str = None,
        survey_id: str = None,
        search_area: str = None
    ):
        """
        Create dialog showing shareable URL for web server
        
        Example:
            dialog = ShareLinkDialog.create_dialog(
                parent=main_window,
                share_url='http://192.168.1.100:8080',
                survey_id='SarOp-2025-11-25-001',
                search_area='Monterey Canyon'
            )
            dialog.exec_()
        """
        
        if not HAS_PYQT5:
            logger.warning("PyQt5 not available, returning None")
            return None
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("Share Sonar Data")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📍 Share This Link with Your Team")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #667eea;")
        layout.addWidget(title)
        
        # Survey info
        if survey_id or search_area:
            info_text = []
            if survey_id:
                info_text.append(f"<b>Survey ID:</b> {survey_id}")
            if search_area:
                info_text.append(f"<b>Search Area:</b> {search_area}")
            
            info = QLabel("<br/>".join(info_text))
            info.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 10px;")
            layout.addWidget(info)
        
        # Share URL section
        url_label = QLabel("Shareable Link:")
        url_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(url_label)
        
        url_edit = QLineEdit(share_url or "http://localhost:8080")
        url_edit.setReadOnly(True)
        url_edit.selectAll()
        url_edit.setStyleSheet(
            "QLineEdit { padding: 8px; font-size: 12px; "
            "background-color: #f0f0f0; border: 1px solid #ddd; }"
        )
        layout.addWidget(url_edit)
        
        # Copy button
        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.setStyleSheet(
            "QPushButton { background-color: #667eea; color: white; "
            "padding: 8px; border-radius: 4px; font-weight: bold; }"
        )
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(share_url or "http://localhost:8080")
        )
        layout.addWidget(copy_btn)
        
        # Instructions
        instructions = QLabel(
            "<b>How to Share:</b><br/>"
            "• Send this link to family/team members<br/>"
            "• They open the link in any web browser<br/>"
            "• No installation needed - works on phones, tablets, laptops<br/>"
            "• Works offline if they're on the same Wi-Fi network<br/>"
            "<br/>"
            "<b>Features:</b><br/>"
            "• Interactive map with zoom/pan<br/>"
            "• Measure distances and areas<br/>"
            "• Toggle sonar layers on/off<br/>"
            "• Export data as GeoJSON<br/>"
            "<br/>"
            "<i>Note: Link only works while SonarSniffer is running.</i>"
        )
        instructions.setStyleSheet("color: #555; font-size: 11px; line-height: 1.6;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        return dialog


# Convenience functions for minimal integration

def get_web_server_config(parent=None):
    """
    Show configuration dialog and return config dict
    
    Usage in sonar_gui.py:
        config = get_web_server_config(parent=self)
        if config:
            # User clicked OK
            if config['enabled']:
                # Start server with these settings
                pass
    """
    
    if not HAS_PYQT5:
        logger.warning("PyQt5 not available")
        return None
    
    dialog = WebServerConfigDialog.create_dialog(parent=parent)
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_config()
    return None


def show_share_link_dialog(parent=None, server=None, survey_id=None, search_area=None):
    """
    Show share link dialog
    
    Usage in sonar_gui.py:
        show_share_link_dialog(
            parent=self,
            server=result.server,
            survey_id='SarOp-2025-11-25-001',
            search_area='Monterey Canyon'
        )
    """
    
    if not HAS_PYQT5:
        logger.warning("PyQt5 not available")
        return
    
    share_url = f"http://{server._get_local_ip()}:{server.port}" if server else None
    dialog = ShareLinkDialog.create_dialog(
        parent=parent,
        share_url=share_url,
        survey_id=survey_id,
        search_area=search_area
    )
    if dialog:
        dialog.exec_()


# Example: Minimal sonar_gui.py integration

MINIMAL_INTEGRATION_EXAMPLE = """
# Add to sonar_gui.py

from sar_web_server_integration_helper import (
    ExportWithWebServer,
    show_share_link_dialog,
    get_web_server_config
)

class SonarGUI:
    def export_button_clicked(self):
        '''Handle export button click'''
        
        # Step 1: Get web server config (optional)
        web_config = get_web_server_config(parent=self)
        if not web_config:
            return  # User cancelled
        
        if not web_config['enabled']:
            # Export without web server (existing code)
            self.export_data_only()
            return
        
        # Step 2: Export with web server
        result = ExportWithWebServer.export_and_serve(
            parent_window=self,
            export_dir=self.output_dir,
            sonar_files=self.sonar_files,
            survey_metadata={
                'survey_id': self.get_survey_id(),
                'search_area': self.get_search_area(),
                'contact_info': self.get_contact_info()
            },
            port=web_config['port'],
            auto_open=web_config['auto_open_browser']
        )
        
        if not result.success:
            self.show_error(f"Export failed: {result.message}")
            return
        
        # Step 3: Show share link dialog
        show_share_link_dialog(
            parent=self,
            server=result.server,
            survey_id=result.survey_id,
            search_area=self.get_search_area()
        )
        
        self.show_message(f"✓ {result.message}\\nShare: {result.share_url}")
"""


if __name__ == '__main__':
    # Test without GUI
    print("=== SAR Web Server Integration Helper ===")
    print()
    print("Usage in sonar_gui.py:")
    print(MINIMAL_INTEGRATION_EXAMPLE)
    print()
    print("Or for advanced integration:")
    print("  - Use ExportWithWebServer.export_and_serve()")
    print("  - Use get_web_server_config(parent=window)")
    print("  - Use show_share_link_dialog(parent=window, server=server)")
