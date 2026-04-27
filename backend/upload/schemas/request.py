from typing import Literal

from pydantic import BaseModel, Field


class UploadImageRequest(BaseModel):
    filename: str
    content_type: Literal["image/jpeg", "image/png"]
    size: int = Field(gt=0, le=20_000_000, description="檔案位元組大小，上限 20MB")
