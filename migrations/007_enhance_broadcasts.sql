-- Улучшение таблицы рассылок: добавление изображений и отложенной отправки

-- Добавляем поле для URL изображения
ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS image_url TEXT;

-- Добавляем поле для запланированной даты/времени отправки
ALTER TABLE broadcasts ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP;

-- Добавляем индекс для быстрого поиска запланированных рассылок
CREATE INDEX IF NOT EXISTS idx_broadcasts_scheduled_at ON broadcasts(scheduled_at) WHERE scheduled_at IS NOT NULL;

-- Обновляем возможные статусы (добавляем 'scheduled')
-- Примечание: В PostgreSQL нет ENUM для status, поэтому просто документируем:
-- Статусы: 'pending', 'scheduled', 'sending', 'completed', 'failed'
