-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    yclients_id INT,
    name VARCHAR(100),
    balance INT DEFAULT 0,
    level VARCHAR(20) DEFAULT 'new', -- 'new', 'regular', 'vip'
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);

-- Таблица транзакций лояльности
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    amount INT NOT NULL,             -- положительное = начисление, отрицательное = списание
    transaction_type VARCHAR(20),    -- 'earn', 'spend'
    description TEXT,
    visit_id INT,                    -- ID визита в YClients
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON loyalty_transactions(user_id);

-- Лог вебхуков от YClients
CREATE TABLE IF NOT EXISTS webhook_log (
    id BIGSERIAL PRIMARY KEY,
    webhook_id VARCHAR(100) UNIQUE, -- ID события из YClients
    phone VARCHAR(20),
    amount INT,
    status VARCHAR(20) DEFAULT 'received', -- 'received', 'processed', 'failed'
    error_message TEXT,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Таблица услуг (для Mini App)
CREATE TABLE IF NOT EXISTS services (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    price INT,
    category VARCHAR(100),
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Таблица мастеров
CREATE TABLE IF NOT EXISTS masters (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(200),
    photo_url TEXT
);

-- Таблица акций
CREATE TABLE IF NOT EXISTS promotions (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    image_url TEXT,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);
