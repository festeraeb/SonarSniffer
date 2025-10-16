#!/usr/bin/env python3
"""
Benchmark Rust vs Python waterfall generation performance
"""

import time
import numpy as np
from pathlib import Path
import sys

def benchmark_python_waterfall():
    """Benchmark current Python waterfall generation"""
    print("=== PYTHON BENCHMARK ===")
    
    # Simulate typical waterfall data
    height, width = 25, 492  # Single channel
    iterations = 100
    
    # Create test data
    left_data = np.random.randint(0, 255, (height, width), dtype=np.uint8)
    right_data = np.random.randint(0, 255, (height, width), dtype=np.uint8)
    
    def python_waterfall_generation(left, right, total_width=984, gap=4):
        """Current Python approach"""
        channel_width = (total_width - gap) // 2
        waterfall = np.zeros((height, total_width), dtype=np.uint8)
        
        # Left channel
        waterfall[:, :channel_width] = left[:, :channel_width]
        
        # Gap
        waterfall[:, channel_width:channel_width + gap] = 128
        
        # Right channel  
        waterfall[:, channel_width + gap:] = right[:, :channel_width]
        
        return waterfall
    
    # Warm up
    for _ in range(10):
        python_waterfall_generation(left_data, right_data)
    
    # Benchmark
    start_time = time.time()
    for _ in range(iterations):
        result = python_waterfall_generation(left_data, right_data)
    end_time = time.time()
    
    python_time = (end_time - start_time) / iterations
    print(f"Python waterfall generation: {python_time*1000:.3f}ms per frame")
    print(f"Result shape: {result.shape}")
    
    return python_time, result

def benchmark_rust_waterfall():
    """Benchmark Rust waterfall generation (if available)"""
    print("\n=== RUST BENCHMARK ===")
    
    try:
        import rsd_video_core
        
        height, width = 25, 492
        iterations = 100
        
        # Create test data  
        left_data = np.random.randint(0, 255, (height, width), dtype=np.uint8)
        right_data = np.random.randint(0, 255, (height, width), dtype=np.uint8)
        
        # Warm up
        for _ in range(10):
            rsd_video_core.generate_sidescan_waterfall(left_data, right_data, 984, 4)
        
        # Benchmark
        start_time = time.time()
        for _ in range(iterations):
            result = rsd_video_core.generate_sidescan_waterfall(left_data, right_data, 984, 4)
        end_time = time.time()
        
        rust_time = (end_time - start_time) / iterations
        print(f"Rust waterfall generation: {rust_time*1000:.3f}ms per frame")
        print(f"Result shape: {result.shape}")
        
        # Built-in benchmark
        builtin_time = rsd_video_core.benchmark_waterfall_generation(1000, height, width)
        print(f"Rust built-in benchmark: {builtin_time*1000:.3f}ms per frame")
        
        return rust_time, result
        
    except ImportError:
        print("Rust module not available - need to build first")
        print("Run: maturin develop --release")
        return None, None

def test_alignment():
    """Test alignment functionality"""
    print("\n=== ALIGNMENT TEST ===")
    
    try:
        import rsd_video_core
        
        # Create test frames with known shift
        frame1 = np.zeros((20, 100), dtype=np.uint8)
        frame2 = np.zeros((20, 100), dtype=np.uint8)
        
        # Add pattern to frame1
        frame1[8:12, 40:60] = 255
        
        # Add same pattern shifted by 7 pixels to frame2
        frame2[8:12, 47:67] = 255
        
        detected_shift = rsd_video_core.align_waterfall_frames(frame1, frame2)
        print(f"Known shift: 7 pixels")
        print(f"Detected shift: {detected_shift} pixels")
        print(f"Accuracy: {'✅ PASS' if abs(detected_shift - 7) <= 1 else '❌ FAIL'}")
        
    except ImportError:
        print("Rust module not available for alignment test")

def main():
    """Run comprehensive benchmarks"""
    print("🚀 RSD Video Core Performance Benchmark")
    print("=" * 50)
    
    # Python benchmark
    python_time, python_result = benchmark_python_waterfall()
    
    # Rust benchmark 
    rust_time, rust_result = benchmark_rust_waterfall()
    
    # Comparison
    if rust_time is not None:
        speedup = python_time / rust_time
        print(f"\n🎯 PERFORMANCE COMPARISON")
        print(f"Speedup: {speedup:.1f}x faster with Rust")
        
        if speedup > 5:
            print("🔥 Excellent performance gain!")
        elif speedup > 2:
            print("✅ Good performance improvement")
        else:
            print("⚠️ Modest improvement - investigate bottlenecks")
        
        # Verify results match
        if python_result is not None and rust_result is not None:
            # Allow for small differences due to implementation details
            if np.allclose(python_result, rust_result, atol=1):
                print("✅ Results match between Python and Rust")
            else:
                print("⚠️ Results differ - check implementation")
    
    # Test alignment
    test_alignment()
    
    print(f"\n📊 SCALING PROJECTION")
    print(f"Current video export (1600 frames): ~58 seconds")
    if rust_time is not None:
        projected_time = rust_time * 1600
        print(f"With Rust acceleration: ~{projected_time:.1f} seconds")
        print(f"Time savings: {58 - projected_time:.1f} seconds")

if __name__ == "__main__":
    main()