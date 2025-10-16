#!/usr/bin/env python3
# block_pipeline.py - Enhanced block-based left/right channel processing with auto-alignment

import csv, json, mmap
from dataclasses import dataclass
from typing import List, Tuple, Iterator, Optional, Dict, Any
from pathlib import Path
import numpy as np
from PIL import Image
import struct

@dataclass
class RSDRecord:
    """Enhanced record with all fields for complete processing"""
    ofs: int
    channel_id: Optional[int]
    seq: int
    time_ms: int
    lat: Optional[float]
    lon: Optional[float] 
    depth_m: Optional[float]
    sample_cnt: Optional[int]
    sonar_ofs: Optional[int]
    sonar_size: Optional[int]
    beam_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    roll_deg: Optional[float] = None
    heave_m: Optional[float] = None
    tx_ofs_m: Optional[float] = None
    rx_ofs_m: Optional[float] = None
    color_id: Optional[int] = None
    extras: Optional[Dict[str, Any]] = None

def read_records_from_csv(csv_path: str) -> List[RSDRecord]:
    """Read RSD records from CSV with all available fields"""
    records = []
    with open(csv_path, 'r', encoding='utf-8', newline='') as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            try:
                # Parse extras JSON if present
                extras = None
                if 'extras_json' in row and row['extras_json']:
                    try:
                        extras = json.loads(row['extras_json'])
                    except:
                        pass
                
                # Helper function to safely convert values
                def safe_float(val, default=None):
                    try:
                        return float(val) if val and val.strip() else default
                    except (ValueError, AttributeError):
                        return default
                
                def safe_int(val, default=None):
                    try:
                        return int(val) if val and val.strip() else default
                    except (ValueError, AttributeError):
                        return default
                
                record = RSDRecord(
                    ofs=safe_int(row.get('ofs'), 0),
                    channel_id=safe_int(row.get('channel_id')),
                    seq=safe_int(row.get('seq'), 0),
                    time_ms=safe_int(row.get('time_ms'), 0),
                    lat=safe_float(row.get('lat')),
                    lon=safe_float(row.get('lon')),
                    depth_m=safe_float(row.get('depth_m')),
                    sample_cnt=safe_int(row.get('sample_cnt')),
                    sonar_ofs=safe_int(row.get('sonar_ofs')),
                    sonar_size=safe_int(row.get('sonar_size')),
                    beam_deg=safe_float(row.get('beam_deg')),
                    pitch_deg=safe_float(row.get('pitch_deg')),
                    roll_deg=safe_float(row.get('roll_deg')),
                    heave_m=safe_float(row.get('heave_m')),
                    tx_ofs_m=safe_float(row.get('tx_ofs_m')),
                    rx_ofs_m=safe_float(row.get('rx_ofs_m')),
                    color_id=safe_int(row.get('color_id')),
                    extras=extras
                )
                records.append(record)
            except Exception as e:
                continue  # Skip malformed rows
    return records

def split_by_channels(records: List[RSDRecord]) -> Dict[int, List[RSDRecord]]:
    """Split records by channel ID and sort by sequence"""
    by_channel = {}
    for record in records:
        if record.channel_id is not None:
            if record.channel_id not in by_channel:
                by_channel[record.channel_id] = []
            by_channel[record.channel_id].append(record)
    
    # Sort each channel by sequence
    for channel_id in by_channel:
        by_channel[channel_id].sort(key=lambda r: r.seq)
    
    return by_channel

def create_channel_blocks(channel_records: List[RSDRecord], block_size: int = 50) -> List[List[RSDRecord]]:
    """Create blocks of records for processing"""
    blocks = []
    print(f"Creating blocks from {len(channel_records)} records with block_size={block_size}")
    
    for i in range(0, len(channel_records), block_size):
        block = channel_records[i:i + block_size]
        if len(block) >= 5:  # Lower threshold - keep blocks with at least 5 records
            blocks.append(block)
            print(f"  Block {len(blocks)-1}: {len(block)} records (seq {block[0].seq} - {block[-1].seq})")
    
    print(f"Created {len(blocks)} total blocks")
    return blocks

def pair_channel_blocks(left_blocks: List[List[RSDRecord]], 
                       right_blocks: List[List[RSDRecord]]) -> List[Tuple[List[RSDRecord], List[RSDRecord]]]:
    """Pair blocks from left and right channels based on sequence alignment"""
    paired_blocks = []
    
    print(f"Pairing {len(left_blocks)} left blocks with {len(right_blocks)} right blocks")
    
    # Use simple index-based pairing to ensure we get multiple blocks
    max_pairs = min(len(left_blocks), len(right_blocks))
    
    for i in range(max_pairs):
        left_block = left_blocks[i]
        right_block = right_blocks[i]
        
        if left_block and right_block:
            paired_blocks.append((left_block, right_block))
            print(f"  Paired block {i}: Left {len(left_block)} records, Right {len(right_block)} records")
    
    print(f"Created {len(paired_blocks)} paired blocks")
    return paired_blocks

def extract_sonar_data(rsd_path: str, record: RSDRecord) -> bytes:
    """Extract sonar data payload from RSD file"""
    if not record.sonar_ofs or not record.sonar_size:
        return b''
    
    try:
        with open(rsd_path, 'rb') as f:
            f.seek(record.sonar_ofs)
            return f.read(record.sonar_size)
    except Exception:
        return b''

def render_sonar_row(payload: bytes, width: int = 1024, intensity_scale: float = 1.0) -> np.ndarray:
    """Render sonar payload as grayscale row with intensity scaling"""
    if not payload:
        return np.zeros((1, width), dtype=np.uint8)
    
    # Convert bytes to intensity values
    raw_data = np.frombuffer(payload, dtype=np.uint8)
    
    # Scale to desired width
    if len(raw_data) != width:
        # Interpolate to target width
        x_old = np.linspace(0, 1, len(raw_data))
        x_new = np.linspace(0, 1, width)
        raw_data = np.interp(x_new, x_old, raw_data)
    
    # Apply intensity scaling and convert to uint8
    scaled_data = np.clip(raw_data * intensity_scale, 0, 255).astype(np.uint8)
    
    return scaled_data.reshape(1, -1)

def calculate_phase_correlation_shift(left_data: np.ndarray, right_data: np.ndarray, 
                                    max_shift: int = 50) -> int:
    """Calculate horizontal shift using phase correlation for better alignment"""
    if left_data.size == 0 or right_data.size == 0:
        return 0
    
    # Ensure same dimensions
    min_width = min(left_data.shape[1], right_data.shape[1])
    left_row = left_data[0, :min_width].astype(np.float32)
    right_row = right_data[0, :min_width].astype(np.float32)
    
    # Apply window to reduce edge effects
    window = np.hanning(min_width)
    left_row *= window
    right_row *= window
    
    # Cross-correlation via FFT
    f_left = np.fft.fft(left_row)
    f_right = np.fft.fft(right_row)
    
    # Phase correlation
    cross_power = f_left * np.conj(f_right)
    cross_power /= (np.abs(cross_power) + 1e-10)  # Normalize
    
    # Get correlation in spatial domain
    correlation = np.fft.ifft(cross_power)
    correlation = np.abs(correlation)
    
    # Find peak within allowed shift range
    shift_range = min(max_shift, min_width // 4)
    
    # Check positive shifts (right channel moves right)
    best_shift = 0
    best_score = correlation[0]
    
    for shift in range(1, shift_range + 1):
        if correlation[shift] > best_score:
            best_score = correlation[shift]
            best_shift = shift
        
        # Check negative shifts (right channel moves left)
        neg_idx = min_width - shift
        if correlation[neg_idx] > best_score:
            best_score = correlation[neg_idx]
            best_shift = -shift
    
    return int(best_shift)

def auto_align_block_pair(rsd_path: str, left_block: List[RSDRecord], 
                         right_block: List[RSDRecord]) -> Tuple[int, float]:
    """Auto-align a pair of blocks and return optimal shift and confidence score"""
    if not left_block or not right_block:
        return 0, 0.0
    
    # Sample a few rows from middle of each block for alignment
    sample_size = min(5, len(left_block), len(right_block))
    mid_start = len(left_block) // 2 - sample_size // 2
    
    left_samples = left_block[mid_start:mid_start + sample_size]
    right_samples = right_block[mid_start:mid_start + sample_size]
    
    shifts = []
    
    for left_rec, right_rec in zip(left_samples, right_samples):
        left_payload = extract_sonar_data(rsd_path, left_rec)
        right_payload = extract_sonar_data(rsd_path, right_rec)
        
        if left_payload and right_payload:
            left_row = render_sonar_row(left_payload)
            right_row = render_sonar_row(right_payload)
            
            shift = calculate_phase_correlation_shift(left_row, right_row)
            shifts.append(shift)
    
    if not shifts:
        return 0, 0.0
    
    # Calculate consensus shift and confidence
    shifts = np.array(shifts)
    median_shift = int(np.median(shifts))
    confidence = 1.0 - (np.std(shifts) / (np.std(shifts) + 10.0))  # Normalize confidence
    
    return median_shift, confidence

def compose_channel_block_preview(rsd_path: str, left_block: List[RSDRecord], 
                                right_block: List[RSDRecord], 
                                preview_mode: str = "both",
                                width: int = 512, 
                                flip_left: bool = False, flip_right: bool = False,
                                remove_water_column: bool = False,
                                water_column_pixels: int = 50) -> np.ndarray:
    """Create proper sidescan preview with left and right channels stitched horizontally
    
    This creates a traditional sidescan sonar waterfall view where:
    - Each ping (row) shows: [LEFT CHANNEL | CENTER GAP | RIGHT CHANNEL]
    - Multiple pings are stacked vertically to show the sonar track over time
    - This produces the classic "waterfall" view with seafloor on both sides
    """
    
    def extract_channel_ping_data(record: RSDRecord, target_width: int, flip: bool) -> np.ndarray:
        """Extract and process sonar data for a single ping from one channel"""
        try:
            sonar_data = extract_sonar_data(rsd_path, record)
            
            if sonar_data and len(sonar_data) > 0:
                # Convert bytes to numpy array
                raw_array = np.frombuffer(sonar_data, dtype=np.uint8)
                
                # Scale to 0-255 range 
                if raw_array.max() > 0:
                    intensity_data = (raw_array.astype(np.float32) * 255.0 / raw_array.max()).astype(np.uint8)
                else:
                    intensity_data = raw_array.astype(np.uint8)
                
                # Resize to target width if needed
                if len(intensity_data) != target_width:
                    x_old = np.linspace(0, 1, len(intensity_data))
                    x_new = np.linspace(0, 1, target_width)
                    intensity_data = np.interp(x_new, x_old, intensity_data).astype(np.uint8)
                
                # Apply flipping if requested
                if flip:
                    intensity_data = intensity_data[::-1]
                
                return intensity_data
            else:
                # No data - return zeros
                return np.zeros(target_width, dtype=np.uint8)
                
        except Exception as e:
            print(f"Error extracting ping data: {e}")
            return np.zeros(target_width, dtype=np.uint8)
    
    # Determine how many pings we have
    num_pings = min(len(left_block), len(right_block)) if left_block and right_block else 0
    if num_pings == 0:
        print("No valid ping pairs found")
        return np.zeros((50, width), dtype=np.uint8)
    
    print(f"Creating sidescan waterfall: {num_pings} pings")
    
    # For sidescan, each channel gets half the width
    channel_width = width // 2
    gap_width = 4  # Small gap between channels
    
    # Calculate final dimensions
    total_width = channel_width * 2 + gap_width
    waterfall_height = num_pings
    
    # Create the waterfall image
    waterfall = np.zeros((waterfall_height, total_width), dtype=np.uint8)
    
    print(f"Waterfall dimensions: {waterfall_height} x {total_width}")
    print(f"Channel width: {channel_width}, Gap: {gap_width}")
    
    # Process each ping pair
    for ping_idx in range(num_pings):
        if ping_idx < len(left_block) and ping_idx < len(right_block):
            left_record = left_block[ping_idx]
            right_record = right_block[ping_idx]
            
            # Extract data for each channel
            left_data = extract_channel_ping_data(left_record, channel_width, flip_left)
            right_data = extract_channel_ping_data(right_record, channel_width, flip_right)
            
            # Remove water column from left channel (crop from right side - boat side)
            if remove_water_column and water_column_pixels > 0:
                if len(left_data) > water_column_pixels:
                    left_data = left_data[:-water_column_pixels]
                    # Pad back to channel_width
                    left_data = np.pad(left_data, (0, channel_width - len(left_data)), 'constant')
            
            # Remove water column from right channel (crop from left side - boat side)  
            if remove_water_column and water_column_pixels > 0:
                if len(right_data) > water_column_pixels:
                    right_data = right_data[water_column_pixels:]
                    # Pad back to channel_width
                    right_data = np.pad(right_data, (channel_width - len(right_data), 0), 'constant')
            
            # Compose the ping row: [LEFT | GAP | RIGHT]
            ping_row = np.zeros(total_width, dtype=np.uint8)
            ping_row[0:channel_width] = left_data[:channel_width]  # Left channel
            # Gap stays black (zeros)
            ping_row[channel_width + gap_width:] = right_data[:channel_width]  # Right channel
            
            # Set this row in the waterfall
            waterfall[ping_idx, :] = ping_row
    
    print(f"Completed waterfall: {waterfall.shape}, range: {waterfall.min()}-{waterfall.max()}")
    
    # Handle different preview modes
    if preview_mode == "left":
        return waterfall[:, :channel_width]
    elif preview_mode == "right": 
        return waterfall[:, channel_width + gap_width:]
    else:  # "both" or any other mode
        return waterfall

def compose_aligned_block(rsd_path: str, left_block: List[RSDRecord], 
                         right_block: List[RSDRecord], shift: int = 0,
                         width: int = 1024, gap: int = 8,
                         flip_left: bool = False, flip_right: bool = False) -> np.ndarray:
    """Compose aligned waterfall image from block pair"""
    max_rows = max(len(left_block), len(right_block))
    
    # Create output image
    total_width = width * 2 + gap
    output = np.zeros((max_rows, total_width), dtype=np.uint8)
    
    for i in range(max_rows):
        # Process left channel
        if i < len(left_block):
            left_payload = extract_sonar_data(rsd_path, left_block[i])
            left_row = render_sonar_row(left_payload, width)
            if flip_left:
                left_row = np.fliplr(left_row)
            output[i, :width] = left_row[0]
        
        # Process right channel with shift
        right_idx = i + shift
        if 0 <= right_idx < len(right_block):
            right_payload = extract_sonar_data(rsd_path, right_block[right_idx])
            right_row = render_sonar_row(right_payload, width)
            if flip_right:
                right_row = np.fliplr(right_row)
            output[i, width + gap:] = right_row[0]
    
    return output

def detect_transducer_config(records: List[RSDRecord]) -> Dict[str, Any]:
    """Detect transducer configuration from record patterns and metadata"""
    config = {
        'scan_type': 'unknown',
        'frequency_bands': [],
        'beam_angles': [],
        'suggested_pairs': [],
        'transducer_serial': None
    }
    
    # Analyze channel patterns
    by_channel = split_by_channels(records)
    channels = sorted(by_channel.keys())
    
    # Detect scan type based on channel count and sample patterns
    if len(channels) == 2:
        config['scan_type'] = 'sidescan_dual'
        config['suggested_pairs'] = [(channels[0], channels[1])]
    elif len(channels) == 1:
        config['scan_type'] = 'sidescan_single'
    elif len(channels) >= 3:
        config['scan_type'] = 'multibeam_or_chirp'
        # Pair adjacent channels
        for i in range(0, len(channels) - 1, 2):
            if i + 1 < len(channels):
                config['suggested_pairs'].append((channels[i], channels[i + 1]))
    
    # Extract transducer info from extras
    for record in records[:100]:  # Check first 100 records
        if record.extras:
            for key, value in record.extras.items():
                if 'serial' in key.lower() and isinstance(value, str):
                    config['transducer_serial'] = value
                    break
            if config['transducer_serial']:
                break
    
    return config

class BlockProcessor:
    """Main class for block-based channel processing"""
    
    def __init__(self, csv_path: str, rsd_path: str, block_size: int = 50):
        self.csv_path = Path(csv_path)
        self.rsd_path = Path(rsd_path)
        self.block_size = block_size
        self.records = read_records_from_csv(str(csv_path))
        self.by_channel = split_by_channels(self.records)
        self.config = detect_transducer_config(self.records)
    
    def get_available_channels(self) -> List[int]:
        """Get list of available channel IDs"""
        return sorted(self.by_channel.keys())
    
    def get_channel_blocks(self, channel_id: int) -> List[List[RSDRecord]]:
        """Get blocks for specific channel"""
        if channel_id not in self.by_channel:
            return []
        return create_channel_blocks(self.by_channel[channel_id], self.block_size)
    
    def process_channel_pair(self, left_channel: int, right_channel: int,
                           auto_align: bool = True, manual_shift: int = 0,
                           flip_left: bool = False, flip_right: bool = False) -> Iterator[Dict[str, Any]]:
        """Process paired channels in blocks with alignment"""
        left_blocks = self.get_channel_blocks(left_channel)
        right_blocks = self.get_channel_blocks(right_channel)
        
        paired_blocks = pair_channel_blocks(left_blocks, right_blocks)
        
        for block_idx, (left_block, right_block) in enumerate(paired_blocks):
            result = {
                'block_index': block_idx,
                'left_channel': left_channel,
                'right_channel': right_channel,
                'left_records': len(left_block),
                'right_records': len(right_block),
                'shift': manual_shift,
                'confidence': 0.0,
                'image': None
            }
            
            # Auto-align if requested
            if auto_align:
                auto_shift, confidence = auto_align_block_pair(
                    str(self.rsd_path), left_block, right_block)
                result['shift'] = auto_shift + manual_shift
                result['confidence'] = confidence
            
            # Compose aligned image
            result['image'] = compose_aligned_block(
                str(self.rsd_path), left_block, right_block, 
                result['shift'], flip_left=flip_left, flip_right=flip_right)
            
            yield result
    
    def export_block_results(self, output_dir: str, left_channel: int, right_channel: int,
                           **kwargs) -> List[str]:
        """Export processed blocks as images and metadata"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        for result in self.process_channel_pair(left_channel, right_channel, **kwargs):
            block_idx = result['block_index']
            
            # Save image
            if result['image'] is not None:
                img = Image.fromarray(result['image'], mode='L')
                img_path = output_path / f"block_{block_idx:04d}_ch{left_channel:02d}_{right_channel:02d}.png"
                img.save(img_path)
                exported_files.append(str(img_path))
            
            # Save metadata
            meta_path = output_path / f"block_{block_idx:04d}_ch{left_channel:02d}_{right_channel:02d}.json"
            meta_data = {k: v for k, v in result.items() if k != 'image'}
            with open(meta_path, 'w') as f:
                json.dump(meta_data, f, indent=2)
            exported_files.append(str(meta_path))
        
        return exported_files

# Utility functions for GUI integration
def get_suggested_channel_pairs(csv_path: str) -> List[Tuple[int, int]]:
    """Get suggested channel pairs for processing"""
    records = read_records_from_csv(csv_path)
    config = detect_transducer_config(records)
    return config.get('suggested_pairs', [])

def get_transducer_info(csv_path: str) -> Dict[str, Any]:
    """Get transducer configuration information"""
    records = read_records_from_csv(csv_path)
    return detect_transducer_config(records)