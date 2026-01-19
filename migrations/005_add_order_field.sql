-- Добавление поля order для управления порядком отображения

-- Добавляем поле order в таблицу мастеров
ALTER TABLE masters ADD COLUMN IF NOT EXISTS "order" INTEGER DEFAULT 0;

-- Добавляем поле order в таблицу услуг
ALTER TABLE services ADD COLUMN IF NOT EXISTS "order" INTEGER DEFAULT 0;

-- Добавляем поле order в таблицу акций
ALTER TABLE promotions ADD COLUMN IF NOT EXISTS "order" INTEGER DEFAULT 0;

-- Устанавливаем начальные значения order на основе id (для существующих записей)
UPDATE masters SET "order" = id WHERE "order" = 0 OR "order" IS NULL;
UPDATE services SET "order" = id WHERE "order" = 0 OR "order" IS NULL;
UPDATE promotions SET "order" = id WHERE "order" = 0 OR "order" IS NULL;

-- Создаем индексы для быстрой сортировки
CREATE INDEX IF NOT EXISTS idx_masters_order ON masters("order");
CREATE INDEX IF NOT EXISTS idx_services_order ON services("order");
CREATE INDEX IF NOT EXISTS idx_promotions_order ON promotions("order");
