"""ECpay 金流 router：AioCheckOut（線上付款）。

Endpoints：
  - GET  /payment/ecpay/checkout/{order_id}
      → 回 HTML（auto-submit form，瀏覽器一打開就 POST 到 ECpay 付款頁）。
        亦作「重新付款」入口（僅 pending_payment 且未逾期的 ecpay 訂單）。
  - POST /payment/ecpay/return        ← ECpay server-to-server 付款結果（權威，可標 paid）
  - POST /payment/ecpay/result        ← ECpay 瀏覽器 POST 導回（僅 redirect，不標 paid）

⚠️ 金流簽章用 SHA256（物流用 MD5）。webhook 必回 "1|OK" / "0|reason"（純字串）。
"""
import logging
from datetime import UTC, datetime
from urllib.parse import parse_qsl
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.exceptions import ConflictError, NotFoundError
from dependencies.auth import require_auth
from orders.models import Order, OrderItem, OrderStatusEnum, PaymentMethodEnum
from payment import service

router = APIRouter(prefix="/payment/ecpay", tags=["payment"])

log = logging.getLogger(__name__)


def _html_escape(s: str) -> str:
    """auto-submit form 的 hidden input value 防 XSS。"""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _base_url(request: Request) -> str:
    """由 request 推導對外 base url（去尾斜線）。Railway 前面有 proxy，base_url 已正確。"""
    return str(request.base_url).rstrip("/")


def _return_url(request: Request) -> str:
    if settings.ecpay_payment_return_url:
        return settings.ecpay_payment_return_url
    return f"{_base_url(request)}/api/v1/payment/ecpay/return"


def _result_url(request: Request) -> str:
    return f"{_base_url(request)}/api/v1/payment/ecpay/result"


def _client_back_url(order_number: str) -> str:
    base = settings.ecpay_payment_client_back_url or settings.frontend_url
    return f"{base.rstrip('/')}/orders/{order_number}"


def _autosubmit_form(action: str, params: dict[str, str]) -> str:
    inputs = "\n".join(
        f'<input type="hidden" name="{k}" value="{_html_escape(v)}" />'
        for k, v in params.items()
    )
    return f"""<!doctype html>
<html lang="zh-TW">
<head>
<meta charset="utf-8" />
<title>正在前往付款…</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
    background: #F4EFE2; color: #2E2823;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; margin: 0;
  }}
  .box {{ text-align: center; }}
  .spinner {{
    width: 28px; height: 28px;
    border: 2px solid #8C6E52; border-top-color: transparent;
    border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <p>正在前往付款頁面…</p>
  </div>
  <form id="ecpay-form" method="POST" action="{action}">
    {inputs}
  </form>
  <script>document.getElementById('ecpay-form').submit();</script>
</body>
</html>"""


@router.get("/checkout/{order_id}", response_class=HTMLResponse, response_model=None)
async def ecpay_checkout(
    order_id: UUID,
    request: Request,
    current_user=Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """產出 auto-submit form HTML，導向 ECpay 付款頁。亦為重新付款入口。"""
    order = (await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )).scalar_one_or_none()
    if order is None:
        raise NotFoundError("訂單不存在")
    if order.payment_method != PaymentMethodEnum.ecpay:
        raise ConflictError("此訂單非線上付款訂單")
    if order.status != OrderStatusEnum.pending_payment:
        raise ConflictError("此訂單已不可付款（已付款 / 已取消 / 已逾期）")
    if order.payment_deadline and order.payment_deadline < datetime.now(UTC):
        raise ConflictError("付款期限已過")

    # ItemName：商品名稱以 # 串接
    titles = (await db.execute(
        select(OrderItem.product_title_snapshot).where(OrderItem.order_id == order.id)
    )).scalars().all()
    item_name = service.sanitize_item_name(list(titles))

    txn = await service.create_transaction_for_order(db, order)
    try:
        params = service.build_aio_checkout_params(
            merchant_trade_no=txn.merchant_trade_no,
            # 用 txn.amount（已四捨五入的整數快照），與 webhook 金額比對一致
            total_amount=int(txn.amount),
            item_name=item_name,
            trade_desc=f"易木 YIIMUI 訂單 {order.order_number}",
            return_url=_return_url(request),
            order_result_url=_result_url(request),
            client_back_url=_client_back_url(order.order_number),
            choose_payment="Credit",  # 階段 1 先只開信用卡；階段 2 放開 ALL
        )
    except ValueError as e:
        # 設定錯誤（MerchantID 未設等）→ 500，不留半截 transaction
        await db.rollback()
        log.error("[ecpay-checkout] build params 失敗：%s", e)
        raise ConflictError(f"付款參數產生失敗：{e}") from e

    await db.commit()

    if settings.ecpay_payment_dry_run:
        # 模擬模式：不真導向 ECpay，回可斷言的內容（含單號 + 參數）供開發 / 測試。
        log.info(
            "[ecpay-checkout] DRY_RUN order=%s mtn=%s",
            order.order_number, txn.merchant_trade_no,
        )
        return HTMLResponse(
            content=(
                f"<!doctype html><html><body data-dry-run='1' "
                f"data-merchant-trade-no='{_html_escape(txn.merchant_trade_no)}'>"
                f"<p>[DRY_RUN] 模擬導向 ECpay 付款頁</p>"
                f"<p>訂單 {_html_escape(order.order_number)} / NT$ {int(txn.amount)}</p>"
                f"</body></html>"
            )
        )

    return HTMLResponse(content=_autosubmit_form(service.aio_checkout_endpoint_url(), params))


@router.post("/return", response_class=PlainTextResponse, response_model=None)
async def ecpay_return(request: Request, db: AsyncSession = Depends(get_db)):
    """ECpay ReturnURL：付款成功 server-to-server 通知（權威來源，可標 paid）。"""
    raw_body = await request.body()
    params = dict(parse_qsl(raw_body.decode("utf-8", errors="replace"), keep_blank_values=True))
    result = await service.process_return_webhook(db, params)
    return PlainTextResponse(content=result)


@router.post("/result", response_class=RedirectResponse, response_model=None)
async def ecpay_result(request: Request, db: AsyncSession = Depends(get_db)):
    """OrderResultURL：ECpay 付款後用瀏覽器 POST 帶結果回來。

    **不可標 paid**（瀏覽器可竄改 / 中斷）；DB 狀態以 /return 為準。
    這裡僅把顧客 303 redirect 回前端結果頁，帶上 ECpay 的 RtnCode 供前端顯示。
    """
    raw_body = await request.body()
    params = dict(parse_qsl(raw_body.decode("utf-8", errors="replace"), keep_blank_values=True))
    rtn_code = params.get("RtnCode", "")
    # 找回 order_id 以導向前端訂單詳情頁（store 路由 /orders/:id 用 UUID）；找不到導回首頁。
    order_id = ""
    mtn = params.get("MerchantTradeNo", "")
    if mtn:
        from orders.models import PaymentTransaction  # noqa: PLC0415
        oid = (await db.execute(
            select(Order.id)
            .join(PaymentTransaction, PaymentTransaction.order_id == Order.id)
            .where(PaymentTransaction.merchant_trade_no == mtn)
        )).scalar_one_or_none()
        order_id = str(oid) if oid else ""

    base = settings.ecpay_payment_client_back_url or settings.frontend_url
    if order_id:
        target = f"{base.rstrip('/')}/orders/{order_id}?pay={rtn_code}"
    else:
        target = f"{base.rstrip('/')}/?pay={rtn_code}"
    return RedirectResponse(url=target, status_code=303)
