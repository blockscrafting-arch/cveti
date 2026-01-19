-- Миграция 010: Добавление поддержки срока жизни баллов и FIFO списания
-- Правила: баллы действуют 90 дней, можно оплатить до 30% от чека баллами

-- Добавляем колонки для отслеживания срока жизни и остатка баллов
ALTER TABLE loyalty_transactions 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS remaining_amount INT;

-- Для существующих транзакций типа 'earn' устанавливаем срок жизни (90 дней от создания)
-- и remaining_amount = amount (все баллы еще доступны)
UPDATE loyalty_transactions 
SET 
    expires_at = created_at + INTERVAL '90 days',
    remaining_amount = amount
WHERE transaction_type = 'earn' AND expires_at IS NULL;

-- Для транзакций типа 'spend' remaining_amount = 0 (они не накапливаются)
UPDATE loyalty_transactions 
SET remaining_amount = 0
WHERE transaction_type = 'spend' AND remaining_amount IS NULL;

-- Добавляем индекс для быстрого поиска активных (не истекших) баллов
CREATE INDEX IF NOT EXISTS idx_transactions_expires_at ON loyalty_transactions(expires_at) 
WHERE expires_at IS NOT NULL;

-- Добавляем индекс для FIFO списания (сортировка по expires_at для транзакций типа 'earn')
CREATE INDEX IF NOT EXISTS idx_transactions_earn_fifo ON loyalty_transactions(user_id, expires_at) 
WHERE transaction_type = 'earn' AND remaining_amount > 0;

-- Функция для расчета актуального баланса пользователя (только не истекшие баллы)
CREATE OR REPLACE FUNCTION get_user_available_balance(p_user_id BIGINT)
RETURNS INT AS $$
BEGIN
    RETURN COALESCE(
        (SELECT SUM(remaining_amount)
         FROM loyalty_transactions
         WHERE user_id = p_user_id
           AND transaction_type = 'earn'
           AND expires_at > NOW()
           AND remaining_amount > 0),
        0
    );
END;
$$ LANGUAGE plpgsql;

-- Функция для списания баллов по принципу FIFO (First In, First Out)
-- Списывает баллы начиная с самых старых (ближайших к истечению)
CREATE OR REPLACE FUNCTION spend_loyalty_points(
    p_user_id BIGINT,
    p_amount_to_spend INT,
    p_total_bill_amount INT,
    p_max_spend_percentage FLOAT DEFAULT 0.3,
    p_description TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_max_allowed_spend INT;
    v_available_balance INT;
    v_remaining_to_spend INT;
    v_transaction RECORD;
    v_spent_from_transaction INT;
    v_result JSON;
BEGIN
    -- Проверка: нельзя списать больше 30% от суммы чека
    v_max_allowed_spend := FLOOR(p_total_bill_amount * p_max_spend_percentage);
    
    IF p_amount_to_spend > v_max_allowed_spend THEN
        RETURN json_build_object(
            'success', false,
            'error', format('Можно оплатить баллами максимум %s%% от суммы чека (максимум %s баллов)', 
                           (p_max_spend_percentage * 100)::INT, v_max_allowed_spend)
        );
    END IF;
    
    -- Получаем доступный баланс
    v_available_balance := get_user_available_balance(p_user_id);
    
    IF p_amount_to_spend > v_available_balance THEN
        RETURN json_build_object(
            'success', false,
            'error', format('Недостаточно баллов. Доступно: %s, требуется: %s', 
                           v_available_balance, p_amount_to_spend)
        );
    END IF;
    
    -- Начинаем списание по FIFO (сначала самые старые баллы)
    v_remaining_to_spend := p_amount_to_spend;
    
    -- Проходим по транзакциям типа 'earn' с остатком, отсортированным по expires_at (старые первыми)
    FOR v_transaction IN
        SELECT id, remaining_amount
        FROM loyalty_transactions
        WHERE user_id = p_user_id
          AND transaction_type = 'earn'
          AND expires_at > NOW()
          AND remaining_amount > 0
        ORDER BY expires_at ASC, id ASC
        FOR UPDATE
    LOOP
        -- Определяем, сколько списать из этой транзакции
        v_spent_from_transaction := LEAST(v_transaction.remaining_amount, v_remaining_to_spend);
        
        -- Уменьшаем remaining_amount
        UPDATE loyalty_transactions
        SET remaining_amount = remaining_amount - v_spent_from_transaction
        WHERE id = v_transaction.id;
        
        -- Уменьшаем оставшуюся сумму для списания
        v_remaining_to_spend := v_remaining_to_spend - v_spent_from_transaction;
        
        -- Если все списали, выходим
        EXIT WHEN v_remaining_to_spend <= 0;
    END LOOP;
    
    -- Создаем транзакцию типа 'spend' для истории
    INSERT INTO loyalty_transactions (
        user_id,
        amount,
        transaction_type,
        description,
        remaining_amount
    ) VALUES (
        p_user_id,
        -p_amount_to_spend,
        'spend',
        COALESCE(p_description, format('Списание %s баллов', p_amount_to_spend)),
        0
    );
    
    -- Обновляем баланс пользователя (пересчитываем из актуальных транзакций)
    UPDATE users
    SET balance = get_user_available_balance(p_user_id),
        updated_at = NOW()
    WHERE id = p_user_id;
    
    RETURN json_build_object(
        'success', true,
        'spent_amount', p_amount_to_spend,
        'remaining_balance', get_user_available_balance(p_user_id)
    );
END;
$$ LANGUAGE plpgsql;

-- Комментарии для документации
COMMENT ON FUNCTION get_user_available_balance(BIGINT) IS 
'Возвращает актуальный баланс пользователя (только не истекшие баллы)';

COMMENT ON FUNCTION spend_loyalty_points(BIGINT, INT, INT, FLOAT, TEXT) IS 
'Списывает баллы по принципу FIFO с проверкой лимита 30% от суммы чека';
