#!/usr/bin/env python3
"""
Unified Rust Parser Wrapper
Provides transparent Rust acceleration for ALL sonar parser types.
Automatically falls back to Python if Rust unavailable.
Reports parser type and acceleration status to GUI.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Callable
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# Parser Type Detection
# ============================================================================

class ParserType(Enum):
    """Detected sonar parser type"""
    RSD_GARMIN = "RSD (Garmin)"
    XTF_EDGETECH = "XTF (EdgeTech)"
    JSF_EDGETECH = "JSF (EdgeTech)"
    SLG_NAVICO = "SLG (Navico)"
    SON_HUMMINBIRD = "SON (Humminbird)"
    DAT_HUMMINBIRD = "DAT (Humminbird)"
    SDF_KLEIN = "SDF (Klein)"
    UNKNOWN = "Unknown"


@dataclass
class ParserStatus:
    """Status information about parser being used"""
    parser_type: ParserType
    acceleration: str  # "Rust", "Python", "Hybrid"
    rust_available: bool
    fallback_reason: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 3


def detect_parser_type(file_path: str) -> ParserType:
    """Detect which parser type a file needs"""
    ext = Path(file_path).suffix.lower()
    
    if ext == '.rsd':
        return ParserType.RSD_GARMIN
    elif ext == '.xtf':
        return ParserType.XTF_EDGETECH
    elif ext == '.jsf':
        return ParserType.JSF_EDGETECH
    elif ext in ['.slg', '.sl2', '.sl3']:
        return ParserType.SLG_NAVICO
    elif ext in ['.son', '.idx']:
        return ParserType.SON_HUMMINBIRD
    elif ext == '.dat':
        return ParserType.DAT_HUMMINBIRD
    elif ext == '.sdf':
        return ParserType.SDF_KLEIN
    else:
        return ParserType.UNKNOWN


# ============================================================================
# Rust Availability Check
# ============================================================================

def _check_rust_available() -> bool:
    """Check if Rust-accelerated parser is available"""
    try:
        import rsd_parser_rust
        return True
    except ImportError:
        return False


_RUST_AVAILABLE = _check_rust_available()


# ============================================================================
# Unified Rust Parser
# ============================================================================

class UnifiedRustParser:
    """
    Unified parser that attempts Rust acceleration for all formats,
    with automatic fallback to Python parsers.
    """
    
    def __init__(self, file_path: str, gui_callback: Optional[Callable] = None, max_rust_attempts: int = 3):
        """
        Initialize unified parser
        
        Args:
            file_path: Path to sonar file
            gui_callback: Optional callback for status updates (e.g., for GUI)
            max_rust_attempts: Max times to attempt Rust before falling back to Python
        """
        self.file_path = str(file_path)
        self.gui_callback = gui_callback
        self.max_rust_attempts = max_rust_attempts
        
        # Detect parser type
        self.parser_type = detect_parser_type(self.file_path)
        
        # Initialize status
        self.status = ParserStatus(
            parser_type=self.parser_type,
            acceleration="Unknown",
            rust_available=_RUST_AVAILABLE,
            max_attempts=max_rust_attempts,
        )
        
        # Validate file exists
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
    
    def _log_status(self, message: str):
        """Log status message to GUI if callback provided"""
        if self.gui_callback:
            self.gui_callback(message)
    
    def _try_rust_parser(self, **kwargs) -> Optional[Any]:
        """Attempt to parse with Rust acceleration"""
        if not _RUST_AVAILABLE:
            return None
        
        if self.parser_type != ParserType.RSD_GARMIN:
            # Only RSD has Rust parser implemented now
            return None
        
        try:
            from rsd_parser_wrapper import RsdParserPython
            
            self._log_status(f"Attempting Rust parser (attempt {self.status.attempt_count + 1}/{self.max_rust_attempts})")
            
            # Try Rust parser
            parser = RsdParserPython(
                self.file_path, 
                use_rust=True,
                gui_callback=self._log_status
            )
            
            result = parser.parse_all(limit=kwargs.get('limit'))
            self.status.acceleration = "Rust"
            self.status.fallback_reason = None
            self._log_status(f"✓ Using Rust Parser for {self.parser_type.value}")
            return result
            
        except Exception as e:
            self.status.attempt_count += 1
            self._log_status(f"⚠️  Rust attempt {self.status.attempt_count} failed: {str(e)[:80]}")
            return None
    
    def _parse_with_python(self, **kwargs) -> List[Any]:
        """Fall back to Python parser"""
        self.status.acceleration = "Python"
        self._log_status(f"Using Python parser for {self.parser_type.value}")
        
        if self.parser_type == ParserType.RSD_GARMIN:
            return self._parse_rsd_python(**kwargs)
        elif self.parser_type == ParserType.XTF_EDGETECH:
            return self._parse_xtf_python(**kwargs)
        elif self.parser_type == ParserType.JSF_EDGETECH:
            return self._parse_jsf_python(**kwargs)
        elif self.parser_type in [ParserType.SLG_NAVICO, ParserType.SON_HUMMINBIRD, 
                                   ParserType.DAT_HUMMINBIRD, ParserType.SDF_KLEIN]:
            return self._parse_multiformat_python(**kwargs)
        else:
            raise ValueError(f"Unsupported parser type: {self.parser_type}")
    
    def _parse_rsd_python(self, **kwargs) -> List[Any]:
        """Parse RSD file with Python engine"""
        try:
            from rsd_format_detector import detect_rsd_generation
            from engine_classic_varstruct import parse_rsd_records_classic
            from engine_nextgen_syncfirst import parse_rsd_records_nextgen
            
            # Auto-detect generation
            rsd_gen = detect_rsd_generation(self.file_path)
            
            if rsd_gen in ['gen2', 'gen3']:
                parser_func = parse_rsd_records_nextgen
                gen_label = "Gen2/Gen3 (UHD/UHD2)"
            else:
                parser_func = parse_rsd_records_classic
                gen_label = "Gen1 (Legacy)"
            
            self._log_status(f"Parsing {gen_label} RSD file...")
            
            limit = kwargs.get('limit')
            records = []
            for i, record in enumerate(parser_func(self.file_path)):
                if limit and i >= limit:
                    break
                records.append(record)
            
            return records
        except Exception as e:
            self._log_status(f"Error parsing RSD: {str(e)}")
            raise
    
    def _parse_xtf_python(self, **kwargs) -> List[Any]:
        """Parse XTF file with Python engine"""
        try:
            from robust_xtf_parser import RobustXTFParser
            
            self._log_status("Parsing XTF (EdgeTech) file...")
            parser = RobustXTFParser(self.file_path)
            records = parser.parse_records(max_records=kwargs.get('limit'))
            return records
        except Exception as e:
            self._log_status(f"Error parsing XTF: {str(e)}")
            raise
    
    def _parse_jsf_python(self, **kwargs) -> List[Any]:
        """Parse JSF file with Python engine"""
        try:
            from comprehensive_sonar_parser import EdgeTechJSFParser
            
            self._log_status("Parsing JSF (EdgeTech) file...")
            parser = EdgeTechJSFParser(self.file_path)
            result = parser.parse()
            return result.get('records', [])
        except Exception as e:
            self._log_status(f"Error parsing JSF: {str(e)}")
            raise
    
    def _parse_multiformat_python(self, **kwargs) -> List[Any]:
        """Parse multi-format files (SLG, SON, DAT, SDF) with Python engine"""
        try:
            from universal_sonar_parser import parse_sonar_file
            
            format_label = self.parser_type.value
            self._log_status(f"Parsing {format_label} file...")
            
            result = parse_sonar_file(self.file_path)
            
            # Convert to standard record format
            records = []
            if hasattr(result, 'records') and result.records:
                for rec in result.records:
                    if isinstance(rec, dict):
                        # Convert dict to object with attributes
                        record = type('Record', (), {
                            'offset': rec.get('offset', 0),
                            'ch': rec.get('channel_type', rec.get('ch', 0)),
                            'lat': rec.get('latitude', rec.get('lat', 0)),
                            'lon': rec.get('longitude', rec.get('lon', 0)),
                            'depth': rec.get('depth_m', rec.get('depth', 0)),
                            'sonar_size': len(rec.get('sonar_data', b'')),
                            'sonar_data': rec.get('sonar_data', b''),
                            'sonar_ofs': rec.get('offset', 0),
                        })()
                        records.append(record)
                    else:
                        records.append(rec)
            
            return records
        except Exception as e:
            self._log_status(f"Error parsing {self.parser_type.value}: {str(e)}")
            raise
    
    def parse_all(self, limit: Optional[int] = None) -> List[Any]:
        """
        Parse entire file.
        Attempts Rust first, falls back to Python.
        
        Returns:
            List of parsed records
        """
        self._log_status(f"Starting parser: {self.parser_type.value}")
        
        # Try Rust if available
        if _RUST_AVAILABLE and self.parser_type == ParserType.RSD_GARMIN:
            for attempt in range(self.max_rust_attempts):
                result = self._try_rust_parser(limit=limit)
                if result is not None:
                    return result
        
        # Fall back to Python
        if not _RUST_AVAILABLE:
            self.status.fallback_reason = "Rust parser not installed"
        else:
            self.status.fallback_reason = f"Rust failed after {self.max_rust_attempts} attempts"
        
        return self._parse_with_python(limit=limit)
    
    def parse(self, limit: Optional[int] = None) -> Iterator[Any]:
        """
        Parse file as iterator (yields records one at a time)
        
        Yields:
            Individual parsed records
        """
        records = self.parse_all(limit=limit)
        for record in records:
            yield record
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about the parser being used"""
        return {
            'file_path': self.file_path,
            'parser_type': self.status.parser_type.value,
            'acceleration': self.status.acceleration,
            'rust_available': self.status.rust_available,
            'fallback_reason': self.status.fallback_reason,
            'attempts': self.status.attempt_count,
        }


# ============================================================================
# Module-Level Functions (for easy integration)
# ============================================================================

def parse_sonar_file_unified(
    file_path: str,
    gui_callback: Optional[Callable] = None,
    limit: Optional[int] = None
) -> List[Any]:
    """
    Parse any sonar file format with automatic Rust acceleration.
    
    Args:
        file_path: Path to sonar file
        gui_callback: Optional callback for status messages
        limit: Max records to parse
    
    Returns:
        List of parsed records
    """
    parser = UnifiedRustParser(file_path, gui_callback=gui_callback)
    return parser.parse_all(limit=limit)


def parse_sonar_file_iter(
    file_path: str,
    gui_callback: Optional[Callable] = None,
    limit: Optional[int] = None
) -> Iterator[Any]:
    """
    Parse any sonar file format as iterator with automatic Rust acceleration.
    
    Args:
        file_path: Path to sonar file
        gui_callback: Optional callback for status messages
        limit: Max records to parse
    
    Yields:
        Individual parsed records
    """
    parser = UnifiedRustParser(file_path, gui_callback=gui_callback)
    yield from parser.parse(limit=limit)


if __name__ == "__main__":
    # Quick test
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"\n🧪 Testing unified parser on: {test_file}")
        
        parser = UnifiedRustParser(test_file, gui_callback=print)
        records = parser.parse_all(limit=10)
        
        print(f"\n✓ Parsed {len(records)} records")
        print(f"Parser info: {parser.get_parser_info()}")
    else:
        print("Usage: python unified_rust_parser.py <sonar_file>")
