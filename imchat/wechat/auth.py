import asyncio
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from .api import WeChatAPIClient
from .exceptions import WeChatAuthError


DEFAULT_ILINK_BOT_TYPE = "3"
FIXED_BASE_URL = "https://ilinkai.weixin.qq.com"
ACTIVE_LOGIN_TTL_MS = 5 * 60_000
QR_LONG_POLL_TIMEOUT_MS = 35_000
MAX_QR_REFRESH_COUNT = 3


@dataclass
class QRCodeResponse:
    qrcode: str
    qrcode_img_content: str


@dataclass
class QRStatusResponse:
    status: str
    bot_token: Optional[str] = None
    ilink_bot_id: Optional[str] = None
    baseurl: Optional[str] = None
    ilink_user_id: Optional[str] = None
    redirect_host: Optional[str] = None


@dataclass
class LoginResult:
    connected: bool
    bot_token: Optional[str] = None
    account_id: Optional[str] = None
    base_url: Optional[str] = None
    user_id: Optional[str] = None
    message: str = ""


class WeChatAuth:

    def __init__(self, bot_type: str = DEFAULT_ILINK_BOT_TYPE):
        self.bot_type = bot_type
        self._active_logins: Dict[str, Dict[str, Any]] = {}

    async def start_login(self, account_id: Optional[str] = None) -> Dict[str, str]:
        session_key = account_id or str(uuid.uuid4())

        now = asyncio.get_event_loop().time() * 1000
        expired = [
            k for k, v in self._active_logins.items()
            if now - v.get("started_at", 0) > ACTIVE_LOGIN_TTL_MS
        ]
        for k in expired:
            del self._active_logins[k]

        existing = self._active_logins.get(session_key)
        if existing and (now - existing["started_at"] < ACTIVE_LOGIN_TTL_MS):
            return {
                "qrcode_url": existing["qrcode_url"],
                "session_key": session_key,
                "message": "二维码已就绪，请使用微信扫描。",
            }

        client = WeChatAPIClient(FIXED_BASE_URL)
        try:
            resp = await client.get_bot_qrcode(self.bot_type)
            qr = QRCodeResponse(
                qrcode=resp["qrcode"],
                qrcode_img_content=resp["qrcode_img_content"],
            )
        except Exception as e:
            raise WeChatAuthError(f"Failed to fetch QR code: {e}")
        finally:
            await client.close()

        self._active_logins[session_key] = {
            "session_key": session_key,
            "id": str(uuid.uuid4()),
            "qrcode": qr.qrcode,
            "qrcode_url": qr.qrcode_img_content,
            "started_at": now,
            "current_api_base_url": FIXED_BASE_URL,
        }

        return {
            "qrcode_url": qr.qrcode_img_content,
            "session_key": session_key,
            "message": "使用微信扫描以下二维码，以完成连接。",
        }

    async def wait_for_login(
        self,
        session_key: str,
        timeout_ms: int = 480_000,
        verbose: bool = False,
        on_status_change: Optional[Callable[[str], None]] = None,
    ) -> LoginResult:
        active_login = self._active_logins.get(session_key)
        if not active_login:
            return LoginResult(
                connected=False,
                message="当前没有进行中的登录，请先发起登录。",
            )

        now = asyncio.get_event_loop().time() * 1000
        if now - active_login["started_at"] > ACTIVE_LOGIN_TTL_MS:
            del self._active_logins[session_key]
            return LoginResult(
                connected=False,
                message="二维码已过期，请重新生成。",
            )

        timeout = max(timeout_ms, 1000)
        deadline = asyncio.get_event_loop().time() * 1000 + timeout
        scanned_printed = False
        qr_refresh_count = 1

        active_login["current_api_base_url"] = FIXED_BASE_URL

        while asyncio.get_event_loop().time() * 1000 < deadline:
            current_base_url = active_login.get("current_api_base_url", FIXED_BASE_URL)
            client = WeChatAPIClient(current_base_url)

            try:
                status_resp = await client.get_qrcode_status(
                    active_login["qrcode"], timeout_ms=QR_LONG_POLL_TIMEOUT_MS
                )
            except Exception as e:
                if verbose:
                    print(f".", end="", flush=True)
                await asyncio.sleep(1)
                continue
            finally:
                await client.close()

            status = status_resp.get("status", "wait")

            if on_status_change:
                on_status_change(status)

            if status == "wait":
                if verbose:
                    print(".", end="", flush=True)

            elif status == "scaned":
                if not scanned_printed:
                    if verbose:
                        print("\n已扫码，在微信继续操作...")
                    scanned_printed = True

            elif status == "expired":
                qr_refresh_count += 1
                if qr_refresh_count > MAX_QR_REFRESH_COUNT:
                    del self._active_logins[session_key]
                    return LoginResult(
                        connected=False,
                        message="登录超时：二维码多次过期，请重新开始登录流程。",
                    )

                if verbose:
                    print(f"\n二维码已过期，正在刷新...({qr_refresh_count}/{MAX_QR_REFRESH_COUNT})")

                try:
                    client = WeChatAPIClient(FIXED_BASE_URL)
                    resp = await client.get_bot_qrcode(self.bot_type)
                    await client.close()

                    active_login["qrcode"] = resp["qrcode"]
                    active_login["qrcode_url"] = resp["qrcode_img_content"]
                    active_login["started_at"] = asyncio.get_event_loop().time() * 1000
                    scanned_printed = False

                    if verbose:
                        print(f"新二维码已生成，请重新扫描")
                        print(f"URL: {resp['qrcode_img_content']}")
                except Exception as e:
                    del self._active_logins[session_key]
                    return LoginResult(
                        connected=False,
                        message=f"刷新二维码失败: {e}",
                    )

            elif status == "scaned_but_redirect":
                redirect_host = status_resp.get("redirect_host")
                if redirect_host:
                    active_login["current_api_base_url"] = f"https://{redirect_host}"

            elif status == "confirmed":
                bot_token = status_resp.get("bot_token")
                ilink_bot_id = status_resp.get("ilink_bot_id")
                baseurl = status_resp.get("baseurl")
                ilink_user_id = status_resp.get("ilink_user_id")

                if not ilink_bot_id:
                    del self._active_logins[session_key]
                    return LoginResult(
                        connected=False,
                        message="登录失败：服务器未返回 ilink_bot_id。",
                    )

                del self._active_logins[session_key]
                return LoginResult(
                    connected=True,
                    bot_token=bot_token,
                    account_id=ilink_bot_id,
                    base_url=baseurl or FIXED_BASE_URL,
                    user_id=ilink_user_id,
                    message="与微信连接成功！",
                )

            await asyncio.sleep(1)

        del self._active_logins[session_key]
        return LoginResult(
            connected=False,
            message="登录超时，请重试。",
        )