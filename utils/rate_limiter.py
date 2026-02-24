import time
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.limits = defaultdict(list)
    
    def check_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        self.limits[key] = [t for t in self.limits[key] if now - t < window_seconds]
        
        if len(self.limits[key]) >= max_requests:
            return False
        
        self.limits[key].append(now)
        return True
    
    def get_wait_time(self, key: str, max_requests: int, window_seconds: int) -> float:
        now = time.time()
        self.limits[key] = [t for t in self.limits[key] if now - t < window_seconds]
        
        if len(self.limits[key]) < max_requests:
            return 0
        
        oldest = min(self.limits[key])
        return window_seconds - (now - oldest)
