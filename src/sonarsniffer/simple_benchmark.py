#!/usr/bin/env python3
"""
SIMPLIFIED PERFORMANCE BENCHMARK
===============================

Core performance benchmarking focusing on achievable optimizations
without complex dependencies that may cause compatibility issues.

🎯 CORE BENCHMARKS:
- Baseline single-threaded parsing
- Multi-threaded parallel processing
- Memory-efficient streaming
- Format parser comparisons

⚡ PERFORMANCE VALIDATION:
- 18x competitive advantage target
- Real-world file processing
- Memory efficiency analysis
- Scalability assessment
"""

import os
import sys
import time
import threading
import multiprocessing
import psutil
import tracemalloc
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import statistics
from pathlib import Path


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    name: str
    duration_seconds: float
    records_processed: int
    bytes_processed: int
    memory_peak_mb: float
    records_per_second: float
    mbytes_per_second: float
    competitive_advantage: float
    optimization_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'duration_seconds': self.duration_seconds,
            'records_processed': self.records_processed,
            'bytes_processed': self.bytes_processed,
            'memory_peak_mb': self.memory_peak_mb,
            'records_per_second': self.records_per_second,
            'mbytes_per_second': self.mbytes_per_second,
            'competitive_advantage': self.competitive_advantage,
            'optimization_type': self.optimization_type
        }


class SimpleBenchmark:
    """Simplified performance benchmark without complex dependencies."""
    
    def __init__(self):
        self.baseline_rps = 5555  # Competitor baseline
        self.results: List[BenchmarkResult] = []
        self.test_files: Dict[str, str] = {}
        
        self.system_info = {
            'cpu_count': os.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'platform': sys.platform
        }
        
        print(f"🖥️  System: {self.system_info['cpu_count']} cores, {self.system_info['memory_gb']:.1f}GB RAM")
    
    def create_test_file(self, name: str, size_mb: int):
        """Create a test file with realistic sonar-like data."""
        file_path = f"benchmark_{name}.dat"
        
        if not os.path.exists(file_path):
            print(f"   Creating {name} file ({size_mb}MB)...")
            
            with open(file_path, 'wb') as f:
                bytes_to_write = size_mb * 1024 * 1024
                chunk_size = 64 * 1024
                written = 0
                
                while written < bytes_to_write:
                    remaining = min(chunk_size, bytes_to_write - written)
                    
                    # Create realistic sonar record structure
                    chunk = bytearray()
                    for i in range(0, remaining, 32):
                        record_size = min(32, remaining - i)
                        record = bytearray(record_size)
                        
                        # Add structured data
                        if record_size >= 8:
                            # Offset and timestamp
                            record[0:4] = (written + i).to_bytes(4, 'little')
                            # Use smaller timestamp to avoid overflow
                            timestamp = int(time.time() % (2**31 / 1000) * 1000)
                            record[4:8] = timestamp.to_bytes(4, 'little')
                        
                        if record_size >= 16:
                            # Coordinate data (simulate lat/lon) - use positive values to avoid signed issues
                            record[8:12] = int(45.0 * 1e6).to_bytes(4, 'little')  # Latitude
                            record[12:16] = int(123.0 * 1e6).to_bytes(4, 'little')  # Longitude (positive)
                        
                        if record_size >= 24:
                            # Depth and beam angle
                            record[16:20] = int(100.0 * 1000).to_bytes(4, 'little')  # Depth (mm)
                            record[20:24] = int(45.0 * 1000).to_bytes(4, 'little')  # Beam angle
                        
                        if record_size >= 32:
                            # Additional sonar data
                            record[24:28] = int(1024).to_bytes(4, 'little')  # Sample count
                            record[28:32] = int(0xDEADBEEF).to_bytes(4, 'little')  # Magic/CRC
                        
                        chunk.extend(record)
                    
                    f.write(chunk)
                    written += len(chunk)
        
        self.test_files[name] = file_path
        return file_path
    
    def baseline_parser(self, file_path: str, max_records: int = None) -> List[Dict]:
        """Simple baseline parser for comparison."""
        records = []
        
        with open(file_path, 'rb') as f:
            data = f.read()
            
            i = 0
            record_count = 0
            
            while i + 32 <= len(data):
                if max_records and record_count >= max_records:
                    break
                
                # Extract 32-byte record
                record_data = data[i:i+32]
                
                # Parse fields
                offset = int.from_bytes(record_data[0:4], 'little')
                timestamp = int.from_bytes(record_data[4:8], 'little')
                lat = int.from_bytes(record_data[8:12], 'little') / 1e6
                lon = int.from_bytes(record_data[12:16], 'little') / 1e6
                depth = int.from_bytes(record_data[16:20], 'little') / 1000.0
                beam_angle = int.from_bytes(record_data[20:24], 'little') / 1000.0
                sample_count = int.from_bytes(record_data[24:28], 'little')
                
                record = {
                    'ofs': offset,
                    'channel_id': 0,
                    'seq': record_count,
                    'time_ms': timestamp,
                    'lat': lat,
                    'lon': lon,
                    'depth_m': depth,
                    'sample_cnt': sample_count,
                    'sonar_ofs': 0,
                    'sonar_size': 0,
                    'beam_deg': beam_angle,
                    'pitch_deg': 0.0,
                    'roll_deg': 0.0,
                    'heave_m': 0.0,
                    'tx_ofs_m': 0.0,
                    'rx_ofs_m': 0.0,
                    'color_id': 0,
                    'extras': {}
                }
                
                records.append(record)
                record_count += 1
                i += 32
        
        return records
    
    def optimized_parser(self, file_path: str, max_records: int = None) -> List[Dict]:
        """Optimized parser with efficient byte operations."""
        records = []
        
        # Read file in chunks for better memory efficiency
        chunk_size = 1024 * 1024  # 1MB chunks
        
        with open(file_path, 'rb') as f:
            record_count = 0
            buffer = b''
            
            while True:
                if max_records and record_count >= max_records:
                    break
                
                # Read chunk
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                # Add to buffer
                buffer += chunk
                
                # Process complete records
                i = 0
                while i + 32 <= len(buffer):
                    if max_records and record_count >= max_records:
                        break
                    
                    # Fast byte extraction using slicing
                    record_data = buffer[i:i+32]
                    
                    # Optimized parsing with fewer function calls
                    fields = [
                        int.from_bytes(record_data[j:j+4], 'little')
                        for j in range(0, 32, 4)
                    ]
                    
                    record = {
                        'ofs': fields[0],
                        'channel_id': 0,
                        'seq': record_count,
                        'time_ms': fields[1],
                        'lat': fields[2] / 1e6,
                        'lon': fields[3] / 1e6,
                        'depth_m': fields[4] / 1000.0,
                        'sample_cnt': fields[6],
                        'beam_deg': fields[5] / 1000.0,
                        'pitch_deg': 0.0,
                        'roll_deg': 0.0,
                        'heave_m': 0.0,
                        'tx_ofs_m': 0.0,
                        'rx_ofs_m': 0.0,
                        'color_id': 0,
                        'extras': {}
                    }
                    
                    records.append(record)
                    record_count += 1
                    i += 32
                
                # Keep remainder for next iteration
                buffer = buffer[i:]
        
        return records
    
    def parallel_parser(self, file_path: str, max_records: int = None, num_workers: int = 4) -> List[Dict]:
        """Multi-threaded parallel parser."""
        import concurrent.futures
        import queue
        
        file_size = os.path.getsize(file_path)
        chunk_size = max(1024 * 1024, file_size // num_workers)  # At least 1MB per chunk
        
        # Calculate chunk boundaries
        chunks = []
        offset = 0
        while offset < file_size:
            end_offset = min(offset + chunk_size, file_size)
            # Align to record boundary (32 bytes)
            end_offset = (end_offset // 32) * 32
            if end_offset > offset:
                chunks.append((offset, end_offset))
            offset = end_offset
        
        def process_chunk(chunk_info):
            """Process a file chunk."""
            start_offset, end_offset = chunk_info
            chunk_records = []
            
            with open(file_path, 'rb') as f:
                f.seek(start_offset)
                data = f.read(end_offset - start_offset)
                
                i = 0
                record_count = 0
                
                while i + 32 <= len(data):
                    if max_records and len(chunk_records) >= max_records // len(chunks):
                        break
                    
                    record_data = data[i:i+32]
                    
                    # Fast parsing
                    fields = [
                        int.from_bytes(record_data[j:j+4], 'little')
                        for j in range(0, 32, 4)
                    ]
                    
                    record = {
                        'ofs': start_offset + i,
                        'channel_id': 0,
                        'seq': record_count,
                        'time_ms': fields[1],
                        'lat': fields[2] / 1e6,
                        'lon': fields[3] / 1e6,
                        'depth_m': fields[4] / 1000.0,
                        'sample_cnt': fields[6],
                        'beam_deg': fields[5] / 1000.0,
                        'pitch_deg': 0.0,
                        'roll_deg': 0.0,
                        'heave_m': 0.0,
                        'tx_ofs_m': 0.0,
                        'rx_ofs_m': 0.0,
                        'color_id': 0,
                        'extras': {}
                    }
                    
                    chunk_records.append(record)
                    record_count += 1
                    i += 32
            
            return chunk_records
        
        # Process chunks in parallel
        all_records = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_chunk = {executor.submit(process_chunk, chunk): chunk for chunk in chunks}
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_records = future.result()
                all_records.extend(chunk_records)
        
        # Sort by offset to maintain order
        all_records.sort(key=lambda r: r['ofs'])
        
        if max_records:
            all_records = all_records[:max_records]
        
        return all_records
    
    def run_benchmark_test(self, name: str, parser_func: callable, test_file: str, 
                          max_records: int = 50000, optimization_type: str = 'unknown', **kwargs) -> BenchmarkResult:
        """Run a single benchmark test."""
        print(f"   Testing {name}...")
        
        # Start monitoring
        tracemalloc.start()
        process = psutil.Process()
        start_cpu_time = process.cpu_times()
        
        start_time = time.time()
        
        # Run parser (filter out optimization_type from kwargs passed to parser)
        parser_kwargs = {k: v for k, v in kwargs.items() if k != 'optimization_type'}
        records = parser_func(test_file, max_records, **parser_kwargs)
        
        end_time = time.time()
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate metrics
        duration = end_time - start_time
        bytes_processed = os.path.getsize(test_file)
        rps = len(records) / duration if duration > 0 else 0
        mbps = (bytes_processed / (1024*1024)) / duration if duration > 0 else 0
        
        result = BenchmarkResult(
            name=name,
            duration_seconds=duration,
            records_processed=len(records),
            bytes_processed=bytes_processed,
            memory_peak_mb=peak / (1024*1024),
            records_per_second=rps,
            mbytes_per_second=mbps,
            competitive_advantage=rps / self.baseline_rps,
            optimization_type=optimization_type
        )
        
        print(f"      Records: {len(records):,}")
        print(f"      Duration: {duration:.3f}s")
        print(f"      RPS: {rps:.0f}")
        print(f"      Memory: {peak / (1024*1024):.1f}MB")
        print(f"      Advantage: {result.competitive_advantage:.2f}x")
        
        return result
    
    def run_all_benchmarks(self):
        """Run comprehensive benchmark suite."""
        print("🚀 SIMPLIFIED PERFORMANCE BENCHMARK")
        print("=" * 40)
        
        # Create test files
        print("\n📁 Creating test files...")
        small_file = self.create_test_file("small", 10)    # 10MB
        medium_file = self.create_test_file("medium", 50)  # 50MB
        large_file = self.create_test_file("large", 200)   # 200MB
        
        # Test 1: Baseline performance
        print("\n📊 Baseline Performance:")
        baseline = self.run_benchmark_test(
            "Baseline Parser",
            self.baseline_parser,
            medium_file,
            optimization_type="baseline"
        )
        self.results.append(baseline)
        
        # Test 2: Optimized single-threaded
        print("\n⚡ Optimized Single-threaded:")
        optimized = self.run_benchmark_test(
            "Optimized Parser",
            self.optimized_parser,
            medium_file,
            optimization_type="optimized"
        )
        self.results.append(optimized)
        
        # Test 3: Parallel processing
        print("\n🔄 Parallel Processing:")
        for workers in [2, 4, 8]:
            if workers <= self.system_info['cpu_count']:
                parallel = self.run_benchmark_test(
                    f"Parallel Parser ({workers} workers)",
                    self.parallel_parser,
                    large_file,
                    num_workers=workers,
                    optimization_type="parallel"
                )
                self.results.append(parallel)
        
        # Test 4: Scalability test
        print("\n📈 Scalability Test:")
        for size_name, file_path in [("small", small_file), ("medium", medium_file), ("large", large_file)]:
            scalability = self.run_benchmark_test(
                f"Scalability Test ({size_name})",
                self.optimized_parser,
                file_path,
                max_records=25000,
                optimization_type="scalability"
            )
            self.results.append(scalability)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        if not self.results:
            return {"error": "No results available"}
        
        # Find best results
        best_result = max(self.results, key=lambda r: r.competitive_advantage)
        baseline_result = next((r for r in self.results if r.optimization_type == "baseline"), None)
        
        # Calculate improvements
        improvements = {}
        if baseline_result:
            for result in self.results:
                if result.optimization_type != "baseline":
                    speedup = result.records_per_second / baseline_result.records_per_second
                    improvements[result.name] = {
                        'speedup': speedup,
                        'memory_ratio': result.memory_peak_mb / baseline_result.memory_peak_mb,
                        'competitive_advantage': result.competitive_advantage
                    }
        
        report = {
            'system_info': self.system_info,
            'benchmark_summary': {
                'total_tests': len(self.results),
                'best_performance': {
                    'name': best_result.name,
                    'rps': best_result.records_per_second,
                    'advantage': best_result.competitive_advantage
                },
                'target_achieved': best_result.competitive_advantage >= 18.0,
                'max_advantage': best_result.competitive_advantage
            },
            'improvements_over_baseline': improvements,
            'all_results': [r.to_dict() for r in self.results]
        }
        
        return report
    
    def save_results(self, output_dir: str = "benchmark_results"):
        """Save results to files."""
        os.makedirs(output_dir, exist_ok=True)
        
        report = self.generate_report()
        
        # Save JSON report
        json_path = os.path.join(output_dir, "simple_benchmark_report.json")
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save CSV
        csv_path = os.path.join(output_dir, "simple_benchmark_results.csv")
        with open(csv_path, 'w') as f:
            f.write("name,optimization_type,records_per_second,competitive_advantage,memory_peak_mb,duration_seconds\n")
            for result in self.results:
                f.write(f"{result.name},{result.optimization_type},{result.records_per_second:.0f},"
                       f"{result.competitive_advantage:.2f},{result.memory_peak_mb:.1f},{result.duration_seconds:.3f}\n")
        
        print(f"\n📁 Results saved to {output_dir}/")
        return report
    
    def cleanup(self):
        """Clean up test files."""
        for name, file_path in self.test_files.items():
            if os.path.exists(file_path):
                os.unlink(file_path)
        print("🧹 Cleaned up test files")


def main():
    """Run simplified benchmark."""
    benchmark = SimpleBenchmark()
    
    try:
        benchmark.run_all_benchmarks()
        
        # Generate and save report
        report = benchmark.save_results()
        
        # Print summary
        print("\n🎯 BENCHMARK SUMMARY")
        print("=" * 30)
        print(f"Total tests: {report['benchmark_summary']['total_tests']}")
        print(f"Best performance: {report['benchmark_summary']['best_performance']['name']}")
        print(f"Max RPS: {report['benchmark_summary']['best_performance']['rps']:.0f}")
        print(f"Max advantage: {report['benchmark_summary']['max_advantage']:.1f}x")
        print(f"Target achieved: {'✅ YES' if report['benchmark_summary']['target_achieved'] else '❌ NO'}")
        
        if report['benchmark_summary']['max_advantage'] >= 18.0:
            print("\n🏆 CONGRATULATIONS! 18x competitive advantage achieved!")
        else:
            needed = 18.0 / report['benchmark_summary']['max_advantage']
            print(f"\n⚠️  Need {needed:.1f}x more performance to reach 18x target")
        
        # Show top improvements
        if report['improvements_over_baseline']:
            print(f"\n📈 TOP IMPROVEMENTS:")
            for name, metrics in list(report['improvements_over_baseline'].items())[:3]:
                print(f"   {name}: {metrics['speedup']:.1f}x speedup")
        
        return report
    
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    report = main()
    print("\n✅ Benchmark complete!")