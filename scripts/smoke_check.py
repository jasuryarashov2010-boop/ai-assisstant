from app.config import get_settings

s = get_settings()
assert s.webhook_path.startswith('/')
assert s.sqlalchemy_database_url.endswith('')
print('config-ok')
