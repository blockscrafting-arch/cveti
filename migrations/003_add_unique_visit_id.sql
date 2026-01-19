-- Добавляем UNIQUE constraint на visit_id для предотвращения дубликатов платежей
-- Это критично для защиты от race condition при одновременных вебхуках

ALTER TABLE loyalty_transactions 
ADD CONSTRAINT unique_visit_id UNIQUE (visit_id);

-- Добавляем индекс для быстрого поиска по visit_id
CREATE INDEX IF NOT EXISTS idx_transactions_visit_id ON loyalty_transactions(visit_id);
