-- Миграция 013: Функция для корректной синхронизации баланса с учетом FIFO
-- Позволяет изменять баланс (в плюс или минус) так, чтобы локальный расчет 
-- (через remaining_amount) оставался согласованным с YClients.

CREATE OR REPLACE FUNCTION adjust_loyalty_balance(
    p_user_id BIGINT,
    p_amount INT,
    p_description TEXT,
    p_expiration_days INT DEFAULT 90
)
RETURNS JSON AS $$
DECLARE
    v_remaining_to_burn INT;
    v_transaction RECORD;
    v_burned_from_transaction INT;
    v_expires_at TIMESTAMP WITH TIME ZONE;
BEGIN
    IF p_amount > 0 THEN
        -- Положительная корректировка: добавляем новую транзакцию типа 'earn'
        -- Используем 'earn', чтобы баллы учитывались в get_user_available_balance
        v_expires_at := NOW() + (p_expiration_days || ' days')::INTERVAL;
        
        INSERT INTO loyalty_transactions (
            user_id,
            amount,
            transaction_type,
            description,
            expires_at,
            remaining_amount
        ) VALUES (
            p_user_id,
            p_amount,
            'earn',
            p_description,
            v_expires_at,
            p_amount
        );
    ELSIF p_amount < 0 THEN
        -- Отрицательная корректировка: сжигаем баллы по FIFO (как spend, но без ограничений %)
        v_remaining_to_burn := ABS(p_amount);
        
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
            v_burned_from_transaction := LEAST(v_transaction.remaining_amount, v_remaining_to_burn);
            
            UPDATE loyalty_transactions
            SET remaining_amount = remaining_amount - v_burned_from_transaction
            WHERE id = v_transaction.id;
            
            v_remaining_to_burn := v_remaining_to_burn - v_burned_from_transaction;
            EXIT WHEN v_remaining_to_burn <= 0;
        END LOOP;
        
        -- Создаем транзакцию для истории
        INSERT INTO loyalty_transactions (
            user_id,
            amount,
            transaction_type,
            description,
            remaining_amount
        ) VALUES (
            p_user_id,
            p_amount,
            'sync_correction',
            p_description,
            0
        );
    END IF;

    -- Обновляем итоговый баланс пользователя в таблице users
    -- Используем пересчет через RPC для точности
    UPDATE users
    SET balance = get_user_available_balance(p_user_id),
        updated_at = NOW()
    WHERE id = p_user_id;

    RETURN json_build_object(
        'success', true,
        'new_balance', get_user_available_balance(p_user_id)
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION adjust_loyalty_balance IS 'Корректирует баланс пользователя (начисление или списание) с сохранением целостности FIFO';
