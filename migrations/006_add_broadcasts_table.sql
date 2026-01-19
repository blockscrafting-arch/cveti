-- Создание таблицы для рассылок

CREATE TABLE IF NOT EXISTS broadcasts (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    recipient_type TEXT NOT NULL DEFAULT 'all', -- 'all', 'selected', 'by_balance', 'by_date'
    recipient_ids JSONB DEFAULT '[]'::jsonb, -- массив ID пользователей для типа 'selected'
    filter_balance_min INTEGER, -- минимальный баланс для фильтра 'by_balance'
    filter_balance_max INTEGER, -- максимальный баланс для фильтра 'by_balance'
    filter_date_from TIMESTAMP, -- дата начала для фильтра 'by_date'
    filter_date_to TIMESTAMP, -- дата конца для фильтра 'by_date'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'sending', 'completed', 'failed'
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL -- tg_id администратора
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_broadcasts_status ON broadcasts(status);
CREATE INDEX IF NOT EXISTS idx_broadcasts_created_at ON broadcasts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_broadcasts_created_by ON broadcasts(created_by);
