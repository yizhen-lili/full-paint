"""Module 23 — ECpay 金流 CheckMacValue（SHA256）單元測試。"""
import pytest

from payment import service

# conftest setup_db 注入 sandbox 帳號：3002607 / pwFHCqoQZGmho4w6 / EkRm7iFT261dpevs


def test_url_encode_preserves_special_chars():
    """ECpay .NET style url encode 必須保留 -_.!*() 不編碼，且轉小寫。"""
    encoded = service._ecpay_url_encode("A-b_c.d!e*f(g)")
    assert encoded == "a-b_c.d!e*f(g)"


def test_check_mac_value_ecpay_official_golden(monkeypatch):
    """以 ECpay 官方文件公開範例驗算 — 證明演算法與 ECpay 端一致（非自簽自驗）。

    來源：ECpay Developers 檢查碼機制說明（AioCheckOut SHA256 範例）。
    HashKey=5294y06JbISpM5x9 / HashIV=v77hoKGq4kWxNNIS。
    若任一步驟（排序 / .NET url encode / 小寫 / sha256 / 大寫）與 ECpay 不一致，
    這個 assert 會失敗 —— 這正是上線前最關鍵的防呆（避免 production 全 CheckMacValueError）。
    """
    from core.config import settings
    monkeypatch.setattr(settings, "ecpay_payment_hash_key", "5294y06JbISpM5x9")
    monkeypatch.setattr(settings, "ecpay_payment_hash_iv", "v77hoKGq4kWxNNIS")
    params = {
        "MerchantID": "2000132",
        "MerchantTradeNo": "ecpay20180504110723",
        "MerchantTradeDate": "2018/05/04 11:07:23",
        "PaymentType": "aio",
        "TotalAmount": "1000",
        "TradeDesc": "促銷方案",
        "ItemName": "Apple iPhone 7 手機殼",
        "ReturnURL": "https://www.ecpay.com.tw/receive.php",
        "ChoosePayment": "ALL",
        "EncryptType": "1",
    }
    mac = service.calculate_check_mac_value(params)
    assert mac == "B4A5010C622CC8710182465D1A8CFFF29B9212264E679C8468893C4A6EBB716B"


def test_check_mac_value_is_uppercase_hex_64():
    params = {"MerchantID": "3002607", "TotalAmount": "100"}
    mac = service.calculate_check_mac_value(params)
    assert len(mac) == 64
    assert mac == mac.upper()


def test_verify_round_trip_true():
    """自己算的 mac 必須驗得過。"""
    params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": "PAYTEST0001",
        "TotalAmount": "500",
        "RtnCode": "1",
    }
    params["CheckMacValue"] = service.calculate_check_mac_value(params)
    assert service.verify_check_mac_value(params) is True


def test_verify_tampered_amount_false():
    """竄改任一欄位後驗章必須失敗。"""
    params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": "PAYTEST0001",
        "TotalAmount": "500",
    }
    params["CheckMacValue"] = service.calculate_check_mac_value(params)
    params["TotalAmount"] = "999"  # 竄改
    assert service.verify_check_mac_value(params) is False


def test_verify_missing_mac_false():
    assert service.verify_check_mac_value({"MerchantID": "3002607"}) is False


@pytest.mark.parametrize("rtn,expected", [(1, True), (0, False), (2, False), (None, False)])
def test_is_payment_success(rtn, expected):
    assert service.is_payment_success(rtn) is expected


def test_to_int():
    assert service.to_int("1260") == 1260
    assert service.to_int("abc") is None
    assert service.to_int(None) is None


def test_generate_merchant_trade_no_within_limit():
    no = service.generate_merchant_trade_no()
    assert no.startswith("PAY")
    assert len(no) <= service.MAX_MERCHANT_TRADE_NO_LEN
    assert no.isalnum()


def test_sanitize_item_name_uses_hash_separator():
    name = service.sanitize_item_name(["畫板 A", "畫#板 B"])
    assert name == "畫板 A#畫 板 B"  # 單項內的 # 換成空白，項目間用 #


def test_sanitize_item_name_empty_fallback():
    assert service.sanitize_item_name([]) == "商品"
