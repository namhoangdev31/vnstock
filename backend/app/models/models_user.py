"""Module tương thích ngược cho các mô hình người dùng.

Chuyển tiếp tới:
- Entities: app.models.entities.user
- DTOs: app.models.dto.user, app.models.dto.common
"""

from app.models.base import get_datetime_utc
from app.models.dto.common import Message, NewPassword, Token, TokenPayload
from app.models.dto.user import (
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.models.entities.user import (
    Item,
    ItemBase,
    User,
    UserBase,
)

__all__ = [
    "Item",
    "ItemBase",
    "ItemCreate",
    "ItemPublic",
    "ItemUpdate",
    "ItemsPublic",
    "Message",
    "NewPassword",
    "Token",
    "TokenPayload",
    "UpdatePassword",
    "User",
    "UserBase",
    "UserCreate",
    "UserPublic",
    "UserRegister",
    "UserUpdate",
    "UserUpdateMe",
    "UsersPublic",
    "get_datetime_utc",
]
