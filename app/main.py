from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, HTTPException, Request
from redis.asyncio import Redis

from app.admin import handlers as admin
from app.bot.handlers import start, user
from app.bot.middlewares.auth import UserMiddleware
from app.bot.middlewares.subscription import SubscriptionMiddleware
from app.config import get_settings
from app.db.models import Plan
from app.db.session import SessionLocal, engine
from app.services.usage import ensure_plans

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("app.main")

redis = Redis.from_url(settings.redis_url, decode_responses=False)
storage = RedisStorage(redis=redis)
bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# Auth must run before subscription checks so both the user and language are known.
dp.message.middleware(UserMiddleware())
dp.callback_query.middleware(UserMiddleware())
dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

# Navigation router first. It clears stale FSM state before feature routers see the update.
dp.include_router(start.router)
dp.include_router(user.router)
dp.include_router(admin.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await ensure_plans(session)
    webhook = f"{settings.webhook_url.rstrip('/')}{settings.webhook_path}" if settings.webhook_url else ""
    if webhook:
        await bot.set_webhook(webhook, secret_token=settings.webhook_secret or None, drop_pending_updates=True)
        log.info("Telegram webhook set: %s", webhook)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        log.warning("WEBHOOK_URL is empty; webhook mode is disabled")
    yield
    await bot.session.close()
    await redis.close()
    await engine.dispose()


app = FastAPI(title="AI Yordamchi Bot", version="2.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True, "service": "ai-assistant-bot", "ai_configured": bool(settings.openai_api_key), "webhook_configured": bool(settings.webhook_url)}


@app.get("/")
async def root():
    return {"service": "AI Yordamchi Bot", "status": "online"}


@app.post(settings.webhook_path)
async def webhook(request: Request):
    if settings.webhook_secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        from aiogram.types import Update
        payload = await request.json()
        await dp.feed_update(bot, Update.model_validate(payload))
    except Exception:
        # Return 200 to Telegram after logging. Handler-level errors already send a friendly message where possible.
        log.exception("Telegram update processing failed")
    return {"ok": True}
