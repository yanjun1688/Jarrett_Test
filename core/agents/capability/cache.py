from typing import Optional, Dict
import time
import logging
from threading import Lock
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    value: str
    created_at: float
    ttl: float
    
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class CapabilityCache:
    """
    能力清单缓存
    
    避免每次都重新构建能力清单
    TTL 设计：5 分钟
    """
    
    DEFAULT_TTL = 300
    
    def __init__(self, ttl: Optional[float] = None):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._ttl = ttl or self.DEFAULT_TTL
    
    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                logger.debug(f"Cache expired: {key}")
                return None
            
            logger.debug(f"Cache hit: {key}")
            return entry.value
    
    def set(self, key: str, value: str, ttl: Optional[float] = None) -> None:
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl or self._ttl
            )
            logger.debug(f"Cache set: {key}")
    
    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()
            logger.info("All capability cache cleared")
    
    def get_stats(self) -> Dict:
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for e in self._cache.values() if e.is_expired())
            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired
            }