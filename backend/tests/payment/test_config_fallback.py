"""Module 23 — 金流 ECpay 金鑰 fallback 到物流金鑰（同帳號共用）。"""
from core.config import Settings

_BASE = dict(
    _env_file=None,  # 隔離 .env / OS 影響
    database_url="postgresql+asyncpg://t/t",
    jwt_secret="t",
    ecpay_merchant_id="L123",
    ecpay_hash_key="LKEY",
    ecpay_hash_iv="LIV",
    ecpay_env="production",
)


def test_payment_creds_fallback_to_logistics():
    """金流變數未設 → 自動沿用物流那組（MerchantID / HashKey / HashIV / env）。"""
    s = Settings(**_BASE)
    assert s.ecpay_payment_merchant_id == "L123"
    assert s.ecpay_payment_hash_key == "LKEY"
    assert s.ecpay_payment_hash_iv == "LIV"
    assert s.ecpay_payment_env == "production"


def test_payment_creds_explicit_override_wins():
    """明確設定金流變數 → 覆蓋 fallback（金流為獨立帳號的情況）。"""
    s = Settings(
        **_BASE,
        ecpay_payment_merchant_id="P999",
        ecpay_payment_hash_key="PKEY",
        ecpay_payment_hash_iv="PIV",
        ecpay_payment_env="stage",
    )
    assert s.ecpay_payment_merchant_id == "P999"
    assert s.ecpay_payment_hash_key == "PKEY"
    assert s.ecpay_payment_hash_iv == "PIV"
    assert s.ecpay_payment_env == "stage"
