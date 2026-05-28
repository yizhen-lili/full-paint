from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class BatchDeleteBatchesRequest(BaseModel):
    """批次硬刪除列印批次 — 一次最多 50 筆。

    每個 id 獨立執行（沿用單筆 delete 的所有檢查），失敗筆不影響其他筆。
    被 order_item 引用永遠拒絕（金流稽核紅線；無 cascade 繞過選項）。
    """
    batch_ids: list[UUID] = Field(min_length=1, max_length=50)

    @field_validator("batch_ids")
    @classmethod
    def unique_ids(cls, v: list[UUID]) -> list[UUID]:
        if len(set(v)) != len(v):
            raise ValueError("batch_ids 內含重複值")
        return v


class PrintItemSpec(BaseModel):
    production_job_id: UUID
    quantity: int = Field(ge=1, le=1000)
    source_type: Literal["order_item", "standalone"] = "standalone"
    source_order_item_id: UUID | None = None

    @model_validator(mode="after")
    def _check_source_consistency(self):
        if self.source_type == "order_item" and self.source_order_item_id is None:
            raise ValueError("source_type=order_item 時 source_order_item_id 必填")
        if self.source_type == "standalone" and self.source_order_item_id is not None:
            raise ValueError("source_type=standalone 時 source_order_item_id 必須為 null")
        return self


class PreviewRequest(BaseModel):
    required: list[PrintItemSpec]
    candidates: list[PrintItemSpec] | None = None

    @field_validator("required")
    @classmethod
    def required_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("required 不可為空")
        return v


class CreateBatchRequest(BaseModel):
    required: list[PrintItemSpec]
    candidates: list[PrintItemSpec] | None = None
    admin_notes: str | None = None

    @field_validator("required")
    @classmethod
    def required_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("required 不可為空")
        return v
