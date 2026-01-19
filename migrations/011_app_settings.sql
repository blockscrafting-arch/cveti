-- Миграция 011: Таблица настроек приложения для управления через админку
-- Все настройки лояльности и приветственных бонусов хранятся здесь

-- Создаем таблицу настроек
CREATE TABLE IF NOT EXISTS app_settings (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'string', -- 'string', 'number', 'float', 'boolean'
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_settings_key ON app_settings(key);

-- Вставляем дефолтные настройки (значения из текущего config.py)
INSERT INTO app_settings (key, value, type, description) VALUES
    ('loyalty_percentage', '0.05', 'float', 'Процент кэшбека с каждой оплаты (0.05 = 5%)'),
    ('loyalty_max_spend_percentage', '0.3', 'float', 'Максимальный процент от суммы чека, который можно оплатить баллами (0.3 = 30%)'),
    ('loyalty_expiration_days', '90', 'number', 'Срок жизни баллов в днях (90 = 3 месяца)'),
    ('welcome_bonus_amount', '0', 'number', 'Количество приветственных баллов для новых пользователей (0 = отключено)')
ON CONFLICT (key) DO NOTHING;

-- Функция для получения значения настройки с дефолтом
CREATE OR REPLACE FUNCTION get_setting(p_key VARCHAR, p_default_value TEXT DEFAULT NULL)
RETURNS TEXT AS $$
DECLARE
    v_value TEXT;
BEGIN
    SELECT value INTO v_value
    FROM app_settings
    WHERE key = p_key;
    
    RETURN COALESCE(v_value, p_default_value);
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления настройки
CREATE OR REPLACE FUNCTION update_setting(p_key VARCHAR, p_value TEXT, p_type VARCHAR DEFAULT 'string')
RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO app_settings (key, value, type, updated_at)
    VALUES (p_key, p_value, p_type, NOW())
    ON CONFLICT (key) 
    DO UPDATE SET 
        value = EXCLUDED.value,
        type = COALESCE(EXCLUDED.type, app_settings.type),
        updated_at = NOW();
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Комментарии для документации
COMMENT ON TABLE app_settings IS 'Динамические настройки приложения, управляемые через админ-панель';
COMMENT ON FUNCTION get_setting(VARCHAR, TEXT) IS 'Получает значение настройки по ключу с опциональным дефолтом';
COMMENT ON FUNCTION update_setting(VARCHAR, TEXT, VARCHAR) IS 'Обновляет или создает настройку';
