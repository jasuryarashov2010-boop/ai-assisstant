from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.db.models import Plan, UsageDaily, User

settings = get_settings()

async def get_or_create_usage(session: AsyncSession, user_id: int) -> UsageDaily:
    day = datetime.now(timezone.utc).date().isoformat()
    row = await session.scalar(select(UsageDaily).where(UsageDaily.user_id == user_id, UsageDaily.day == day))
    if row: return row
    row = UsageDaily(user_id=user_id, day=day)
    session.add(row); await session.flush(); return row

async def get_plan(session: AsyncSession, code: str) -> Plan:
    plan = await session.scalar(select(Plan).where(Plan.code == code))
    if plan: return plan
    defaults = {
        'free': ('🆓 Free','Free','Free',settings.default_free_daily_ai,3,False,True,False,0),
        'pro': ('⭐ Pro','Pro','Pro',settings.default_pro_daily_ai,15,True,True,True,49000),
        'comfort': ('💎 Comfort','Comfort','Comfort',settings.default_comfort_daily_ai,30,True,True,True,99000),
    }
    n = defaults[code]
    plan = Plan(code=code,name_uz=n[0],name_en=n[1],name_ru=n[2],daily_ai_limit=n[3],daily_ticket_limit=n[4],image_enabled=n[5],voice_enabled=n[6],file_enabled=n[7],price_monthly=n[8])
    session.add(plan); await session.flush(); return plan

async def ensure_plans(session: AsyncSession):
    for code in ('free','pro','comfort'): await get_plan(session, code)
    await session.commit()

async def effective_plan(session: AsyncSession, user: User) -> Plan:
    code = user.plan_code if user.plan_code in ('free','pro','comfort') else 'free'
    if code != 'free' and user.plan_expires_at is not None and user.plan_expires_at <= datetime.now(timezone.utc):
        user.plan_code = 'free'
        user.plan_expires_at = None
        await session.flush()
        code = 'free'
    return await get_plan(session, code)

async def ai_allowed(session: AsyncSession, user: User) -> tuple[bool,int,int]:
    plan = await effective_plan(session, user)
    usage = await get_or_create_usage(session, user.id)
    remaining = max(0, plan.daily_ai_limit - usage.ai_requests)
    return remaining > 0, remaining, plan.daily_ai_limit

async def consume_ai(session: AsyncSession, user: User) -> bool:
    allowed,_,_=await ai_allowed(session,user)
    if not allowed: return False
    usage=await get_or_create_usage(session,user.id); usage.ai_requests += 1
    await session.commit(); return True

async def ticket_allowed(session: AsyncSession, user: User) -> bool:
    plan = await effective_plan(session, user)
    usage = await get_or_create_usage(session, user.id)
    return usage.tickets_created < plan.daily_ticket_limit

async def consume_ticket(session: AsyncSession, user: User) -> None:
    usage = await get_or_create_usage(session, user.id)
    usage.tickets_created += 1
    await session.commit()
