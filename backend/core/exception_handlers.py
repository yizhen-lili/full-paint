import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from core.exceptions import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body: dict = {"detail": exc.detail}
    if exc.code is not None:
        body["code"] = exc.code
    # 把 AppError.extra 合進 response body（不存在則略過）。
    # 用例：刪除受阻時把結構化引用清單帶出去給前端展示
    if getattr(exc, "extra", None):
        body.update(exc.extra)
    return JSONResponse(status_code=exc.status_code, content=body)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "伺服器內部錯誤"})
