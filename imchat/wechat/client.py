import asyncio
import uuid
from typing import Optional, List, Callable, AsyncIterator, Dict, Any
from dataclasses import dataclass, field

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
from .exceptions import WeChatError, WeChatSessionExpired


@dataclass
class MessageContext:
    """入站消息上下文"""
    body: str
    from_user_id: str
    to_user_id: str
    message: WeixinMessage
    account_id: str
    media_path: Optional[str] = None
    media_type: Optional[str] = None
    context_token: Optional[str] = None


class WeChatClient:
    """
    微信聊天客户端

    使用示例:
        client = WeChatClient(base_url="https://ilinkai.weixin.qq.com", token="your_token")

        # 发送文本消息
        await client.send_text("user@im.wechat", "Hello!")

        # 接收消息 (长轮询)
        async for msg in client.poll_messages():
            print(msg.body)
    """

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
    # 认证
    # ------------------------------------------------------------------

    async def login_with_qr(
        self,
        timeout_ms: int = 480_000,
        verbose: bool = False,
        on_status_change: Optional[Callable[[str], None]] = None,
    ) -> LoginResult:
        """
        扫码登录流程
        返回包含 bot_token 和 account_id 的 LoginResult
        """
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

        return result

    def set_token(self, token: str):
        """设置已获取的 token"""
        self.token = token
        self._api.token = token

    # ------------------------------------------------------------------
    # 消息发送
    # ------------------------------------------------------------------

    def _generate_client_id(self) -> str:
        return f"pywechat-{uuid.uuid4().hex[:16]}"

    def _get_context_token(self, user_id: str) -> Optional[str]:
        return self._context_tokens.get(user_id)

    def _set_context_token(self, user_id: str, token: str):
        self._context_tokens[user_id] = token

    async def send_text(self, to: str, text: str, context_token: Optional[str] = None) -> str:
        """发送文本消息"""
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
        """发送图片消息"""
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
        """发送视频消息"""
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
        """发送文件消息"""
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
        """发送媒体消息的内部方法"""
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

        # 分别发送每条消息
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
        """发送 typing 指示器"""
        req = SendTypingReq(
            ilink_user_id=to,
            typing_ticket=typing_ticket,
            status=int(status),
        )
        await self._api.send_typing(req)

    # ------------------------------------------------------------------
    # 消息接收
    # ------------------------------------------------------------------

    async def get_updates(self, get_updates_buf: Optional[str] = None) -> List[WeixinMessage]:
        """获取一次消息更新"""
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
        """
        长轮询消息循环
        这是一个异步生成器,持续 yield 收到的消息

        使用示例:
            async for ctx in client.poll_messages():
                print(f"收到消息: {ctx.body}")
                await client.send_text(ctx.from_user_id, "收到!")
        """
        self._running = True

        while self._running:
            try:
                msgs = await self.get_updates()
                for msg in msgs:
                    ctx = self._message_to_context(msg)

                    # 缓存 context_token
                    if msg.context_token and msg.from_user_id:
                        self._set_context_token(msg.from_user_id, msg.context_token)

                    if on_message:
                        on_message(ctx)

                    yield ctx

            except WeChatSessionExpired:
                # 会话过期,暂停一段时间
                await asyncio.sleep(60 * 60)  # 暂停 1 小时
            except Exception:
                # 其他错误,短暂等待后重试
                await asyncio.sleep(2)

    def _message_to_context(self, msg: WeixinMessage) -> MessageContext:
        """将 WeixinMessage 转换为 MessageContext"""
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
        """从 item_list 提取文本内容"""
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
    # 媒体下载
    # ------------------------------------------------------------------

    async def download_media(
        self,
        encrypted_query_param: str,
        aes_key_base64: str,
        full_url: Optional[str] = None,
    ) -> bytes:
        """下载并解密媒体文件"""
        return await self._cdn.download_and_decrypt(
            encrypted_query_param, aes_key_base64, full_url
        )

    async def download_media_plain(
        self,
        encrypted_query_param: str,
        full_url: Optional[str] = None,
    ) -> bytes:
        """下载未加密的媒体文件"""
        return await self._cdn.download_plain(encrypted_query_param, full_url)

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------

    async def get_config(
        self, user_id: str, context_token: Optional[str] = None
    ) -> GetConfigResp:
        """获取用户配置 (包含 typing_ticket)"""
        return await self._api.get_config(user_id, context_token)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def stop(self):
        """停止消息轮询"""
        self._running = False

    async def close(self):
        """关闭客户端,释放资源"""
        self.stop()
        await self._api.close()
        await self._cdn.close()
