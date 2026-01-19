-- Удаление поля rating из таблицы masters
-- Если колонка существует, она будет удалена

ALTER TABLE masters DROP COLUMN IF EXISTS rating;
