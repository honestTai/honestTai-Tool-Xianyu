"""Seller-side Goofish automation adapter.

This service keeps the current app as the owning GUI and reuses goofish-cli for
seller operations such as customer-service messaging and item publishing.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from src.infrastructure.config.env_manager import env_manager


ACCOUNT_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")
_GOOFISH_ENV_LOCK = threading.RLock()


class SellerToolError(RuntimeError):
    """Raised when seller-side automation cannot be completed."""


def _strip_quotes(value: str) -> str:
    if not value:
        return value
    if value.startswith(("\"", "'")) and value.endswith(("\"", "'")):
        return value[1:-1]
    return value


def _state_dir() -> Path:
    raw = env_manager.get_value("ACCOUNT_STATE_DIR", "state") or "state"
    return Path(_strip_quotes(raw.strip()))


def _account_path(account_name: str) -> Path:
    if not ACCOUNT_NAME_RE.match(account_name):
        raise SellerToolError("账号名称只能包含字母、数字、下划线或短横线。")
    return _state_dir() / f"{account_name}.json"


def list_seller_accounts() -> list[dict[str, str]]:
    state_dir = _state_dir()
    if not state_dir.is_dir():
        return []
    return [
        {"name": path.stem, "path": str(path)}
        for path in sorted(state_dir.glob("*.json"))
        if ACCOUNT_NAME_RE.match(path.stem)
    ]


def _normalize_cookie_entries(raw: Any) -> list[dict[str, str]]:
    if isinstance(raw, dict) and isinstance(raw.get("cookies"), list):
        raw = raw["cookies"]

    if isinstance(raw, list):
        entries: list[dict[str, str]] = []
        for cookie in raw:
            if not isinstance(cookie, dict):
                continue
            name = cookie.get("name")
            value = cookie.get("value")
            if name is None or value is None:
                continue
            entries.append({"name": str(name), "value": str(value)})
        return entries

    if isinstance(raw, dict):
        return [{"name": str(key), "value": str(value)} for key, value in raw.items()]

    raise SellerToolError("账号登录态 JSON 格式不受支持。")


def _prepare_goofish_cookie_file(account_name: str | None) -> str | None:
    if not account_name:
        return None

    source_path = _account_path(account_name)
    if not source_path.exists():
        raise SellerToolError(f"账号不存在: {account_name}")

    raw = json.loads(source_path.read_text(encoding="utf-8"))
    cookies = _normalize_cookie_entries(raw)
    if not cookies:
        raise SellerToolError("账号登录态中没有可用 cookie。")

    cache_dir = Path("data") / "goofish-cookies"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_path = cache_dir / f"{account_name}.json"
    target_path.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(target_path.resolve())


@contextmanager
def _goofish_cookie_env(account_name: str | None):
    cookie_path = _prepare_goofish_cookie_file(account_name)
    old_cookie_path = os.environ.get("GOOFISH_COOKIES_PATH")
    old_no_bootstrap = os.environ.get("GOOFISH_NO_CHROME_BOOTSTRAP")
    try:
        if cookie_path:
            os.environ["GOOFISH_COOKIES_PATH"] = cookie_path
            os.environ["GOOFISH_NO_CHROME_BOOTSTRAP"] = "1"
        yield
    finally:
        if old_cookie_path is None:
            os.environ.pop("GOOFISH_COOKIES_PATH", None)
        else:
            os.environ["GOOFISH_COOKIES_PATH"] = old_cookie_path

        if old_no_bootstrap is None:
            os.environ.pop("GOOFISH_NO_CHROME_BOOTSTRAP", None)
        else:
            os.environ["GOOFISH_NO_CHROME_BOOTSTRAP"] = old_no_bootstrap


def _run_with_account(account_name: str | None, func: Callable[[], Any]) -> Any:
    try:
        with _GOOFISH_ENV_LOCK:
            with _goofish_cookie_env(account_name):
                return func()
    except SellerToolError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface upstream tool errors cleanly
        raise SellerToolError(str(exc)) from exc


async def _to_thread(account_name: str | None, func: Callable[[], Any]) -> Any:
    return await asyncio.to_thread(_run_with_account, account_name, func)


class GoofishSellerService:
    async def auth_status(self, account_name: str | None = None) -> dict[str, Any]:
        def _call():
            from goofish_cli.commands.auth.status import status

            return status()

        return await _to_thread(account_name, _call)

    async def list_chats(
        self,
        *,
        account_name: str | None = None,
        fetch_num: int = 50,
        watch_secs: float = 0.0,
    ) -> dict[str, Any]:
        def _call():
            from goofish_cli.commands.message.list_chats import list_chats

            return list_chats(fetch_num=fetch_num, watch_secs=watch_secs)

        return await _to_thread(account_name, _call)

    async def message_history(
        self,
        *,
        cid: str,
        account_name: str | None = None,
        limit_per_page: int = 20,
    ) -> list[dict[str, Any]]:
        def _call():
            from goofish_cli.commands.message.history import history

            return history(cid=cid, limit_per_page=limit_per_page)

        return await _to_thread(account_name, _call)

    async def send_message(
        self,
        *,
        cid: str,
        toid: str,
        text: str,
        account_name: str | None = None,
        item_id: str = "",
    ) -> dict[str, Any]:
        def _call():
            from goofish_cli.commands.message.send import send

            return send(cid=cid, toid=toid, text=text, item_id=item_id)

        return await _to_thread(account_name, _call)

    async def publish_item(
        self,
        *,
        title: str,
        desc: str,
        images: list[str],
        price: float,
        account_name: str | None = None,
        original_price: float | None = None,
        delivery: str = "无需邮寄",
        post_price: float = 0,
        can_self_pickup: bool = True,
    ) -> dict[str, Any]:
        def _call():
            from goofish_cli.commands.item.publish import publish

            return publish(
                title=title,
                desc=desc,
                images=images,
                price=price,
                original_price=original_price,
                delivery=delivery,
                post_price=post_price,
                can_self_pickup=can_self_pickup,
            )

        return await _to_thread(account_name, _call)


seller_service = GoofishSellerService()
