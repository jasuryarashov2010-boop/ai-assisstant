# AI Yordamchi Telegram Bot

Modular Telegram AI + Support + Ticket + Plans + Referral + Admin CRM bot.

## Stack
- Python 3.13
- aiogram 3.31
- FastAPI webhook
- PostgreSQL + async SQLAlchemy
- Redis/Valkey for FSM, rate limiting and cache
- Alembic migrations
- OpenAI provider adapter

## Main features
- Mandatory channel subscription
- UZ/EN/RU language selection
- HTML-styled colored UX with reply + inline buttons
- AI chat, voice transcription, file intake, image generation
- Conversation history and tickets
- Support tickets, ratings, feedback
- Free / Pro / Comfort plans with daily quotas
- Referral/deep-link tracking
- Admin dashboard, user management, plans, channels, tickets, operators, RBAC
- Broadcast by all / segment / Telegram ID
- AI Knowledge Base management
- AI Learning Lab: prompts, coding/library lessons and ready-to-post channel content
- Audit logs and rate limiting

## Run locally
1. Copy `.env.example` to `.env`.
2. Fill PostgreSQL, Redis, Telegram and OpenAI credentials.
3. Install packages: `pip install -r requirements.txt`
4. Run migrations: `alembic upgrade head`
5. Start: `uvicorn app.main:app --reload`

For local Telegram webhook testing use a public HTTPS tunnel or polling adapter.

## Render
The service binds to `0.0.0.0:${PORT}` and exposes `/health`. Render documents that web services must bind to `0.0.0.0` and can use HTTP health checks. Keep secrets in Render environment variables, not in Git. The included `render.yaml` is a starting point.

Important: Render's free Postgres has an expiration/lifecycle limitation, so it should not be treated as permanent production storage. Use a durable paid/external Postgres before going live.

## Important implementation notes
The project is an executable foundation rather than a claim of a fully production-certified system. AI, Telegram and datastore credentials are intentionally external. The included Build Notes records what was verified in the sandbox.

Telegram's normal Bot API HTML is used for visual hierarchy (bold, blockquote, code, spoiler, emoji). Telegram messages do not provide arbitrary CSS text-color styling in bot messages.
