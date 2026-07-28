from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

json_type = JSON().with_variant(postgresql.JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # CHANNEL, DM, GROUP
    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    members: Mapped[List["ChatConversationMember"]] = relationship("ChatConversationMember", back_populates="conversation", cascade="all, delete-orphan")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatConversationMember(Base):
    __tablename__ = "chat_conversation_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="MEMBER", nullable=False)  # OWNER, MODERATOR, MEMBER, READ_ONLY
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_read_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notification_level: Mapped[str] = mapped_column(String(30), default="ALL", nullable=False)  # ALL, MENTIONS, MUTED
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    conversation: Mapped["ChatConversation"] = relationship("ChatConversation", back_populates="members")
    user: Mapped["User"] = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    parent_message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)  # TEXT, IMAGE, VIDEO, AUDIO, FILE, SYSTEM, MODULE_LINK
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_search: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ephemeral: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    visibility_mode: Mapped[str] = mapped_column(String(30), default="NORMAL", nullable=False)  # NORMAL, ONCE, TEMPORARY, AUDIT
    viewed_by_users: Mapped[Optional[List[int]]] = mapped_column(json_type, nullable=True, default=list)

    conversation: Mapped["ChatConversation"] = relationship("ChatConversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_user_id])
    versions: Mapped[List["ChatMessageVersion"]] = relationship("ChatMessageVersion", back_populates="message", cascade="all, delete-orphan")
    attachments: Mapped[List["ChatMessageAttachment"]] = relationship("ChatMessageAttachment", back_populates="message", cascade="all, delete-orphan")
    reactions: Mapped[List["ChatReaction"]] = relationship("ChatReaction", back_populates="message", cascade="all, delete-orphan")
    mentions: Mapped[List["ChatMention"]] = relationship("ChatMention", back_populates="message", cascade="all, delete-orphan")


class ChatMessageVersion(Base):
    __tablename__ = "chat_message_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    previous_body: Mapped[str] = mapped_column(Text, nullable=False)
    new_body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    edited_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="versions")
    editor: Mapped["User"] = relationship("User")


class ChatMessageAttachment(Base):
    __tablename__ = "chat_message_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True, nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(30), nullable=False)  # IMAGE, VIDEO, AUDIO, GIF, DOCUMENT, OTHER
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="attachments")
    file: Mapped["File"] = relationship("File")
    uploader: Mapped["User"] = relationship("User")


class ChatReaction(Base):
    __tablename__ = "chat_reactions"
    __table_args__ = (UniqueConstraint("message_id", "user_id", "emoji", name="uq_chat_message_user_reaction"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    emoji: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="reactions")
    user: Mapped["User"] = relationship("User")


class ChatMention(Base):
    __tablename__ = "chat_mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    mention_type: Mapped[str] = mapped_column(String(30), nullable=False)  # USER, CHANNEL, GROUP, MODULE, IT_TICKET, KANBAN_CARD, KANBAN_BOARD, APPROVAL, FILE, ASSET, CERTIFICATE
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_label: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="mentions")


class ChatPin(Base):
    __tablename__ = "chat_pins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    pinned_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChatReadReceipt(Base):
    __tablename__ = "chat_read_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChatNotificationSetting(Base):
    __tablename__ = "chat_notification_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True, nullable=True)
    global_level: Mapped[str] = mapped_column(String(30), default="ALL", nullable=False)  # ALL, MENTIONS, MUTED
    muted_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ChatActivity(Base):
    __tablename__ = "chat_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True, nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChatMessiasAudit(Base):
    __tablename__ = "chat_messias_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    messias_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_conversations.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChatConversationLink(Base):
    __tablename__ = "chat_conversation_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True, nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=True)
    module_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChatMessageDelete(Base):
    __tablename__ = "chat_message_deletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    message: Mapped["ChatMessage"] = relationship("ChatMessage")
    user: Mapped["User"] = relationship("User")
