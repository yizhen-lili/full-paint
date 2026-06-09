"""Module 23 — AioCheckOut 參數組裝單元測試。"""
import pytest

from payment import service


def _base_kwargs(**over):
    kw = dict(
        merchant_trade_no="PAYTEST0001",
        total_amount=1260,
        item_name="油畫模板",
        trade_desc="易木 YIIMUI 訂單 PL-X",
        return_url="https://x.test/api/v1/payment/ecpay/return",
        order_result_url="https://x.test/api/v1/payment/ecpay/result",
        client_back_url="https://store.test/orders/PL-X",
    )
    kw.update(over)
    return kw


def test_build_params_has_required_fields():
    p = service.build_aio_checkout_params(**_base_kwargs())
    assert p["MerchantID"] == "3002607"
    assert p["MerchantTradeNo"] == "PAYTEST0001"
    assert p["PaymentType"] == "aio"
    assert p["TotalAmount"] == "1260"        # 整數字串
    assert p["EncryptType"] == "1"           # SHA256
    assert p["ChoosePayment"] == "Credit"    # 階段 1 預設
    assert "CheckMacValue" in p


def test_build_params_check_mac_value_valid():
    """產出的 CheckMacValue 必須能用 verify 驗回（含 mac 一起驗）。"""
    p = service.build_aio_checkout_params(**_base_kwargs())
    assert service.verify_check_mac_value(p) is True


def test_build_params_choose_payment_override():
    p = service.build_aio_checkout_params(**_base_kwargs(choose_payment="ALL"))
    assert p["ChoosePayment"] == "ALL"


def test_build_params_rejects_zero_amount():
    with pytest.raises(ValueError, match="正整數"):
        service.build_aio_checkout_params(**_base_kwargs(total_amount=0))


def test_build_params_rejects_missing_return_url():
    with pytest.raises(ValueError, match="ReturnURL"):
        service.build_aio_checkout_params(**_base_kwargs(return_url=""))


def test_build_params_includes_payment_info_url_when_given():
    p = service.build_aio_checkout_params(
        **_base_kwargs(payment_info_url="https://x.test/api/v1/payment/ecpay/payment-info")
    )
    assert p["PaymentInfoURL"].endswith("/payment-info")


def test_aio_checkout_endpoint_stage():
    # conftest 設 ecpay_payment_env=stage
    assert "payment-stage.ecpay.com.tw" in service.aio_checkout_endpoint_url()


class _FakeOrder:
    def __init__(self, total):
        self.total = total


@pytest.mark.parametrize("total,expected", [
    ("1260", 1260),       # 整數
    ("694.60", 695),      # 百分比折扣小數 → 四捨五入進位
    ("694.40", 694),      # 四捨五入捨去
    ("0.50", 1),          # ROUND_HALF_UP（.5 進位）
])
def test_charge_amount_rounds_to_integer(total, expected):
    from decimal import Decimal
    assert service.charge_amount(_FakeOrder(Decimal(total))) == expected
