import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Ticket, TicketMessage, TicketStatus, User

async def create_ticket(session: AsyncSession, user: User, subject='Support') -> Ticket:
    public_id = secrets.token_hex(3).upper()
    ticket = Ticket(public_id=public_id,user_id=user.id,subject=subject,status=TicketStatus.PENDING.value)
    session.add(ticket); await session.flush(); return ticket

async def add_message(session: AsyncSession, ticket_id: int, sender_type: str, sender_id: int, content: str, attachment_type=None, file_id=None):
    session.add(TicketMessage(ticket_id=ticket_id,sender_type=sender_type,sender_telegram_id=sender_id,content=content,attachment_type=attachment_type,attachment_file_id=file_id))
    await session.flush()

async def find_active_ticket(session: AsyncSession, user: User):
    return await session.scalar(select(Ticket).where(Ticket.user_id==user.id, Ticket.status.in_([TicketStatus.PENDING.value, TicketStatus.PROCESSING.value])).order_by(Ticket.created_at.desc()))

async def get_ticket_by_public(session: AsyncSession, public_id: str):
    return await session.scalar(select(Ticket).where(Ticket.public_id == public_id.upper()))
