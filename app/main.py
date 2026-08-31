import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from app.config import get_settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.db.models import User, Plan
from app.bot.middlewares.auth import UserMiddleware
from app.bot.middlewares.subscription import SubscriptionMiddleware
from app.bot.handlers import start, user
from app.admin import handlers as admin
from app.services.usage import ensure_plans

settings=get_settings(); logging.basicConfig(level=getattr(logging,settings.log_level.upper(),'INFO'))

redis=Redis.from_url(settings.redis_url,decode_responses=False)
storage=RedisStorage(redis=redis)
bot=Bot(settings.bot_token,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher(storage=storage)

# Order matters: auth populates user/db before subscription checks.
dp.message.middleware(UserMiddleware()); dp.callback_query.middleware(UserMiddleware())
dp.message.middleware(SubscriptionMiddleware()); dp.callback_query.middleware(SubscriptionMiddleware())
dp.include_router(start.router); dp.include_router(user.router); dp.include_router(admin.router)

@asynccontextmanager
async def lifespan(app:FastAPI):
    async with SessionLocal() as s: await ensure_plans(s)
    if settings.webhook_url:
        await bot.set_webhook(f'{settings.webhook_url.rstrip("/")}{settings.webhook_path}',secret_token=settings.webhook_secret or None,drop_pending_updates=True)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
    yield
    await bot.session.close(); await redis.close(); await engine.dispose()

app=FastAPI(title='AI Yordamchi Bot',version='1.0.0',lifespan=lifespan)

@app.get('/health')
async def health():
    return {'ok':True,'service':'ai-assistant-bot'}

@app.post(settings.webhook_path)
async def webhook(request:Request):
    if settings.webhook_secret and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != settings.webhook_secret:
        raise HTTPException(status_code=403,detail='forbidden')
    data=await request.json(); from aiogram.types import Update
    await dp.feed_update(bot,Update.model_validate(data))
    return {'ok':True}

@app.get('/')
async def root(): return {'service':'AI Yordamchi Bot','status':'online'}
