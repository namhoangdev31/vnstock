"""Các đối tượng truyền tải dữ liệu (DTO) dùng chung cho thông báo và xác thực token."""

from sqlmodel import Field, SQLModel

# =============================================================================
# REQUEST DTOs
# =============================================================================


class NewPassword(SQLModel):
    """Payload đặt lại mật khẩu mới thông qua mã token xác thực."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


# =============================================================================
# RESPONSE DTOs
# =============================================================================


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
