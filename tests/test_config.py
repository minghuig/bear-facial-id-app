import pytest
from app.config import settings


def test_production_rejects_mock_pipeline(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'aws')
    monkeypatch.setenv('PIPELINE', 'mock-v1')
    settings.cache_clear()
    try:
        with pytest.raises(ValueError, match='Mock pipeline forbidden'):
            settings()
    finally:
        settings.cache_clear()


def test_owner_settings_switch_rejects_nonlocal_environment(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'aws')
    monkeypatch.setenv('PIPELINE', 'real-v1-test')
    monkeypatch.setenv('LOCAL_OWNER_SETTINGS', 'true')
    settings.cache_clear()
    try:
        with pytest.raises(ValueError, match='Local owner settings'):
            settings()
    finally:
        settings.cache_clear()
