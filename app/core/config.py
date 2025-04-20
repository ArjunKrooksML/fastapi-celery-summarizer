from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()