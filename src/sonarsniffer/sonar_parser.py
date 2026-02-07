#!/usr/bin/env python3
"""
SonarSniffer Parser Module

Unified interface for parsing various sonar data formats (RSD, SON, XTF)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Handle both package and direct imports
try:
    from .engine_nextgen_syncfirst import parse_rsd_records_nextgen, RSDRecord
except ImportError:
    # Fallback for direct script execution
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from engine_nextgen_syncfirst import parse_rsd_records_nextgen, RSDRecord


class SonarParser:
    """
    Unified sonar data parser supporting multiple formats
    """

    def __init__(self):
        self.supported_formats = [".rsd", ".son", ".xtf"]

    def parse_file(
        self, file_path: str, max_records: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Parse a sonar data file

        Args:
            file_path: Path to the sonar data file
            max_records: Maximum number of records to parse (None for all)

        Returns:
            Dictionary containing parsed data and metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Warn on likely synthetic / generated samples to avoid accidental "real-world" tests
        try:
            if self._is_likely_synthetic(file_path):
                logger.warning(
                    "Likely synthetic sample detected: %s — synthetic samples should be kept in samples/synthetic/ and avoided for real-world tests",
                    file_path,
                )
        except Exception:
            pass

        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()

        if file_ext not in self.supported_formats:
            raise ValueError(
                f"Unsupported file format: {file_ext}. Supported: {self.supported_formats}"
            )

        if file_ext == ".rsd":
            return self._parse_rsd_file(str(file_path), max_records)
        elif file_ext == ".son":
            return self._parse_son_file(str(file_path), max_records)
        elif file_ext == ".xtf":
            return self._parse_xtf_file(str(file_path), max_records)
        else:
            raise ValueError(f"No parser available for format: {file_ext}")

    def _try_use_rust_parser(self, file_path: str, max_records: Optional[int] = None):
        """Attempt to parse using compiled rust extension if available."""
        try:
            # rust extension may be built for a different Python ABI — import may fail
            import rsd_parser_rust as rustp

            if hasattr(rustp, "parse_rsd_records"):
                # Expect parse_rsd_records(path, limit) -> iterable of records-like tuples/dicts
                records = list(rustp.parse_rsd_records(file_path, max_records or 0))
                return records
        except Exception:
            pass

        return None

    def _is_likely_synthetic(self, file_path: str) -> bool:
        """Heuristic check to detect synthetic or generated sample files.

        Criteria:
          - filename contains 'synthetic'
          - file size is very small (< 10 KB)

        Returns True when the file likely represents synthetic/generated data.
        """
        try:
            name = os.path.basename(str(file_path)).lower()
            if "synthetic" in name:
                return True
            size = os.path.getsize(str(file_path))
            if size <= 10 * 1024:
                return True
        except Exception:
            # Conservative default: not synthetic if we can't inspect
            return False

        return False

    def _parse_rsd_file(
        self, file_path: str, max_records: Optional[int] = None
    ) -> Dict[str, Any]:
        """Parse Garmin RSD format file"""
        # Prefer compiled Rust parser when available for performance
        records = self._try_use_rust_parser(file_path, max_records)
        if records is None:
            records = list(
                parse_rsd_records_nextgen(file_path, limit_records=max_records or 0)
            )

        # Extract metadata
        metadata = {
            "filename": os.path.basename(file_path),
            "format": "RSD",
            "total_records_in_file": len(records),  # All records from file
            "file_size": os.path.getsize(file_path),
        }

        # Calculate bounds if records exist
        if records:
            import math

            # Filter for valid coordinates: not 0, not NaN, within valid ranges
            # Valid latitude: -90 to 90, Valid longitude: -180 to 180
            valid_records = [
                r
                for r in records
                if (
                    r.lat != 0.0
                    and not math.isnan(r.lat)
                    and -90 <= r.lat <= 90
                    and r.lon != 0.0
                    and not math.isnan(r.lon)
                    and -180 <= r.lon <= 180
                )
            ]

            # Count valid records for display
            metadata["record_count"] = len(valid_records)

            lats = [r.lat for r in valid_records]
            lons = [r.lon for r in valid_records]

            if lats and lons:
                metadata.update(
                    {
                        "bounds": {
                            "north": max(lats),
                            "south": min(lats),
                            "east": max(lons),
                            "west": min(lons),
                        },
                        "center_lat": sum(lats) / len(lats),
                        "center_lon": sum(lons) / len(lons),
                    }
                )

            depths = [r.depth_m for r in valid_records if r.depth_m > 0]
            if depths:
                metadata.update(
                    {
                        "depth_range": f"{min(depths):.1f}m - {max(depths):.1f}m",
                        "min_depth": min(depths),
                        "max_depth": max(depths),
                    }
                )

        # Convert records to dictionaries for easier processing
        data_records = []
        for record in records:
            data_records.append(
                {
                    "ofs": getattr(record, "ofs", None),
                    "channel_id": getattr(record, "channel_id", None),
                    "seq": getattr(record, "seq", None),
                    "time_ms": getattr(record, "time_ms", None),
                    "lat": getattr(record, "lat", None),
                    "lon": getattr(record, "lon", None),
                    "depth_m": getattr(record, "depth_m", None),
                    "sample_cnt": getattr(record, "sample_cnt", None),
                    "sonar_ofs": getattr(record, "sonar_ofs", None),
                    "sonar_size": getattr(record, "sonar_size", None),
                    "beam_deg": getattr(record, "beam_deg", None),
                    "pitch_deg": getattr(record, "pitch_deg", None),
                    "roll_deg": getattr(record, "roll_deg", None),
                    "heave_m": getattr(record, "heave_m", None),
                    "tx_ofs_m": getattr(record, "tx_ofs_m", None),
                    "rx_ofs_m": getattr(record, "rx_ofs_m", None),
                    "color_id": getattr(record, "color_id", None),
                    "extras": getattr(record, "extras", None),
                }
            )

        return {
            "metadata": metadata,
            "records": data_records,
        }

    def parse_file_in_chunks(self, file_path: str, batch_size: int = 1000):
        """Yield batches of parsed records (as dicts) for large file processing.

        This uses the existing iterators in the parsing engine to avoid loading
        the entire file into memory. It supports RSD format currently.
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()

        if ext == ".rsd":
            # Try compiled rust parser first — if it returns a list, yield slices
            try:
                import rsd_parser_rust as rustp

                if hasattr(rustp, "parse_rsd_records"):
                    all_records = list(rustp.parse_rsd_records(str(file_path), 0))
                    for i in range(0, len(all_records), batch_size):
                        batch = all_records[i : i + batch_size]
                        yield [self._record_to_dict(r) for r in batch]
                    return
            except Exception:
                pass

            # Fallback to the Python generator which yields RSDRecord objects
            batch = []
            for r in parse_rsd_records_nextgen(str(file_path), limit_records=0):
                batch.append(r)
                if len(batch) >= batch_size:
                    yield [self._record_to_dict(rr) for rr in batch]
                    batch = []
            if batch:
                yield [self._record_to_dict(rr) for rr in batch]
            return

        # For other formats, fall back to non-chunked parse and yield the full record set once
        parsed = self.parse_file(str(file_path))
        yield parsed.get("records", [])

    def _record_to_dict(self, record):
        return {
            "ofs": record.ofs,
            "channel_id": record.channel_id,
            "seq": record.seq,
            "time_ms": record.time_ms,
            "lat": record.lat,
            "lon": record.lon,
            "depth_m": record.depth_m,
            "sample_cnt": record.sample_cnt,
            "sonar_ofs": record.sonar_ofs,
            "sonar_size": record.sonar_size,
            "beam_deg": record.beam_deg,
            "pitch_deg": record.pitch_deg,
            "roll_deg": record.roll_deg,
            "heave_m": record.heave_m,
            "tx_ofs_m": record.tx_ofs_m,
            "rx_ofs_m": record.rx_ofs_m,
            "color_id": record.color_id,
            "extras": record.extras,
        }

    def _parse_son_file(
        self, file_path: str, max_records: Optional[int] = None
    ) -> Dict[str, Any]:
        """Parse SON format file - placeholder implementation"""
        # TODO: Implement SON parser
        raise NotImplementedError("SON format parsing not yet implemented")

    def _parse_xtf_file(
        self, file_path: str, max_records: Optional[int] = None
    ) -> Dict[str, Any]:
        """Parse XTF format file - placeholder implementation"""
        # TODO: Implement XTF parser
        raise NotImplementedError("XTF format parsing not yet implemented")

    def get_supported_formats(self) -> list:
        """Get list of supported file formats"""
        return self.supported_formats.copy()
