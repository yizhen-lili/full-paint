from pydantic import BaseModel


class PublicUploadResponse(BaseModel):
    upload_url: str
    public_url: str


class PrivateUploadResponse(BaseModel):
    upload_url: str
    firebase_path: str
