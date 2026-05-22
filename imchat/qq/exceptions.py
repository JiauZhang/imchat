class QQError(Exception):
    pass


class AuthError(QQError):
    pass


class APIError(QQError):
    def __init__(
        self,
        message: str,
        status: int = 0,
        path: str = "",
        biz_code: int | None = None,
        biz_message: str | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.path = path
        self.biz_code = biz_code
        self.biz_message = biz_message


class GatewayError(QQError):
    pass


class TokenExpiredError(AuthError):
    pass


QQAuthError = AuthError
QQAPIError = APIError
QQGatewayError = GatewayError