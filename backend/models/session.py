from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship

from models.user import User


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)

    # relationship backref
    user: User = Relationship(back_populates="sessions")
