"""ECpay CVS Map 同分頁 redirect 流程測試。

涵蓋：
  - /cvs-map?return=... 路徑白名單驗證
  - /cvs-map 把 return 寫進 ServerReplyURL query
  - /cvs-callback 解析 ECpay 回傳，303 redirect 到 store
  - return 缺失 / 非法時 fallback 到首頁
  - 失敗路徑（無 CVSStoreID、MAC 不對）redirect with cvs_error

歷史背景：舊版用 popup + postMessage 通信，行動 Safari 因 window.opener 被清空
+ window.close() 被拒，造成選完店無法返回。改為同分頁 303 redirect 後解決。
"""
import pytest
from httpx import AsyncClient

from core.config import settings

CVS_MAP_URL = "/api/v1/logistics/cvs-map"
CVS_CALLBACK_URL = "/api/v1/logistics/cvs-callback"


@pytest.fixture(autouse=True)
def _ecpay_test_creds(monkeypatch):
    """確保 ECpay 設定有合法 stub 值，讓 service.build_cvs_map_form() 不爆。"""
    monkeypatch.setattr(settings, "ecpay_merchant_id", "2000132")
    monkeypatch.setattr(settings, "ecpay_hash_key", "5294y06JbISpM5x9")
    monkeypatch.setattr(settings, "ecpay_hash_iv", "v77hoKGq4kWxNNIS")
    monkeypatch.setattr(settings, "ecpay_env", "staging")
    # ServerReplyURL must be https；測試用固定值
    monkeypatch.setattr(settings, "ecpay_server_reply_url",
                        "https://test.example.com/api/v1/logistics/cvs-callback")
    monkeypatch.setattr(settings, "frontend_url", "https://store.example.com")


# ── /cvs-map: return param 驗證 ─────────────────────────────────────────────

class TestCvsMapReturnParam:
    @pytest.mark.asyncio
    async def test_return_shipping_profiles_accepted(self, client: AsyncClient):
        resp = await client.get(
            f"{CVS_MAP_URL}?type=UNIMARTC2C&return=/profile/shipping-profiles"
        )
        assert resp.status_code == 200
        # ServerReplyURL 應該包含 ?return=%2Fprofile%2Fshipping-profiles
        body = resp.text
        assert "ServerReplyURL" in body
        assert "%2Fprofile%2Fshipping-profiles" in body or "/profile/shipping-profiles" in body

    @pytest.mark.asyncio
    async def test_return_checkout_accepted(self, client: AsyncClient):
        resp = await client.get(f"{CVS_MAP_URL}?type=UNIMARTC2C&return=/checkout")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_return_orders_uuid_accepted(self, client: AsyncClient):
        uuid = "11111111-2222-3333-4444-555555555555"
        resp = await client.get(f"{CVS_MAP_URL}?type=UNIMARTC2C&return=/orders/{uuid}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_return_external_url_rejected(self, client: AsyncClient):
        resp = await client.get(
            f"{CVS_MAP_URL}?type=UNIMARTC2C&return=https://evil.example.com"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_return_path_traversal_rejected(self, client: AsyncClient):
        resp = await client.get(
            f"{CVS_MAP_URL}?type=UNIMARTC2C&return=/profile/shipping-profiles/../../admin"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_return_protocol_relative_rejected(self, client: AsyncClient):
        resp = await client.get(
            f"{CVS_MAP_URL}?type=UNIMARTC2C&return=//evil.example.com"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_return_random_path_rejected(self, client: AsyncClient):
        resp = await client.get(
            f"{CVS_MAP_URL}?type=UNIMARTC2C&return=/admin/users"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_no_return_param_ok(self, client: AsyncClient):
        """不帶 return 仍可運作（fallback 行為，舊路徑相容）."""
        resp = await client.get(f"{CVS_MAP_URL}?type=UNIMARTC2C")
        assert resp.status_code == 200


# ── /cvs-callback: 303 redirect ─────────────────────────────────────────────


def _make_callback_body(**overrides) -> str:
    """組 ECpay-style form-encoded body。CVS Map 實際不附 CheckMacValue（quirk）."""
    from urllib.parse import urlencode
    params = {
        "MerchantID": "2000132",
        "MerchantTradeNo": "CVS250604ABCD1234567",
        "LogisticsSubType": "UNIMARTC2C",
        "CVSStoreID": "131386",
        "CVSStoreName": "新店忠孝",
        "CVSAddress": "新北市新店區忠孝路100號",
        "CVSTelephone": "02-29111111",
        "CVSOutSide": "0",
        "ExtraData": "",
    }
    params.update(overrides)
    return urlencode(params)


class TestCvsCallbackRedirect:
    @pytest.mark.asyncio
    async def test_success_redirects_to_store_with_cvs_params(self, client: AsyncClient):
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=/profile/shipping-profiles",
            content=_make_callback_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        assert loc.startswith("https://store.example.com/profile/shipping-profiles?")
        assert "cvs_store_id=131386" in loc
        assert "cvs_sub_type=UNIMARTC2C" in loc
        # 中文 URL encode
        assert "cvs_store_name=" in loc
        # 不應有 cvs_error
        assert "cvs_error" not in loc

    @pytest.mark.asyncio
    async def test_success_with_checkout_return(self, client: AsyncClient):
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=/checkout",
            content=_make_callback_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"].startswith("https://store.example.com/checkout?")

    @pytest.mark.asyncio
    async def test_success_with_order_detail_return(self, client: AsyncClient):
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=/orders/{uuid}",
            content=_make_callback_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        assert loc.startswith(f"https://store.example.com/orders/{uuid}?")

    @pytest.mark.asyncio
    async def test_missing_store_id_redirects_with_error(self, client: AsyncClient):
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=/profile/shipping-profiles",
            content=_make_callback_body(CVSStoreID=""),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        assert "cvs_error=missing_store" in loc
        # 不能洩漏 store 資料（不存在）
        assert "cvs_store_id=" not in loc

    @pytest.mark.asyncio
    async def test_no_return_param_redirects_to_root(self, client: AsyncClient):
        resp = await client.post(
            CVS_CALLBACK_URL,
            content=_make_callback_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        assert loc.startswith("https://store.example.com/?")

    @pytest.mark.asyncio
    async def test_invalid_return_param_redirects_to_root(self, client: AsyncClient):
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=https://evil.example.com",
            content=_make_callback_body(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        # fallback 到首頁，不能跳到 evil
        assert loc.startswith("https://store.example.com/?")
        assert "evil" not in loc

    @pytest.mark.asyncio
    async def test_chinese_store_name_url_encoded(self, client: AsyncClient):
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=/profile/shipping-profiles",
            content=_make_callback_body(CVSStoreName="新店忠孝門市"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        # 確認是 percent-encoded 而不是 raw bytes
        assert "%E6%96%B0" in loc or "%E6%9F%93" in loc or "%" in loc.split("cvs_store_name=")[1]

    @pytest.mark.asyncio
    async def test_mac_invalid_redirects_with_invalid_error(self, client: AsyncClient):
        """MAC 存在但對不起來 → cvs_error=invalid。

        實作邏輯：service.calculate_check_mac_value 算出來會跟我們 fixture 給的 garbage
        值不同 → valid=False → query 變 cvs_error=invalid。
        """
        body = _make_callback_body(CheckMacValue="GARBAGEMACVALUE12345")
        resp = await client.post(
            f"{CVS_CALLBACK_URL}?return=/profile/shipping-profiles",
            content=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        loc = resp.headers["location"]
        assert "cvs_error=invalid" in loc
        assert "cvs_store_id=" not in loc


# ── _validate_return_path unit tests ──────────────────────────────────────


class TestValidateReturnPath:
    """直接測 helper，覆蓋邊界 case。"""

    def test_valid_paths(self):
        from logistics.router import _validate_return_path
        assert _validate_return_path("/profile/shipping-profiles") == "/profile/shipping-profiles"
        assert _validate_return_path("/checkout") == "/checkout"
        uuid = "12345678-1234-1234-1234-123456789012"
        assert _validate_return_path(f"/orders/{uuid}") == f"/orders/{uuid}"

    def test_empty_or_none(self):
        from logistics.router import _validate_return_path
        assert _validate_return_path("") is None
        assert _validate_return_path("relative") is None

    def test_external_url_rejected(self):
        from logistics.router import _validate_return_path
        assert _validate_return_path("https://evil.com") is None
        assert _validate_return_path("//evil.com") is None
        assert _validate_return_path("javascript:alert(1)") is None

    def test_path_traversal_rejected(self):
        from logistics.router import _validate_return_path
        assert _validate_return_path("/profile/../admin") is None
        assert _validate_return_path("/checkout/..") is None

    def test_random_path_rejected(self):
        from logistics.router import _validate_return_path
        assert _validate_return_path("/admin/users") is None
        assert _validate_return_path("/api/v1/internal") is None
        assert _validate_return_path("/orders/not-a-uuid") is None
