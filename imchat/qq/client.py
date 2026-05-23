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
    StreamMessageRequest,
)
from ..keystore import load_keys, save_keys, delete_keys

logger = logging.getLogger("imchat.qq.client")


class QQClient:

    def __init__(
        self,
        config: QQConfig | None = None,
        app_id: str | None = None,
        client_secret: str | None = None,
        markdown_support: bool = True,
    ) -> None:
        if config:
            self.config = config
        else:
            self.config = QQConfig(
                app_id=app_id or "",
                client_secret=client_secret or "",
                markdown_support=markdown_support,
            )
            if not self.config.app_id:
                self.config.app_id = QQConfig.from_env().app_id
            if not self.config.resolve_client_secret():
                self.config.client_secret = QQConfig.from_env().resolve_client_secret()
            if not self.config.app_id or not self.config.resolve_client_secret():
                saved = self.from_saved_keys()
                if saved:
                    self.config = saved.config
        self.auth = AuthManager()
        self.api = QQBotAPI(
            auth=self.auth,
            app_id=self.config.app_id,
            client_secret=self.config.resolve_client_secret(),
            markdown_support=self.config.markdown_support,
        )
        self.gateway = GatewayClient(self.api)

    @classmethod
    def from_saved_keys(cls) -> QQClient | None:
        keys = load_keys("qq")
        saved_app_id = keys.get("app_id")
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
            raise ValueError(
                "QQClient not configured. Get app_id and client_secret from:\n"
                "  https://bot.q.qq.com/\n\n"
                "Then set credentials via:\n"
                "  1. Environment: export QQBOT_APP_ID=<app_id> QQBOT_CLIENT_SECRET=<client_secret>\n"
                "  2. Direct: client = QQClient(app_id='...', client_secret='...')\n"
                "  3. Save: client.save_credentials()\n"
                "  4. CLI: examples/qq_api_only.py --app-id <app_id> --client-secret <client_secret>"
            )

        self.auth.start_background_refresh(
            self.config.app_id,
            self.config.resolve_client_secret(),
        )

        try:
            await self.gateway.start()
        finally:
            self.auth.stop_background_refresh(self.config.app_id)
            await self.auth.close()
            await self.api.close()

    async def stop(self) -> None:
        await self.gateway.stop()
        self.auth.stop_background_refresh(self.config.app_id)
        await self.auth.close()
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

    async def get_gateway_url(self) -> str:
        return await self.api.get_gateway_url()

    async def send_c2c_input_notify(
        self,
        openid: str,
        msg_id: str | None = None,
        input_second: int = 60,
    ) -> dict[str, Any]:
        return await self.api.send_c2c_input_notify(openid, msg_id=msg_id, input_second=input_second)

    async def upload_c2c_media(
        self,
        openid: str,
        file_type: Any,
        url: str | None = None,
        file_data: bytes | None = None,
        srv_send_msg: bool = False,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        return await self.api.upload_c2c_media(openid, file_type, url=url, file_data=file_data, srv_send_msg=srv_send_msg, file_name=file_name)

    async def upload_group_media(
        self,
        group_openid: str,
        file_type: Any,
        url: str | None = None,
        file_data: bytes | None = None,
        srv_send_msg: bool = False,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        return await self.api.upload_group_media(group_openid, file_type, url=url, file_data=file_data, srv_send_msg=srv_send_msg, file_name=file_name)

    async def send_c2c_voice(
        self,
        openid: str,
        voice_data: bytes | None = None,
        voice_url: str | None = None,
        msg_id: str | None = None,
    ) -> Any:
        return await self.api.send_c2c_voice(openid, voice_data=voice_data, voice_url=voice_url, msg_id=msg_id)

    async def send_group_voice(
        self,
        group_openid: str,
        voice_data: bytes | None = None,
        voice_url: str | None = None,
        msg_id: str | None = None,
    ) -> dict[str, Any]:
        return await self.api.send_group_voice(group_openid, voice_data=voice_data, voice_url=voice_url, msg_id=msg_id)

    async def send_c2c_file(
        self,
        openid: str,
        file_data: bytes | None = None,
        file_url: str | None = None,
        msg_id: str | None = None,
        file_name: str | None = None,
    ) -> Any:
        return await self.api.send_c2c_file(openid, file_data=file_data, file_url=file_url, msg_id=msg_id, file_name=file_name)

    async def send_group_file(
        self,
        group_openid: str,
        file_data: bytes | None = None,
        file_url: str | None = None,
        msg_id: str | None = None,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        return await self.api.send_group_file(group_openid, file_data=file_data, file_url=file_url, msg_id=msg_id, file_name=file_name)

    async def send_c2c_video(
        self,
        openid: str,
        video_data: bytes | None = None,
        video_url: str | None = None,
        msg_id: str | None = None,
        content: str = "",
    ) -> Any:
        return await self.api.send_c2c_video(openid, video_data=video_data, video_url=video_url, msg_id=msg_id, content=content)

    async def send_group_video(
        self,
        group_openid: str,
        video_data: bytes | None = None,
        video_url: str | None = None,
        msg_id: str | None = None,
        content: str = "",
    ) -> dict[str, Any]:
        return await self.api.send_group_video(group_openid, video_data=video_data, video_url=video_url, msg_id=msg_id, content=content)

    async def send_c2c_stream_message(self, openid: str, req: StreamMessageRequest) -> Any:
        return await self.api.send_c2c_stream_message(openid, req)