from typing import Optional
from datetime import datetime
from uuid import uuid4, UUID

from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    password_hash: str = Field(nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # relationships
    sessions: list["Session"] = Relationship(
        back_populates="user"
    )
