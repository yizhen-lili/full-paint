from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from admin import service
from admin.schemas.request import AdminUpdateUserRequest
from admin.schemas.response import AdminUserListResponse, AdminUserResponse
from core.database import get_db
from dependencies.auth import require_admin

router = APIRouter(tags=["Admin - Users"])


@router.get("/admin/users", response_model=AdminUserListResponse)
async def list_users(
    search: str | None = Query(default=None),
    role: Literal["admin", "customer"] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    operator=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    users, total = await service.list_users(db, search, role, is_active, page, page_size)
    return AdminUserListResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
    )



@router.get("/admin/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    operator=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user(db, user_id)


@router.patch("/admin/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    body: AdminUpdateUserRequest,
    operator=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    return await service.update_user(db, operator, user_id, fields)
