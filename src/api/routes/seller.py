"""Seller-side customer-service and listing routes."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.goofish_seller_service import (
    SellerToolError,
    list_seller_accounts,
    seller_service,
)


router = APIRouter(prefix="/api/seller", tags=["seller"])


class AccountScopedRequest(BaseModel):
    account_name: str | None = None


class ChatListRequest(AccountScopedRequest):
    fetch_num: int = Field(default=50, ge=1, le=200)
    watch_secs: float = Field(default=0.0, ge=0, le=30)


class ChatHistoryRequest(AccountScopedRequest):
    cid: str = Field(min_length=1)
    limit_per_page: int = Field(default=20, ge=1, le=100)


class SendMessageRequest(AccountScopedRequest):
    cid: str = Field(min_length=1)
    toid: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=1000)
    item_id: str = ""


class PublishItemRequest(AccountScopedRequest):
    title: str = Field(min_length=1, max_length=60)
    desc: str = Field(min_length=1, max_length=5000)
    images: list[str] = Field(min_length=1)
    price: float = Field(gt=0)
    original_price: float | None = Field(default=None, gt=0)
    delivery: Literal["包邮", "按距离计费", "一口价", "无需邮寄"] = "无需邮寄"
    post_price: float = Field(default=0, ge=0)
    can_self_pickup: bool = True


def _handle_seller_error(exc: SellerToolError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/accounts")
async def get_seller_accounts():
    return {"accounts": list_seller_accounts()}


@router.post("/auth/status")
async def auth_status(payload: AccountScopedRequest):
    try:
        result = await seller_service.auth_status(payload.account_name)
    except SellerToolError as exc:
        raise _handle_seller_error(exc) from exc
    return result


@router.post("/chats")
async def list_chats(payload: ChatListRequest):
    try:
        return await seller_service.list_chats(
            account_name=payload.account_name,
            fetch_num=payload.fetch_num,
            watch_secs=payload.watch_secs,
        )
    except SellerToolError as exc:
        raise _handle_seller_error(exc) from exc


@router.post("/history")
async def chat_history(payload: ChatHistoryRequest):
    try:
        return {
            "messages": await seller_service.message_history(
                account_name=payload.account_name,
                cid=payload.cid,
                limit_per_page=payload.limit_per_page,
            )
        }
    except SellerToolError as exc:
        raise _handle_seller_error(exc) from exc


@router.post("/send")
async def send_message(payload: SendMessageRequest):
    try:
        return await seller_service.send_message(
            account_name=payload.account_name,
            cid=payload.cid,
            toid=payload.toid,
            text=payload.text,
            item_id=payload.item_id,
        )
    except SellerToolError as exc:
        raise _handle_seller_error(exc) from exc


@router.post("/publish")
async def publish_item(payload: PublishItemRequest):
    try:
        return await seller_service.publish_item(
            account_name=payload.account_name,
            title=payload.title,
            desc=payload.desc,
            images=payload.images,
            price=payload.price,
            original_price=payload.original_price,
            delivery=payload.delivery,
            post_price=payload.post_price,
            can_self_pickup=payload.can_self_pickup,
        )
    except SellerToolError as exc:
        raise _handle_seller_error(exc) from exc
