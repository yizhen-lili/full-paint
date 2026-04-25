from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from product.models import ProductStatusEnum


class SeriesResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    product_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SeriesListResponse(BaseModel):
    items: list[SeriesResponse]


class TagResponse(BaseModel):
    id: UUID
    name: str
    product_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    items: list[TagResponse]


class TagBriefResponse(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ProductImageResponse(BaseModel):
    id: UUID
    image_url: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductImageListResponse(BaseModel):
    items: list[ProductImageResponse]


class VariantJobSpecResponse(BaseModel):
    detail: str
    difficulty: str
    canvas_w_cm: float
    canvas_h_cm: float
    num_colors_used: int | None


class VariantResponse(BaseModel):
    id: UUID
    product_id: UUID
    production_job_id: UUID
    price: Decimal
    price_formula_base: Decimal
    is_active: bool
    created_at: datetime
    job_spec: VariantJobSpecResponse

    model_config = {"from_attributes": True}


class ProductBriefResponse(BaseModel):
    id: UUID
    title: str
    status: ProductStatusEnum
    cover_image_url: str
    variant_count: int
    tags: list[TagBriefResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductBriefResponse]
    total: int
    page: int
    page_size: int


class ProductDetailResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    cover_image_url: str
    series_id: UUID | None
    series_order: int | None
    status: ProductStatusEnum
    tags: list[TagBriefResponse]
    images: list[ProductImageResponse]
    variants: list[VariantResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AvailableJobResponse(BaseModel):
    id: UUID
    detail: str
    difficulty: str
    canvas_w_cm: float
    canvas_h_cm: float
    num_colors_used: int
    price_formula_base: Decimal

    model_config = {"from_attributes": True}


class AvailableJobListResponse(BaseModel):
    items: list[AvailableJobResponse]
