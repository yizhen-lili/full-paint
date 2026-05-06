import logging

from fastapi import APIRouter, Depends

from dependencies.auth import require_admin, require_auth
from production import service as production_service
from production.schemas.request import UploadProductionImageRequest
from production.schemas.response import UploadUrlResponse
from upload import service as upload_service
from upload.schemas.request import UploadImageRequest
from upload.schemas.response import PrivateUploadResponse, PublicUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


@router.post("/upload/production-image", response_model=UploadUrlResponse)
async def upload_production_image(
    body: UploadProductionImageRequest,
    operator=Depends(require_admin),
):
    return production_service.generate_upload_signed_url(body.filename, body.content_type)


@router.post("/upload/product-image", response_model=PublicUploadResponse)
async def upload_product_image(
    body: UploadImageRequest,
    _=Depends(require_admin),
):
    return upload_service.generate_public_signed_url(
        "product_images", body.filename, body.content_type
    )


@router.post("/upload/case-image", response_model=PublicUploadResponse)
async def upload_case_image(
    body: UploadImageRequest,
    _=Depends(require_admin),
):
    return upload_service.generate_public_signed_url(
        "case_images", body.filename, body.content_type
    )


@router.post("/upload/custom-photo", response_model=PrivateUploadResponse)
async def upload_custom_photo(
    body: UploadImageRequest,
    _=Depends(require_auth),
):
    return upload_service.generate_private_signed_url(
        "custom_photos", body.filename, body.content_type
    )


# ── Diagnostics（admin 用）─────────────────────────────────────────────


@router.get("/admin/system/firebase-status", tags=["System"])
async def firebase_status(_=Depends(require_admin)):
    """檢查 Firebase Storage bucket + CORS 設定（每次 reload 確保不是 cached）。"""
    from core.firebase import get_bucket
    bucket = get_bucket()
    bucket.reload()  # 強制從 GCS 拉最新 metadata
    return {
        "bucket": bucket.name,
        "cors": bucket.cors or [],
    }


@router.post("/admin/system/firebase-cors-fix", tags=["System"])
async def firebase_cors_fix(_=Depends(require_admin)):
    """一鍵修正 Firebase Storage CORS（允許 localhost / vercel admin 直傳）。

    Firebase 新版 .firebasestorage.app bucket 的 CORS 透過 Admin SDK 設定可能不持久。
    這裡用 google-cloud-storage SDK 直接操作 GCS bucket，更可靠。
    """
    import json as _json
    import os
    import base64

    from google.cloud import storage
    from google.oauth2 import service_account

    from core.config import settings

    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "https://yiimui-admin.vercel.app",
        "https://paint-by-number-store.vercel.app",
    ]
    rules = [
        {
            "origin": ALLOWED_ORIGINS,
            "method": ["PUT", "GET", "HEAD", "OPTIONS", "POST"],
            "responseHeader": ["Content-Type", "Content-MD5", "x-goog-resumable"],
            "maxAgeSeconds": 3600,
        }
    ]

    # 取得 service account credentials（從 BASE64 env 解或從 FIREBASE_CREDENTIALS）
    b64 = os.environ.get("FIREBASE_CREDENTIALS_BASE64", "").strip()
    cred_json: dict | None = None
    if b64:
        cred_json = _json.loads(base64.b64decode(b64).decode("utf-8"))
    elif settings.firebase_credentials.strip():
        v = settings.firebase_credentials.strip()
        if v.startswith("{"):
            cred_json = _json.loads(v)
        else:
            with open(v, "r") as f:
                cred_json = _json.load(f)

    if not cred_json:
        return {"ok": False, "error": "No firebase credentials available"}

    credentials = service_account.Credentials.from_service_account_info(cred_json)
    storage_client = storage.Client(
        credentials=credentials,
        project=cred_json.get("project_id"),
    )

    bucket_name = settings.firebase_storage_bucket
    bucket = storage_client.bucket(bucket_name)
    bucket.reload()  # 確保不是 cached
    before = list(bucket.cors or [])
    bucket.cors = rules
    bucket.update()  # 用 update 而不是 patch
    bucket.reload()  # re-read 真實 GCS 狀態
    after = list(bucket.cors or [])

    # 也試試 legacy .appspot.com bucket 以防萬一
    legacy_name = bucket_name.replace(".firebasestorage.app", ".appspot.com")
    legacy_result = {"name": legacy_name, "tried": False}
    if legacy_name != bucket_name:
        try:
            legacy = storage_client.bucket(legacy_name)
            legacy.reload()
            legacy.cors = rules
            legacy.update()
            legacy.reload()
            legacy_result = {
                "name": legacy_name,
                "tried": True,
                "cors": list(legacy.cors or []),
            }
        except Exception as e:
            legacy_result = {"name": legacy_name, "tried": True, "error": str(e)}

    return {
        "ok": len(after) > 0,
        "primary_bucket": bucket_name,
        "before": before,
        "after": after,
        "legacy_bucket": legacy_result,
        "message": "CORS rules updated" if len(after) > 0 else "CORS update did not persist",
    }
