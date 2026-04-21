from fastapi import APIRouter, Depends

from dependencies.auth import require_admin
from production import service
from production.schemas.request import UploadProductionImageRequest
from production.schemas.response import UploadUrlResponse

router = APIRouter(tags=["Upload"])


@router.post("/upload/production-image", response_model=UploadUrlResponse)
async def upload_production_image(
    body: UploadProductionImageRequest,
    operator=Depends(require_admin),
):
    return service.generate_upload_signed_url(body.filename, body.content_type)
