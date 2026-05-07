"""ECpay 物流（CVS Map / 超商選店）service。

流程：
  1. 前端開新視窗 → GET /logistics/cvs-map?type=UNIMARTC2C → 我們回 auto-submit form HTML
  2. Form auto-submit POST 到 ECpay map page → 用戶選店
  3. ECpay 把選店結果 POST 回 ServerReplyURL（即 /logistics/cvs-callback）
  4. callback 驗 CheckMacValue → 回 HTML 用 postMessage 把資料丟給 opener window → close()

CheckMacValue 演算法（ECpay 物流 規範，採 MD5 — 非金流的 SHA256）：
  1. 參數依 key 字典序排序（A→Z）
  2. 串成 HashKey=xxx&Key1=Val1&...&HashIV=yyy
  3. URL encode（.NET style：空格 → +；保留不編碼 -_.!*()）
  4. 全部轉小寫
  5. MD5
  6. 轉大寫

來源：https://developers.ecpay.com.tw/7424/  及  https://developers.ecpay.com.tw/8795/
"""
import hashlib
import secrets
from datetime import datetime
from urllib.parse import quote_plus

from core.config import settings


# ── 環境 endpoint ─────────────────────────────────────────────────────────────

def _ecpay_base_url() -> str:
    if settings.ecpay_env == "production":
        return "https://logistics.ecpay.com.tw"
    return "https://logistics-stage.ecpay.com.tw"


# ── 支援的物流子類型 ──────────────────────────────────────────────────────────

# 支援的 LogisticsSubType（B2C + C2C 全列）
# 帳號實際開了哪幾項要看 ECpay 後台「物流選單」
LOGISTICS_SUB_TYPES = {
    # B2C（大宗寄倉，月結合約）
    "UNIMART": "7-Eleven 大宗寄倉",
    "UNIMARTFREEZE": "7-Eleven 冷凍店取",
    "FAMI": "全家 大宗寄倉",
    "HILIFE": "萊爾富 大宗寄倉",
    # C2C（店到店，個人寄件）
    "UNIMARTC2C": "7-Eleven 交貨便",
    "FAMIC2C": "全家 店到店",
    "HILIFEC2C": "萊爾富 來來貨運",
    "OKMARTC2C": "OK 超商",
}


def is_supported_sub_type(sub_type: str) -> bool:
    return sub_type in LOGISTICS_SUB_TYPES


# ── 欄位長度限制（ECpay /8795/ 規範）─────────────────────────────────────────
# 來源：docs/integration_specs/ecpay_cvs_map.md §11

MAX_MERCHANT_ID_LEN = 10
MAX_MERCHANT_TRADE_NO_LEN = 20
MAX_SERVER_REPLY_URL_LEN = 200
MAX_EXTRA_DATA_LEN = 20

# Response 欄位長度上限（驗 ECpay 回傳資料完整性用）
MAX_CVS_STORE_ID_LEN = 9
MAX_CVS_STORE_NAME_LEN = 10
MAX_CVS_ADDRESS_LEN = 60
MAX_CVS_TELEPHONE_LEN = 20


# ── CheckMacValue ─────────────────────────────────────────────────────────────

def _ecpay_url_encode(s: str) -> str:
    """ECpay 的 .NET style URL encode：與 Python urllib.parse.quote_plus 大致一致，
    但需保留 '-', '_', '.', '!', '*', '(', ')' 不編碼，且最後轉小寫。"""
    # quote_plus 預設會編碼 -, _, ., 但實際上 RFC 不要求；ECpay 需保留它們
    encoded = quote_plus(s, safe="-_.!*()")
    return encoded.lower()


def calculate_check_mac_value(params: dict[str, str]) -> str:
    """產生 ECpay CheckMacValue (物流：MD5 大寫)."""
    # 1. 依 key 字典序升冪排序（ECpay key 都 PascalCase，case-insensitive 結果相同）
    sorted_keys = sorted(params.keys(), key=lambda k: k.lower())

    # 2. 串成 raw string
    pairs = [f"{k}={params[k]}" for k in sorted_keys]
    raw = (
        f"HashKey={settings.ecpay_hash_key}"
        + "&"
        + "&".join(pairs)
        + f"&HashIV={settings.ecpay_hash_iv}"
    )

    # 3. URL encode + lowercase
    encoded = _ecpay_url_encode(raw)

    # 4. MD5 + uppercase（物流 API 用 MD5，非金流的 SHA256）
    return hashlib.md5(encoded.encode("utf-8")).hexdigest().upper()


def verify_check_mac_value(params: dict[str, str]) -> bool:
    """驗證 ECpay 回傳的 CheckMacValue。"""
    received = params.get("CheckMacValue", "")
    if not received:
        return False
    rest = {k: v for k, v in params.items() if k != "CheckMacValue"}
    expected = calculate_check_mac_value(rest)
    return received.upper() == expected


# ── Map URL 產生 ──────────────────────────────────────────────────────────────

def generate_merchant_trade_no() -> str:
    """產生 ECpay 規範內、唯一的 MerchantTradeNo（最多 20 字元、英數）。

    格式：CVS + yyMMddHHmmss(12) + 4 hex = 19 字元，安全在 20 字元限制內。
    CVS Map 一次性用、不對應實際物流訂單，無需保存。
    """
    ts = datetime.now().strftime("%y%m%d%H%M%S")  # 12
    rand = secrets.token_hex(2).upper()            # 4
    no = f"CVS{ts}{rand}"  # 19 字元
    assert len(no) <= MAX_MERCHANT_TRADE_NO_LEN, "MerchantTradeNo length out of spec"
    return no


def build_cvs_map_form(
    logistics_sub_type: str,
    server_reply_url: str,
    extra_data: str = "",
) -> dict[str, str]:
    """產出送到 ECpay /Express/map 的所有參數（含 CheckMacValue）。

    驗證規則（依 docs/integration_specs/ecpay_cvs_map.md §3）：
    - LogisticsSubType 必須在 LOGISTICS_SUB_TYPES 列表內
    - MerchantID 必須有設定且 ≤ 10 字元
    - ServerReplyURL 必須以 https 開頭、≤ 200 字元
    - ExtraData ≤ 20 字元
    違反任何一條 raise ValueError，由 caller 轉成 HTTP 400 回傳。
    """
    if not is_supported_sub_type(logistics_sub_type):
        raise ValueError(f"不支援的物流類型：{logistics_sub_type}")

    if not settings.ecpay_merchant_id:
        raise ValueError("ECPAY_MERCHANT_ID 未設定")
    if len(settings.ecpay_merchant_id) > MAX_MERCHANT_ID_LEN:
        raise ValueError(f"ECPAY_MERCHANT_ID 過長（規範 ≤ {MAX_MERCHANT_ID_LEN}）")

    if not server_reply_url:
        raise ValueError("ServerReplyURL 不可空白")
    if not server_reply_url.startswith("https://"):
        raise ValueError("ServerReplyURL 必須以 https:// 開頭（ECpay 要求）")
    if len(server_reply_url) > MAX_SERVER_REPLY_URL_LEN:
        raise ValueError(f"ServerReplyURL 超過 {MAX_SERVER_REPLY_URL_LEN} 字元限制")

    if extra_data and len(extra_data) > MAX_EXTRA_DATA_LEN:
        raise ValueError(f"ExtraData 超過 {MAX_EXTRA_DATA_LEN} 字元限制")

    params = {
        "MerchantID": settings.ecpay_merchant_id,
        "MerchantTradeNo": generate_merchant_trade_no(),
        "LogisticsType": "CVS",
        "LogisticsSubType": logistics_sub_type,
        "IsCollection": "N",
        "ServerReplyURL": server_reply_url,
        "Device": "0",  # 0 = PC
    }
    if extra_data:
        params["ExtraData"] = extra_data

    params["CheckMacValue"] = calculate_check_mac_value(params)
    return params


def truncate_response_field(value: str, max_len: int) -> str:
    """ECpay 回傳欄位若超過規範長度（少數狀況），截斷並 log。
    不直接 raise — response 已收到，截斷比拒絕資料完整性更友善。"""
    if value and len(value) > max_len:
        return value[:max_len]
    return value


def map_endpoint_url() -> str:
    return f"{_ecpay_base_url()}/Express/map"
