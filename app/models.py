from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    classifications: Mapped[list["Classification"]] = relationship(back_populates="message")


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    distortion_type: Mapped[str] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    message: Mapped["Message"] = relationship(back_populates="classifications")


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint: Mapped[str] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    latency_ms: Mapped[float] = mapped_column(nullable=False)
    input_tokens: Mapped[int] = mapped_column(nullable=False)
    output_tokens: Mapped[int] = mapped_column(nullable=False)
    cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
