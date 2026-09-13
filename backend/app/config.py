from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg://bears:bears@db/bears'
    environment: str = 'local'
    pipeline: str = 'mock-v1'
    worker_token: str
    s3_endpoint: str | None = None
    s3_bucket: str = 'only-bears'
    aws_region: str = 'us-west-2'
    cors_origin: str = 'http://localhost:5173'
    lease_seconds: int = 300
    job_timeout_seconds: int = 1800
    max_attempts: int = 3

@lru_cache
def settings():
    s = Settings()
    if len(s.worker_token) < 24:
        raise ValueError('WORKER_TOKEN must have at least 24 characters')
    if s.environment != 'local' and s.pipeline.startswith('mock'):
        raise ValueError('Mock pipeline forbidden outside local environment')
    return s
