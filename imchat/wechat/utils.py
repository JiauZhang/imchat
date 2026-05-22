import mimetypes
from typing import Optional


def get_mime_from_filename(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def get_extension_from_content_type(content_type: Optional[str], url: str = "") -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext

    if url:
        from urllib.parse import urlparse
        path = urlparse(url).path
        if "." in path:
            return path[path.rfind("."):]

    return ".bin"
