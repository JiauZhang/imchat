from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Coroutine, Literal


class MediaFileType(IntEnum):
    IMAGE = 1
    VIDEO = 2
    VOICE = 3
    FILE = 4


class StreamInputMode(str, Enum):
    REPLACE = "replace"


class StreamInputState(IntEnum):
    GENERATING = 1
    DONE = 10


class StreamContentType(str, Enum):
    MARKDOWN = "markdown"


@dataclass
class MessageAttachment:
    content_type: str
    url: str
    filename: str | None = None
    height: int | None = None
    width: int | None = None
    size: int | None = None
    voice_wav_url: str | None = None
    asr_refer_text: str | None = None


@dataclass
class Mention:
    scope: Literal["all", "single"] | None = None
    id: str | None = None
    user_openid: str | None = None
    member_openid: str | None = None
    nickname: str | None = None
    bot: bool = False
    is_you: bool = False


@dataclass
class MessageScene:
    source: str
    ext: list[str] = field(default_factory=list)


@dataclass
class MsgElement:
    msg_idx: str | None = None
    message_type: int | None = None
    content: str | None = None
    attachments: list[MessageAttachment] = field(default_factory=list)
    msg_elements: list[MsgElement] = field(default_factory=list)


@dataclass
class MessageResponse:
    id: str
    timestamp: int | str
    ref_idx: str | None = None


@dataclass
class BaseMessage:
    id: str
    content: str
    timestamp: str
    author_id: str
    author_name: str | None = None
    author_bot: bool = False
    attachments: list[MessageAttachment] = field(default_factory=list)
    message_scene: MessageScene | None = None
    message_type: int = 0
    msg_elements: list[MsgElement] = field(default_factory=list)
    msg_idx: str | None = None
    ref_msg_idx: str | None = None

    _api: Any = field(default=None, repr=False)
    _token: str = field(default="", repr=False)

    async def reply(self, content: str, **kwargs: Any) -> MessageResponse:
        raise NotImplementedError

    async def reply_with_image(
        self, image_url: str | None = None, image_data: bytes | None = None, content: str = ""
    ) -> MessageResponse:
        raise NotImplementedError


@dataclass
class C2CMessage(BaseMessage):
    user_openid: str = ""

    async def reply(self, content: str, **kwargs: Any) -> MessageResponse:
        if self._api is None:
            raise RuntimeError("API not available")
        return await self._api.send_c2c_message(
            self.user_openid, content, msg_id=self.id, **kwargs
        )

    async def reply_with_image(
        self, image_url: str | None = None, image_data: bytes | None = None, content: str = ""
    ) -> MessageResponse:
        if self._api is None:
            raise RuntimeError("API not available")
        return await self._api.send_c2c_image(
            self.user_openid, image_url=image_url, image_data=image_data, msg_id=self.id, content=content
        )


@dataclass
class GroupMessage(BaseMessage):
    group_openid: str = ""
    group_id: str = ""
    member_openid: str = ""
    mentions: list[Mention] = field(default_factory=list)

    async def reply(self, content: str, **kwargs: Any) -> MessageResponse:
        if self._api is None:
            raise RuntimeError("API not available")
        return await self._api.send_group_message(
            self.group_openid, content, msg_id=self.id, **kwargs
        )

    async def reply_with_image(
        self, image_url: str | None = None, image_data: bytes | None = None, content: str = ""
    ) -> MessageResponse:
        if self._api is None:
            raise RuntimeError("API not available")
        return await self._api.send_group_image(
            self.group_openid, image_url=image_url, image_data=image_data, msg_id=self.id, content=content
        )


@dataclass
class GuildMessage(BaseMessage):
    channel_id: str = ""
    guild_id: str = ""

    async def reply(self, content: str, **kwargs: Any) -> MessageResponse:
        if self._api is None:
            raise RuntimeError("API not available")
        return await self._api.send_channel_message(
            self.channel_id, content, msg_id=self.id
        )

    async def reply_with_image(
        self, image_url: str | None = None, image_data: bytes | None = None, content: str = ""
    ) -> MessageResponse:
        raise NotImplementedError("use api.send_channel_image for guild image messages")


@dataclass
class DirectMessage(BaseMessage):
    guild_id: str = ""

    async def reply(self, content: str, **kwargs: Any) -> MessageResponse:
        if self._api is None:
            raise RuntimeError("API not available")
        return await self._api.send_dm_message(
            self.guild_id, content, msg_id=self.id
        )

    async def reply_with_image(
        self, image_url: str | None = None, image_data: bytes | None = None, content: str = ""
    ) -> MessageResponse:
        raise NotImplementedError("use api.send_dm_image for dm image messages")


@dataclass
class Interaction:
    id: str
    type: int
    scene: str | None = None
    chat_type: int | None = None
    timestamp: str | None = None
    guild_id: str | None = None
    channel_id: str | None = None
    user_openid: str | None = None
    group_openid: str | None = None
    group_member_openid: str | None = None
    version: int = 0
    data_type: int = 0
    button_data: str | None = None
    button_id: str | None = None
    user_id: str | None = None
    feature_id: str | None = None
    message_id: str | None = None

    _api: Any = field(default=None, repr=False)
    _token: str = field(default="", repr=False)

    async def acknowledge(self, code: int = 0, data: dict[str, Any] | None = None) -> None:
        if self._api is None:
            raise RuntimeError("API not available")
        await self._api.acknowledge_interaction(self.id, code=code, data=data)


MessageHandler = Callable[[BaseMessage], Coroutine[Any, Any, None]]
C2CMessageHandler = Callable[[C2CMessage], Coroutine[Any, Any, None]]
GroupMessageHandler = Callable[[GroupMessage], Coroutine[Any, Any, None]]
GuildMessageHandler = Callable[[GuildMessage], Coroutine[Any, Any, None]]
DirectMessageHandler = Callable[[DirectMessage], Coroutine[Any, Any, None]]
InteractionHandler = Callable[[Interaction], Coroutine[Any, Any, None]]
ReadyHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
ErrorHandler = Callable[[Exception], Coroutine[Any, Any, None]]


@dataclass
class StreamMessageRequest:
    input_mode: StreamInputMode = StreamInputMode.REPLACE
    input_state: StreamInputState = StreamInputState.GENERATING
    content_type: StreamContentType = StreamContentType.MARKDOWN
    content_raw: str = ""
    event_id: str = ""
    msg_id: str = ""
    msg_seq: int = 0
    index: int = 0
    stream_msg_id: str | None = None


@dataclass
class KeyboardButton:
    id: str
    label: str
    style: int = 0
    action_type: int = 1
    data: str = ""
    enter: bool = False
    reply: bool = False
    permission_type: int = 0
    specify_role_ids: list[str] = field(default_factory=list)
    specify_user_ids: list[str] = field(default_factory=list)
    click_limit: int = 0
    unsupport_tips: str = ""
    modal_content: str = ""
    modal_confirm_text: str = ""
    modal_cancel_text: str = ""
    group_id: str = ""


@dataclass
class KeyboardRow:
    buttons: list[KeyboardButton] = field(default_factory=list)


@dataclass
class InlineKeyboard:
    template_id: str | None = None
    rows: list[KeyboardRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if self.template_id:
            return {"id": self.template_id}
        return {
            "content": {
                "rows": [
                    {
                        "buttons": [
                            {
                                "id": b.id,
                                "render_data": {
                                    "label": b.label,
                                    "style": b.style,
                                },
                                "action": {
                                    "type": b.action_type,
                                    "data": b.data,
                                    "enter": b.enter,
                                    "reply": b.reply,
                                    "permission": {
                                        "type": b.permission_type,
                                        "specify_role_ids": b.specify_role_ids,
                                        "specify_user_ids": b.specify_user_ids,
                                    },
                                    "click_limit": b.click_limit,
                                    "unsupport_tips": b.unsupport_tips,
                                    **({"modal": {"content": b.modal_content, "confirm_text": b.modal_confirm_text, "cancel_text": b.modal_cancel_text}} if b.modal_content else {}),
                                },
                                **({"group_id": b.group_id} if b.group_id else {}),
                            }
                            for b in row.buttons
                        ]
                    }
                    for row in self.rows
                ]
            }
        }


QQErrorHandler = ErrorHandler