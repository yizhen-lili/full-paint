import logging
import uuid

from fastapi import APIRouter, Depends

from dependencies.auth import require_admin, require_auth
from production import service as production_service
from production.schemas.request import UploadProductionImageRequest
from production.schemas.response import UploadUrlResponse
from upload.schemas.request import UploadImageRequest
from upload.schemas.response import PrivateUploadResponse, PublicUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])


def _stub_public_pair(prefix: str, filename: str) -> dict:
    """Generate stub upload + public URLs. Replace with real Firebase Admin SDK later."""
    logger.warning(
        "Upload endpoint is STUB — replace with Firebase Admin SDK signed URLs"
    )
    token = uuid.uuid4().hex[:12]
    safe_name = filename.replace("/", "_")
    return {
        "upload_url": f"https://stub.firebase/upload/{prefix}/{token}/{safe_name}?token=mock",
        "public_url": f"https://stub.firebase/public/{prefix}/{token}/{safe_name}",
    }


def _stub_private_pair(prefix: str, filename: str) -> dict:
    logger.warning(
        "Private upload endpoint is STUB — replace with Firebase Admin SDK signed URLs"
    )
    token = uuid.uuid4().hex[:12]
    safe_name = filename.replace("/", "_")
    return {
        "upload_url": f"https://stub.firebase/upload/{prefix}/{token}/{safe_name}?token=mock",
        "firebase_path": f"{prefix}/{token}/{safe_name}",
    }


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
    return _stub_public_pair("product_images", body.filename)


@router.post("/upload/case-image", response_model=PublicUploadResponse)
async def upload_case_image(
    body: UploadImageRequest,
    _=Depends(require_admin),
):
    return _stub_public_pair("case_images", body.filename)


@router.post("/upload/custom-photo", response_model=PrivateUploadResponse)
async def upload_custom_photo(
    body: UploadImageRequest,
    _=Depends(require_auth),
):
    return _stub_private_pair("custom_photos", body.filename)
