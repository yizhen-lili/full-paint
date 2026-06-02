from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from product.models import ProductStatusEnum


class ThemeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None
    cover_image_url: str | None = None
    sort_order: int = Field(default=0, ge=0)


class ThemeUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None
    cover_image_url: str | None = None
    sort_order: int = Field(default=0, ge=0)


class SeriesCreateRequest(BaseModel):
    name: str
    description: str | None = None
    theme_id: UUID | None = None
    is_featured: bool = False
    sample_cover_image_url: str | None = None


class SeriesUpdateRequest(BaseModel):
    name: str
    description: str | None = None
    theme_id: UUID | None = None
    is_featured: bool = False
    sample_cover_image_url: str | None = None


class TagCreateRequest(BaseModel):
    name: str


class TagUpdateRequest(BaseModel):
    name: str


class ProductCreateRequest(BaseModel):
    title: str
    description: str | None = None
    cover_image_url: str
    series_id: UUID | None = None
    series_order: int | None = None
    status: ProductStatusEnum = ProductStatusEnum.draft
    is_featured: bool = False
    tag_ids: list[UUID] = []


class ProductUpdateRequest(BaseModel):
    title: str
    description: str | None = None
    cover_image_url: str
    series_id: UUID | None = None
    series_order: int | None = None
    status: ProductStatusEnum
    is_featured: bool = False
    tag_ids: list[UUID] = []


class ProductImageCreateRequest(BaseModel):
    image_url: str
    sort_order: int = 0


class ImageReorderRequest(BaseModel):
    order: list[UUID]

    @field_validator("order")
    @classmethod
    def order_not_empty(cls, v: list[UUID]) -> list[UUID]:
        if not v:
            raise ValueError("order 不可為空")
        return v


class HomepageOrderRequest(BaseModel):
    """首頁置頂商品拖曳排序。

    後端會 atomic 清空所有 homepage_order，再依此 list 順序賦值 1..N。
    - 空陣列 = 全部清空
    - 上限 12 筆（業務規則，超過 400）
    - 每個 id 必須是現存 product 且 status='on_sale'（draft/off_sale 400）
    - 不能重複（400）
    """
    product_ids: list[UUID] = Field(default_factory=list, max_length=12)

    @field_validator("product_ids")
    @classmethod
    def no_duplicates(cls, v: list[UUID]) -> list[UUID]:
        if len(v) != len(set(v)):
            raise ValueError("product_ids 不可重複")
        return v


class VariantCreateRequest(BaseModel):
    production_job_id: UUID
    price: float

    @field_validator("price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("售價必須大於 0")
        return v


class VariantUpdateRequest(BaseModel):
    price: float | None = None
    is_active: bool | None = None

    @field_validator("price")
    @classmethod
    def price_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("售價必須大於 0")
        return v
