from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.domains.identity.application import crud
from app.domains.identity.application.schemas import UserCreate
from app.domains.identity.domain.models import User

_engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

if not str(settings.DATABASE_URL).startswith("sqlite"):
    _engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "connect_args": {"connect_timeout": 5, "prepare_threshold": None},
        }
    )

engine = create_engine(
    str(settings.DATABASE_URL),
    **_engine_kwargs,
)


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        crud.create_user(session=session, user_create=user_in)
