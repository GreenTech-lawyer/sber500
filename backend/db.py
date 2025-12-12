from sqlmodel import SQLModel, create_engine, Session
from core.config import settings

# Using SQLALCHEMY_DATABASE_URI from settings
DATABASE_URL = str(settings.SQLALCHEMY_DATABASE_URI)
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    # import models to ensure they are registered before create_all
    import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

