# Build verification

- Python source and Alembic files: `compileall` passed.
- Project contains modular bot/admin/database/service layers and migration.
- Full dependency installation/runtime integration test could not be executed in this sandbox because outbound package downloads are blocked. Deploy/CI should perform the real dependency install and Telegram/OpenAI integration smoke tests.

## First production-hardening targets
1. Add DB-backed operator RBAC checks for every operator action.
2. Add queue/worker for long broadcasts and file/image processing.
3. Add pgvector/RAG indexing instead of keyword retrieval when the Knowledge Base grows.
4. Add plan expiry scheduler and automatic downgrade to Free.
5. Add proper segment broadcast builder and persistent message templates.
