from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _normalize_async_driver(cls, v: str) -> str:
        """Railway PostgreSQL plugin 注入 `postgresql://...`，但 backend 用 SQLAlchemy
        async + asyncpg driver — URL scheme 必須是 `postgresql+asyncpg://...`。
        本地 .env 已寫對；雲端 reference 自動補 +asyncpg。
        """
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days_customer: int = 7
    jwt_expire_hours_admin: int = 8

    # Google Sign-in（store customer 端，admin 不用）— Google Cloud Console OAuth 2.0 Client ID
    # 用途：驗 Google Identity Services 發的 ID token 的 audience 欄位。
    # 空字串時 service.google_signin 主動 raise 503，避免靜默失敗。
    google_client_id: str = ""

    resend_api_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    # 客人按「回信」會回到這個地址 — 通常是商家可即時收信的 Gmail / 工作信箱
    support_email: str = ""
    frontend_url: str = "http://localhost:5173"
    admin_url: str = "http://localhost:5174"

    firebase_credentials: str = ""
    firebase_storage_bucket: str = ""

    redis_url: str = "redis://localhost:6379/0"

    # SAM 模型檔（vit_b ~375MB）；本地預設指向 paint-by-number/models/sam_vit_b.pth
    # 部署環境由 Dockerfile RUN curl 下載到 /app/models/ 並設此 env var
    sam_model_path: str | None = None

    # ── ECpay 物流（CVS Map / 超商選店）──────────────────────────────────
    # 物流產品的 MerchantID / HashKey / HashIV（與電子發票是不同帳號）
    ecpay_merchant_id: str = ""
    ecpay_hash_key: str = ""
    ecpay_hash_iv: str = ""
    # 'stage' = 沙箱（logistics-stage.ecpay.com.tw）
    # 'production' = 正式（logistics.ecpay.com.tw）
    ecpay_env: str = "stage"
    # ServerReplyURL：ECpay 把選店結果 POST 回我們的 callback URL（必須可被外網存取）
    # 預設留空 → service 由 request.base_url 自動推導
    ecpay_server_reply_url: str = ""

    # 'true' = 模擬模式（不真打 ECpay /Express/Create）
    # 'false' = 正式模式（真送 ECpay 建單）
    # 開發 / UI 驗收期間設 true，避免在正式 ECpay 帳號留真實託運單。
    ecpay_dry_run: bool = False

    # ── ECpay 金流（AioCheckOut / 線上付款）────────────────────────────────
    # 金流的 MerchantID / HashKey / HashIV（與物流、電子發票都是不同帳號）。
    # ⚠️ 金流簽章用 SHA256（物流用 MD5）。
    # 開發測試用官方公開 sandbox 組（3002607）；正式上線換 user 正式帳號。
    ecpay_payment_merchant_id: str = ""
    ecpay_payment_hash_key: str = ""
    ecpay_payment_hash_iv: str = ""
    # 'stage' = 沙箱（payment-stage.ecpay.com.tw）
    # 'production' = 正式（payment.ecpay.com.tw）
    ecpay_payment_env: str = "stage"
    # ReturnURL（付款成功 server-to-server 權威 webhook）。留空 → 由 request.base_url 推導。
    ecpay_payment_return_url: str = ""
    # 顧客在 ECpay 按「返回商店」導回的前端 URL。留空 → 用 frontend_url。
    ecpay_payment_client_back_url: str = ""
    # 'true' = 模擬模式（不真導向 ECpay）；開發 / 測試期用。
    ecpay_payment_dry_run: bool = False

    @field_validator(
        "ecpay_merchant_id", "ecpay_hash_key", "ecpay_hash_iv",
        "ecpay_env", "ecpay_server_reply_url",
        "ecpay_payment_merchant_id", "ecpay_payment_hash_key", "ecpay_payment_hash_iv",
        "ecpay_payment_env", "ecpay_payment_return_url", "ecpay_payment_client_back_url",
    )
    @classmethod
    def _strip_ecpay(cls, v: str) -> str:
        """環境變數複製貼上常帶換行 / 前後空白；strip 掉避免簽章對不起來。"""
        return v.strip() if v else v

    class Config:
        env_file = ".env"


settings = Settings()
