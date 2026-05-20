class WeChatError(Exception):
    """基础异常"""
    pass


class WeChatAPIError(WeChatError):
    """API 调用错误"""
    def __init__(self, message: str, status_code: int = 0, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class WeChatAuthError(WeChatError):
    """认证错误"""
    pass


class WeChatSessionExpired(WeChatError):
    """会话过期 (errcode -14)"""
    pass


class WeChatCDNError(WeChatError):
    """CDN 上传/下载错误"""
    pass
