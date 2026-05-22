class WeChatError(Exception):
    pass


class WeChatAPIError(WeChatError):
    def __init__(self, message: str, status_code: int = 0, response_text: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class WeChatAuthError(WeChatError):
    pass


class WeChatSessionExpired(WeChatError):
    pass


class WeChatCDNError(WeChatError):
    pass