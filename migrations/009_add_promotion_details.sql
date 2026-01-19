-- Добавление полей для детальной информации об акциях

-- Детальное описание акции
ALTER TABLE promotions ADD COLUMN IF NOT EXISTS detail_text TEXT;

-- Условия акции
ALTER TABLE promotions ADD COLUMN IF NOT EXISTS conditions TEXT;

-- URL для кнопки действия
ALTER TABLE promotions ADD COLUMN IF NOT EXISTS action_url TEXT;

-- Текст кнопки действия (по умолчанию "Записаться")
ALTER TABLE promotions ADD COLUMN IF NOT EXISTS action_text VARCHAR(100) DEFAULT 'Записаться';
