from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class PlanCode(str, Enum):
    FREE='free'; PRO='pro'; COMFORT='comfort'
class TicketStatus(str, Enum):
    PENDING='pending'; PROCESSING='processing'; CLOSED='closed'; ESCALATED='escalated'
class Role(str, Enum):
    SUPER_ADMIN='super_admin'; ADMIN='admin'; OPERATOR='operator'; AI_MANAGER='ai_manager'; ANALYST='analyst'

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(primary_key=True)
    telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str|None]=mapped_column(String(64), index=True)
    full_name: Mapped[str]=mapped_column(String(255), default='')
    language: Mapped[str]=mapped_column(String(5), default='')
    plan_code: Mapped[str]=mapped_column(String(20), default=PlanCode.FREE.value, index=True)
    plan_expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    is_banned: Mapped[bool]=mapped_column(Boolean, default=False, index=True)
    referrals_count: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    last_active_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Plan(Base):
    __tablename__='plans'
    id: Mapped[int]=mapped_column(primary_key=True)
    code: Mapped[str]=mapped_column(String(20), unique=True, index=True)
    name_uz: Mapped[str]=mapped_column(String(80))
    name_en: Mapped[str]=mapped_column(String(80))
    name_ru: Mapped[str]=mapped_column(String(80))
    daily_ai_limit: Mapped[int]=mapped_column(Integer)
    daily_ticket_limit: Mapped[int]=mapped_column(Integer)
    image_enabled: Mapped[bool]=mapped_column(Boolean, default=False)
    voice_enabled: Mapped[bool]=mapped_column(Boolean, default=False)
    file_enabled: Mapped[bool]=mapped_column(Boolean, default=False)
    price_monthly: Mapped[int]=mapped_column(Integer, default=0)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)

class Channel(Base):
    __tablename__='channels'
    id: Mapped[int]=mapped_column(primary_key=True)
    chat_id: Mapped[int]=mapped_column(BigInteger, unique=True)
    title: Mapped[str]=mapped_column(String(255))
    invite_url: Mapped[str]=mapped_column(String(500))
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)

class Operator(Base):
    __tablename__='operators'
    id: Mapped[int]=mapped_column(primary_key=True)
    telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True)
    role: Mapped[str]=mapped_column(String(30), default=Role.OPERATOR.value)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)

class Ticket(Base):
    __tablename__='tickets'
    id: Mapped[int]=mapped_column(primary_key=True)
    public_id: Mapped[str]=mapped_column(String(16), unique=True, index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'), index=True)
    operator_id: Mapped[int|None]=mapped_column(ForeignKey('operators.id'), nullable=True)
    subject: Mapped[str]=mapped_column(String(255), default='AI/Support')
    status: Mapped[str]=mapped_column(String(20), default=TicketStatus.PENDING.value, index=True)
    priority: Mapped[str]=mapped_column(String(20), default='normal')
    ai_summary: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class TicketMessage(Base):
    __tablename__='ticket_messages'
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey('tickets.id', ondelete='CASCADE'), index=True)
    sender_type: Mapped[str]=mapped_column(String(20))
    sender_telegram_id: Mapped[int|None]=mapped_column(BigInteger)
    content: Mapped[str]=mapped_column(Text)
    attachment_type: Mapped[str|None]=mapped_column(String(30))
    attachment_file_id: Mapped[str|None]=mapped_column(String(255))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Rating(Base):
    __tablename__='ratings'
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[int]=mapped_column(ForeignKey('tickets.id', ondelete='CASCADE'), unique=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    score: Mapped[int]=mapped_column(Integer)
    comment: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Feedback(Base):
    __tablename__='feedback'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    text: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class AIConversation(Base):
    __tablename__='ai_conversations'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str]=mapped_column(String(255), default='New chat')
    is_closed: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class AIMessage(Base):
    __tablename__='ai_messages'
    id: Mapped[int]=mapped_column(primary_key=True)
    conversation_id: Mapped[int]=mapped_column(ForeignKey('ai_conversations.id', ondelete='CASCADE'), index=True)
    role: Mapped[str]=mapped_column(String(20))
    content: Mapped[str]=mapped_column(Text)
    model: Mapped[str|None]=mapped_column(String(100))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class UsageDaily(Base):
    __tablename__='usage_daily'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    day: Mapped[str]=mapped_column(String(10), index=True)
    ai_requests: Mapped[int]=mapped_column(Integer, default=0)
    tickets_created: Mapped[int]=mapped_column(Integer, default=0)
    __table_args__=(UniqueConstraint('user_id','day',name='uq_usage_user_day'),)

class Referral(Base):
    __tablename__='referrals'
    id: Mapped[int]=mapped_column(primary_key=True)
    inviter_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    invited_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    source: Mapped[str]=mapped_column(String(100), default='deep_link')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    __table_args__=(UniqueConstraint('inviter_id','invited_id',name='uq_referral_pair'),)

class KnowledgeItem(Base):
    __tablename__='knowledge_items'
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(255))
    content: Mapped[str]=mapped_column(Text)
    tags: Mapped[list]=mapped_column(JSON, default=list)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class LearningItem(Base):
    __tablename__='learning_items'
    id: Mapped[int]=mapped_column(primary_key=True)
    kind: Mapped[str]=mapped_column(String(40))
    title: Mapped[str]=mapped_column(String(255))
    prompt: Mapped[str]=mapped_column(Text)
    tags: Mapped[list]=mapped_column(JSON, default=list)
    content: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Broadcast(Base):
    __tablename__='broadcasts'
    id: Mapped[int]=mapped_column(primary_key=True)
    target_type: Mapped[str]=mapped_column(String(30))
    target_value: Mapped[str|None]=mapped_column(String(255))
    message_text: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20), default='draft')
    sent_count: Mapped[int]=mapped_column(Integer, default=0)
    failed_count: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class AuditLog(Base):
    __tablename__='audit_logs'
    id: Mapped[int]=mapped_column(primary_key=True)
    admin_id: Mapped[int]=mapped_column(BigInteger)
    action: Mapped[str]=mapped_column(String(100), index=True)
    target_type: Mapped[str|None]=mapped_column(String(50))
    target_id: Mapped[str|None]=mapped_column(String(100))
    payload: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
