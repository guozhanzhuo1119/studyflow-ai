"""带错误码的业务异常，由 API 层统一转成 {"ok": false, "error": ...}。"""


class ServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
