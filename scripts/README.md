# Скрипты миграции

## migrate_images.py

Скрипт для миграции изображений из внешних URL (unsplash.com и др.) в Supabase Storage.

**ВАЖНО:** Это Python скрипт, его нужно запускать через командную строку Python, а НЕ через SQL редактор Supabase!

### Использование

#### Запуск через командную строку (Windows)

**С виртуальным окружением:**
```cmd
cd D:\vladexecute\proj\CVETI
venv\Scripts\activate.bat
python -m scripts.migrate_images --dry-run
```

**Без виртуального окружения:**
```cmd
cd D:\vladexecute\proj\CVETI
py -m scripts.migrate_images --dry-run
```

#### Dry-run режим (проверка без изменений)
```bash
python -m scripts.migrate_images --dry-run
```

#### Реальная миграция всех таблиц
```bash
python -m scripts.migrate_images
```

#### Миграция только одной таблицы
```bash
python -m scripts.migrate_images --table services
python -m scripts.migrate_images --table masters
python -m scripts.migrate_images --table promotions
```

#### Комбинация опций
```bash
python -m scripts.migrate_images --dry-run --table services
```

### ⚠️ ВАЖНО: НЕ запускайте через SQL редактор!

Этот скрипт - **Python скрипт**, его нужно запускать через командную строку Python, а не через SQL редактор Supabase!

### Что делает скрипт

1. Находит все записи с внешними URL (не Supabase Storage)
2. Скачивает изображения по старым URL
3. Загружает их в Supabase Storage в соответствующие папки:
   - `services/` - для услуг
   - `masters/` - для мастеров
   - `promotions/` - для акций
4. Обновляет URL в базе данных на новые Supabase Storage URL

### Безопасность

- **Всегда делайте backup БД перед миграцией!**
- Используйте `--dry-run` для проверки перед реальной миграцией
- Скрипт пропускает записи, которые уже мигрированы
- При ошибке загрузки старый URL сохраняется

### Требования

- Настроенные переменные окружения для Supabase Storage:
  - `SUPABASE_STORAGE_S3_ENDPOINT`
  - `SUPABASE_STORAGE_ACCESS_KEY`
  - `SUPABASE_STORAGE_SECRET_KEY`
  - `SUPABASE_STORAGE_BUCKET`
  - `SUPABASE_URL`

### Пример вывода

```
2024-01-15 10:00:00 - INFO - ============================================================
2024-01-15 10:00:00 - INFO - Image Migration Script
2024-01-15 10:00:00 - INFO - ============================================================
2024-01-15 10:00:00 - INFO - Migrating services...
2024-01-15 10:00:01 - INFO -   Service 1: migrated successfully
2024-01-15 10:00:02 - INFO -   Service 2: already migrated or no image
...
2024-01-15 10:00:10 - INFO - ============================================================
2024-01-15 10:00:10 - INFO - Migration Summary
2024-01-15 10:00:10 - INFO - ============================================================
2024-01-15 10:00:10 - INFO - Services:
2024-01-15 10:00:10 - INFO -   Total: 4
2024-01-15 10:00:10 - INFO -   Success: 4
2024-01-15 10:00:10 - INFO -   Failed: 0
2024-01-15 10:00:10 - INFO -   Skipped: 0
```

## diagnose_user.py

Скрипт для диагностики пользователя: проверка записей в `users`, истории транзакций,
логов вебхуков и сверка с YClients.

### Использование

```bash
python -m scripts.diagnose_user --phone +79991234567
python -m scripts.diagnose_user --tg-id 123456789
python -m scripts.diagnose_user --user-id 42
```

### Полезные опции

```bash
python -m scripts.diagnose_user --phone +79991234567 --limit 50
python -m scripts.diagnose_user --phone +79991234567 --skip-yclients
```

## backfill_visits.py

Единоразовый синк визитов из YClients в локальную таблицу `yclients_visits`.

### Использование

```bash
python -m scripts.backfill_visits
python -m scripts.backfill_visits --only-user-id 42
python -m scripts.backfill_visits --limit-per-user 100
```
