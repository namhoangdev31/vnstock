from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.core.security import get_password_hash
from app.domains.identity.application import crud
from app.domains.identity.application.schemas import UserCreate
from app.domains.identity.domain.models import User

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 5, "prepare_threshold": None},
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
    else:
        user.hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
        session.add(user)
        session.commit()
