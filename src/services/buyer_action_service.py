"""
买家侧扫货动作扩展点。

默认不执行任何动作。开启后，会在推荐商品完成分析与落库后，把结构化 payload
POST 到你的项目服务，由你的服务决定是否提醒、排队、人工确认或继续发起私信。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import requests

from src.infrastructure.config.settings import (
    BuyerAgentSettings,
    buyer_agent_settings,
)


class BuyerActionService:
    """把推荐商品事件转发给外部买家 Agent。"""

    def __init__(self, settings: BuyerAgentSettings) -> None:
        self.settings = settings

    async def handle_recommended_item(self, record: dict, keyword: str) -> None:
        if not self.settings.enabled:
            return

        payload = build_recommended_item_payload(record, keyword)
        if not self.settings.webhook_url:
            print("[BuyerAgent] BUYER_AGENT_ENABLED=true 但未配置 BUYER_AGENT_WEBHOOK_URL，已跳过")
            return

        await asyncio.to_thread(self._post_webhook, payload)

    def _post_webhook(self, payload: dict[str, Any]) -> None:
        headers = self._parse_headers()
        response = requests.post(
            self.settings.webhook_url,
            headers=headers,
            json=payload,
            timeout=self.settings.webhook_timeout_seconds,
        )
        response.raise_for_status()

    def _parse_headers(self) -> dict[str, str]:
        if not self.settings.webhook_headers:
            return {}
        parsed = json.loads(self.settings.webhook_headers)
        if not isinstance(parsed, dict):
            raise ValueError("BUYER_AGENT_WEBHOOK_HEADERS 必须是 JSON 对象")
        return {str(key): str(value) for key, value in parsed.items()}


def build_recommended_item_payload(record: dict, keyword: str) -> dict[str, Any]:
    item = record.get("商品信息", {}) or {}
    seller = record.get("卖家信息", {}) or {}
    analysis = record.get("ai_analysis", {}) or {}

    return {
        "event": "recommended_item",
        "keyword": keyword,
        "task_name": record.get("任务名称", ""),
        "crawl_time": record.get("爬取时间", ""),
        "item": {
            "id": item.get("商品ID"),
            "title": item.get("商品标题"),
            "price": item.get("当前售价"),
            "link": item.get("商品链接"),
            "main_image": item.get("商品主图链接"),
            "image_urls": item.get("商品图片列表", []),
            "want_count": item.get("“想要”人数"),
            "browse_count": item.get("浏览量"),
        },
        "seller": seller,
        "analysis": analysis,
        "price_reference": record.get("价格参考", {}),
        "price_insight": record.get("price_insight", {}),
        "raw_record": record,
    }


def build_buyer_action_service(
    settings: BuyerAgentSettings | None = None,
) -> BuyerActionService:
    return BuyerActionService(settings or buyer_agent_settings)
