from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg://bears:bears@db/bears'
    environment: str = 'local'
    # The default exists for isolated tests; every runnable stack supplies PIPELINE explicitly.
    pipeline: str = 'mock-v1'
    worker_token: str
    s3_endpoint: str | None = None
    s3_bucket: str = 'only-bears'
    aws_region: str = 'us-west-2'
    cors_origin: str = 'http://localhost:5173'
    lease_seconds: int = 300
    job_timeout_seconds: int = 1800
    max_attempts: int = 3
    auto_recognize: bool = True
    auth_mode: str = 'local'
    public_deployment: bool = False
    public_origin: str = 'http://localhost:5173'
    google_client_id: str = ''
    google_client_secret: str = ''
    oauth_cookie_secret: str = ''
    owner_google_sub: str = ''
    local_owner_settings: bool = False

@lru_cache
def settings():
    s = Settings()
    if len(s.worker_token) < 24:
        raise ValueError('WORKER_TOKEN must have at least 24 characters')
    if s.environment != 'local' and s.pipeline.startswith('mock'):
        raise ValueError('Mock pipeline forbidden outside local environment')
    if s.auth_mode not in ('local', 'google'):
        raise ValueError('Unknown authentication mode')
    if s.public_deployment and (s.auth_mode != 'google' or not s.public_origin.startswith('https://')):
        raise ValueError('Public deployment requires Google authentication and HTTPS')
    if s.local_owner_settings and (s.environment != 'local' or s.auth_mode != 'local' or s.public_deployment):
        raise ValueError('Local owner settings are only available in local development')
    if s.auth_mode == 'google' and (not s.google_client_id or not s.google_client_secret or len(s.oauth_cookie_secret) < 32):
        raise ValueError('Google authentication configuration is incomplete')
    return s
