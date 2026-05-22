from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from .api import QQBotAPI
from .auth import AuthManager
from .config import QQConfig
from .gateway import GatewayClient
from .types import (
    C2CMessage,
    DirectMessage,
    GroupMessage,
    GuildMessage,
    Interaction,
    MessageHandler,
)
from ..keystore import load_keys, save_keys, delete_keys

logger = logging.getLogger("imchat.qq.client")


class QQClient:

    def __init__(self, config: QQConfig | None = None) -> None:
        self.config = config or QQConfig.from_env()
        self.auth = AuthManager()
        self.api = QQBotAPI(
            auth=self.auth,
            app_id=self.config.app_id,
            client_secret=self.config.resolve_client_secret(),
            markdown_support=self.config.markdown_support,
        )
        self.gateway = GatewayClient(self.api)
        self._message_handlers: list[MessageHandler] = []

    @classmethod
    def from_saved_keys(cls, app_id: str | None = None) -> QQClient | None:
        keys = load_keys("qq")
        saved_app_id = app_id or keys.get("app_id")
        client_secret = keys.get("client_secret")
        if not saved_app_id or not client_secret:
            return None
        config = QQConfig(
            app_id=saved_app_id,
            client_secret=client_secret,
            markdown_support=keys.get("markdown_support", True),
        )
        return cls(config)

    def save_credentials(self) -> None:
        save_keys("qq", {
            "app_id": self.config.app_id,
            "client_secret": self.config.resolve_client_secret(),
            "markdown_support": self.config.markdown_support,
        })

    def logout(self) -> None:
        delete_keys("qq")

    def on_message(self, handler: MessageHandler | None = None) -> Callable[[MessageHandler], MessageHandler] | MessageHandler:
        def decorator(h: MessageHandler) -> MessageHandler:
            self._message_handlers.append(h)
            self.gateway.on_c2c_message(lambda msg: self._route_message(msg, h))
            self.gateway.on_group_message(lambda msg: self._route_message(msg, h))
            self.gateway.on_guild_message(lambda msg: self._route_message(msg, h))
            self.gateway.on_direct_message(lambda msg: self._route_message(msg, h))
            return h

        if handler is not None:
            return decorator(handler)
        return decorator

    def on_c2c_message(self, handler: Callable[[C2CMessage], Coroutine[Any, Any, None]]) -> Callable[[C2CMessage], Coroutine[Any, Any, None]]:
        self.gateway.on_c2c_message(handler)
        return handler

    def on_group_message(self, handler: Callable[[GroupMessage], Coroutine[Any, Any, None]]) -> Callable[[GroupMessage], Coroutine[Any, Any, None]]:
        self.gateway.on_group_message(handler)
        return handler

    def on_guild_message(self, handler: Callable[[GuildMessage], Coroutine[Any, Any, None]]) -> Callable[[GuildMessage], Coroutine[Any, Any, None]]:
        self.gateway.on_guild_message(handler)
        return handler

    def on_direct_message(self, handler: Callable[[DirectMessage], Coroutine[Any, Any, None]]) -> Callable[[DirectMessage], Coroutine[Any, Any, None]]:
        self.gateway.on_direct_message(handler)
        return handler

    def on_interaction(self, handler: Callable[[Interaction], Coroutine[Any, Any, None]]) -> Callable[[Interaction], Coroutine[Any, Any, None]]:
        self.gateway.on_interaction(handler)
        return handler

    def on_ready(self, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> Callable[[dict[str, Any]], Coroutine[Any, Any, None]]:
        self.gateway.on_ready(handler)
        return handler

    def on_error(self, handler: Callable[[Exception], Coroutine[Any, Any, None]]) -> Callable[[Exception], Coroutine[Any, Any, None]]:
        self.gateway.on_error(handler)
        return handler

    async def start(self) -> None:
        if not self.config.app_id or not self.config.resolve_client_secret():
            raise ValueError("QQClient not configured (missing app_id or client_secret)")

        self.auth.start_background_refresh(
            self.config.app_id,
            self.config.resolve_client_secret(),
        )

        try:
            await self.gateway.start()
        finally:
            self.auth.stop_background_refresh(self.config.app_id)
            await self.api.close()

    async def stop(self) -> None:
        await self.gateway.stop()
        self.auth.stop_background_refresh(self.config.app_id)
        await self.api.close()

    async def send_c2c_message(self, openid: str, content: str, **kwargs: Any) -> Any:
        return await self.api.send_c2c_message(openid, content, **kwargs)

    async def send_group_message(self, group_openid: str, content: str, **kwargs: Any) -> Any:
        return await self.api.send_group_message(group_openid, content, **kwargs)

    async def send_channel_message(self, channel_id: str, content: str, **kwargs: Any) -> Any:
        return await self.api.send_channel_message(channel_id, content, **kwargs)

    async def send_dm_message(self, guild_id: str, content: str, **kwargs: Any) -> Any:
        return await self.api.send_dm_message(guild_id, content, **kwargs)

    async def send_c2c_image(self, openid: str, image_url: str | None = None, image_data: bytes | None = None, **kwargs: Any) -> Any:
        return await self.api.send_c2c_image(openid, image_url=image_url, image_data=image_data, **kwargs)

    async def send_group_image(self, group_openid: str, image_url: str | None = None, image_data: bytes | None = None, **kwargs: Any) -> Any:
        return await self.api.send_group_image(group_openid, image_url=image_url, image_data=image_data, **kwargs)

    @staticmethod
    async def _route_message(msg: Any, handler: MessageHandler) -> None:
        try:
            await handler(msg)
        except Exception as e:
            logger.error(f"[qq-client] Message handler error: {e}")