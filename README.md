# AI Yordamchi Bot v4

Telegram ichida AI Chat'ni markazga qo‘yadigan modular bot: AI Chat, chat history, Voice, File Analysis, Vision, Image Generation, Study, Coding, Data Analysis, Tickets, Support, Plans, Referral va Admin AI Learning Lab.

## Eng muhim UX qoidalari
- Reply keyboard = global bo‘limlar.
- Inline keyboard = ayni ekranning amallari.
- Har bir inline ekranida Orqaga mavjud.
- Global navigation eski FSM holatini tozalaydi, shuning uchun Tariflar tugmasi Image prompt sifatida talqin qilinmaydi.
- AI javobi kelishidan oldin `⏳ AI o‘ylayapti…` ko‘rsatiladi.
- OpenAI xatosi foydalanuvchiga tushunarli ko‘rsatiladi va server logiga yoziladi.
- Uzoq AI javoblari Telegram limitiga mos bo‘laklarga bo‘linadi.

## AI
AI matn chatida OpenAI Responses API ishlatiladi, agar SDK'da u mavjud bo‘lmasa Chat Completions fallback qilinadi. `temperature` qattiq berilmagan, shuning uchun reasoning modellari bilan moslik yaxshiroq.

## Render
Runtime: Docker. Build/Start Command bo‘sh qoldiriladi; Dockerfile migration va Uvicorn'ni ishga tushiradi.

Environment Variables: `BOT_TOKEN`, `ADMIN_IDS`, `DATABASE_URL`, `REDIS_URL`, `WEBHOOK_URL`, `WEBHOOK_SECRET`, `OPENAI_API_KEY`.

`/health` endpoint `ai_configured` va `webhook_configured` holatini ham qaytaradi.

## GitHub architectural references
Arxitektura naqshlari ochiq GitHub loyihalaridagi aiogram router/middleware, webhook, PostgreSQL/Redis, i18n, support/ticket, RAG va admin panel yondashuvlarini qayta implementatsiya qilish orqali tanlangan; kod nusxalanmagan.
