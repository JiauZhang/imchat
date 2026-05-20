import os
import hashlib
import secrets
from typing import Optional, Tuple
import httpx

from .api import WeChatAPIClient
from .crypto import encrypt_aes_ecb, aes_ecb_padded_size, decrypt_aes_ecb, parse_aes_key
from .types import UploadMediaType, GetUploadUrlReq
from .exceptions import WeChatCDNError


ENABLE_CDN_URL_FALLBACK = True
UPLOAD_MAX_RETRIES = 3


class WeChatCDNClient:
    """微信 CDN 客户端"""

    def __init__(
        self,
        api_client: WeChatAPIClient,
        cdn_base_url: str = "https://novac2c.cdn.weixin.qq.com/c2c",
    ):
        self.api = api_client
        self.cdn_base_url = cdn_base_url.rstrip("/")
        self._http = httpx.AsyncClient()

    def _build_download_url(self, encrypted_query_param: str) -> str:
        return f"{self.cdn_base_url}/download?encrypted_query_param={encrypted_query_param}"

    def _build_upload_url(self, upload_param: str, filekey: str) -> str:
        return (
            f"{self.cdn_base_url}/upload?"
            f"encrypted_query_param={upload_param}&filekey={filekey}"
        )

    async def upload_file(
        self,
        file_path: str,
        to_user_id: str,
        media_type: UploadMediaType = UploadMediaType.FILE,
    ) -> "UploadedFileInfo":
        """
        上传本地文件到微信 CDN
        流程: 读取文件 → 计算 MD5 → 生成 AES key → 获取上传 URL → 加密上传
        """
        with open(file_path, "rb") as f:
            plaintext = f.read()

        rawsize = len(plaintext)
        rawfilemd5 = hashlib.md5(plaintext).hexdigest()
        filesize = aes_ecb_padded_size(rawsize)
        filekey = secrets.token_hex(16)
        aeskey = secrets.token_bytes(16)

        req = GetUploadUrlReq(
            filekey=filekey,
            media_type=int(media_type),
            to_user_id=to_user_id,
            rawsize=rawsize,
            rawfilemd5=rawfilemd5,
            filesize=filesize,
            no_need_thumb=True,
            aeskey=aeskey.hex(),
        )

        upload_url_resp = await self.api.get_upload_url(req)

        upload_full_url = upload_url_resp.upload_full_url
        upload_param = upload_url_resp.upload_param

        if not upload_full_url and not upload_param:
            raise WeChatCDNError("getUploadUrl returned no upload URL")

        ciphertext = encrypt_aes_ecb(plaintext, aeskey)

        # 确定 CDN 上传 URL
        if upload_full_url and upload_full_url.strip():
            cdn_url = upload_full_url.strip()
        elif upload_param:
            cdn_url = self._build_upload_url(upload_param, filekey)
        else:
            raise WeChatCDNError("CDN upload URL missing")

        download_param = await self._upload_to_cdn(cdn_url, ciphertext, filekey)

        return UploadedFileInfo(
            filekey=filekey,
            download_encrypted_query_param=download_param,
            aeskey=aeskey.hex(),
            file_size=rawsize,
            file_size_ciphertext=filesize,
        )

    async def _upload_to_cdn(
        self, cdn_url: str, ciphertext: bytes, filekey: str
    ) -> str:
        """上传加密后的数据到 CDN,带重试"""
        last_error = None

        for attempt in range(1, UPLOAD_MAX_RETRIES + 1):
            try:
                resp = await self._http.post(
                    cdn_url,
                    headers={"Content-Type": "application/octet-stream"},
                    content=ciphertext,
                )

                if 400 <= resp.status_code < 500:
                    err_msg = resp.headers.get("x-error-message") or resp.text
                    raise WeChatCDNError(f"CDN upload client error {resp.status_code}: {err_msg}")

                if resp.status_code != 200:
                    err_msg = resp.headers.get("x-error-message") or f"status {resp.status_code}"
                    raise WeChatCDNError(f"CDN upload server error: {err_msg}")

                download_param = resp.headers.get("x-encrypted-param")
                if not download_param:
                    raise WeChatCDNError("CDN upload response missing x-encrypted-param header")

                return download_param

            except WeChatCDNError as e:
                last_error = e
                if "client error" in str(e):
                    raise
                if attempt < UPLOAD_MAX_RETRIES:
                    continue
                else:
                    raise WeChatCDNError(
                        f"CDN upload failed after {UPLOAD_MAX_RETRIES} attempts: {e}"
                    )

        raise last_error or WeChatCDNError("CDN upload failed")

    async def download_and_decrypt(
        self,
        encrypted_query_param: str,
        aes_key_base64: str,
        full_url: Optional[str] = None,
    ) -> bytes:
        """下载并解密 CDN 文件"""
        key = parse_aes_key(aes_key_base64)

        if full_url:
            url = full_url
        elif ENABLE_CDN_URL_FALLBACK:
            url = self._build_download_url(encrypted_query_param)
        else:
            raise WeChatCDNError("full_url is required (CDN URL fallback is disabled)")

        resp = await self._http.get(url)
        if not resp.is_success:
            body = resp.text or "(unreadable)"
            raise WeChatCDNError(f"CDN download {resp.status_code} {resp.reason_phrase}: {body}")

        encrypted = resp.content
        return decrypt_aes_ecb(encrypted, key)

    async def download_plain(
        self,
        encrypted_query_param: str,
        full_url: Optional[str] = None,
    ) -> bytes:
        """下载未加密的 CDN 文件"""
        if full_url:
            url = full_url
        elif ENABLE_CDN_URL_FALLBACK:
            url = self._build_download_url(encrypted_query_param)
        else:
            raise WeChatCDNError("full_url is required (CDN URL fallback is disabled)")

        resp = await self._http.get(url)
        if not resp.is_success:
            body = resp.text or "(unreadable)"
            raise WeChatCDNError(f"CDN download {resp.status_code} {resp.reason_phrase}: {body}")

        return resp.content

    async def close(self):
        await self._http.aclose()


class UploadedFileInfo:
    """上传后的文件信息"""

    def __init__(
        self,
        filekey: str,
        download_encrypted_query_param: str,
        aeskey: str,
        file_size: int,
        file_size_ciphertext: int,
    ):
        self.filekey = filekey
        self.download_encrypted_query_param = download_encrypted_query_param
        self.aeskey = aeskey
        self.file_size = file_size
        self.file_size_ciphertext = file_size_ciphertext
