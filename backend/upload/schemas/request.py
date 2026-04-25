from typing import Literal

from pydantic import BaseModel


class UploadImageRequest(BaseModel):
    filename: str
    content_type: Literal["image/jpeg", "image/png"]
