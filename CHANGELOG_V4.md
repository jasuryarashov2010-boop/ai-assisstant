# v4 — AI-first navigation rebuild

## Fixed
- AI Chat no longer depends on a stale/global conversation; every active chat has an explicit conversation_id in FSM.
- OpenAI calls now use Responses API when available and fall back to Chat Completions without forcing temperature.
- AI errors are caught per-request and written to server logs instead of silently killing the Telegram update.
- AI requests show a waiting state and only consume quota after a successful AI response.
- Long AI replies are split for Telegram message limits.
- Main reply-keyboard navigation clears every feature FSM before routing, preventing Tariflar/Support/Profile buttons from being interpreted as Image/Ticket/Voice input.
- Every important inline screen has an explicit Back button.
- Added chat history and reopen/continue flow.
- Ticket flow now has explicit open/continue/close navigation.
- Home/profile/plan screens share one consistent visual hierarchy.
- `/health` reports whether AI and webhook configuration are present.

## Design approach
Telegram bot messages cannot use arbitrary CSS colors. The UI therefore uses colored emoji, blockquotes, strong headings, spoiler status chips, compact inline keyboards, and a persistent reply keyboard.

## Reference review
Architecture was informed by public GitHub projects covering aiogram routers/middleware, PostgreSQL/Redis, webhook/FastAPI, i18n, support bots, broadcast/admin tools, RAG, and Mini App/Dishka patterns. No repository code was copied into this project.
