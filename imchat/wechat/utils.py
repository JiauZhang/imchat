import mimetypes
from typing import Optional


def get_mime_from_filename(filename: str) -> str:
    """根据文件名猜测 MIME 类型"""
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def get_extension_from_content_type(content_type: Optional[str], url: str = "") -> str:
    """从 Content-Type 或 URL 获取文件扩展名"""
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext

    # 从 URL 提取扩展名
    if url:
        from urllib.parse import urlparse
        path = urlparse(url).path
        if "." in path:
            return path[path.rfind("."):]

    return ".bin"
