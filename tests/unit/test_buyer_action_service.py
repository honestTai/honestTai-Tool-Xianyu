import asyncio

from src.infrastructure.config.settings import BuyerAgentSettings
from src.services.buyer_action_service import (
    BuyerActionService,
    build_recommended_item_payload,
)


def test_build_recommended_item_payload_normalizes_core_fields():
    record = {
        "任务名称": "Macbook",
        "爬取时间": "2026-05-25T12:00:00",
        "商品信息": {
            "商品ID": "123",
            "商品标题": "MacBook Pro",
            "当前售价": "5999",
            "商品链接": "https://www.goofish.com/item?id=123",
            "商品主图链接": "https://img.example.com/a.jpg",
            "商品图片列表": ["https://img.example.com/a.jpg"],
            "“想要”人数": "8",
            "浏览量": "99",
        },
        "卖家信息": {"卖家昵称": "demo"},
        "ai_analysis": {"is_recommended": True, "reason": "价格合适"},
        "价格参考": {"样本数": 10},
        "price_insight": {"position": "low"},
    }

    payload = build_recommended_item_payload(record, "macbook")

    assert payload["event"] == "recommended_item"
    assert payload["keyword"] == "macbook"
    assert payload["task_name"] == "Macbook"
    assert payload["item"]["id"] == "123"
    assert payload["item"]["title"] == "MacBook Pro"
    assert payload["seller"] == {"卖家昵称": "demo"}
    assert payload["analysis"]["reason"] == "价格合适"
    assert payload["raw_record"] is record


def test_buyer_action_service_posts_webhook(monkeypatch):
    captured = {}

    class _FakeResponse:
        status_code = 204

        def raise_for_status(self):
            return None

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("requests.post", _fake_post)

    service = BuyerActionService(
        BuyerAgentSettings(
            BUYER_AGENT_ENABLED=True,
            BUYER_AGENT_WEBHOOK_URL="https://agent.example.com/hook",
            BUYER_AGENT_WEBHOOK_HEADERS='{"Authorization":"Bearer token"}',
            BUYER_AGENT_WEBHOOK_TIMEOUT_SECONDS=3,
        )
    )

    asyncio.run(
        service.handle_recommended_item(
            {
                "任务名称": "Demo",
                "商品信息": {"商品ID": "1", "商品标题": "Sony A7M4"},
                "卖家信息": {},
                "ai_analysis": {"is_recommended": True},
            },
            "sony",
        )
    )

    assert captured["url"] == "https://agent.example.com/hook"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["json"]["keyword"] == "sony"
    assert captured["json"]["item"]["title"] == "Sony A7M4"
    assert captured["timeout"] == 3


def test_buyer_action_service_noops_when_disabled(monkeypatch):
    def _fake_post(*args, **kwargs):
        raise AssertionError("disabled buyer action should not post")

    monkeypatch.setattr("requests.post", _fake_post)

    service = BuyerActionService(
        BuyerAgentSettings(
            BUYER_AGENT_ENABLED=False,
            BUYER_AGENT_WEBHOOK_URL="https://agent.example.com/hook",
        )
    )

    asyncio.run(service.handle_recommended_item({"商品信息": {}}, "demo"))
