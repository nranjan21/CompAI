"""
Cache Manager for storing and retrieving agent results.
Implements file-based caching with optional TTL support.
"""

import json
import hashlib
import gzip
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
from app.utils.logger import logger


class CacheManager:
    """Manages file-based caching for agent results."""
    
    def __init__(self, cache_dir: Path = Path("./cache"), compress: bool = False):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            compress: Whether to compress cache files
        """
        self.cache_dir = cache_dir
        self.compress = compress
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📦 Cache manager initialized at {cache_dir}")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generate a unique cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            MD5 hash of the arguments
        """
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        extension = ".json.gz" if self.compress else ".json"
        return self.cache_dir / f"{key}{extension}"
    
    def get(self, key: str, ttl_hours: Optional[int] = None) -> Optional[Any]:
        """
        Retrieve a value from cache.
        
        Args:
            key: Cache key
            ttl_hours: Time-to-live in hours (None = no expiration)
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        # Check TTL if specified
        if ttl_hours is not None:
            modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            expiration_time = modified_time + timedelta(hours=ttl_hours)
            
            if datetime.now() > expiration_time:
                logger.debug(f"🕒 Cache expired for key {key}")
                cache_path.unlink()  # Delete expired cache
                return None
        
        try:
            if self.compress:
                with gzip.open(cache_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            logger.debug(f"✅ Cache hit for key {key}")
            return data
        except Exception as e:
            logger.warning(f"⚠️ Error reading cache for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        Store a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            
        Returns:
            True if successful, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        try:
            if self.compress:
                with gzip.open(cache_path, 'wt', encoding='utf-8') as f:
                    json.dump(value, f)
            else:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(value, f, indent=2)
            
            logger.debug(f"💾 Cached data for key {key}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Error writing cache for key {key}: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """
        Remove a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"🗑️ Invalidated cache for key {key}")
            return True
        
        return False
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json*"):
            cache_file.unlink()
            count += 1
        
        logger.info(f"🧹 Cleared {count} cache entries")
        return count
    
    def get_or_compute(self, key: str, compute_fn, ttl_hours: Optional[int] = None, *args, **kwargs) -> Any:
        """
        Get from cache or compute and cache the result.
        
        Args:
            key: Cache key
            compute_fn: Function to call if cache miss
            ttl_hours: Time-to-live in hours
            *args: Arguments to pass to compute_fn
            **kwargs: Keyword arguments to pass to compute_fn
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached_value = self.get(key, ttl_hours)
        
        if cached_value is not None:
            return cached_value
        
        # Compute and cache
        logger.debug(f"⚙️ Computing value for key {key}")
        value = compute_fn(*args, **kwargs)
        self.set(key, value)
        
        return value


# Global cache manager instance
cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global cache_manager
    if cache_manager is None:
        from app.core.config import config
        cache_manager = CacheManager(cache_dir=config.system.cache_dir)
    return cache_manager
