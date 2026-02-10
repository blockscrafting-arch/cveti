"""
Минимальные smoke-тесты для критических путей:
- health check
- корневой маршрут / webapp
- webhook YClients (отказ без секрета, валидация payload)
- webhook Telegram (отказ без секрета при включённом TELEGRAM_WEBHOOK_SECRET)
"""
import os
import pytest
from unittest.mock import patch

# Перед импортом app задаём секреты для webhook-тестов
os.environ.setdefault("WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")


class TestHealth:
    """Проверка /health."""

    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")
        assert "database" in data


class TestRootAndWebapp:
    """Проверка корня и Mini App."""

    def test_root_returns_200_or_json(self, client):
        r = client.get("/")
        assert r.status_code == 200
        # Может быть HTML (FileResponse) или JSON
        assert r.headers.get("content-type", "").startswith(("text/html", "application/json"))

    def test_webapp_index_returns_200(self, client):
        r = client.get("/webapp/")
        assert r.status_code == 200


class TestWebhookYClients:
    """Проверка webhook YClients: отказ без секрета, валидация payload."""

    def test_yclients_webhook_rejects_without_secret(self, client):
        r = client.post(
            "/webhook/yclients",
            json={"resource_id": "1", "data": {"client": {"phone": "79001234567"}, "amount": 100, "visit_id": 1}},
        )
        assert r.status_code == 403

    def test_yclients_webhook_rejects_invalid_payload(self, client):
        r = client.post(
            "/webhook/yclients",
            json={},
            headers={"X-Webhook-Secret": os.environ.get("WEBHOOK_SECRET", "test-secret")},
        )
        # 422 Unprocessable Entity (validation) или 400
        assert r.status_code in (400, 422)

    def test_yclients_webhook_accepts_valid_payload_with_secret(self, client):
        # С валидным секретом и телом принимается и возвращается 200 (обработка в фоне)
        r = client.post(
            "/webhook/yclients",
            json={
                "resource_id": "smoke-test-1",
                "data": {
                    "client": {"phone": "79001234567"},
                    "amount": 100,
                    "visit_id": 1,
                },
            },
            headers={"X-Webhook-Secret": os.environ.get("WEBHOOK_SECRET", "test-secret")},
        )
        assert r.status_code == 200
        assert r.json().get("status") == "accepted"


class TestWebhookTelegram:
    """Проверка webhook Telegram: без бота или без секрета — ошибка."""

    def test_telegram_webhook_returns_json(self, client):
        # Без секрета или с неверным — 403; без инициализации бота — 500
        r = client.post("/webhook/telegram", json={"update_id": 1})
        assert r.status_code in (403, 500)
        assert "ok" in r.json() or "detail" in r.json()
