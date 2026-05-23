from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

import aiohttp

from .api import QQBotAPI
from .types import (
    C2CMessage,
    DirectMessage,
    GroupMessage,
    GuildMessage,
    Interaction,
    Mention,
    MessageAttachment,
    MessageScene,
    MsgElement,
)

logger = logging.getLogger("imchat.qq.gateway")

INTENTS = {
    "GUILDS": 1 << 0,
    "GUILD_MEMBERS": 1 << 1,
    "PUBLIC_GUILD_MESSAGES": 1 << 30,
    "DIRECT_MESSAGE": 1 << 12,
    "GROUP_AND_C2C": 1 << 25,
    "INTERACTION": 1 << 26,
}
FULL_INTENTS = (
    INTENTS["PUBLIC_GUILD_MESSAGES"]
    | INTENTS["DIRECT_MESSAGE"]
    | INTENTS["GROUP_AND_C2C"]
    | INTENTS["INTERACTION"]
)

RECONNECT_DELAYS = [1, 2, 5, 10, 30, 60]
MAX_RECONNECT_ATTEMPTS = 100


class GatewayClient:

    def __init__(self, api: QQBotAPI) -> None:
        self.api = api
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._running = False
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._session_id: str | None = None
        self._last_seq: int | None = None
        self._reconnect_attempts = 0

        self._c2c_handlers: list[Callable[[C2CMessage], Coroutine[Any, Any, None]]] = []
        self._group_handlers: list[Callable[[GroupMessage], Coroutine[Any, Any, None]]] = []
        self._guild_handlers: list[Callable[[GuildMessage], Coroutine[Any, Any, None]]] = []
        self._dm_handlers: list[Callable[[DirectMessage], Coroutine[Any, Any, None]]] = []
        self._interaction_handlers: list[Callable[[Interaction], Coroutine[Any, Any, None]]] = []
        self._ready_handlers: list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]] = []
        self._error_handlers: list[Callable[[Exception], Coroutine[Any, Any, None]]] = []

    def on_c2c_message(self, handler: Callable[[C2CMessage], Coroutine[Any, Any, None]]) -> Callable[[C2CMessage], Coroutine[Any, Any, None]]:
        self._c2c_handlers.append(handler)
        return handler

    def on_group_message(self, handler: Callable[[GroupMessage], Coroutine[Any, Any, None]]) -> Callable[[GroupMessage], Coroutine[Any, Any, None]]:
        self._group_handlers.append(handler)
        return handler

    def on_guild_message(self, handler: Callable[[GuildMessage], Coroutine[Any, Any, None]]) -> Callable[[GuildMessage], Coroutine[Any, Any, None]]:
        self._guild_handlers.append(handler)
        return handler

    def on_direct_message(self, handler: Callable[[DirectMessage], Coroutine[Any, Any, None]]) -> Callable[[DirectMessage], Coroutine[Any, Any, None]]:
        self._dm_handlers.append(handler)
        return handler

    def on_interaction(self, handler: Callable[[Interaction], Coroutine[Any, Any, None]]) -> Callable[[Interaction], Coroutine[Any, Any, None]]:
        self._interaction_handlers.append(handler)
        return handler

    def on_ready(self, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> Callable[[dict[str, Any]], Coroutine[Any, Any, None]]:
        self._ready_handlers.append(handler)
        return handler

    def on_error(self, handler: Callable[[Exception], Coroutine[Any, Any, None]]) -> Callable[[Exception], Coroutine[Any, Any, None]]:
        self._error_handlers.append(handler)
        return handler

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"[qq-gateway] Connection error: {e}")
                await self._notify_error(e)
                if not await self._schedule_reconnect():
                    break

    async def stop(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._session:
            await self._session.close()
            self._session = None

    async def _connect(self) -> None:
        token = await self.api.auth.get_access_token(self.api.app_id, self.api.client_secret)
        gateway_url = await self.api.get_gateway_url()

        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.api._user_agent()},
        )
        self._ws = await self._session.ws_connect(gateway_url)
        self._reconnect_attempts = 0

        try:
            async for msg in self._ws:
                if not self._running:
                    break
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_ws_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    break
        finally:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            if self._ws:
                await self._ws.close()
                self._ws = None
            if self._session:
                await self._session.close()
                self._session = None

    async def _handle_ws_message(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return

        op = payload.get("op")
        d = payload.get("d")
        s = payload.get("s")
        t = payload.get("t")

        if s is not None:
            self._last_seq = s

        if op == 10:
            await self._handle_hello(d)
        elif op == 0:
            await self._handle_dispatch(t, d)
        elif op == 11:
            pass
        elif op == 7:
            if self._ws:
                await self._ws.close()
        elif op == 9:
            await self._handle_invalid_session(d)

    async def _handle_hello(self, d: Any) -> None:
        interval = d.get("heartbeat_interval", 41250)

        token = await self.api.auth.get_access_token(self.api.app_id, self.api.client_secret)

        if self._session_id and self._last_seq is not None:
            await self._ws.send_json({
                "op": 6,
                "d": {
                    "token": f"QQBot {token}",
                    "session_id": self._session_id,
                    "seq": self._last_seq,
                },
            })
        else:
            await self._ws.send_json({
                "op": 2,
                "d": {
                    "token": f"QQBot {token}",
                    "intents": FULL_INTENTS,
                    "shard": [0, 1],
                },
            })

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))

    async def _handle_dispatch(self, t: str | None, d: Any) -> None:
        if t == "READY":
            self._session_id = d.get("session_id")
            for handler in self._ready_handlers:
                asyncio.create_task(handler(d))

        elif t == "RESUMED":
            for handler in self._ready_handlers:
                asyncio.create_task(handler(d))

        elif t == "C2C_MESSAGE_CREATE":
            msg = self._parse_c2c_message(d)
            if msg.author_bot:
                return
            for handler in self._c2c_handlers:
                asyncio.create_task(handler(msg))

        elif t == "AT_MESSAGE_CREATE":
            msg = self._parse_guild_message(d)
            for handler in self._guild_handlers:
                asyncio.create_task(handler(msg))

        elif t == "DIRECT_MESSAGE_CREATE":
            msg = self._parse_dm_message(d)
            for handler in self._dm_handlers:
                asyncio.create_task(handler(msg))

        elif t == "GROUP_AT_MESSAGE_CREATE" or t == "GROUP_MESSAGE_CREATE":
            msg = self._parse_group_message(d)
            for handler in self._group_handlers:
                asyncio.create_task(handler(msg))

        elif t == "INTERACTION_CREATE":
            interaction = self._parse_interaction(d)
            for handler in self._interaction_handlers:
                asyncio.create_task(handler(interaction))

        elif t in ("GROUP_ADD_ROBOT", "GROUP_DEL_ROBOT", "GROUP_MSG_REJECT", "GROUP_MSG_RECEIVE"):
            pass

    async def _handle_invalid_session(self, d: Any) -> None:
        can_resume = d if isinstance(d, bool) else False
        if not can_resume:
            self._session_id = None
            self._last_seq = None
        if self._ws:
            await self._ws.close()

    async def _heartbeat_loop(self, interval: int) -> None:
        try:
            while self._running and self._ws and not self._ws.closed:
                await asyncio.sleep(interval / 1000)
                if self._ws and not self._ws.closed:
                    await self._ws.send_json({"op": 1, "d": self._last_seq})
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _schedule_reconnect(self) -> bool:
        if not self._running or self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            return False

        delay = RECONNECT_DELAYS[min(self._reconnect_attempts, len(RECONNECT_DELAYS) - 1)]
        self._reconnect_attempts += 1
        await asyncio.sleep(delay)
        return True

    async def _notify_error(self, error: Exception) -> None:
        for handler in self._error_handlers:
            try:
                await handler(error)
            except Exception:
                pass

    def _parse_c2c_message(self, d: Any) -> C2CMessage:
        author = d.get("author", {})
        scene = d.get("message_scene")
        refs = self._parse_ref_indices(
            scene.get("ext") if scene else None,
            d.get("message_type"),
            d.get("msg_elements"),
        )
        msg = C2CMessage(
            id=d.get("id", ""),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", ""),
            author_id=author.get("user_openid", ""),
            author_bot=author.get("bot", False),
            user_openid=author.get("user_openid", ""),
            attachments=[self._parse_attachment(a) for a in d.get("attachments", [])],
            message_scene=MessageScene(source=scene["source"], ext=scene.get("ext", [])) if scene else None,
            message_type=d.get("message_type", 0),
            msg_elements=[self._parse_msg_element(e) for e in d.get("msg_elements", [])],
            msg_idx=refs.get("msg_idx"),
            ref_msg_idx=refs.get("ref_msg_idx"),
        )
        msg._api = self.api
        return msg

    def _parse_group_message(self, d: Any) -> GroupMessage:
        author = d.get("author", {})
        scene = d.get("message_scene")
        refs = self._parse_ref_indices(
            scene.get("ext") if scene else None,
            d.get("message_type"),
            d.get("msg_elements"),
        )
        msg = GroupMessage(
            id=d.get("id", ""),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", ""),
            author_id=author.get("member_openid", ""),
            author_name=author.get("username"),
            author_bot=author.get("bot", False),
            group_openid=d.get("group_openid", ""),
            group_id=d.get("group_id", ""),
            member_openid=author.get("member_openid", ""),
            mentions=[self._parse_mention(m) for m in d.get("mentions", [])],
            attachments=[self._parse_attachment(a) for a in d.get("attachments", [])],
            message_scene=MessageScene(source=scene["source"], ext=scene.get("ext", [])) if scene else None,
            message_type=d.get("message_type", 0),
            msg_elements=[self._parse_msg_element(e) for e in d.get("msg_elements", [])],
            msg_idx=refs.get("msg_idx"),
            ref_msg_idx=refs.get("ref_msg_idx"),
        )
        msg._api = self.api
        return msg

    def _parse_guild_message(self, d: Any) -> GuildMessage:
        author = d.get("author", {})
        msg = GuildMessage(
            id=d.get("id", ""),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", ""),
            author_id=author.get("id", ""),
            author_name=author.get("username"),
            author_bot=author.get("bot", False),
            channel_id=d.get("channel_id", ""),
            guild_id=d.get("guild_id", ""),
            attachments=[self._parse_attachment(a) for a in d.get("attachments", [])],
        )
        msg._api = self.api
        return msg

    def _parse_dm_message(self, d: Any) -> DirectMessage:
        author = d.get("author", {})
        msg = DirectMessage(
            id=d.get("id", ""),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", ""),
            author_id=author.get("id", ""),
            author_name=author.get("username"),
            author_bot=author.get("bot", False),
            guild_id=d.get("guild_id", ""),
            attachments=[self._parse_attachment(a) for a in d.get("attachments", [])],
        )
        msg._api = self.api
        return msg

    def _parse_interaction(self, d: Any) -> Interaction:
        data = d.get("data", {})
        resolved = data.get("resolved", {})
        interaction = Interaction(
            id=d.get("id", ""),
            type=d.get("type", 0),
            scene=d.get("scene"),
            chat_type=d.get("chat_type"),
            timestamp=d.get("timestamp"),
            guild_id=d.get("guild_id"),
            channel_id=d.get("channel_id"),
            user_openid=d.get("user_openid"),
            group_openid=d.get("group_openid"),
            group_member_openid=d.get("group_member_openid"),
            version=d.get("version", 0),
            data_type=data.get("type", 0),
            button_data=resolved.get("button_data"),
            button_id=resolved.get("button_id"),
            user_id=resolved.get("user_id"),
            feature_id=resolved.get("feature_id"),
            message_id=resolved.get("message_id"),
        )
        interaction._api = self.api
        return interaction

    @staticmethod
    def _parse_attachment(a: Any) -> MessageAttachment:
        return MessageAttachment(
            content_type=a.get("content_type", ""),
            url=a.get("url", ""),
            filename=a.get("filename"),
            height=a.get("height"),
            width=a.get("width"),
            size=a.get("size"),
            voice_wav_url=a.get("voice_wav_url"),
            asr_refer_text=a.get("asr_refer_text"),
        )

    @staticmethod
    def _parse_mention(m: Any) -> Mention:
        return Mention(
            scope=m.get("scope"),
            id=m.get("id"),
            user_openid=m.get("user_openid"),
            member_openid=m.get("member_openid"),
            nickname=m.get("nickname"),
            bot=m.get("bot", False),
            is_you=m.get("is_you", False),
        )

    @staticmethod
    def _parse_msg_element(e: Any) -> MsgElement:
        return MsgElement(
            msg_idx=e.get("msg_idx"),
            message_type=e.get("message_type"),
            content=e.get("content"),
            attachments=[GatewayClient._parse_attachment(a) for a in e.get("attachments", [])],
            msg_elements=[GatewayClient._parse_msg_element(se) for se in e.get("msg_elements", [])],
        )

    @staticmethod
    def _parse_ref_indices(ext: list[str] | None, msg_type: int | None, msg_elements: list[Any] | None) -> dict[str, str | None]:
        result: dict[str, str | None] = {"ref_msg_idx": None, "msg_idx": None}
        if ext:
            for item in ext:
                if item.startswith("ref_msg_idx="):
                    result["ref_msg_idx"] = item[len("ref_msg_idx="):]
                elif item.startswith("msg_idx="):
                    result["msg_idx"] = item[len("msg_idx="):]
        if msg_type == 103 and msg_elements:
            ref = msg_elements[0]
            if ref.get("msg_idx") and not result["ref_msg_idx"]:
                result["ref_msg_idx"] = ref["msg_idx"]
        return result