import json
import base64
import secrets
from typing import Optional, Dict, Any
import httpx

from .types import (
    BaseInfo,
    GetUpdatesReq,
    GetUpdatesResp,
    GetUploadUrlReq,
    GetUploadUrlResp,
    SendMessageReq,
    SendTypingReq,
    GetConfigResp,
)
from .exceptions import WeChatAPIError, WeChatSessionExpired


DEFAULT_LONG_POLL_TIMEOUT_MS = 35_000
DEFAULT_API_TIMEOUT_MS = 15_000
DEFAULT_CONFIG_TIMEOUT_MS = 10_000
SESSION_EXPIRED_ERRCODE = -14


class WeChatAPIClient:
    """微信 ilink API 客户端"""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        ilink_app_id: str = "bot",
        channel_version: str = "1.0.0",
        timeout_ms: int = DEFAULT_API_TIMEOUT_MS,
        long_poll_timeout_ms: int = DEFAULT_LONG_POLL_TIMEOUT_MS,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.ilink_app_id = ilink_app_id
        self.channel_version = channel_version
        self.timeout_ms = timeout_ms
        self.long_poll_timeout_ms = long_poll_timeout_ms
        self._client = httpx.AsyncClient()

    def _build_client_version(self) -> int:
        """iLink-App-ClientVersion: uint32 encoded as 0x00MMNNPP"""
        parts = self.channel_version.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return ((major & 0xFF) << 16) | ((minor & 0xFF) << 8) | (patch & 0xFF)

    def _random_wechat_uin(self) -> str:
        """X-WECHAT-UIN header: random uint32 -> decimal string -> base64"""
        uint32 = secrets.randbits(32)
        return base64.b64encode(str(uint32).encode("utf-8")).decode("utf-8")

    def _build_common_headers(self) -> Dict[str, str]:
        headers = {
            "iLink-App-Id": self.ilink_app_id,
            "iLink-App-ClientVersion": str(self._build_client_version()),
        }
        return headers

    def _build_post_headers(self, body: str) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Content-Length": str(len(body.encode("utf-8"))),
            "X-WECHAT-UIN": self._random_wechat_uin(),
            **self._build_common_headers(),
        }
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        return headers

    def _build_base_info(self) -> Dict[str, Any]:
        return {"channel_version": self.channel_version}

    async def _api_get(self, endpoint: str, timeout_ms: Optional[int] = None) -> str:
        """GET 请求"""
        url = self.base_url + endpoint.lstrip("/")
        headers = self._build_common_headers()
        timeout = timeout_ms or self.timeout_ms

        try:
            resp = await self._client.get(url, headers=headers, timeout=timeout / 1000)
        except httpx.TimeoutException:
            raise WeChatAPIError(f"GET {endpoint} timeout after {timeout}ms")

        text = resp.text
        if resp.status_code >= 400:
            raise WeChatAPIError(
                f"GET {endpoint} {resp.status_code}: {text}",
                status_code=resp.status_code,
                response_text=text,
            )
        return text

    async def _api_post(
        self, endpoint: str, body_dict: Dict[str, Any], timeout_ms: Optional[int] = None
    ) -> str:
        """POST JSON 请求"""
        url = self.base_url + endpoint.lstrip("/")
        body = json.dumps(body_dict, ensure_ascii=False)
        headers = self._build_post_headers(body)
        timeout = timeout_ms or self.timeout_ms

        try:
            resp = await self._client.post(
                url, headers=headers, content=body.encode("utf-8"), timeout=timeout / 1000
            )
        except httpx.TimeoutException:
            raise WeChatAPIError(f"POST {endpoint} timeout after {timeout}ms")

        text = resp.text
        if resp.status_code >= 400:
            raise WeChatAPIError(
                f"POST {endpoint} {resp.status_code}: {text}",
                status_code=resp.status_code,
                response_text=text,
            )
        return text

    async def get_updates(self, get_updates_buf: str = "") -> GetUpdatesResp:
        """长轮询获取消息更新"""
        try:
            text = await self._api_post(
                "ilink/bot/getupdates",
                {
                    "get_updates_buf": get_updates_buf,
                    "base_info": self._build_base_info(),
                },
                timeout_ms=self.long_poll_timeout_ms,
            )
            return GetUpdatesResp.from_dict(json.loads(text))
        except httpx.TimeoutException:
            # 长轮询超时是正常的,返回空响应让调用方重试
            return GetUpdatesResp(
                ret=0, msgs=[], get_updates_buf=get_updates_buf
            )

    async def get_upload_url(self, req: GetUploadUrlReq) -> GetUploadUrlResp:
        """获取预签名的 CDN 上传 URL"""
        body = req.to_dict()
        body["base_info"] = self._build_base_info()
        text = await self._api_post("ilink/bot/getuploadurl", body)
        return GetUploadUrlResp.from_dict(json.loads(text))

    async def send_message(self, req: SendMessageReq) -> None:
        """发送单条消息"""
        body = req.to_dict()
        if body.get("msg"):
            body["msg"]["base_info"] = self._build_base_info()
        await self._api_post("ilink/bot/sendmessage", body)

    async def get_config(
        self, ilink_user_id: str, context_token: Optional[str] = None
    ) -> GetConfigResp:
        """获取用户配置 (包含 typing_ticket)"""
        body = {
            "ilink_user_id": ilink_user_id,
            "base_info": self._build_base_info(),
        }
        if context_token:
            body["context_token"] = context_token
        text = await self._api_post(
            "ilink/bot/getconfig", body, timeout_ms=DEFAULT_CONFIG_TIMEOUT_MS
        )
        return GetConfigResp.from_dict(json.loads(text))

    async def send_typing(self, req: SendTypingReq) -> None:
        """发送 typing 指示器"""
        body = req.to_dict()
        body["base_info"] = self._build_base_info()
        await self._api_post("ilink/bot/sendtyping", body, timeout_ms=DEFAULT_CONFIG_TIMEOUT_MS)

    async def get_bot_qrcode(self, bot_type: str = "3") -> Dict[str, Any]:
        """获取登录 QR 码"""
        endpoint = f"ilink/bot/get_bot_qrcode?bot_type={bot_type}"
        text = await self._api_get(endpoint)
        return json.loads(text)

    async def get_qrcode_status(
        self, qrcode: str, timeout_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """轮询 QR 码状态"""
        endpoint = f"ilink/bot/get_qrcode_status?qrcode={qrcode}"
        try:
            text = await self._api_get(endpoint, timeout_ms=timeout_ms or 35_000)
            return json.loads(text)
        except httpx.TimeoutException:
            return {"status": "wait"}

    async def close(self):
        await self._client.aclose()
