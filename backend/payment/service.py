"""ECpay 金流 service — AioCheckOut（線上付款）。

CheckMacValue 演算法（ECpay 金流 規範，採 SHA256）：
  1. 參數依 key 字典序排序（A→Z）
  2. 串成 HashKey=xxx&Key1=Val1&...&HashIV=yyy
  3. URL encode（.NET style：空格 → +；保留不編碼 -_.!*()）
  4. 全部轉小寫
  5. SHA256          ← 與物流的 MD5 不同
  6. 轉大寫

⚠️ 金流用 SHA256；物流用 MD5。EncryptType=1 必帶（告訴 ECpay 用 SHA256）。

文件：docs/integration_specs/ecpay_aio_checkout.md
"""
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings

# _ecpay_url_encode 是純函數（不依賴任何帳號設定），直接沿用物流模組的單一實作，
# 避免兩份 .NET-style URL encode 各自維護而漂移。
from logistics.service import _ecpay_url_encode
from orders.models import (
    Order,
    OrderStatusEnum,
    PaymentTransaction,
    PaymentTransactionStatusEnum,
)

logger = logging.getLogger(__name__)


# ── 環境 endpoint ─────────────────────────────────────────────────────────────

def _payment_base_url() -> str:
    if settings.ecpay_payment_env == "production":
        return "https://payment.ecpay.com.tw"
    return "https://payment-stage.ecpay.com.tw"


def aio_checkout_endpoint_url() -> str:
    return f"{_payment_base_url()}/Cashier/AioCheckOut/V5"


# ── 欄位長度限制（ECpay AioCheckOut 規範）─────────────────────────────────────

MAX_MERCHANT_ID_LEN = 10
MAX_MERCHANT_TRADE_NO_LEN = 20
MAX_ITEM_NAME_LEN = 400
MAX_TRADE_DESC_LEN = 200
# 超商代碼 / 條碼上限。信用卡無此限，故階段 1（Credit-only）不檢查；
# ⚠️ 階段 2 放開 ChoosePayment=ALL 時，必須對含 CVS/BARCODE 的情況加此上限檢查。
MAX_TOTAL_AMOUNT = 20000


# ── CheckMacValue（SHA256）────────────────────────────────────────────────────

def calculate_check_mac_value(params: dict[str, str]) -> str:
    """產生 ECpay CheckMacValue（金流：SHA256 大寫）。"""
    sorted_keys = sorted(params.keys(), key=lambda k: k.lower())
    pairs = [f"{k}={params[k]}" for k in sorted_keys]
    raw = (
        f"HashKey={settings.ecpay_payment_hash_key}"
        + "&"
        + "&".join(pairs)
        + f"&HashIV={settings.ecpay_payment_hash_iv}"
    )
    encoded = _ecpay_url_encode(raw)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def verify_check_mac_value(params: dict[str, str]) -> bool:
    """驗證 ECpay 回傳的 CheckMacValue。空值或不符皆回 False。"""
    received = params.get("CheckMacValue", "")
    if not received:
        return False
    rest = {k: v for k, v in params.items() if k != "CheckMacValue"}
    expected = calculate_check_mac_value(rest)
    return received.upper() == expected


# ── MerchantTradeNo ──────────────────────────────────────────────────────────

def generate_merchant_trade_no() -> str:
    """產生唯一的 MerchantTradeNo（≤20 字、英數）。

    格式：PAY + yyMMddHHmmss(12) + 4 hex = 19 字元，安全在 20 字元限制內。
    """
    ts = datetime.now().strftime("%y%m%d%H%M%S")  # 12
    rand = secrets.token_hex(2).upper()            # 4
    no = f"PAY{ts}{rand}"  # 19 字元
    assert len(no) <= MAX_MERCHANT_TRADE_NO_LEN, "MerchantTradeNo length out of spec"
    return no


# ── ItemName / TradeDesc sanitize ────────────────────────────────────────────

def sanitize_item_name(titles: list[str]) -> str:
    """商品名稱組成 ItemName：多項用 # 分隔（ECpay 規範），截斷到 400 字。

    ECpay ItemName 不可含 #（被當分隔符），把單項名稱裡的 # 換成空白。
    """
    clean = [(t or "").replace("#", " ").strip() or "商品" for t in titles]
    name = "#".join(clean) if clean else "商品"
    return name[:MAX_ITEM_NAME_LEN]


# ── AioCheckOut 參數組裝 ──────────────────────────────────────────────────────

# 產品決策（user 2026-06-09）：只開「信用卡 / Apple Pay / 超商代碼 / 超商條碼」，
# 排除「ATM 虛擬帳號」與「網路ATM(WebATM / 網路銀行)」。
ALWAYS_IGNORE_PAYMENTS = ("ATM", "WebATM")


def resolve_ignore_payment(total_amount: int, choose_payment: str) -> str:
    """組 IgnorePayment（ChoosePayment=ALL 時排除不開放的付款方式，以 # 分隔）。

    - 一律排除 ATM / WebATM（產品決策）。
    - 金額超過超商代碼/條碼上限（NT$20,000）時，額外排除 CVS / BARCODE，
      避免顧客選了超商付款卻被 ECpay 退件（此時只剩信用卡 / Apple Pay）。

    僅 ChoosePayment=ALL 時有意義（單選不會列出多種方式）。
    """
    if choose_payment != "ALL":
        return ""
    ignore = list(ALWAYS_IGNORE_PAYMENTS)
    if total_amount > MAX_TOTAL_AMOUNT:
        ignore += ["CVS", "BARCODE"]
    return "#".join(ignore)


def build_aio_checkout_params(
    *,
    merchant_trade_no: str,
    total_amount: int,
    item_name: str,
    trade_desc: str,
    return_url: str,
    order_result_url: str,
    client_back_url: str,
    payment_info_url: str = "",
    choose_payment: str = "Credit",
) -> dict[str, str]:
    """組 AioCheckOut 送出參數（含 CheckMacValue）。

    驗證：
    - MerchantID 必須有設定且 ≤ 10 字元
    - total_amount 必須為正整數
    - ReturnURL / OrderResultURL 必填
    違反 raise ValueError，由 caller 轉成 HTTP 4xx/5xx。

    金額 > MAX_TOTAL_AMOUNT 且 ChoosePayment=ALL → 自動 IgnorePayment=CVS#BARCODE。
    """
    if not settings.ecpay_payment_merchant_id:
        raise ValueError("ECPAY_PAYMENT_MERCHANT_ID 未設定")
    if len(settings.ecpay_payment_merchant_id) > MAX_MERCHANT_ID_LEN:
        raise ValueError(f"ECPAY_PAYMENT_MERCHANT_ID 過長（規範 ≤ {MAX_MERCHANT_ID_LEN}）")
    if total_amount <= 0:
        raise ValueError("付款金額必須為正整數")
    if not return_url:
        raise ValueError("ReturnURL 不可空白")
    if not order_result_url:
        raise ValueError("OrderResultURL 不可空白")

    params = {
        "MerchantID": settings.ecpay_payment_merchant_id,
        "MerchantTradeNo": merchant_trade_no,
        "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        "PaymentType": "aio",
        "TotalAmount": str(total_amount),
        "TradeDesc": (trade_desc or "")[:MAX_TRADE_DESC_LEN],
        "ItemName": item_name,
        "ReturnURL": return_url,
        "ChoosePayment": choose_payment,
        "EncryptType": "1",  # 1 = SHA256
        "NeedExtraPaidInfo": "Y",
        "OrderResultURL": order_result_url,
        "ClientBackURL": client_back_url,
    }
    if payment_info_url:
        params["PaymentInfoURL"] = payment_info_url
    ignore = resolve_ignore_payment(total_amount, choose_payment)
    if ignore:
        params["IgnorePayment"] = ignore

    params["CheckMacValue"] = calculate_check_mac_value(params)
    return params


# ── RtnCode 判定 ──────────────────────────────────────────────────────────────

# PaymentInfoURL「取號成功」（≠ 付款成功）的 RtnCode。
# 來源：ECpay AIO PaymentInfo 文件 /16557/ — ATM 取號=2；CVS/BARCODE 取號=10100073。
ATM_CODE_ISSUED_RTN_CODE = 2
CVS_CODE_ISSUED_RTN_CODE = 10100073


def is_payment_success(rtn_code: int | None) -> bool:
    """ReturnURL：RtnCode == 1 才是真正付款成功（唯一可標 paid 的依據）。"""
    return rtn_code == 1


def is_code_issued(rtn_code: int | None) -> bool:
    """PaymentInfoURL：取號成功（拿到虛擬帳號/繳費代碼，但顧客尚未付款）。"""
    return rtn_code in (ATM_CODE_ISSUED_RTN_CODE, CVS_CODE_ISSUED_RTN_CODE)


def to_int(raw: str | None) -> int | None:
    """ECpay 回傳的數字欄位（RtnCode / TradeAmt）是字串，轉 int；非數字回 None。"""
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


# ECpay 時間為台灣時間（UTC+8）；轉成 tz-aware 才能與 payment_deadline（UTC）比較。
_TW_TZ = timezone(timedelta(hours=8))


def parse_ecpay_datetime(raw: str | None) -> datetime | None:
    """解析 ECpay 回傳的時間字串（ExpireDate 等）。

    ATM ExpireDate 多為 'yyyy/MM/dd'（純日期）；CVS/BARCODE 為 'yyyy/MM/dd HH:mm:ss'。
    兩種格式都試；回 tz-aware（台灣時區）datetime，無法解析回 None。
    """
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            # 純日期視為當日 23:59:59（繳費截止當天有效）
            if fmt == "%Y/%m/%d":
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.replace(tzinfo=_TW_TZ)
        except ValueError:
            continue
    return None


# ── DB 層：交易建立 + ReturnURL webhook 處理 ──────────────────────────────────

def charge_amount(order: Order) -> int:
    """ECpay TotalAmount 只接受整數；order.total 可能因百分比折扣 round(,2) 產生小數。
    四捨五入到整數，作為實際送 ECpay 的金額。

    用 Decimal(str(...)) 而非 Decimal(float)：防禦尚未經 DB round-trip（仍為 float）的
    order.total 產生 694.5999... 的浮點誤差。
    """
    return int(Decimal(str(order.total)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


async def create_transaction_for_order(
    db: AsyncSession, order: Order
) -> PaymentTransaction:
    """為一張訂單建立一筆新的付款交易（每次結帳 / 重試各一筆）。

    merchant_trade_no 為唯一單號；amount 存「實際送 ECpay 的整數金額」快照，確保
    送 ECpay 的 TotalAmount / webhook 金額比對 / 實收三者一致（避免 int() 截斷小數）。
    """
    txn = PaymentTransaction(
        order_id=order.id,
        merchant_trade_no=generate_merchant_trade_no(),
        amount=charge_amount(order),
        status=PaymentTransactionStatusEnum.created,
    )
    db.add(txn)
    await db.flush()
    return txn


async def mark_awaiting_transactions_expired(db: AsyncSession, order_id) -> None:
    """訂單逾期取消時，把該訂單仍在等繳費的 ATM/超商交易標 expired（呼叫端負責 commit）。"""
    await db.execute(
        update(PaymentTransaction)
        .where(
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.status == PaymentTransactionStatusEnum.awaiting_atm,
        )
        .values(status=PaymentTransactionStatusEnum.expired)
    )


async def process_return_webhook(db: AsyncSession, params: dict[str, str]) -> str:
    """處理 ECpay ReturnURL（付款成功 server-to-server 權威 webhook）。

    回傳要回給 ECpay 的純字串：成功 / 已知失敗 → "1|OK"；驗章或資料異常 → "0|<reason>"
    （讓 ECpay 重送、且不洩漏細節）。**唯一可標 paid 的路徑。**
    """
    # 延遲 import 避免與 orders.service 形成載入順序問題（orders.service 不 import payment）
    from auth.models import User
    from orders.service import _apply_paid_side_effects, _publish_order_status_changed

    # 1. 驗章（失敗回非 1，讓 ECpay 重送）
    if not verify_check_mac_value(params):
        logger.warning("[ecpay-return] CheckMacValue 驗證失敗")
        return "0|CheckMacValueError"

    mtn = params.get("MerchantTradeNo", "")
    txn = (await db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.merchant_trade_no == mtn)
        .with_for_update()
    )).scalar_one_or_none()
    if txn is None:
        logger.warning("[ecpay-return] 找不到交易 MerchantTradeNo=%s", mtn)
        return "0|OrderNotFound"

    # 2. 金額比對（用發起時快照 txn.amount，避免訂單被改價誤判）
    trade_amt = to_int(params.get("TradeAmt"))
    if trade_amt is None or trade_amt != int(txn.amount):
        logger.warning(
            "[ecpay-return] 金額不符 trade_amt=%s expected=%s mtn=%s",
            trade_amt, int(txn.amount), mtn,
        )
        return "0|AmountMismatch"

    # 3. 記錄 webhook 軌跡
    rtn_code = to_int(params.get("RtnCode"))
    txn.last_rtn_code = rtn_code
    txn.last_rtn_msg = params.get("RtnMsg")
    txn.raw_callback = params
    txn.ecpay_trade_no = params.get("TradeNo") or txn.ecpay_trade_no
    txn.payment_type = params.get("PaymentType") or txn.payment_type

    # 4. Idempotency：已處理過直接回 OK，不重複副作用
    if txn.status == PaymentTransactionStatusEnum.paid:
        return "1|OK"

    # 5. RtnCode 判定
    if not is_payment_success(rtn_code):
        txn.status = PaymentTransactionStatusEnum.failed
        await db.commit()
        return "1|OK"  # 已知失敗，不需 ECpay 重送

    # 6. 付款成功 → 標 paid（鎖 Order，guard pending_payment 防重 / 防競態）
    order = (await db.execute(
        select(Order).where(Order.id == txn.order_id).with_for_update()
    )).scalar_one_or_none()
    if order is None:
        logger.error("[ecpay-return] 交易 %s 對應訂單不存在", mtn)
        return "0|OrderNotFound"

    txn.status = PaymentTransactionStatusEnum.paid
    txn.paid_at = datetime.now(UTC)

    if order.status == OrderStatusEnum.pending_payment:
        user = (await db.execute(
            select(User).where(User.id == order.user_id)
        )).scalar_one()
        await _apply_paid_side_effects(db, order, user)
        await db.commit()
        _publish_order_status_changed(order)
    else:
        # 訂單已非 pending_payment（多半是 ATM 取號後逾期被 Celery 取消，但顧客仍繳了費）：
        # 不標 paid（避免覆蓋已取消狀態），但這是「孤兒款項」—— 顧客付了錢卻沒有有效訂單，
        # 必須通知 admin 人工退款處理（不能只 log 吞掉）。
        from notifications.service import create_notification  # noqa: PLC0415
        logger.warning(
            "[ecpay-return] 孤兒款項：訂單 %s 已為 %s 卻收到付款成功，需人工退款",
            order.order_number, order.status,
        )
        await create_notification(
            db,
            type="ecpay_paid_after_close",
            message=(
                f"訂單 {order.order_number} 已是「{order.status}」卻收到 ECpay 付款成功"
                f"（交易 {txn.merchant_trade_no}，NT$ {int(txn.amount)}）—— 顧客已付款，請人工退款"
            ),
            reference_type="order",
            reference_id=order.id,
            requires_action=True,
        )
        await db.commit()
    return "1|OK"


async def process_payment_info_webhook(db: AsyncSession, params: dict[str, str]) -> str:
    """處理 ECpay PaymentInfoURL（ATM/超商取號通知）。

    取號成功 ≠ 付款成功（RtnCode 為 2 / 10100073，不是 1）。**絕不標 paid。**
    存虛擬帳號 / 繳費代碼 + 期限，transaction → awaiting_atm，訂單維持 pending_payment，
    payment_deadline 對齊 min(現有, ExpireDate)，寄帳號 email。回 "1|OK"。
    """
    from auth.models import User
    from orders.service import _send_email

    if not verify_check_mac_value(params):
        logger.warning("[ecpay-payment-info] CheckMacValue 驗證失敗")
        return "0|CheckMacValueError"

    mtn = params.get("MerchantTradeNo", "")
    txn = (await db.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.merchant_trade_no == mtn)
        .with_for_update()
    )).scalar_one_or_none()
    if txn is None:
        logger.warning("[ecpay-payment-info] 找不到交易 MerchantTradeNo=%s", mtn)
        return "0|OrderNotFound"

    rtn_code = to_int(params.get("RtnCode"))
    txn.last_rtn_code = rtn_code
    txn.last_rtn_msg = params.get("RtnMsg")
    txn.raw_callback = params
    txn.ecpay_trade_no = params.get("TradeNo") or txn.ecpay_trade_no
    txn.payment_type = params.get("PaymentType") or txn.payment_type

    if not is_code_issued(rtn_code):
        # 非取號成功碼：記錄即可（理論上不該到這），不改狀態
        logger.warning("[ecpay-payment-info] 非取號成功 RtnCode=%s mtn=%s", rtn_code, mtn)
        await db.commit()
        return "1|OK"

    # 首次取號才寄帳號 email（ECpay 可能重送同一取號通知，避免重複寄信）
    first_issue = txn.status == PaymentTransactionStatusEnum.created

    # 取號成功 → 存帳號 / 代碼 + 期限
    txn.bank_code = params.get("BankCode") or None
    txn.vaccount = params.get("vAccount") or None
    txn.payment_no = params.get("PaymentNo") or None
    expire = parse_ecpay_datetime(params.get("ExpireDate"))
    txn.expire_date = expire
    # 只從 created / awaiting_atm 轉入 awaiting_atm；不覆蓋 paid / failed / expired
    # （取號通知重送或邊界亂序時，已終結的狀態不回退）
    if txn.status in (
        PaymentTransactionStatusEnum.created,
        PaymentTransactionStatusEnum.awaiting_atm,
    ):
        txn.status = PaymentTransactionStatusEnum.awaiting_atm

    # 對齊訂單付款期限：取 min（不延長，維持我方庫存保留政策；逾期未付走 Celery + 孤兒款項處理）
    order = (await db.execute(
        select(Order).where(Order.id == txn.order_id).with_for_update()
    )).scalar_one_or_none()
    if order is not None and expire is not None and order.payment_deadline:
        if expire < order.payment_deadline:
            order.payment_deadline = expire

    await db.commit()

    # 寄虛擬帳號 / 繳費代碼 email（取號才有帳號可給顧客；重送不重寄）
    if order is not None and first_issue:
        user = (await db.execute(
            select(User.email).where(User.id == order.user_id)
        )).scalar_one_or_none()
        if user:
            await _send_email(
                to=user,
                subject=f"【易木 YIIMUI】付款資訊 {order.order_number}",
                html=_payment_info_email_html(order.order_number, txn),
            )
    return "1|OK"


def _payment_info_email_html(order_number: str, txn: PaymentTransaction) -> str:
    """ATM 虛擬帳號 / 超商繳費代碼通知信內容。"""
    lines = [f"<p>您的訂單 {order_number} 付款資訊如下，請於期限前完成繳費：</p>"]
    if txn.vaccount:
        lines.append(f"<p>ATM 銀行代碼：{txn.bank_code or ''}<br>虛擬帳號：{txn.vaccount}</p>")
    if txn.payment_no:
        lines.append(f"<p>超商繳費代碼：{txn.payment_no}</p>")
    lines.append(f"<p>應繳金額：NT$ {int(txn.amount)}</p>")
    if txn.expire_date:
        lines.append(f"<p>繳費期限：{txn.expire_date.strftime('%Y-%m-%d %H:%M')}（台灣時間）</p>")
    lines.append("<p>繳費完成後訂單將自動確認。</p>")
    return "".join(lines)
