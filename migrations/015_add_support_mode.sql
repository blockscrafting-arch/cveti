ALTER TABLE users
ADD COLUMN IF NOT EXISTS support_mode BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN users.support_mode IS 'Пользователь ожидает ответа поддержки в боте';
