#!/usr/bin/env python3
"""
Geospatial Caching Optimization - Advanced data caching for bathymetric processing
LRU cache, spatial indexing, and intelligent prefetching
"""

import numpy as np
import logging
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, Callable
from collections import OrderedDict
import pickle
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry"""
    key: str
    data: Any
    timestamp: datetime
    size_mb: float
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    
    @property
    def age_seconds(self) -> float:
        """Age of cache entry in seconds"""
        return (datetime.now() - self.timestamp).total_seconds()


class LRUCache:
    """
    Least Recently Used cache with size limits
    
    Features:
    - Automatic eviction when size exceeded
    - Access tracking for optimization
    - Memory-efficient storage
    """
    
    def __init__(self, max_size_mb: float = 1000.0):
        """
        Initialize LRU cache
        
        Args:
            max_size_mb: Maximum cache size in MB
        """
        self.max_size_mb = max_size_mb
        self.cache: Dict[str, CacheEntry] = OrderedDict()
        self.total_size_mb = 0.0
        self.hits = 0
        self.misses = 0
    
    def _estimate_size_mb(self, obj: Any) -> float:
        """Estimate object size in MB"""
        try:
            # For numpy arrays
            if isinstance(obj, np.ndarray):
                return obj.nbytes / (1024 * 1024)
            
            # For serializable objects
            serialized = pickle.dumps(obj)
            return len(serialized) / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Could not estimate size: {e}")
            return 0.1  # Conservative estimate
    
    def put(self, key: str, value: Any) -> bool:
        """
        Add item to cache
        
        Args:
            key: Cache key
            value: Data to cache
            
        Returns:
            True if added, False if rejected (too large)
        """
        size_mb = self._estimate_size_mb(value)
        
        # Reject items larger than cache itself
        if size_mb > self.max_size_mb:
            logger.warning(f"Cache item too large: {size_mb:.1f}MB > {self.max_size_mb:.1f}MB")
            return False
        
        # Remove existing entry if present (to update)
        if key in self.cache:
            self.total_size_mb -= self.cache[key].size_mb
            del self.cache[key]
        
        # Evict entries until space available
        while self.total_size_mb + size_mb > self.max_size_mb and self.cache:
            # Remove least recently used (first item in OrderedDict)
            evicted_key, evicted_entry = next(iter(self.cache.items()))
            self.total_size_mb -= evicted_entry.size_mb
            del self.cache[evicted_key]
            logger.debug(f"Evicted cache entry: {evicted_key}")
        
        # Add entry
        entry = CacheEntry(
            key=key,
            data=value,
            timestamp=datetime.now(),
            size_mb=size_mb
        )
        
        self.cache[key] = entry
        self.total_size_mb += size_mb
        
        logger.debug(f"Cached {key}: {size_mb:.2f}MB (total: {self.total_size_mb:.1f}MB)")
        return True
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve item from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found
        """
        if key in self.cache:
            entry = self.cache[key]
            entry.access_count += 1
            entry.last_access = datetime.now()
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            self.hits += 1
            return entry.data
        
        self.misses += 1
        return None
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.total_size_mb = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0-1)"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "size_mb": self.total_size_mb,
            "max_size_mb": self.max_size_mb,
            "num_entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate
        }


class SpatialCache:
    """
    Spatial index cache for geographic data
    
    Caches grid cells and regions for fast lookup
    """
    
    def __init__(self, max_size_mb: float = 2000.0):
        self.lru_cache = LRUCache(max_size_mb)
        self.spatial_index = {}  # Maps spatial region to cache key
    
    def cache_region(self, bounds: Tuple[float, float, float, float],
                    data: np.ndarray, depth: int = 0) -> str:
        """
        Cache geographic region
        
        Args:
            bounds: (min_lon, min_lat, max_lon, max_lat)
            data: Region data (bathymetry grid)
            depth: Quadtree depth for subdivision
            
        Returns:
            Cache key
        """
        # Generate key from bounds
        key = f"region_{depth}_{hash(bounds)}"
        
        # Cache data
        self.lru_cache.put(key, data)
        
        # Index by bounds
        self.spatial_index[key] = bounds
        
        return key
    
    def get_overlapping_regions(self, bounds: Tuple[float, float, float, float]
                               ) -> Dict[str, np.ndarray]:
        """
        Get all cached regions overlapping given bounds
        
        Args:
            bounds: (min_lon, min_lat, max_lon, max_lat)
            
        Returns:
            Dictionary of {key: data} for overlapping regions
        """
        results = {}
        
        min_lon, min_lat, max_lon, max_lat = bounds
        
        for key, region_bounds in self.spatial_index.items():
            r_min_lon, r_min_lat, r_max_lon, r_max_lat = region_bounds
            
            # Check overlap
            if (min_lon < r_max_lon and max_lon > r_min_lon and
                min_lat < r_max_lat and max_lat > r_min_lat):
                
                data = self.lru_cache.get(key)
                if data is not None:
                    results[key] = data
        
        return results
    
    def clear_old_entries(self, max_age_seconds: float = 3600.0) -> int:
        """
        Remove cache entries older than specified age
        
        Args:
            max_age_seconds: Maximum age in seconds
            
        Returns:
            Number of entries removed
        """
        removed = 0
        keys_to_remove = []
        
        for key, entry in self.lru_cache.cache.items():
            if entry.age_seconds > max_age_seconds:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            entry = self.lru_cache.cache[key]
            self.lru_cache.total_size_mb -= entry.size_mb
            del self.lru_cache.cache[key]
            
            if key in self.spatial_index:
                del self.spatial_index[key]
            
            removed += 1
        
        return removed


class ComputationCache:
    """
    Cache for expensive computation results
    
    Automatically memoizes function results
    """
    
    def __init__(self, max_size_mb: float = 1000.0):
        self.cache = LRUCache(max_size_mb)
        self.function_caches = {}
    
    def make_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function and arguments"""
        key_data = f"{func_name}_{args}_{kwargs}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return key_hash
    
    def memoize(self, func: Callable) -> Callable:
        """
        Decorator to memoize function results
        
        Usage:
            @cache.memoize
            def expensive_computation(x, y):
                return x + y
        """
        def wrapper(*args, **kwargs):
            key = self.make_key(func.__name__, *args, **kwargs)
            
            # Check cache
            result = self.cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Compute and cache
            logger.debug(f"Computing {func.__name__}...")
            result = func(*args, **kwargs)
            self.cache.put(key, result)
            
            return result
        
        return wrapper
    
    def cache_result(self, func_name: str, result: Any, *args, **kwargs) -> None:
        """Manually cache a computation result"""
        key = self.make_key(func_name, *args, **kwargs)
        self.cache.put(key, result)
    
    def get_cached_result(self, func_name: str, *args, **kwargs) -> Optional[Any]:
        """Retrieve cached result if available"""
        key = self.make_key(func_name, *args, **kwargs)
        return self.cache.get(key)


class PrefetchStrategy:
    """
    Intelligent prefetching for predictable data access patterns
    """
    
    @staticmethod
    def predict_next_regions(current_bounds: Tuple[float, float, float, float],
                            movement_vector: Tuple[float, float],
                            grid_size: float = 10.0) -> list:
        """
        Predict likely next regions to access
        
        Args:
            current_bounds: Current region bounds
            movement_vector: (lon_delta, lat_delta) per step
            grid_size: Size of each grid region
            
        Returns:
            List of predicted bounds to prefetch
        """
        min_lon, min_lat, max_lon, max_lat = current_bounds
        lon_delta, lat_delta = movement_vector
        
        # Generate 3x3 grid of potential next regions
        predicted = []
        
        for i in range(-1, 2):
            for j in range(-1, 2):
                pred_min_lon = min_lon + (i * grid_size) + lon_delta
                pred_min_lat = min_lat + (j * grid_size) + lat_delta
                pred_max_lon = pred_min_lon + grid_size
                pred_max_lat = pred_min_lat + grid_size
                
                predicted.append((pred_min_lon, pred_min_lat, pred_max_lon, pred_max_lat))
        
        return predicted


class CacheManager:
    """
    Unified cache management for bathymetric processing
    
    Coordinates LRU, spatial, and computation caches
    """
    
    def __init__(self, max_total_mb: float = 5000.0):
        self.max_total_mb = max_total_mb
        
        # Allocate cache space
        lru_mb = max_total_mb * 0.4
        spatial_mb = max_total_mb * 0.4
        computation_mb = max_total_mb * 0.2
        
        self.lru_cache = LRUCache(lru_mb)
        self.spatial_cache = SpatialCache(spatial_mb)
        self.computation_cache = ComputationCache(computation_mb)
    
    def get_stats(self) -> Dict:
        """Get statistics for all caches"""
        return {
            "lru": self.lru_cache.stats(),
            "total_size_mb": (self.lru_cache.total_size_mb + 
                            self.spatial_cache.lru_cache.total_size_mb +
                            self.computation_cache.cache.total_size_mb),
            "max_size_mb": self.max_total_mb
        }
    
    def clear_all(self) -> None:
        """Clear all caches"""
        self.lru_cache.clear()
        self.spatial_cache.lru_cache.clear()
        self.computation_cache.cache.clear()


if __name__ == "__main__":
    # Example usage
    print("Testing LRU Cache...")
    
    lru = LRUCache(max_size_mb=100)
    
    # Add items
    for i in range(5):
        data = np.random.rand(100, 100)
        lru.put(f"grid_{i}", data)
    
    # Access some items
    for i in range(3):
        lru.get(f"grid_{i}")
    
    print(f"Cache stats: {lru.stats()}")
    
    # Test spatial cache
    print("\nTesting Spatial Cache...")
    
    spatial = SpatialCache(max_size_mb=500)
    
    # Cache some regions
    bounds1 = (-122.5, 37.5, -122.0, 38.0)
    data1 = np.random.rand(100, 100)
    key1 = spatial.cache_region(bounds1, data1)
    
    bounds2 = (-122.3, 37.7, -121.8, 38.2)
    data2 = np.random.rand(100, 100)
    key2 = spatial.cache_region(bounds2, data2)
    
    # Find overlapping
    query_bounds = (-122.2, 37.8, -121.9, 38.1)
    overlapping = spatial.get_overlapping_regions(query_bounds)
    
    print(f"Found {len(overlapping)} overlapping regions")
    
    # Test computation cache
    print("\nTesting Computation Cache...")
    
    comp_cache = ComputationCache(max_size_mb=100)
    
    @comp_cache.memoize
    def expensive_func(x, y):
        time.sleep(0.1)  # Simulate expensive computation
        return x + y
    
    # First call (computes)
    result1 = expensive_func(1, 2)
    print(f"First call: {result1} (computed)")
    
    # Second call (cached)
    result2 = expensive_func(1, 2)
    print(f"Second call: {result2} (cached)")
    
    print(f"Cache stats: {comp_cache.cache.stats()}")
