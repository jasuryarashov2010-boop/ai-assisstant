# GitHub architecture review used for this build

I reviewed 20 public repositories/projects as architectural references. No source code was copied into this project; patterns were reimplemented for this bot.

1. nishonow/aiogram-bot-template — admin tools, broadcasts, mandatory channels, action logs.
2. UznetDev/Aiogram-Bot-Template — admin permissions and channel management.
3. Er1one/telegram-bot-template — webhook/FastAPI, PostgreSQL, Redis, i18n, tests.
4. Abulqosim0227/Automation-for-businesses- — FastAPI + aiogram webhook + async SQLAlchemy + Redis + Alembic.
5. Erlaio/rag-telegram-bot — knowledge-base/RAG separation and LLM abstraction.
6. mkbeh/fastapi-admin-panel — FastAPI/PostgreSQL admin architecture.
7. MrConsoleka/aiogram-miniapp-template — modular routers, DI concepts, webhook/security patterns.
8. ilyarolf/AiogramShopBot — admin flows, referrals, localization and analytics patterns.
9. dvkonstantinov/aiogram-support-bot — support routing and anonymous operator model.
10. dvkonstantinov/aiogram-support-bot-postgres — PostgreSQL support persistence/reporting.
11. S1avv/aiogrammer — modular admin and anti-spam middleware.
12. arturboyun/AiogramBotTemplate — SQLAlchemy, Alembic, Redis, FastAPI, Ruff structure.
13. VeryBigSad/telegram-bot-template — webhook, Redis, i18n, logging.
14. andrew000/aiogram-template — SQLAlchemy/Alembic, Redis and localization.
15. wakaree/aiogram_bot_template — Flow/Interactor/Presenter separation and FastAPI webhook.
16. ulugby/aiogram3-bot-template — current aiogram patterns and HTML/custom-emoji usage.
17. NotBupyc/aiogram-bot-template — SQLAlchemy/Alembic and Redis configuration.
18. bodaue/aiogram_v3_template — aiogram 3 + SQLAlchemy 2 + Alembic + Redis.
19. netbriler/aiogram-peewee-template — rate limiting, webhook and deployment configuration ideas.
20. aiogram/bot — official project container/service composition reference.

Architecture adopted here:
- aiogram 3.x routers + middleware
- FastAPI webhook
- async SQLAlchemy 2.x + PostgreSQL
- Redis/Valkey for state, counters and cache only
- Alembic migrations
- modular services for AI/support/knowledge/usage
- Telegram-only role based admin foundation
- HTML-first presentation and hybrid reply/inline keyboards
