import asyncio
import uuid
from typing import Optional, List, Callable, AsyncIterator, Dict, Any
from dataclasses import dataclass, field

from .exceptions import WeChatError, WeChatSessionExpired
from .api import WeChatAPIClient, DEFAULT_LONG_POLL_TIMEOUT_MS
from .auth import WeChatAuth, LoginResult
from .cdn import WeChatCDNClient, UploadedFileInfo
from .types import (
    WeixinMessage,
    MessageItem,
    TextItem,
    ImageItem,
    VoiceItem,
    FileItem,
    VideoItem,
    CDNMedia,
    SendMessageReq,
    SendTypingReq,
    MessageType,
    MessageState,
    MessageItemType,
    TypingStatus,
    GetConfigResp,
)
from ..keystore import load_keys, save_keys, delete_keys


@dataclass
class MessageContext:
    body: str
    from_user_id: str
    to_user_id: str
    message: WeixinMessage
    account_id: str
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    context_token: Optional[str] = None


class WeChatClient:

    def __init__(
        self,
        base_url: str = "https://ilinkai.weixin.qq.com",
        token: Optional[str] = None,
        cdn_base_url: str = "https://novac2c.cdn.weixin.qq.com/c2c",
        account_id: Optional[str] = None,
        ilink_app_id: str = "bot",
        channel_version: str = "1.0.0",
    ):
        self.base_url = base_url
        self.token = token
        self.cdn_base_url = cdn_base_url
        self.account_id = account_id or str(uuid.uuid4())
        self._api = WeChatAPIClient(
            base_url=base_url,
            token=token,
            ilink_app_id=ilink_app_id,
            channel_version=channel_version,
        )
        self._cdn = WeChatCDNClient(self._api, cdn_base_url)
        self._auth = WeChatAuth()
        self._get_updates_buf = ""
        self._context_tokens: Dict[str, str] = {}
        self._running = False

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------

    @classmethod
    def from_saved_keys(cls) -> Optional["WeChatClient"]:
        keys = load_keys("wechat")
        token = keys.get("token")
        if not token:
            return None
        return cls(
            base_url=keys.get("base_url", "https://ilinkai.weixin.qq.com"),
            token=token,
            account_id=keys.get("account_id"),
        )

    async def login_with_qr(
        self,
        timeout_ms: int = 480_000,
        verbose: bool = False,
        on_status_change: Optional[Callable[[str], None]] = None,
    ) -> LoginResult:
        start = await self._auth.start_login(self.account_id)
        qrcode_url = start["qrcode_url"]
        session_key = start["session_key"]

        if verbose:
            print(f"请使用微信扫描二维码:")
            print(f"URL: {qrcode_url}")

        result = await self._auth.wait_for_login(
            session_key=session_key,
            timeout_ms=timeout_ms,
            verbose=verbose,
            on_status_change=on_status_change,
        )

        if result.connected and result.bot_token:
            self.token = result.bot_token
            self._api.token = result.bot_token
            if result.base_url:
                self.base_url = result.base_url
                self._api.base_url = result.base_url.rstrip("/") + "/"
            if result.account_id:
                self.account_id = result.account_id

            save_keys("wechat", {
                "token": result.bot_token,
                "account_id": result.account_id,
                "user_id": result.user_id,
                "base_url": result.base_url or self.base_url,
            })

        return result

    def set_token(self, token: str):
        self.token = token
        self._api.token = token

    def logout(self):
        delete_keys("wechat")
        self.token = None
        self._api.token = None
        self.account_id = str(uuid.uuid4())

    # ------------------------------------------------------------------
    # send
    # ------------------------------------------------------------------

    def _generate_client_id(self) -> str:
        return f"pywechat-{uuid.uuid4().hex[:16]}"

    def _get_context_token(self, user_id: str) -> Optional[str]:
        return self._context_tokens.get(user_id)

    def _set_context_token(self, user_id: str, token: str):
        self._context_tokens[user_id] = token

    async def send_text(self, to: str, text: str, context_token: Optional[str] = None) -> str:
        client_id = self._generate_client_id()
        ctx_token = context_token or self._get_context_token(to)

        item_list = []
        if text:
            item_list.append(MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=text)))

        req = SendMessageReq(
            msg=WeixinMessage(
                to_user_id=to,
                client_id=client_id,
                message_type=MessageType.BOT,
                message_state=MessageState.FINISH,
                item_list=item_list if item_list else None,
                context_token=ctx_token,
            )
        )

        await self._api.send_message(req)
        return client_id

    async def send_image(
        self,
        to: str,
        file_path: str,
        text: Optional[str] = None,
        context_token: Optional[str] = None,
    ) -> str:
        uploaded = await self._cdn.upload_file(
            file_path, to, media_type=UploadMediaType.IMAGE
        )
        return await self._send_media_message(
            to, text, uploaded, MessageItemType.IMAGE, context_token
        )

    async def send_video(
        self,
        to: str,
        file_path: str,
        text: Optional[str] = None,
        context_token: Optional[str] = None,
    ) -> str:
        uploaded = await self._cdn.upload_file(
            file_path, to, media_type=UploadMediaType.VIDEO
        )
        return await self._send_media_message(
            to, text, uploaded, MessageItemType.VIDEO, context_token
        )

    async def send_file(
        self,
        to: str,
        file_path: str,
        text: Optional[str] = None,
        context_token: Optional[str] = None,
    ) -> str:
        import os
        uploaded = await self._cdn.upload_file(
            file_path, to, media_type=UploadMediaType.FILE
        )
        return await self._send_media_message(
            to, text, uploaded, MessageItemType.FILE, context_token
        )

    async def _send_media_message(
        self,
        to: str,
        text: Optional[str],
        uploaded: UploadedFileInfo,
        media_type: MessageItemType,
        context_token: Optional[str] = None,
    ) -> str:
        ctx_token = context_token or self._get_context_token(to)
        client_id = self._generate_client_id()

        items: List[MessageItem] = []
        if text:
            items.append(MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=text)))

        media = CDNMedia(
            encrypt_query_param=uploaded.download_encrypted_query_param,
            aes_key=uploaded.aeskey,
            encrypt_type=1,
        )

        if media_type == MessageItemType.IMAGE:
            items.append(
                MessageItem(
                    type=MessageItemType.IMAGE,
                    image_item=ImageItem(media=media, mid_size=uploaded.file_size_ciphertext),
                )
            )
        elif media_type == MessageItemType.VIDEO:
            items.append(
                MessageItem(
                    type=MessageItemType.VIDEO,
                    video_item=VideoItem(media=media, video_size=uploaded.file_size_ciphertext),
                )
            )
        elif media_type == MessageItemType.FILE:
            import os
            file_name = os.path.basename(uploaded.filekey)
            items.append(
                MessageItem(
                    type=MessageItemType.FILE,
                    file_item=FileItem(
                        media=media,
                        file_name=file_name,
                        len=str(uploaded.file_size),
                    ),
                )
            )

        last_client_id = ""
        for item in items:
            last_client_id = self._generate_client_id()
            req = SendMessageReq(
                msg=WeixinMessage(
                    to_user_id=to,
                    client_id=last_client_id,
                    message_type=MessageType.BOT,
                    message_state=MessageState.FINISH,
                    item_list=[item],
                    context_token=ctx_token,
                )
            )
            await self._api.send_message(req)

        return last_client_id

    async def send_typing(self, to: str, typing_ticket: str, status: TypingStatus = TypingStatus.TYPING):
        req = SendTypingReq(
            ilink_user_id=to,
            typing_ticket=typing_ticket,
            status=int(status),
        )
        await self._api.send_typing(req)

    # ------------------------------------------------------------------
    # receive
    # ------------------------------------------------------------------

    async def get_updates(self, get_updates_buf: Optional[str] = None) -> List[WeixinMessage]:
        buf = get_updates_buf if get_updates_buf is not None else self._get_updates_buf
        resp = await self._api.get_updates(buf)

        if resp.ret != 0 and resp.ret is not None:
            if resp.errcode == -14:
                raise WeChatSessionExpired("Session expired (errcode -14)")
            raise WeChatError(f"getUpdates failed: ret={resp.ret} errcode={resp.errcode} errmsg={resp.errmsg}")

        if resp.get_updates_buf:
            self._get_updates_buf = resp.get_updates_buf

        return resp.msgs or []

    async def poll_messages(
        self,
        on_message: Optional[Callable[[MessageContext], None]] = None,
        auto_ack: bool = True,
    ) -> AsyncIterator[MessageContext]:
        self._running = True

        while self._running:
            try:
                msgs = await self.get_updates()
                for msg in msgs:
                    ctx = self._message_to_context(msg)

                    if msg.context_token and msg.from_user_id:
                        self._set_context_token(msg.from_user_id, msg.context_token)

                    if on_message:
                        on_message(ctx)

                    yield ctx

            except WeChatSessionExpired:
                await asyncio.sleep(60 * 60)
            except Exception:
                await asyncio.sleep(2)

    def _message_to_context(self, msg: WeixinMessage) -> MessageContext:
        body = self._extract_body(msg.item_list)

        ctx = MessageContext(
            body=body,
            from_user_id=msg.from_user_id or "",
            to_user_id=msg.to_user_id or msg.from_user_id or "",
            message=msg,
            account_id=self.account_id,
            context_token=msg.context_token,
        )
        return ctx

    def _extract_body(self, item_list: Optional[List[MessageItem]]) -> str:
        if not item_list:
            return ""

        for item in item_list:
            if item.type == MessageItemType.TEXT and item.text_item and item.text_item.text:
                text = item.text_item.text
                ref = item.ref_msg
                if not ref:
                    return text
                if ref.message_item and self._is_media_item(ref.message_item):
                    return text
                parts = []
                if ref.title:
                    parts.append(ref.title)
                if ref.message_item:
                    ref_body = self._extract_body([ref.message_item])
                    if ref_body:
                        parts.append(ref_body)
                if not parts:
                    return text
                return f"[引用: {' | '.join(parts)}]\n{text}"

            if item.type == MessageItemType.VOICE and item.voice_item and item.voice_item.text:
                return item.voice_item.text

        return ""

    def _is_media_item(self, item: MessageItem) -> bool:
        return item.type in (
            MessageItemType.IMAGE,
            MessageItemType.VIDEO,
            MessageItemType.FILE,
            MessageItemType.VOICE,
        )

    # ------------------------------------------------------------------
    # media download
    # ------------------------------------------------------------------

    async def download_media(
        self,
        encrypted_query_param: str,
        aes_key_base64: str,
        full_url: Optional[str] = None,
    ) -> bytes:
        return await self._cdn.download_and_decrypt(
            encrypted_query_param, aes_key_base64, full_url
        )

    async def download_media_plain(
        self,
        encrypted_query_param: str,
        full_url: Optional[str] = None,
    ) -> bytes:
        return await self._cdn.download_plain(encrypted_query_param, full_url)

    # ------------------------------------------------------------------
    # config
    # ------------------------------------------------------------------

    async def get_config(
        self, user_id: str, context_token: Optional[str] = None
    ) -> GetConfigResp:
        return await self._api.get_config(user_id, context_token)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def stop(self):
        self._running = False

    async def close(self):
        self.stop()
        await self._api.close()
        await self._cdn.close()