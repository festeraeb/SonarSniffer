#!/usr/bin/env python3
"""
Rust vs Python Performance Comparison
Direct benchmark of the Rust acceleration
"""

import time
import numpy as np
import sys

def python_waterfall_generation(left_data, right_data, width, gap_pixels=4):
    """Simple Python waterfall generation for comparison"""
    height = min(left_data.shape[0], right_data.shape[0])
    channel_width = (width - gap_pixels) // 2
    
    waterfall = np.zeros((height, width), dtype=np.uint8)
    
    for row in range(height):
        # Left channel
        if channel_width <= left_data.shape[1]:
            waterfall[row, :channel_width] = left_data[row, :channel_width]
        
        # Gap
        waterfall[row, channel_width:channel_width + gap_pixels] = 128
        
        # Right channel  
        if channel_width <= right_data.shape[1]:
            start_col = channel_width + gap_pixels
            waterfall[row, start_col:start_col + channel_width] = right_data[row, :channel_width]
    
    return waterfall

def benchmark_comparison():
    """Compare Rust vs Python performance"""
    print("🚀 Rust vs Python Performance Benchmark")
    print("=" * 45)
    
    # Test configurations
    test_configs = [
        (25, 492, "Small - 25x492"),
        (100, 492, "Medium - 100x492"), 
        (500, 492, "Large - 500x492"),
        (1000, 492, "XLarge - 1000x492")
    ]
    
    try:
        import rsd_video_core
        rust_available = True
    except ImportError:
        rust_available = False
        print("❌ Rust module not available")
        return
    
    results = []
    
    for height, channel_width, description in test_configs:
        print(f"\n{description}")
        print("-" * len(description))
        
        # Generate test data
        left_data = np.random.randint(0, 255, (height, channel_width), dtype=np.uint8)
        right_data = np.random.randint(0, 255, (height, channel_width), dtype=np.uint8)
        total_width = channel_width * 2 + 4
        
        # Python benchmark
        iterations = 50 if height <= 100 else 10
        
        start_time = time.perf_counter()
        for _ in range(iterations):
            python_result = python_waterfall_generation(left_data, right_data, total_width)
        python_time = (time.perf_counter() - start_time) / iterations
        
        # Rust benchmark
        start_time = time.perf_counter()
        for _ in range(iterations):
            rust_result = rsd_video_core.generate_sidescan_waterfall(left_data, right_data, total_width, 4)
        rust_time = (time.perf_counter() - start_time) / iterations
        
        # Calculate speedup
        speedup = python_time / rust_time if rust_time > 0 else float('inf')
        
        # Verify results match (approximately)
        shape_match = python_result.shape == rust_result.shape
        content_similar = np.allclose(python_result.astype(float), rust_result.astype(float), atol=1.0)
        
        print(f"  Python: {python_time*1000:.3f}ms per frame")
        print(f"  Rust:   {rust_time*1000:.3f}ms per frame")
        print(f"  Speedup: {speedup:.1f}x faster")
        print(f"  Correctness: {'✅' if shape_match and content_similar else '❌'}")
        
        results.append({
            'config': description,
            'python_ms': python_time * 1000,
            'rust_ms': rust_time * 1000,
            'speedup': speedup,
            'correct': shape_match and content_similar
        })
    
    # Summary
    print(f"\n📊 Performance Summary")
    print("=" * 25)
    avg_speedup = np.mean([r['speedup'] for r in results])
    all_correct = all(r['correct'] for r in results)
    
    print(f"Average speedup: {avg_speedup:.1f}x")
    print(f"All tests correct: {'✅' if all_correct else '❌'}")
    
    # Extrapolate to video rendering
    print(f"\n🎬 Video Rendering Projection")
    print("=" * 30)
    frames_1600 = 1600
    large_frame_rust_time = results[-1]['rust_ms'] / 1000  # Convert to seconds
    large_frame_python_time = results[-1]['python_ms'] / 1000
    
    rust_total = frames_1600 * large_frame_rust_time
    python_total = frames_1600 * large_frame_python_time
    
    print(f"For 1600 frame export (1000x492):")
    print(f"  Python estimated: {python_total:.1f}s ({python_total/60:.1f} min)")
    print(f"  Rust estimated:   {rust_total:.1f}s ({rust_total/60:.1f} min)")
    print(f"  Time saved: {python_total - rust_total:.1f}s ({(python_total - rust_total)/60:.1f} min)")
    
    return results

if __name__ == "__main__":
    benchmark_comparison()