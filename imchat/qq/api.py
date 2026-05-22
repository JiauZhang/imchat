from __future__ import annotations

import base64
import logging
import random
import time
from typing import Any

import aiohttp

from .auth import AuthManager
from .exceptions import APIError
from .types import (
    InlineKeyboard,
    MediaFileType,
    MessageResponse,
    StreamMessageRequest,
)

logger = logging.getLogger("imchat.qq.api")

API_BASE = "https://api.sgroup.qq.com"
DEFAULT_TIMEOUT = 30.0
FILE_UPLOAD_TIMEOUT = 120.0


class QQBotAPI:

    def __init__(
        self,
        auth: AuthManager,
        app_id: str,
        client_secret: str,
        markdown_support: bool = False,
    ) -> None:
        self.auth = auth
        self.app_id = app_id
        self.client_secret = client_secret
        self.markdown_support = markdown_support
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=API_BASE,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
                headers={"User-Agent": self._user_agent()},
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        json: Any = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        token = await self.auth.get_access_token(self.app_id, self.client_secret)
        headers = {
            "Authorization": f"QQBot {token}",
            "Content-Type": "application/json",
        }

        session = await self._get_session()
        try:
            async with session.request(
                method=method,
                url=path,
                headers=headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=timeout or DEFAULT_TIMEOUT),
                **kwargs,
            ) as resp:
                raw_body = await resp.text()

                content_type = resp.headers.get("content-type", "")
                is_html = "text/html" in content_type or raw_body.strip().startswith("<")

                if resp.status >= 400:
                    if is_html:
                        status_hint = (
                            "service unavailable, please retry later"
                            if resp.status in (502, 503, 504)
                            else "rate limited"
                            if resp.status == 429
                            else f"HTTP {resp.status}"
                        )
                        raise APIError(f"{status_hint} ({path})", resp.status, path)

                    try:
                        error = await resp.json()
                    except Exception:
                        error = None
                    if error:
                        biz_code = error.get("code") or error.get("err_code")
                        biz_message = error.get("message")
                        raise APIError(
                            f"API Error [{path}]: {biz_message or raw_body}",
                            resp.status,
                            path,
                            biz_code,
                            biz_message,
                        )
                    raise APIError(f"API Error [{path}] HTTP {resp.status}: {raw_body[:200]}", resp.status, path)

                if is_html:
                    raise APIError(f"non-JSON response from QQ server ({path})", resp.status, path)

                try:
                    return await resp.json()
                except Exception as e:
                    raise APIError(f"invalid response format ({path})", resp.status, path) from e

        except aiohttp.ServerTimeoutError as e:
            raise APIError(f"Request timeout [{path}]: exceeded {timeout or DEFAULT_TIMEOUT}s", 0, path) from e
        except aiohttp.ClientError as e:
            raise APIError(f"Network error [{path}]: {e}", 0, path) from e

    async def get_gateway_url(self) -> str:
        data = await self._request("GET", "/gateway")
        return str(data["url"])

    async def send_c2c_message(
        self,
        openid: str,
        content: str,
        msg_id: str | None = None,
        message_reference: str | None = None,
        inline_keyboard: InlineKeyboard | None = None,
    ) -> MessageResponse:
        body = self._build_message_body(content, msg_id, message_reference, inline_keyboard)
        data = await self._request("POST", f"/v2/users/{openid}/messages", json=body)
        return self._to_message_response(data)

    async def send_group_message(
        self,
        group_openid: str,
        content: str,
        msg_id: str | None = None,
        message_reference: str | None = None,
        inline_keyboard: InlineKeyboard | None = None,
    ) -> MessageResponse:
        body = self._build_message_body(content, msg_id, message_reference, inline_keyboard)
        data = await self._request("POST", f"/v2/groups/{group_openid}/messages", json=body)
        return self._to_message_response(data)

    async def send_channel_message(
        self,
        channel_id: str,
        content: str,
        msg_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"content": content}
        if msg_id:
            body["msg_id"] = msg_id
        return await self._request("POST", f"/channels/{channel_id}/messages", json=body)

    async def send_dm_message(
        self,
        guild_id: str,
        content: str,
        msg_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"content": content}
        if msg_id:
            body["msg_id"] = msg_id
        return await self._request("POST", f"/dms/{guild_id}/messages", json=body)

    async def send_proactive_c2c_message(self, openid: str, content: str) -> MessageResponse:
        body = self._build_proactive_body(content)
        data = await self._request("POST", f"/v2/users/{openid}/messages", json=body)
        return self._to_message_response(data)

    async def send_proactive_group_message(self, group_openid: str, content: str) -> dict[str, Any]:
        body = self._build_proactive_body(content)
        return await self._request("POST", f"/v2/groups/{group_openid}/messages", json=body)

    async def send_c2c_input_notify(
        self,
        openid: str,
        msg_id: str | None = None,
        input_second: int = 60,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "msg_type": 6,
            "input_notify": {"input_type": 1, "input_second": input_second},
            "msg_seq": self._next_msg_seq(msg_id or ""),
        }
        if msg_id:
            body["msg_id"] = msg_id
        return await self._request("POST", f"/v2/users/{openid}/messages", json=body)

    async def acknowledge_interaction(
        self,
        interaction_id: str,
        code: int = 0,
        data: dict[str, Any] | None = None,
    ) -> None:
        body: dict[str, Any] = {"code": code}
        if data:
            body["data"] = data
        await self._request("PUT", f"/interactions/{interaction_id}", json=body)

    async def upload_c2c_media(
        self,
        openid: str,
        file_type: MediaFileType,
        url: str | None = None,
        file_data: bytes | None = None,
        srv_send_msg: bool = False,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        if not url and not file_data:
            raise ValueError("upload_c2c_media: url or file_data is required")
        body: dict[str, Any] = {"file_type": int(file_type), "srv_send_msg": srv_send_msg}
        if url:
            body["url"] = url
        elif file_data:
            body["file_data"] = base64.b64encode(file_data).decode()
        if file_type == MediaFileType.FILE and file_name:
            body["file_name"] = file_name
        return await self._request("POST", f"/v2/users/{openid}/files", json=body, timeout=FILE_UPLOAD_TIMEOUT)

    async def upload_group_media(
        self,
        group_openid: str,
        file_type: MediaFileType,
        url: str | None = None,
        file_data: bytes | None = None,
        srv_send_msg: bool = False,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        if not url and not file_data:
            raise ValueError("upload_group_media: url or file_data is required")
        body: dict[str, Any] = {"file_type": int(file_type), "srv_send_msg": srv_send_msg}
        if url:
            body["url"] = url
        elif file_data:
            body["file_data"] = base64.b64encode(file_data).decode()
        if file_type == MediaFileType.FILE and file_name:
            body["file_name"] = file_name
        return await self._request("POST", f"/v2/groups/{group_openid}/files", json=body, timeout=FILE_UPLOAD_TIMEOUT)

    async def send_c2c_media_message(
        self,
        openid: str,
        file_info: str,
        msg_id: str | None = None,
        content: str | None = None,
    ) -> MessageResponse:
        body: dict[str, Any] = {
            "msg_type": 7,
            "media": {"file_info": file_info},
            "msg_seq": self._next_msg_seq(msg_id or ""),
        }
        if content:
            body["content"] = content
        if msg_id:
            body["msg_id"] = msg_id
        data = await self._request("POST", f"/v2/users/{openid}/messages", json=body)
        return self._to_message_response(data)

    async def send_group_media_message(
        self,
        group_openid: str,
        file_info: str,
        msg_id: str | None = None,
        content: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "msg_type": 7,
            "media": {"file_info": file_info},
            "msg_seq": self._next_msg_seq(msg_id or ""),
        }
        if content:
            body["content"] = content
        if msg_id:
            body["msg_id"] = msg_id
        return await self._request("POST", f"/v2/groups/{group_openid}/messages", json=body)

    async def send_c2c_image(
        self,
        openid: str,
        image_url: str | None = None,
        image_data: bytes | None = None,
        msg_id: str | None = None,
        content: str = "",
    ) -> MessageResponse:
        upload = await self.upload_c2c_media(openid, MediaFileType.IMAGE, url=image_url, file_data=image_data)
        return await self.send_c2c_media_message(openid, upload["file_info"], msg_id=msg_id, content=content)

    async def send_group_image(
        self,
        group_openid: str,
        image_url: str | None = None,
        image_data: bytes | None = None,
        msg_id: str | None = None,
        content: str = "",
    ) -> dict[str, Any]:
        upload = await self.upload_group_media(group_openid, MediaFileType.IMAGE, url=image_url, file_data=image_data)
        return await self.send_group_media_message(group_openid, upload["file_info"], msg_id=msg_id, content=content)

    async def send_c2c_voice(
        self,
        openid: str,
        voice_data: bytes | None = None,
        voice_url: str | None = None,
        msg_id: str | None = None,
    ) -> MessageResponse:
        upload = await self.upload_c2c_media(openid, MediaFileType.VOICE, url=voice_url, file_data=voice_data)
        return await self.send_c2c_media_message(openid, upload["file_info"], msg_id=msg_id)

    async def send_group_voice(
        self,
        group_openid: str,
        voice_data: bytes | None = None,
        voice_url: str | None = None,
        msg_id: str | None = None,
    ) -> dict[str, Any]:
        upload = await self.upload_group_media(group_openid, MediaFileType.VOICE, url=voice_url, file_data=voice_data)
        return await self.send_group_media_message(group_openid, upload["file_info"], msg_id=msg_id)

    async def send_c2c_file(
        self,
        openid: str,
        file_data: bytes | None = None,
        file_url: str | None = None,
        msg_id: str | None = None,
        file_name: str | None = None,
    ) -> MessageResponse:
        upload = await self.upload_c2c_media(openid, MediaFileType.FILE, url=file_url, file_data=file_data, file_name=file_name)
        return await self.send_c2c_media_message(openid, upload["file_info"], msg_id=msg_id)

    async def send_group_file(
        self,
        group_openid: str,
        file_data: bytes | None = None,
        file_url: str | None = None,
        msg_id: str | None = None,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        upload = await self.upload_group_media(group_openid, MediaFileType.FILE, url=file_url, file_data=file_data, file_name=file_name)
        return await self.send_group_media_message(group_openid, upload["file_info"], msg_id=msg_id)

    async def send_c2c_video(
        self,
        openid: str,
        video_data: bytes | None = None,
        video_url: str | None = None,
        msg_id: str | None = None,
        content: str = "",
    ) -> MessageResponse:
        upload = await self.upload_c2c_media(openid, MediaFileType.VIDEO, url=video_url, file_data=video_data)
        return await self.send_c2c_media_message(openid, upload["file_info"], msg_id=msg_id, content=content)

    async def send_group_video(
        self,
        group_openid: str,
        video_data: bytes | None = None,
        video_url: str | None = None,
        msg_id: str | None = None,
        content: str = "",
    ) -> dict[str, Any]:
        upload = await self.upload_group_media(group_openid, MediaFileType.VIDEO, url=video_url, file_data=video_data)
        return await self.send_group_media_message(group_openid, upload["file_info"], msg_id=msg_id, content=content)

    async def send_c2c_stream_message(
        self,
        openid: str,
        req: StreamMessageRequest,
    ) -> MessageResponse:
        body: dict[str, Any] = {
            "input_mode": req.input_mode.value,
            "input_state": req.input_state.value,
            "content_type": req.content_type.value,
            "content_raw": req.content_raw,
            "event_id": req.event_id,
            "msg_id": req.msg_id,
            "msg_seq": req.msg_seq,
            "index": req.index,
        }
        if req.stream_msg_id:
            body["stream_msg_id"] = req.stream_msg_id
        data = await self._request("POST", f"/v2/users/{openid}/stream_messages", json=body)
        return self._to_message_response(data)

    def _build_message_body(
        self,
        content: str,
        msg_id: str | None,
        message_reference: str | None = None,
        inline_keyboard: InlineKeyboard | None = None,
    ) -> dict[str, Any]:
        if self.markdown_support:
            body: dict[str, Any] = {
                "markdown": {"content": content},
                "msg_type": 2,
                "msg_seq": self._next_msg_seq(msg_id or ""),
            }
        else:
            body = {
                "content": content,
                "msg_type": 0,
                "msg_seq": self._next_msg_seq(msg_id or ""),
            }
        if msg_id:
            body["msg_id"] = msg_id
        if message_reference and not self.markdown_support:
            body["message_reference"] = {"message_id": message_reference}
        if inline_keyboard:
            body["keyboard"] = inline_keyboard.to_dict()
        return body

    def _build_proactive_body(self, content: str) -> dict[str, Any]:
        if not content or not content.strip():
            raise ValueError("proactive message content must not be empty")
        if self.markdown_support:
            return {"markdown": {"content": content}, "msg_type": 2}
        return {"content": content, "msg_type": 0}

    @staticmethod
    def _next_msg_seq(msg_id: str) -> int:
        time_part = int(time.time() * 1000) % 100000000
        rand = random.randint(0, 65535)
        return (time_part ^ rand) % 65536

    @staticmethod
    def _to_message_response(data: Any) -> MessageResponse:
        return MessageResponse(
            id=str(data.get("id", "")),
            timestamp=data.get("timestamp", 0),
            ref_idx=data.get("ext_info", {}).get("ref_idx"),
        )

    @staticmethod
    def _user_agent() -> str:
        import platform
        import sys

        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        os_name = platform.system().lower()
        return f"QQBotSDK/0.1.0 (Python/{py_version}; {os_name})"