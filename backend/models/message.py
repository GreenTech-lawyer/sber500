from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, Dict, Any

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # user_id stored as string to decouple from internal users table
    user_id: str = Field(index=True, nullable=False)
    correlation_id: Optional[str] = Field(default=None, index=True)
    direction: str = Field(nullable=False)  # 'user' | 'bot'
    text: Optional[str] = Field(default=None)
    payload: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON), default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
