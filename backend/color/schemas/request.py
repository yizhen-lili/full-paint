from pydantic import BaseModel, field_validator


class CreateColorRequest(BaseModel):
    code: str
    name: str
    color_family: str | None = None
    brand: str | None = None
    rgb: list[int]

    @field_validator("rgb")
    @classmethod
    def validate_rgb(cls, v: list[int]) -> list[int]:
        if len(v) != 3:
            raise ValueError("rgb 必須為 3 個元素的陣列 [R, G, B]")
        if not all(0 <= c <= 255 for c in v):
            raise ValueError("RGB 各值必須在 0 ~ 255 之間")
        return v
    stock_ml: float = 0.0

    @field_validator("code", "name")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("不可為空白字串")
        return v

    @field_validator("stock_ml")
    @classmethod
    def validate_stock(cls, v: float) -> float:
        if v < 0:
            raise ValueError("stock_ml 不可為負數")
        return v


class UpdateColorRequest(CreateColorRequest):
    pass


class AddStockRequest(BaseModel):
    add_ml: float

    @field_validator("add_ml")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("add_ml 必須大於 0")
        return v
