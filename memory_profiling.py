#!/usr/bin/env python3
"""
Memory Profiling Utility - Monitor and optimize RAM usage
Tracks peak memory, bottlenecks, and provides optimization recommendations
"""

import os
import psutil
import numpy as np
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple
from collections import defaultdict
from datetime import datetime
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Single memory measurement"""
    timestamp: datetime
    rss: float  # Resident set size (MB)
    vms: float  # Virtual memory size (MB)
    percent: float  # Percentage of system memory
    label: str = ""


@dataclass
class MemoryStats:
    """Statistics for memory usage over time"""
    label: str
    start_rss: float
    peak_rss: float
    end_rss: float
    peak_delta: float  # Change from start to peak (MB)
    total_delta: float  # Change from start to end (MB)
    duration: float  # Duration in seconds
    snapshots: List[MemorySnapshot] = field(default_factory=list)
    
    @property
    def efficiency(self) -> float:
        """Memory efficiency score (0-1, higher is better)"""
        if self.total_delta <= 0:
            return 1.0
        return max(0.0, 1.0 - (self.peak_delta / max(self.start_rss, 1.0)))


class MemoryProfiler:
    """
    Track memory usage for analysis and optimization
    
    Usage:
        profiler = MemoryProfiler()
        with profiler.track("data_loading"):
            data = load_large_file()
        profiler.report()
    """
    
    def __init__(self, sample_interval: float = 0.1, warn_threshold: float = 500.0):
        """
        Initialize memory profiler
        
        Args:
            sample_interval: Time between memory measurements (seconds)
            warn_threshold: Issue warning if peak memory exceeds (MB)
        """
        self.sample_interval = sample_interval
        self.warn_threshold = warn_threshold
        self.stats: Dict[str, MemoryStats] = {}
        self.current_process = psutil.Process(os.getpid())
        self.global_peak_rss = 0.0
    
    def get_memory(self) -> Tuple[float, float, float]:
        """
        Get current memory usage
        
        Returns:
            (rss_mb, vms_mb, percent)
        """
        try:
            mem_info = self.current_process.memory_info()
            mem_percent = self.current_process.memory_percent()
            
            rss_mb = mem_info.rss / (1024 * 1024)
            vms_mb = mem_info.vms / (1024 * 1024)
            
            return rss_mb, vms_mb, mem_percent
        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            return 0.0, 0.0, 0.0
    
    @contextmanager
    def track(self, label: str):
        """
        Context manager for tracking memory usage
        
        Usage:
            with profiler.track("operation"):
                do_something()
        """
        start_time = time.time()
        start_rss, _, _ = self.get_memory()
        
        peak_rss = start_rss
        snapshots = []
        
        try:
            # Start monitoring thread would go here
            # For simplicity, sample at start, during, and end
            
            yield
            
        finally:
            # Collect final measurements
            duration = time.time() - start_time
            
            # Sample several times during operation
            for _ in range(5):
                current_rss, current_vms, current_percent = self.get_memory()
                peak_rss = max(peak_rss, current_rss)
                
                snapshot = MemorySnapshot(
                    timestamp=datetime.now(),
                    rss=current_rss,
                    vms=current_vms,
                    percent=current_percent,
                    label=label
                )
                snapshots.append(snapshot)
                
                time.sleep(min(duration / 10, self.sample_interval))
            
            # Final measurement
            end_rss, _, _ = self.get_memory()
            peak_rss = max(peak_rss, end_rss)
            
            # Store stats
            stats = MemoryStats(
                label=label,
                start_rss=start_rss,
                peak_rss=peak_rss,
                end_rss=end_rss,
                peak_delta=peak_rss - start_rss,
                total_delta=end_rss - start_rss,
                duration=duration,
                snapshots=snapshots
            )
            
            self.stats[label] = stats
            self.global_peak_rss = max(self.global_peak_rss, peak_rss)
            
            # Warn if exceeded threshold
            if peak_rss > self.warn_threshold:
                logger.warning(f"Memory warning: {label} used {peak_rss:.1f}MB "
                              f"(threshold: {self.warn_threshold:.1f}MB)")
    
    def estimate_array_size(self, dtype: np.dtype, *shape) -> float:
        """Estimate array size in MB"""
        num_elements = np.prod(shape)
        bytes_per_element = np.dtype(dtype).itemsize
        total_bytes = num_elements * bytes_per_element
        return total_bytes / (1024 * 1024)
    
    def report(self, sort_by: str = "peak_delta") -> str:
        """
        Generate memory profiling report
        
        Args:
            sort_by: Sort criterion ("peak_delta", "total_delta", "duration")
            
        Returns:
            Formatted report string
        """
        if not self.stats:
            return "No memory stats collected"
        
        # Sort stats
        if sort_by == "peak_delta":
            sorted_stats = sorted(self.stats.items(), 
                                 key=lambda x: x[1].peak_delta, reverse=True)
        elif sort_by == "total_delta":
            sorted_stats = sorted(self.stats.items(),
                                 key=lambda x: x[1].total_delta, reverse=True)
        else:  # duration
            sorted_stats = sorted(self.stats.items(),
                                 key=lambda x: x[1].duration, reverse=True)
        
        lines = [
            "=" * 80,
            "MEMORY PROFILING REPORT",
            "=" * 80,
            f"Global peak memory: {self.global_peak_rss:.1f} MB",
            ""
        ]
        
        # Table header
        lines.append(f"{'Operation':<30} {'Peak (MB)':<15} {'Delta (MB)':<15} {'Duration (s)':<15} {'Efficiency':<10}")
        lines.append("-" * 80)
        
        # Table rows
        total_peak_delta = 0
        for label, stats in sorted_stats:
            efficiency_pct = stats.efficiency * 100
            lines.append(
                f"{label[:30]:<30} {stats.peak_rss:<15.1f} "
                f"{stats.peak_delta:<15.1f} {stats.duration:<15.2f} "
                f"{efficiency_pct:<10.0f}%"
            )
            total_peak_delta += stats.peak_delta
        
        lines.append("-" * 80)
        lines.append("")
        
        # Analysis section
        lines.append("ANALYSIS:")
        lines.append(f"  Total operations tracked: {len(self.stats)}")
        lines.append(f"  Average peak delta: {total_peak_delta / len(self.stats):.1f} MB")
        
        # Find largest consumer
        largest = max(sorted_stats, key=lambda x: x[1].peak_delta)
        lines.append(f"  Largest consumer: {largest[0]} ({largest[1].peak_delta:.1f} MB)")
        
        # Recommendations
        lines.append("\nRECOMMENDATIONS:")
        for label, stats in sorted_stats[:3]:
            if stats.peak_delta > 100:
                lines.append(f"  - {label}: Consider streaming/chunking (using {stats.peak_delta:.1f} MB)")
            if stats.efficiency < 0.5:
                lines.append(f"  - {label}: High memory leakage, consider cleanup")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Convert stats to dictionary for logging/saving"""
        return {
            label: {
                "start_rss": stats.start_rss,
                "peak_rss": stats.peak_rss,
                "end_rss": stats.end_rss,
                "peak_delta": stats.peak_delta,
                "total_delta": stats.total_delta,
                "duration": stats.duration,
                "efficiency": stats.efficiency
            }
            for label, stats in self.stats.items()
        }


class MemoryOptimizer:
    """
    Provides memory optimization recommendations and utilities
    """
    
    @staticmethod
    def optimize_array(array: np.ndarray) -> np.ndarray:
        """
        Optimize array memory usage by reducing dtype precision if possible
        
        Example: float64 → float32 saves 50% memory
        """
        current_size = array.nbytes / (1024 * 1024)
        
        # Try reducing precision
        if array.dtype == np.float64:
            optimized = array.astype(np.float32)
            new_size = optimized.nbytes / (1024 * 1024)
            
            if np.allclose(array, optimized, rtol=1e-6):
                logger.info(f"Optimized array: {current_size:.1f} MB → {new_size:.1f} MB "
                           f"({100*(1-new_size/current_size):.0f}% reduction)")
                return optimized
        
        return array
    
    @staticmethod
    def chunk_array(array: np.ndarray, chunk_size: int = 1000) -> List[np.ndarray]:
        """
        Split large array into chunks for memory-efficient processing
        
        Args:
            array: Input array
            chunk_size: Maximum rows per chunk
            
        Returns:
            List of array chunks
        """
        chunks = []
        for i in range(0, len(array), chunk_size):
            chunks.append(array[i:i + chunk_size])
        return chunks
    
    @staticmethod
    def estimate_grid_memory(grid_size: int, dtype=np.float32) -> float:
        """Estimate memory required for 2D grid"""
        bytes_per_element = np.dtype(dtype).itemsize
        total_bytes = grid_size * grid_size * bytes_per_element
        return total_bytes / (1024 * 1024)
    
    @staticmethod
    def get_optimal_chunk_size(available_memory_mb: float = 1000,
                             grid_rows: int = 10000) -> int:
        """
        Calculate optimal chunk size for memory-constrained processing
        
        Args:
            available_memory_mb: Available RAM (MB)
            grid_rows: Total rows to process
            
        Returns:
            Recommended chunk size (rows)
        """
        # Estimate 4 bytes per element
        bytes_per_row = 4 * grid_rows
        available_bytes = available_memory_mb * 1024 * 1024
        
        # Conservative: use 60% of available memory
        chunk_bytes = available_bytes * 0.6
        chunk_rows = max(1, int(chunk_bytes / bytes_per_row))
        
        return chunk_rows


if __name__ == "__main__":
    # Example usage
    profiler = MemoryProfiler(warn_threshold=100)
    
    # Simulate different operations
    with profiler.track("array_creation"):
        arr = np.random.rand(5000, 5000)
        time.sleep(0.1)
    
    with profiler.track("array_processing"):
        result = np.sum(arr, axis=1)
        time.sleep(0.1)
    
    with profiler.track("cleanup"):
        del arr, result
        time.sleep(0.05)
    
    # Generate report
    print(profiler.report())
    
    # Memory estimation examples
    print("\nMemory Estimation Examples:")
    print(f"  5000x5000 float32 grid: {MemoryOptimizer.estimate_grid_memory(5000):.1f} MB")
    print(f"  10000x10000 float32 grid: {MemoryOptimizer.estimate_grid_memory(10000):.1f} MB")
    
    # Optimal chunk sizing
    chunk_size = MemoryOptimizer.get_optimal_chunk_size(available_memory_mb=1000, grid_rows=10000)
    print(f"  Optimal chunk size for 10000-row grid: {chunk_size} rows")
