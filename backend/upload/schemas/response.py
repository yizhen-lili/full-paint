from datetime import datetime

from pydantic import BaseModel


class PublicUploadResponse(BaseModel):
    upload_url: str
    public_url: str
    expires_at: datetime


class PrivateUploadResponse(BaseModel):
    upload_url: str
    firebase_path: str
    expires_at: datetime
