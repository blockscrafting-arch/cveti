-- Добавляем колонки для хранения деталей лояльности YClients
ALTER TABLE users ADD COLUMN IF NOT EXISTS loyalty_card_number TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS loyalty_status TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS loyalty_last_sync TIMESTAMPTZ;

-- Комментарии к колонкам
COMMENT ON COLUMN users.loyalty_card_number IS 'Номер карты лояльности из YClients';
COMMENT ON COLUMN users.loyalty_status IS 'Тип или статус карты лояльности (например, Бонусная карта)';
COMMENT ON COLUMN users.loyalty_last_sync IS 'Время последней успешной синхронизации с YClients';
