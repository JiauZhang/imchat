from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import IntEnum


class UploadMediaType(IntEnum):
    IMAGE = 1
    VIDEO = 2
    FILE = 3
    VOICE = 4


class MessageType(IntEnum):
    NONE = 0
    USER = 1
    BOT = 2


class MessageItemType(IntEnum):
    NONE = 0
    TEXT = 1
    IMAGE = 2
    VOICE = 3
    FILE = 4
    VIDEO = 5


class MessageState(IntEnum):
    NEW = 0
    GENERATING = 1
    FINISH = 2


class TypingStatus(IntEnum):
    TYPING = 1
    CANCEL = 2


@dataclass
class BaseInfo:
    channel_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.channel_version is not None:
            d["channel_version"] = self.channel_version
        return d


@dataclass
class CDNMedia:
    encrypt_query_param: Optional[str] = None
    aes_key: Optional[str] = None
    encrypt_type: Optional[int] = None
    full_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.encrypt_query_param is not None:
            d["encrypt_query_param"] = self.encrypt_query_param
        if self.aes_key is not None:
            d["aes_key"] = self.aes_key
        if self.encrypt_type is not None:
            d["encrypt_type"] = self.encrypt_type
        if self.full_url is not None:
            d["full_url"] = self.full_url
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CDNMedia":
        return cls(
            encrypt_query_param=d.get("encrypt_query_param"),
            aes_key=d.get("aes_key"),
            encrypt_type=d.get("encrypt_type"),
            full_url=d.get("full_url"),
        )


@dataclass
class TextItem:
    text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.text is not None:
            d["text"] = self.text
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TextItem":
        return cls(text=d.get("text"))


@dataclass
class ImageItem:
    media: Optional[CDNMedia] = None
    thumb_media: Optional[CDNMedia] = None
    aeskey: Optional[str] = None
    url: Optional[str] = None
    mid_size: Optional[int] = None
    thumb_size: Optional[int] = None
    thumb_height: Optional[int] = None
    thumb_width: Optional[int] = None
    hd_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.media is not None:
            d["media"] = self.media.to_dict()
        if self.thumb_media is not None:
            d["thumb_media"] = self.thumb_media.to_dict()
        if self.aeskey is not None:
            d["aeskey"] = self.aeskey
        if self.url is not None:
            d["url"] = self.url
        if self.mid_size is not None:
            d["mid_size"] = self.mid_size
        if self.thumb_size is not None:
            d["thumb_size"] = self.thumb_size
        if self.thumb_height is not None:
            d["thumb_height"] = self.thumb_height
        if self.thumb_width is not None:
            d["thumb_width"] = self.thumb_width
        if self.hd_size is not None:
            d["hd_size"] = self.hd_size
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ImageItem":
        return cls(
            media=CDNMedia.from_dict(d["media"]) if d.get("media") else None,
            thumb_media=CDNMedia.from_dict(d["thumb_media"]) if d.get("thumb_media") else None,
            aeskey=d.get("aeskey"),
            url=d.get("url"),
            mid_size=d.get("mid_size"),
            thumb_size=d.get("thumb_size"),
            thumb_height=d.get("thumb_height"),
            thumb_width=d.get("thumb_width"),
            hd_size=d.get("hd_size"),
        )


@dataclass
class VoiceItem:
    media: Optional[CDNMedia] = None
    encode_type: Optional[int] = None
    bits_per_sample: Optional[int] = None
    sample_rate: Optional[int] = None
    playtime: Optional[int] = None
    text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.media is not None:
            d["media"] = self.media.to_dict()
        if self.encode_type is not None:
            d["encode_type"] = self.encode_type
        if self.bits_per_sample is not None:
            d["bits_per_sample"] = self.bits_per_sample
        if self.sample_rate is not None:
            d["sample_rate"] = self.sample_rate
        if self.playtime is not None:
            d["playtime"] = self.playtime
        if self.text is not None:
            d["text"] = self.text
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VoiceItem":
        return cls(
            media=CDNMedia.from_dict(d["media"]) if d.get("media") else None,
            encode_type=d.get("encode_type"),
            bits_per_sample=d.get("bits_per_sample"),
            sample_rate=d.get("sample_rate"),
            playtime=d.get("playtime"),
            text=d.get("text"),
        )


@dataclass
class FileItem:
    media: Optional[CDNMedia] = None
    file_name: Optional[str] = None
    md5: Optional[str] = None
    len: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.media is not None:
            d["media"] = self.media.to_dict()
        if self.file_name is not None:
            d["file_name"] = self.file_name
        if self.md5 is not None:
            d["md5"] = self.md5
        if self.len is not None:
            d["len"] = self.len
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FileItem":
        return cls(
            media=CDNMedia.from_dict(d["media"]) if d.get("media") else None,
            file_name=d.get("file_name"),
            md5=d.get("md5"),
            len=d.get("len"),
        )


@dataclass
class VideoItem:
    media: Optional[CDNMedia] = None
    video_size: Optional[int] = None
    play_length: Optional[int] = None
    video_md5: Optional[str] = None
    thumb_media: Optional[CDNMedia] = None
    thumb_size: Optional[int] = None
    thumb_height: Optional[int] = None
    thumb_width: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.media is not None:
            d["media"] = self.media.to_dict()
        if self.video_size is not None:
            d["video_size"] = self.video_size
        if self.play_length is not None:
            d["play_length"] = self.play_length
        if self.video_md5 is not None:
            d["video_md5"] = self.video_md5
        if self.thumb_media is not None:
            d["thumb_media"] = self.thumb_media.to_dict()
        if self.thumb_size is not None:
            d["thumb_size"] = self.thumb_size
        if self.thumb_height is not None:
            d["thumb_height"] = self.thumb_height
        if self.thumb_width is not None:
            d["thumb_width"] = self.thumb_width
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VideoItem":
        return cls(
            media=CDNMedia.from_dict(d["media"]) if d.get("media") else None,
            video_size=d.get("video_size"),
            play_length=d.get("play_length"),
            video_md5=d.get("video_md5"),
            thumb_media=CDNMedia.from_dict(d["thumb_media"]) if d.get("thumb_media") else None,
            thumb_size=d.get("thumb_size"),
            thumb_height=d.get("thumb_height"),
            thumb_width=d.get("thumb_width"),
        )


@dataclass
class RefMessage:
    message_item: Optional["MessageItem"] = None
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.message_item is not None:
            d["message_item"] = self.message_item.to_dict()
        if self.title is not None:
            d["title"] = self.title
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RefMessage":
        return cls(
            message_item=MessageItem.from_dict(d["message_item"]) if d.get("message_item") else None,
            title=d.get("title"),
        )


@dataclass
class MessageItem:
    type: Optional[int] = None
    create_time_ms: Optional[int] = None
    update_time_ms: Optional[int] = None
    is_completed: Optional[bool] = None
    msg_id: Optional[str] = None
    ref_msg: Optional[RefMessage] = None
    text_item: Optional[TextItem] = None
    image_item: Optional[ImageItem] = None
    voice_item: Optional[VoiceItem] = None
    file_item: Optional[FileItem] = None
    video_item: Optional[VideoItem] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.type is not None:
            d["type"] = self.type
        if self.create_time_ms is not None:
            d["create_time_ms"] = self.create_time_ms
        if self.update_time_ms is not None:
            d["update_time_ms"] = self.update_time_ms
        if self.is_completed is not None:
            d["is_completed"] = self.is_completed
        if self.msg_id is not None:
            d["msg_id"] = self.msg_id
        if self.ref_msg is not None:
            d["ref_msg"] = self.ref_msg.to_dict()
        if self.text_item is not None:
            d["text_item"] = self.text_item.to_dict()
        if self.image_item is not None:
            d["image_item"] = self.image_item.to_dict()
        if self.voice_item is not None:
            d["voice_item"] = self.voice_item.to_dict()
        if self.file_item is not None:
            d["file_item"] = self.file_item.to_dict()
        if self.video_item is not None:
            d["video_item"] = self.video_item.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MessageItem":
        return cls(
            type=d.get("type"),
            create_time_ms=d.get("create_time_ms"),
            update_time_ms=d.get("update_time_ms"),
            is_completed=d.get("is_completed"),
            msg_id=d.get("msg_id"),
            ref_msg=RefMessage.from_dict(d["ref_msg"]) if d.get("ref_msg") else None,
            text_item=TextItem.from_dict(d["text_item"]) if d.get("text_item") else None,
            image_item=ImageItem.from_dict(d["image_item"]) if d.get("image_item") else None,
            voice_item=VoiceItem.from_dict(d["voice_item"]) if d.get("voice_item") else None,
            file_item=FileItem.from_dict(d["file_item"]) if d.get("file_item") else None,
            video_item=VideoItem.from_dict(d["video_item"]) if d.get("video_item") else None,
        )


@dataclass
class WeixinMessage:
    seq: Optional[int] = None
    message_id: Optional[int] = None
    from_user_id: Optional[str] = None
    to_user_id: Optional[str] = None
    client_id: Optional[str] = None
    create_time_ms: Optional[int] = None
    update_time_ms: Optional[int] = None
    delete_time_ms: Optional[int] = None
    session_id: Optional[str] = None
    group_id: Optional[str] = None
    message_type: Optional[int] = None
    message_state: Optional[int] = None
    item_list: Optional[List[MessageItem]] = None
    context_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.seq is not None:
            d["seq"] = self.seq
        if self.message_id is not None:
            d["message_id"] = self.message_id
        if self.from_user_id is not None:
            d["from_user_id"] = self.from_user_id
        if self.to_user_id is not None:
            d["to_user_id"] = self.to_user_id
        if self.client_id is not None:
            d["client_id"] = self.client_id
        if self.create_time_ms is not None:
            d["create_time_ms"] = self.create_time_ms
        if self.update_time_ms is not None:
            d["update_time_ms"] = self.update_time_ms
        if self.delete_time_ms is not None:
            d["delete_time_ms"] = self.delete_time_ms
        if self.session_id is not None:
            d["session_id"] = self.session_id
        if self.group_id is not None:
            d["group_id"] = self.group_id
        if self.message_type is not None:
            d["message_type"] = self.message_type
        if self.message_state is not None:
            d["message_state"] = self.message_state
        if self.item_list is not None:
            d["item_list"] = [item.to_dict() for item in self.item_list]
        if self.context_token is not None:
            d["context_token"] = self.context_token
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WeixinMessage":
        return cls(
            seq=d.get("seq"),
            message_id=d.get("message_id"),
            from_user_id=d.get("from_user_id"),
            to_user_id=d.get("to_user_id"),
            client_id=d.get("client_id"),
            create_time_ms=d.get("create_time_ms"),
            update_time_ms=d.get("update_time_ms"),
            delete_time_ms=d.get("delete_time_ms"),
            session_id=d.get("session_id"),
            group_id=d.get("group_id"),
            message_type=d.get("message_type"),
            message_state=d.get("message_state"),
            item_list=[MessageItem.from_dict(item) for item in d["item_list"]] if d.get("item_list") else None,
            context_token=d.get("context_token"),
        )


@dataclass
class GetUpdatesReq:
    sync_buf: Optional[str] = None
    get_updates_buf: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.sync_buf is not None:
            d["sync_buf"] = self.sync_buf
        if self.get_updates_buf is not None:
            d["get_updates_buf"] = self.get_updates_buf
        return d


@dataclass
class GetUpdatesResp:
    ret: Optional[int] = None
    errcode: Optional[int] = None
    errmsg: Optional[str] = None
    msgs: Optional[List[WeixinMessage]] = None
    sync_buf: Optional[str] = None
    get_updates_buf: Optional[str] = None
    longpolling_timeout_ms: Optional[int] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GetUpdatesResp":
        return cls(
            ret=d.get("ret"),
            errcode=d.get("errcode"),
            errmsg=d.get("errmsg"),
            msgs=[WeixinMessage.from_dict(m) for m in d["msgs"]] if d.get("msgs") else None,
            sync_buf=d.get("sync_buf"),
            get_updates_buf=d.get("get_updates_buf"),
            longpolling_timeout_ms=d.get("longpolling_timeout_ms"),
        )


@dataclass
class SendMessageReq:
    msg: Optional[WeixinMessage] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.msg is not None:
            d["msg"] = self.msg.to_dict()
        return d


@dataclass
class SendTypingReq:
    ilink_user_id: Optional[str] = None
    typing_ticket: Optional[str] = None
    status: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.ilink_user_id is not None:
            d["ilink_user_id"] = self.ilink_user_id
        if self.typing_ticket is not None:
            d["typing_ticket"] = self.typing_ticket
        if self.status is not None:
            d["status"] = self.status
        return d


@dataclass
class GetUploadUrlReq:
    filekey: Optional[str] = None
    media_type: Optional[int] = None
    to_user_id: Optional[str] = None
    rawsize: Optional[int] = None
    rawfilemd5: Optional[str] = None
    filesize: Optional[int] = None
    thumb_rawsize: Optional[int] = None
    thumb_rawfilemd5: Optional[str] = None
    thumb_filesize: Optional[int] = None
    no_need_thumb: Optional[bool] = None
    aeskey: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.filekey is not None:
            d["filekey"] = self.filekey
        if self.media_type is not None:
            d["media_type"] = self.media_type
        if self.to_user_id is not None:
            d["to_user_id"] = self.to_user_id
        if self.rawsize is not None:
            d["rawsize"] = self.rawsize
        if self.rawfilemd5 is not None:
            d["rawfilemd5"] = self.rawfilemd5
        if self.filesize is not None:
            d["filesize"] = self.filesize
        if self.thumb_rawsize is not None:
            d["thumb_rawsize"] = self.thumb_rawsize
        if self.thumb_rawfilemd5 is not None:
            d["thumb_rawfilemd5"] = self.thumb_rawfilemd5
        if self.thumb_filesize is not None:
            d["thumb_filesize"] = self.thumb_filesize
        if self.no_need_thumb is not None:
            d["no_need_thumb"] = self.no_need_thumb
        if self.aeskey is not None:
            d["aeskey"] = self.aeskey
        return d


@dataclass
class GetUploadUrlResp:
    upload_param: Optional[str] = None
    thumb_upload_param: Optional[str] = None
    upload_full_url: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GetUploadUrlResp":
        return cls(
            upload_param=d.get("upload_param"),
            thumb_upload_param=d.get("thumb_upload_param"),
            upload_full_url=d.get("upload_full_url"),
        )


@dataclass
class GetConfigResp:
    ret: Optional[int] = None
    errmsg: Optional[str] = None
    typing_ticket: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GetConfigResp":
        return cls(
            ret=d.get("ret"),
            errmsg=d.get("errmsg"),
            typing_ticket=d.get("typing_ticket"),
        )


WeChatMessage = WeixinMessage
WeChatMessageItem = MessageItem
WeChatTextItem = TextItem
WeChatImageItem = ImageItem
WeChatVoiceItem = VoiceItem
WeChatFileItem = FileItem
WeChatVideoItem = VideoItem
WeChatCDNMedia = CDNMedia
WeChatSendMessageReq = SendMessageReq
WeChatSendTypingReq = SendTypingReq
WeChatGetUpdatesReq = GetUpdatesReq
WeChatGetUpdatesResp = GetUpdatesResp
WeChatGetUploadUrlReq = GetUploadUrlReq
WeChatGetUploadUrlResp = GetUploadUrlResp
WeChatGetConfigResp = GetConfigResp
WeChatBaseInfo = BaseInfo
WeChatUploadMediaType = UploadMediaType
WeChatMessageType = MessageType
WeChatMessageItemType = MessageItemType
WeChatMessageState = MessageState
WeChatTypingStatus = TypingStatus
