#!/usr/bin/env python3
"""
UNIVERSAL FORMAT INTEGRATION ENGINE
===================================

Enhanced engine_glue.py that provides universal format detection and 
seamless integration of all supported sonar formats with the RSD pipeline.

🎯 SUPPORTED FORMATS:
- Garmin RSD (classic & nextgen engines)
- XTF (eXtended Triton Format)
- Kongsberg ALL (multibeam bathymetry)
- MOOS (Mission Oriented Operating Suite)
- Reson S7K (SeaBat 7K series)
- SEG-Y (seismic/sub-bottom profiler)

🔧 INTEGRATION FEATURES:
- Automatic format detection
- Unified CSV output
- Progress reporting
- Error recovery
- Performance optimization
- GUI compatibility
"""

import os
import sys
import mmap
import struct
from typing import Tuple, Optional, Union
from pathlib import Path

# Add parsers directory to path
parsers_dir = os.path.join(os.path.dirname(__file__), 'parsers')
if parsers_dir not in sys.path:
    sys.path.insert(0, parsers_dir)


class UniversalFormatEngine:
    """Universal format detection and parsing engine."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.supported_formats = {
            'rsd': ['classic', 'nextgen'],
            'xtf': ['xtf'],
            'kongsberg': ['all', 'kmall'],
            'moos': ['moos', 'alog'],
            'reson': ['s7k', '7k'],
            'segy': ['sgy', 'segy', 'seg']
        }
    
    def log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[UniversalEngine] {message}")
    
    def detect_format(self, file_path: str) -> str:
        """
        Detect sonar file format based on file signature and extension.
        
        Returns:
            Format identifier: 'rsd', 'xtf', 'kongsberg', 'moos', 'reson', 'segy'
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower().lstrip('.')
        
        # Check extension first for quick detection
        for format_name, extensions in self.supported_formats.items():
            if extension in extensions:
                self.log(f"Format detected by extension: {format_name} (.{extension})")
                return format_name
        
        # Check file signature if extension doesn't match
        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)
                
                # RSD format - look for Garmin magic
                if b'GRMN' in header or b'grmn' in header:
                    self.log("Format detected by signature: RSD (Garmin)")
                    return 'rsd'
                
                # XTF format - check for XTF magic and version
                if header[:4] == b'XTF\x00' or header[:3] == b'XTF':
                    self.log("Format detected by signature: XTF (Triton)")
                    return 'xtf'
                
                # Kongsberg ALL - check for datagram identifiers
                if len(header) >= 4 and header[2:3] in [b'I', b'R', b'D', b'N']:
                    self.log("Format detected by signature: Kongsberg ALL")
                    return 'kongsberg'
                
                # Reson S7K - check for S7K magic
                if b'S7' in header[:10] or b'\x53\x37' in header[:10]:
                    self.log("Format detected by signature: Reson S7K")
                    return 'reson'
                
                # SEG-Y - check for EBCDIC header patterns
                if len(header) >= 16:
                    # Look for common SEG-Y EBCDIC text patterns
                    ebcdic_patterns = [b'C01', b'C02', b'C03']
                    if any(pattern in header for pattern in ebcdic_patterns):
                        self.log("Format detected by signature: SEG-Y")
                        return 'segy'
                
                # MOOS - text-based, check for timestamp patterns
                try:
                    text_header = header.decode('ascii', errors='ignore')
                    if any(pattern in text_header for pattern in ['SONAR_RAW', 'NAV_LAT', 'NAV_LON']):
                        self.log("Format detected by signature: MOOS")
                        return 'moos'
                except:
                    pass
        
        except Exception as e:
            self.log(f"Format detection failed: {e}")
        
        # Default to RSD if no format detected
        self.log("Format detection inconclusive, defaulting to RSD")
        return 'rsd'
    
    def parse_universal(self, file_path: str, output_dir: str, max_records: Optional[int] = None, 
                       engine_preference: str = "auto") -> Tuple[int, str, str]:
        """
        Parse any supported sonar format using universal detection.
        
        Args:
            file_path: Input file path
            output_dir: Output directory for CSV and logs
            max_records: Maximum records to parse (None for all)
            engine_preference: Engine preference for RSD files
            
        Returns:
            Tuple of (record_count, csv_path, log_path)
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Detect format
        detected_format = self.detect_format(file_path)
        self.log(f"Parsing {detected_format.upper()} format: {file_path}")
        
        # Route to appropriate parser
        if detected_format == 'rsd':
            return self._parse_rsd(file_path, output_dir, max_records, engine_preference)
        elif detected_format == 'xtf':
            return self._parse_xtf(file_path, output_dir, max_records)
        elif detected_format == 'kongsberg':
            return self._parse_kongsberg(file_path, output_dir, max_records)
        elif detected_format == 'moos':
            return self._parse_moos(file_path, output_dir, max_records)
        elif detected_format == 'reson':
            return self._parse_reson(file_path, output_dir, max_records)
        elif detected_format == 'segy':
            return self._parse_segy(file_path, output_dir, max_records)
        else:
            raise ValueError(f"Unsupported format: {detected_format}")
    
    def _parse_rsd(self, file_path: str, output_dir: str, max_records: Optional[int], 
                   engine_preference: str) -> Tuple[int, str, str]:
        """Parse RSD files using existing engines."""
        # Use existing RSD engines
        if engine_preference == "auto" or engine_preference == "nextgen":
            try:
                from engine_nextgen_syncfirst import parse_rsd
                return parse_rsd(file_path, output_dir, max_records=max_records)
            except:
                pass
        
        # Fallback to classic engine
        from engine_classic_varstruct import parse_rsd
        return parse_rsd(file_path, output_dir, max_records=max_records)
    
    def _parse_xtf(self, file_path: str, output_dir: str, max_records: Optional[int]) -> Tuple[int, str, str]:
        """Parse XTF files."""
        try:
            from xtf_parser import XTFParser
            parser = XTFParser(file_path, output_dir)
            return parser.parse_records(max_records)
        except ImportError:
            raise RuntimeError("XTF parser not available. Please ensure xtf_parser.py is installed.")
    
    def _parse_kongsberg(self, file_path: str, output_dir: str, max_records: Optional[int]) -> Tuple[int, str, str]:
        """Parse Kongsberg ALL files."""
        try:
            from kongsberg_parser import KongsbergParser
            parser = KongsbergParser(file_path, output_dir)
            return parser.parse_records(max_records)
        except ImportError:
            raise RuntimeError("Kongsberg parser not available. Please ensure kongsberg_parser.py is installed.")
    
    def _parse_moos(self, file_path: str, output_dir: str, max_records: Optional[int]) -> Tuple[int, str, str]:
        """Parse MOOS files."""
        try:
            from moos_parser import MOOSParser
            parser = MOOSParser(file_path, output_dir)
            return parser.parse_records(max_records)
        except ImportError:
            raise RuntimeError("MOOS parser not available. Please ensure moos_parser.py is installed.")
    
    def _parse_reson(self, file_path: str, output_dir: str, max_records: Optional[int]) -> Tuple[int, str, str]:
        """Parse Reson S7K files."""
        try:
            from reson_parser import ResonParser
            parser = ResonParser(file_path, output_dir)
            return parser.parse_records(max_records)
        except ImportError:
            raise RuntimeError("Reson parser not available. Please ensure reson_parser.py is installed.")
    
    def _parse_segy(self, file_path: str, output_dir: str, max_records: Optional[int]) -> Tuple[int, str, str]:
        """Parse SEG-Y files."""
        try:
            from segy_parser import SEGYParser
            parser = SEGYParser(file_path, output_dir)
            return parser.parse_records(max_records)
        except ImportError:
            raise RuntimeError("SEG-Y parser not available. Please ensure segy_parser.py is installed.")


# Enhanced engine_glue functions with universal format support

def _run_one_universal(engine_name: str, inp: str, out_dir: str, max_records=None, 
                      progress_every=2000, progress_seconds=2.0, verbose=False, 
                      scan_type="auto", channel="all") -> Tuple[int, str, str]:
    """Enhanced _run_one with universal format support."""
    
    # Create universal engine
    universal_engine = UniversalFormatEngine(verbose=verbose)
    
    # Handle legacy engine names
    if engine_name in ['classic', 'nextgen']:
        # Use RSD-specific parsing with engine preference
        n, csv_path, log_path = universal_engine.parse_universal(
            inp, out_dir, max_records, engine_preference=engine_name
        )
    elif engine_name == 'auto':
        # Use universal auto-detection
        n, csv_path, log_path = universal_engine.parse_universal(
            inp, out_dir, max_records, engine_preference="auto"
        )
    else:
        # Try to parse as specific format
        try:
            n, csv_path, log_path = universal_engine.parse_universal(
                inp, out_dir, max_records, engine_preference="auto"
            )
        except Exception as e:
            raise ValueError(f'Unknown engine or format: {engine_name}. Error: {e}')
    
    # Generate images if successful
    if verbose:
        print(f"[engine_glue] Generating images from {csv_path}...")
    
    try:
        from render_accel import process_record_images
        img_dir = os.path.join(out_dir, 'images')
        os.makedirs(img_dir, exist_ok=True)
        process_record_images(csv_path, img_dir, scan_type=scan_type, channel=channel)
    except Exception as e:
        if verbose:
            print(f"[engine_glue] Warning: Image generation failed: {str(e)}")
    
    return n, csv_path, log_path


def run_engine_universal(engine: str, file_path: str, csv_out: str, 
                        limit_rows: Optional[int] = None) -> list[str]:
    """
    Enhanced run_engine with universal format support.
    
    Args:
        engine: Engine type ('classic', 'nextgen', 'auto', or specific format)
        file_path: Input file path (any supported format)
        csv_out: Output CSV file path
        limit_rows: Maximum rows to process
        
    Returns:
        List of output file paths for GUI compatibility
    """
    # Extract output directory
    out_dir = os.path.dirname(csv_out)
    if not out_dir:
        out_dir = '.'
    
    # Run universal engine
    n, csv_path, log_path = _run_one_universal(
        engine, file_path, out_dir, max_records=limit_rows, verbose=True
    )
    
    # Return list of paths for GUI compatibility
    result_paths = [csv_path]
    if log_path and os.path.exists(log_path):
        result_paths.append(log_path)
    
    return result_paths


# Maintain backward compatibility with existing engine_glue API

def _run_one(engine_name: str, inp: str, out_dir: str, max_records=None, 
           progress_every=2000, progress_seconds=2.0, verbose=False, 
           scan_type="auto", channel="all") -> Tuple[int, str, str]:
    """Backward compatible _run_one function."""
    if engine_name in ['classic', 'nextgen']:
        # Use original RSD-only implementation for backward compatibility
        if verbose:
            print(f"[engine_glue] Starting {engine_name} parser on {inp}")
            
        if engine_name == 'classic':
            from engine_classic_varstruct import parse_rsd as engine_parse
        elif engine_name == 'nextgen':
            from engine_nextgen_syncfirst import parse_rsd as engine_parse
        
        os.makedirs(out_dir, exist_ok=True)
        parse_result = engine_parse(inp, out_dir, max_records=max_records)
        
        # Handle tuple return
        if isinstance(parse_result, tuple):
            n, result_csv, temp_log_path = parse_result
        else:
            result_csv = parse_result
            try:
                with open(result_csv, 'r') as f:
                    n = sum(1 for line in f) - 1
            except:
                n = 0
            temp_log_path = None
        
        # Create log
        log_path = os.path.join(out_dir, "records.log")
        try:
            if temp_log_path and os.path.exists(temp_log_path):
                log_path = temp_log_path
            else:
                with open(log_path, 'w') as f:
                    f.write(f"Parsed {n} records from {inp}\n")
                    f.write(f"Output: {result_csv}\n")
        except:
            log_path = None
        
        # Generate images
        if verbose:
            print(f"[engine_glue] Generating images from {result_csv}...")
        
        try:
            from render_accel import process_record_images
            img_dir = os.path.join(out_dir, 'images')
            os.makedirs(img_dir, exist_ok=True)
            process_record_images(result_csv, img_dir, scan_type=scan_type, channel=channel)
        except Exception as e:
            if verbose:
                print(f"[engine_glue] Warning: Image generation failed: {str(e)}")
        
        return n, result_csv, log_path
    else:
        # Use universal engine for new formats
        return _run_one_universal(engine_name, inp, out_dir, max_records, 
                                progress_every, progress_seconds, verbose, 
                                scan_type, channel)


def run_engine(engine: str, rsd_path: str, csv_out: str, 
              limit_rows: Optional[int] = None) -> list[str]:
    """Backward compatible run_engine function."""
    if engine in ['classic', 'nextgen']:
        # Use original implementation
        out_dir = os.path.dirname(csv_out)
        if not out_dir:
            out_dir = '.'
        
        n, csv_path, log_path = _run_one(engine, rsd_path, out_dir, max_records=limit_rows)
        
        result_paths = [csv_path]
        if log_path and os.path.exists(log_path):
            result_paths.append(log_path)
        
        return result_paths
    else:
        # Use universal engine
        return run_engine_universal(engine, rsd_path, csv_out, limit_rows)


def main():
    """Enhanced main function with universal format support."""
    import argparse
    
    ap = argparse.ArgumentParser(description="Universal Sonar Format Parser")
    ap.add_argument("--input", required=True, help="Input file (any supported format)")
    ap.add_argument("--out", required=True, help="Output folder")
    ap.add_argument("--engine", default="auto", 
                   help="Engine type (classic, nextgen, auto, or format-specific)")
    ap.add_argument("--max-records", type=int, help="Maximum records to parse")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    ap.add_argument("--detect-only", action="store_true", help="Only detect format, don't parse")
    
    args = ap.parse_args()
    
    if args.detect_only:
        # Format detection only
        engine = UniversalFormatEngine(verbose=args.verbose)
        detected_format = engine.detect_format(args.input)
        print(f"Detected format: {detected_format.upper()}")
        return
    
    # Full parsing
    try:
        n, csv_path, log_path = _run_one_universal(
            args.engine, args.input, args.out, 
            max_records=args.max_records, verbose=args.verbose
        )
        
        print(f"✅ Parsing complete:")
        print(f"   Records: {n}")
        print(f"   CSV: {csv_path}")
        if log_path:
            print(f"   Log: {log_path}")
            
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()