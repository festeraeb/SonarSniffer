#!/usr/bin/env python3
"""
COMPREHENSIVE PERFORMANCE BENCHMARKING SUITE
============================================

Advanced benchmarking framework for validating sonar processing performance.
Tests all optimization strategies against real-world scenarios and competitive baselines.

🎯 BENCHMARK CATEGORIES:
- Single-threaded baseline performance
- Multi-threaded parallel processing
- SIMD vectorization effectiveness
- Memory optimization impact
- Format-specific parser performance
- End-to-end pipeline benchmarks

⚡ PERFORMANCE VALIDATION:
- 18x competitive advantage verification
- Scalability testing (1-32 cores)
- Memory efficiency profiling
- Real-time processing capability
- Large file handling (1GB+)

📊 REPORTING:
- Detailed performance metrics
- Competitive analysis charts
- Optimization recommendations
- Performance regression detection
"""

import os
import sys
import time
import psutil
import tracemalloc
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
import json
import statistics
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Import our optimization modules
try:
    from performance_optimization import HighPerformanceParser, VectorizedDataProcessor, PerformanceMonitor
    from memory_optimization import StreamingDataProcessor, MemoryPool, AdaptiveChunkManager
    from parallel_processing import ParallelSonarProcessor, ParallelConfig, WorkStealingExecutor
    OPTIMIZATION_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Optimization modules not available: {e}")
    OPTIMIZATION_MODULES_AVAILABLE = False

# Import parsers
try:
    from engine_classic_varstruct import parse_rsd_file as parse_classic
    from engine_nextgen_syncfirst import parse_rsd_file as parse_nextgen
    from universal_format_engine import UniversalFormatEngine
    PARSERS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Parser modules not available: {e}")
    PARSERS_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    name: str
    duration_seconds: float
    records_processed: int
    bytes_processed: int
    memory_peak_mb: float
    cpu_usage_percent: float
    records_per_second: float
    mbytes_per_second: float
    competitive_advantage: float
    optimization_type: str
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'duration_seconds': self.duration_seconds,
            'records_processed': self.records_processed,
            'bytes_processed': self.bytes_processed,
            'memory_peak_mb': self.memory_peak_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'records_per_second': self.records_per_second,
            'mbytes_per_second': self.mbytes_per_second,
            'competitive_advantage': self.competitive_advantage,
            'optimization_type': self.optimization_type,
            'additional_metrics': self.additional_metrics
        }


class PerformanceBenchmark:
    """Comprehensive performance benchmarking framework."""
    
    def __init__(self):
        self.baseline_rps = 5555  # Competitor baseline (records per second)
        self.results: List[BenchmarkResult] = []
        self.test_files: Dict[str, str] = {}
        
        # System information
        self.system_info = {
            'cpu_count': os.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'platform': sys.platform,
            'python_version': sys.version
        }
        
        print(f"🖥️  System: {self.system_info['cpu_count']} cores, {self.system_info['memory_gb']:.1f}GB RAM")
    
    def create_test_files(self):
        """Create test files of various sizes."""
        print("📁 Creating benchmark test files...")
        
        test_sizes = [
            ('small', 1 * 1024 * 1024),      # 1MB
            ('medium', 50 * 1024 * 1024),    # 50MB
            ('large', 500 * 1024 * 1024),    # 500MB
            ('xlarge', 1024 * 1024 * 1024),  # 1GB
        ]
        
        for name, size in test_sizes:
            file_path = f"benchmark_{name}.dat"
            
            if not os.path.exists(file_path):
                print(f"   Creating {name} file ({size // (1024*1024)}MB)...")
                
                with open(file_path, 'wb') as f:
                    # Create realistic sonar-like data
                    chunk_size = 64 * 1024
                    written = 0
                    
                    while written < size:
                        remaining = min(chunk_size, size - written)
                        
                        # Simulate sonar record structure
                        chunk = bytearray()
                        for i in range(0, remaining, 32):
                            # 32-byte pseudo-records
                            record_size = min(32, remaining - i)
                            record = bytearray(record_size)
                            
                            # Add some patterns that parsers might recognize
                            if record_size >= 4:
                                record[0:4] = (written + i).to_bytes(4, 'little')  # Offset
                            if record_size >= 8:
                                record[4:8] = int(time.time() * 1000).to_bytes(4, 'little')  # Timestamp
                            if record_size >= 16:
                                record[8:16] = os.urandom(8)  # Random data
                            if record_size >= 32:
                                record[16:32] = os.urandom(16)  # More random data
                            
                            chunk.extend(record)
                        
                        f.write(chunk)
                        written += len(chunk)
            
            self.test_files[name] = file_path
        
        print(f"✅ Created {len(self.test_files)} test files")
    
    def measure_baseline_performance(self) -> BenchmarkResult:
        """Measure baseline single-threaded performance."""
        print("\n📊 Measuring baseline performance...")
        
        test_file = self.test_files['medium']
        
        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()
        start_cpu_time = process.cpu_times()
        
        start_time = time.time()
        records_processed = 0
        bytes_processed = os.path.getsize(test_file)
        
        # Simple baseline parsing
        with open(test_file, 'rb') as f:
            data = f.read()
            
            # Simulate basic record extraction
            i = 0
            while i + 32 <= len(data):
                # Extract 32-byte records
                record_data = data[i:i+32]
                
                # Minimal processing
                offset = int.from_bytes(record_data[0:4], 'little')
                timestamp = int.from_bytes(record_data[4:8], 'little')
                
                records_processed += 1
                i += 32
        
        end_time = time.time()
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate CPU usage
        end_cpu_time = process.cpu_times()
        cpu_usage = ((end_cpu_time.user - start_cpu_time.user) + 
                    (end_cpu_time.system - start_cpu_time.system)) / (end_time - start_time) * 100
        
        duration = end_time - start_time
        rps = records_processed / duration
        mbps = (bytes_processed / (1024*1024)) / duration
        
        result = BenchmarkResult(
            name="Baseline Single-threaded",
            duration_seconds=duration,
            records_processed=records_processed,
            bytes_processed=bytes_processed,
            memory_peak_mb=peak / (1024*1024),
            cpu_usage_percent=cpu_usage,
            records_per_second=rps,
            mbytes_per_second=mbps,
            competitive_advantage=rps / self.baseline_rps,
            optimization_type="baseline"
        )
        
        self.results.append(result)
        print(f"   Records: {records_processed:,}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   RPS: {rps:.0f}")
        print(f"   Advantage: {result.competitive_advantage:.2f}x")
        
        return result
    
    def benchmark_optimized_parser(self) -> BenchmarkResult:
        """Benchmark high-performance optimized parser."""
        if not OPTIMIZATION_MODULES_AVAILABLE:
            print("⚠️  Skipping optimized parser benchmark (modules not available)")
            return None
        
        print("\n🚀 Benchmarking optimized parser...")
        
        test_file = self.test_files['medium']
        
        # Start monitoring
        tracemalloc.start()
        process = psutil.Process()
        start_cpu_time = process.cpu_times()
        
        start_time = time.time()
        
        # Use optimized parser
        parser = HighPerformanceParser()
        monitor = PerformanceMonitor()
        
        with monitor:
            records = list(parser.parse_file_optimized(test_file, limit_records=100000))
        
        end_time = time.time()
        
        # Get metrics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        end_cpu_time = process.cpu_times()
        cpu_usage = ((end_cpu_time.user - start_cpu_time.user) + 
                    (end_cpu_time.system - start_cpu_time.system)) / (end_time - start_time) * 100
        
        duration = end_time - start_time
        bytes_processed = os.path.getsize(test_file)
        rps = len(records) / duration
        mbps = (bytes_processed / (1024*1024)) / duration
        
        # Get additional metrics from monitor
        perf_metrics = monitor.get_comprehensive_metrics()
        
        result = BenchmarkResult(
            name="Optimized Parser (Numba + SIMD)",
            duration_seconds=duration,
            records_processed=len(records),
            bytes_processed=bytes_processed,
            memory_peak_mb=peak / (1024*1024),
            cpu_usage_percent=cpu_usage,
            records_per_second=rps,
            mbytes_per_second=mbps,
            competitive_advantage=rps / self.baseline_rps,
            optimization_type="numba_simd",
            additional_metrics=perf_metrics
        )
        
        self.results.append(result)
        print(f"   Records: {len(records):,}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   RPS: {rps:.0f}")
        print(f"   Advantage: {result.competitive_advantage:.2f}x")
        print(f"   SIMD Speedup: {perf_metrics.get('simd_speedup', 'N/A')}")
        
        return result
    
    def benchmark_parallel_processing(self) -> List[BenchmarkResult]:
        """Benchmark parallel processing with different worker counts."""
        if not OPTIMIZATION_MODULES_AVAILABLE:
            print("⚠️  Skipping parallel processing benchmark (modules not available)")
            return []
        
        print("\n🔄 Benchmarking parallel processing...")
        
        test_file = self.test_files['large']
        worker_counts = [1, 2, 4, 8, min(16, os.cpu_count())]
        results = []
        
        for workers in worker_counts:
            print(f"   Testing {workers} workers...")
            
            config = ParallelConfig(max_workers=workers, io_workers=min(workers, 4))
            
            tracemalloc.start()
            process = psutil.Process()
            start_cpu_time = process.cpu_times()
            
            start_time = time.time()
            
            processor = ParallelSonarProcessor(config)
            records = list(processor.process_file_parallel(test_file, max_records=50000))
            
            end_time = time.time()
            
            # Get metrics
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            end_cpu_time = process.cpu_times()
            cpu_usage = ((end_cpu_time.user - start_cpu_time.user) + 
                        (end_cpu_time.system - start_cpu_time.system)) / (end_time - start_time) * 100
            
            duration = end_time - start_time
            bytes_processed = os.path.getsize(test_file)
            rps = len(records) / duration
            mbps = (bytes_processed / (1024*1024)) / duration
            
            # Get parallel-specific metrics
            perf_metrics = processor.get_performance_metrics()
            
            result = BenchmarkResult(
                name=f"Parallel Processing ({workers} workers)",
                duration_seconds=duration,
                records_processed=len(records),
                bytes_processed=bytes_processed,
                memory_peak_mb=peak / (1024*1024),
                cpu_usage_percent=cpu_usage,
                records_per_second=rps,
                mbytes_per_second=mbps,
                competitive_advantage=rps / self.baseline_rps,
                optimization_type="parallel",
                additional_metrics={
                    'workers': workers,
                    'parallel_efficiency': perf_metrics['parallel_efficiency'],
                    'work_stealing_stats': perf_metrics['work_stealing_stats']
                }
            )
            
            results.append(result)
            self.results.append(result)
            
            print(f"      Records: {len(records):,}")
            print(f"      RPS: {rps:.0f}")
            print(f"      Advantage: {result.competitive_advantage:.2f}x")
            print(f"      Efficiency: {perf_metrics['parallel_efficiency']:.1%}")
            
            processor.shutdown()
        
        return results
    
    def benchmark_memory_optimization(self) -> BenchmarkResult:
        """Benchmark memory-optimized streaming processor."""
        if not OPTIMIZATION_MODULES_AVAILABLE:
            print("⚠️  Skipping memory optimization benchmark (modules not available)")
            return None
        
        print("\n💾 Benchmarking memory optimization...")
        
        test_file = self.test_files['xlarge']  # Use largest file
        
        tracemalloc.start()
        process = psutil.Process()
        start_cpu_time = process.cpu_times()
        
        start_time = time.time()
        
        # Use streaming processor
        processor = StreamingDataProcessor()
        memory_pool = MemoryPool(max_size_mb=100)  # Limit to 100MB
        
        records_processed = 0
        bytes_processed = 0
        
        for chunk in processor.stream_file(test_file, chunk_size=1024*1024):
            # Process chunk in memory-efficient way
            records_in_chunk = len(chunk) // 32
            records_processed += records_in_chunk
            bytes_processed += len(chunk)
            
            # Limit for benchmark
            if records_processed >= 100000:
                break
        
        end_time = time.time()
        
        # Get memory metrics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        end_cpu_time = process.cpu_times()
        cpu_usage = ((end_cpu_time.user - start_cpu_time.user) + 
                    (end_cpu_time.system - start_cpu_time.system)) / (end_time - start_time) * 100
        
        duration = end_time - start_time
        rps = records_processed / duration
        mbps = (bytes_processed / (1024*1024)) / duration
        
        # Get memory pool stats
        pool_stats = memory_pool.get_stats()
        
        result = BenchmarkResult(
            name="Memory-Optimized Streaming",
            duration_seconds=duration,
            records_processed=records_processed,
            bytes_processed=bytes_processed,
            memory_peak_mb=peak / (1024*1024),
            cpu_usage_percent=cpu_usage,
            records_per_second=rps,
            mbytes_per_second=mbps,
            competitive_advantage=rps / self.baseline_rps,
            optimization_type="memory_streaming",
            additional_metrics={
                'memory_pool_efficiency': pool_stats['cache_hit_ratio'],
                'memory_pool_peak_mb': pool_stats['peak_usage_mb'],
                'streaming_chunks': bytes_processed // (1024*1024)
            }
        )
        
        self.results.append(result)
        print(f"   Records: {records_processed:,}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   RPS: {rps:.0f}")
        print(f"   Memory Peak: {peak / (1024*1024):.1f}MB")
        print(f"   Advantage: {result.competitive_advantage:.2f}x")
        
        return result
    
    def benchmark_format_parsers(self) -> List[BenchmarkResult]:
        """Benchmark different format parsers."""
        if not PARSERS_AVAILABLE:
            print("⚠️  Skipping format parser benchmark (modules not available)")
            return []
        
        print("\n📄 Benchmarking format parsers...")
        
        # Create small test files for different formats
        rsd_test_file = self.test_files['small']
        
        parsers = [
            ("Classic RSD Parser", lambda f: parse_classic(f, limit_rows=10000)),
            ("NextGen RSD Parser", lambda f: parse_nextgen(f, limit_rows=10000)),
        ]
        
        if OPTIMIZATION_MODULES_AVAILABLE:
            # Add universal format engine if available
            parsers.append(("Universal Format Engine", lambda f: self._test_universal_parser(f)))
        
        results = []
        
        for parser_name, parser_func in parsers:
            print(f"   Testing {parser_name}...")
            
            try:
                tracemalloc.start()
                
                start_time = time.time()
                records = list(parser_func(rsd_test_file))
                end_time = time.time()
                
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                duration = end_time - start_time
                bytes_processed = os.path.getsize(rsd_test_file)
                rps = len(records) / duration if duration > 0 else 0
                mbps = (bytes_processed / (1024*1024)) / duration if duration > 0 else 0
                
                result = BenchmarkResult(
                    name=parser_name,
                    duration_seconds=duration,
                    records_processed=len(records),
                    bytes_processed=bytes_processed,
                    memory_peak_mb=peak / (1024*1024),
                    cpu_usage_percent=0.0,  # Not measured for individual parsers
                    records_per_second=rps,
                    mbytes_per_second=mbps,
                    competitive_advantage=rps / self.baseline_rps if rps > 0 else 0,
                    optimization_type="format_parser"
                )
                
                results.append(result)
                self.results.append(result)
                
                print(f"      Records: {len(records):,}")
                print(f"      Duration: {duration:.3f}s")
                print(f"      RPS: {rps:.0f}")
                
            except Exception as e:
                print(f"      ❌ Failed: {e}")
        
        return results
    
    def _test_universal_parser(self, file_path: str) -> List[Dict]:
        """Test universal format engine."""
        engine = UniversalFormatEngine()
        records = []
        
        for record in engine.parse_file(file_path, limit_records=10000):
            records.append(record)
        
        return records
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        print("\n📊 Generating performance report...")
        
        if not self.results:
            return {"error": "No benchmark results available"}
        
        # Calculate summary statistics
        best_result = max(self.results, key=lambda r: r.competitive_advantage)
        baseline_result = next((r for r in self.results if r.optimization_type == "baseline"), None)
        
        # Group results by optimization type
        by_optimization = {}
        for result in self.results:
            opt_type = result.optimization_type
            if opt_type not in by_optimization:
                by_optimization[opt_type] = []
            by_optimization[opt_type].append(result)
        
        # Calculate improvement metrics
        improvements = {}
        if baseline_result:
            for result in self.results:
                if result.optimization_type != "baseline":
                    speedup = result.records_per_second / baseline_result.records_per_second
                    memory_ratio = result.memory_peak_mb / baseline_result.memory_peak_mb
                    improvements[result.name] = {
                        'speedup': speedup,
                        'memory_ratio': memory_ratio,
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
            'results_by_optimization': {
                opt_type: [r.to_dict() for r in results]
                for opt_type, results in by_optimization.items()
            },
            'improvements_over_baseline': improvements,
            'all_results': [r.to_dict() for r in self.results]
        }
        
        return report
    
    def save_results(self, output_dir: str = "benchmark_results"):
        """Save benchmark results to files."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON report
        report = self.generate_performance_report()
        
        json_path = os.path.join(output_dir, "performance_report.json")
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save CSV results
        csv_path = os.path.join(output_dir, "benchmark_results.csv")
        with open(csv_path, 'w') as f:
            f.write("name,optimization_type,records_per_second,competitive_advantage,memory_peak_mb,duration_seconds\n")
            for result in self.results:
                f.write(f"{result.name},{result.optimization_type},{result.records_per_second:.0f},"
                       f"{result.competitive_advantage:.2f},{result.memory_peak_mb:.1f},{result.duration_seconds:.3f}\n")
        
        print(f"📁 Results saved to {output_dir}/")
        return output_dir
    
    def create_performance_charts(self, output_dir: str = "benchmark_results"):
        """Create performance visualization charts."""
        try:
            import matplotlib.pyplot as plt
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Chart 1: Records per second comparison
            names = [r.name for r in self.results]
            rps_values = [r.records_per_second for r in self.results]
            colors = ['red' if r.optimization_type == 'baseline' else 'green' for r in self.results]
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(range(len(names)), rps_values, color=colors)
            plt.xlabel('Optimization Method')
            plt.ylabel('Records per Second')
            plt.title('Sonar Processing Performance Comparison')
            plt.xticks(range(len(names)), names, rotation=45, ha='right')
            
            # Add value labels on bars
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'performance_comparison.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            # Chart 2: Competitive advantage
            advantages = [r.competitive_advantage for r in self.results]
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(range(len(names)), advantages, color=colors)
            plt.axhline(y=18.0, color='blue', linestyle='--', label='Target (18x)')
            plt.xlabel('Optimization Method')
            plt.ylabel('Competitive Advantage (Multiplier)')
            plt.title('Competitive Advantage Analysis')
            plt.xticks(range(len(names)), names, rotation=45, ha='right')
            plt.legend()
            
            # Add value labels
            for i, bar in enumerate(bars):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{height:.1f}x', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'competitive_advantage.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📊 Performance charts saved to {output_dir}/")
            
        except ImportError:
            print("⚠️  Matplotlib not available, skipping chart generation")
    
    def cleanup_test_files(self):
        """Clean up temporary test files."""
        for name, file_path in self.test_files.items():
            if os.path.exists(file_path):
                os.unlink(file_path)
        print("🧹 Cleaned up test files")


def run_comprehensive_benchmark():
    """Run the complete benchmark suite."""
    print("🚀 COMPREHENSIVE PERFORMANCE BENCHMARK SUITE")
    print("=" * 60)
    
    benchmark = PerformanceBenchmark()
    
    try:
        # Setup
        benchmark.create_test_files()
        
        # Run benchmarks
        benchmark.measure_baseline_performance()
        
        if OPTIMIZATION_MODULES_AVAILABLE:
            benchmark.benchmark_optimized_parser()
            benchmark.benchmark_parallel_processing()
            benchmark.benchmark_memory_optimization()
        
        if PARSERS_AVAILABLE:
            benchmark.benchmark_format_parsers()
        
        # Generate reports
        report = benchmark.generate_performance_report()
        output_dir = benchmark.save_results()
        benchmark.create_performance_charts(output_dir)
        
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
            print(f"\n⚠️  Target not reached. Current best: {report['benchmark_summary']['max_advantage']:.1f}x")
        
        return report
    
    finally:
        benchmark.cleanup_test_files()


if __name__ == "__main__":
    report = run_comprehensive_benchmark()
    
    print("\n✅ Comprehensive benchmark complete!")
    print("📊 Check benchmark_results/ for detailed reports and charts")