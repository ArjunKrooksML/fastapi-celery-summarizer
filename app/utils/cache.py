import redis
from typing import Optional
from app.core.config import settings

class Cache:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Cache, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'redis'): # Ensure init runs only once
             self.redis = redis.Redis(
                 host=settings.REDIS_HOST,
                 port=settings.REDIS_PORT,
                 db=settings.REDIS_DB,
                 decode_responses=True # Decode responses to strings
             )

    def get(self, key: str) -> Optional[str]:
        return self.redis.get(key)

    def set(self, key: str, value: str, expire: Optional[int] = 3600):
        self.redis.set(key, value, ex=expire)

    def delete(self, key: str):
        self.redis.delete(key)


cache_instance = Cache()