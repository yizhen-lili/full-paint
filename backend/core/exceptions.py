class AppError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class BadRequestError(AppError):
    def __init__(self, detail: str = "請求無法處理"):
        super().__init__(400, detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "請先登入"):
        super().__init__(401, detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "權限不足"):
        super().__init__(403, detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "資源不存在"):
        super().__init__(404, detail)


class ConflictError(AppError):
    def __init__(self, detail: str = "資料衝突"):
        super().__init__(409, detail)


class ExternalServiceError(AppError):
    def __init__(self, detail: str = "外部服務異常，請稍後再試"):
        super().__init__(503, detail)
