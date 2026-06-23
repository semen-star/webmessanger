from datetime import datetime
from pydantic import BaseModel, field_validator


# ── AUTH ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username:     str
    password:     str
    display_name: str
    avatar:       str = "👤"

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Логин минимум 3 символа")
        if len(v) > 50:
            raise ValueError("Логин максимум 50 символов")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Логин: только буквы, цифры, _ и -")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Пароль минимум 6 символов")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── USER ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id:           int
    username:     str
    display_name: str
    avatar:       str
    bio:          str
    is_online:    bool
    created_at:   datetime

    model_config = {"from_attributes": True}


class UserShort(BaseModel):
    id:           int
    username:     str
    display_name: str
    avatar:       str
    is_online:    bool

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    avatar:       str | None = None
    bio:          str | None = None


# ── POSTS ─────────────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Текст поста не может быть пустым")
        return v


class PostOut(BaseModel):
    id:         int
    text:       str
    created_at: datetime
    author:     UserShort
    likes_count:    int = 0
    comments_count: int = 0
    liked_by_me:    bool = False

    model_config = {"from_attributes": True}


# ── COMMENTS ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    text: str


class CommentOut(BaseModel):
    id:         int
    text:       str
    created_at: datetime
    author:     UserShort

    model_config = {"from_attributes": True}


# ── MESSAGES ──────────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    text: str


class MessageOut(BaseModel):
    id:          int
    sender_id:   int
    receiver_id: int
    text:        str
    is_read:     bool
    created_at:  datetime

    model_config = {"from_attributes": True}


class DialogOut(BaseModel):
    """Последнее сообщение в диалоге + собеседник."""
    partner:        UserShort
    last_message:   MessageOut | None
    unread_count:   int


# ── FRIENDSHIP ────────────────────────────────────────────────────────────────

class FriendshipOut(BaseModel):
    id:          int
    requester:   UserShort
    addressee:   UserShort
    status:      str
    created_at:  datetime

    model_config = {"from_attributes": True}
