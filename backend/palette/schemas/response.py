from uuid import UUID

from pydantic import BaseModel


class PhysicalColorBriefResponse(BaseModel):
    id: UUID
    code: str
    name: str
    rgb: list[int]
    stock_ml: float


class PaletteMappingResponse(BaseModel):
    template_id: int
    algorithm_rgb: list[int]
    physical_color: PhysicalColorBriefResponse | None
    required_ml: float | None
    mapped_by: str


class PaletteMappingListResponse(BaseModel):
    mappings: list[PaletteMappingResponse]


class ShortageColorItem(BaseModel):
    template_id: int
    physical_color_id: UUID
    code: str
    name: str


class CompleteResponse(BaseModel):
    all_stocked: bool
    shortage_colors: list[ShortageColorItem]
