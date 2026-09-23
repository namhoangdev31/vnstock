"""Identity & Access Management — application layer (use cases, DTOs)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.domains.identity.domain.models import ItemBase, UserBase

# =============================================================================
# REQUEST DTOs
# =============================================================================


class UserCreate(UserBase):
    """Payload tạo mới người dùng có mật khẩu."""

    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    """Payload đăng ký tài khoản mới từ giao diện người dùng."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(SQLModel):
    """Payload cập nhật thông tin người dùng (tất cả các trường đều là tùy chọn)."""

    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    """Payload người dùng tự cập nhật thông tin cá nhân."""

    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    """Payload đổi mật khẩu khi đang đăng nhập."""

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class NewPassword(SQLModel):
    """Payload đặt lại mật khẩu mới thông qua mã token xác thực."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ItemCreate(ItemBase):
    """Payload tạo mới vật phẩm."""

    pass


class ItemUpdate(SQLModel):
    """Payload cập nhật vật phẩm."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# =============================================================================
# RESPONSE DTOs
# =============================================================================


class UserPublic(UserBase):
    """Thông tin tài khoản người dùng công khai trả về cho API."""

    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    """Danh sách người dùng và tổng số lượng."""

    data: list[UserPublic]
    count: int


class ItemPublic(ItemBase):
    """Thông tin vật phẩm công khai trả về cho API."""

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    """Danh sách vật phẩm và tổng số lượng."""

    data: list[ItemPublic]
    count: int


class Message(SQLModel):
    """Thông báo phản hồi đơn giản."""

    message: str


class Token(SQLModel):
    """Payload JSON chứa chuỗi JWT access token và kiểu xác thực."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    """Nội dung định danh giải mã được từ JWT token."""

    sub: str | None = None
