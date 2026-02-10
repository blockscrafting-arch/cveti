"""
Фикстуры для smoke-тестов. Мокаем Supabase и Bot, чтобы не требовать реальное окружение.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Устанавливаем тестовое окружение до импорта приложения
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")


@pytest.fixture
def mock_supabase():
    """Мок Supabase client с async select(), возвращающий пустой список."""
    client = MagicMock()
    client.select = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


@pytest.fixture
def app(mock_supabase):
    """FastAPI app с замоканным get_supabase (патч активен на время теста)."""
    from api.main import app as fastapi_app
    with patch("api.main.get_supabase", return_value=mock_supabase):
        yield fastapi_app


@pytest.fixture
def client(app):
    """TestClient для FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)
