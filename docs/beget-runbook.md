# Развертывание CVETI на Beget (VPS + PostgreSQL DBaaS + S3)

Этот документ описывает стабильный вариант развертывания проекта на Beget и
типовые проблемы, которые мы уже ловили. Секреты сюда не пишем — только имена
переменных и шаги.

## 1. Архитектура

- **API и бот**: один контейнер `app` (FastAPI + Aiogram).
- **REST к БД**: контейнер `postgrest` (аналог Supabase REST).
- **БД**: PostgreSQL DBaaS от Beget.
- **Файлы**: S3‑совместимое хранилище Beget.
- **Прокси/SSL**: системный Nginx + Certbot.

Важно: в коде исторически используются имена `SUPABASE_*`. Сейчас это:
- `SUPABASE_URL`/`SUPABASE_REST_PATH` — URL PostgREST.
- `SUPABASE_STORAGE_*` — настройки S3 (Beget).

## 2. Обязательные переменные окружения

См. `.env.example` и заполните реальные значения.

### Бот и домен

- `TELEGRAM_BOT_TOKEN`
- `BASE_URL` (домен проекта, например `https://cveti-cosmetology.ru`)
- `WEBHOOK_SECRET` (секрет для вебхука YClients)
- `ADMIN_IDS` (ID админов через запятую)

### PostgREST (DBaaS)

- `SUPABASE_URL` — адрес PostgREST
  - при работе в Docker обычно `http://postgrest:3000`
- `SUPABASE_REST_PATH` — **пусто** для PostgREST (он слушает `/`)
- `SUPABASE_KEY` — оставьте пустым, если JWT не используете
- `POSTGREST_DB_URI` — строка подключения к Beget DBaaS
- `POSTGREST_DB_SCHEMA` — обычно `public`
- `POSTGREST_DB_ANON_ROLE` — роль для запросов
- `POSTGREST_JWT_SECRET` — **только** если включаете JWT‑авторизацию

### S3 (Beget)

- `SUPABASE_STORAGE_S3_ENDPOINT` — `https://s3.ru1.storage.beget.cloud`
- `SUPABASE_STORAGE_S3_REGION` — `ru1`
- `SUPABASE_STORAGE_ACCESS_KEY`
- `SUPABASE_STORAGE_SECRET_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `SUPABASE_STORAGE_PUBLIC_URL_BASE` — опционально (см. раздел про 403)
- `STORAGE_PUBLIC_URL_TEMPLATE` — опционально, если хотите жёсткий шаблон URL
- `S3_SUPABASE_FALLBACK_ENABLED` — по умолчанию `false`

### YClients

- `YCLIENTS_PARTNER_TOKEN`
- `YCLIENTS_USER_TOKEN`
- `YCLIENTS_COMPANY_ID`
- `YCLIENTS_BOOKING_URL`

### Лояльность

Параметры по умолчанию читаются из `.env`, их можно менять через админку:
- `LOYALTY_PERCENTAGE`
- `LOYALTY_MAX_SPEND_PERCENTAGE`
- `LOYALTY_EXPIRATION_DAYS`

## 3. Запуск в Docker

```bash
docker compose up -d --build
```

Логи:

```bash
docker compose logs app --tail=200
docker compose logs postgrest --tail=200
```

## 4. Nginx и SSL

### 4.1. Reverse proxy

Схема: домен → Nginx → `http://127.0.0.1:8000`.

### 4.2. Лимит загрузки файлов (50 MB)

В **server**‑блоке домена добавьте:

```
client_max_body_size 50m;
```

После этого:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4.3. SSL

```bash
sudo certbot --nginx -d cveti-cosmetology.ru -d www.cveti-cosmetology.ru
```

## 5. Вебхуки

### Telegram

URL: `https://<домен>/webhook/telegram`

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://<домен>/webhook/telegram&drop_pending_updates=true"
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

### YClients

URL: `https://<домен>/webhook/yclients`
Header: `X-Webhook-Secret: <WEBHOOK_SECRET>`

## 6. Типовые проблемы и решения

### 6.1. `Server lacks JWT secret` (PostgREST 500)

Причина: клиент отправляет `Authorization`/`apikey`, но `POSTGREST_JWT_SECRET`
не задан.

Решение:
- если JWT не нужен — оставьте `SUPABASE_KEY` пустым;
- если JWT нужен — задайте `POSTGREST_JWT_SECRET` и используйте валидные токены.

### 6.2. `XAmzContentSHA256Mismatch` при загрузке в S3

Причина: Beget S3 не принимает `aws-chunked` payload signing от boto3.

Что уже сделано в коде:
- попытка стандартного S3 `put_object`;
- если ошибка `XAmzContentSHA256Mismatch` — fallback на прямой SigV4 HTTP PUT.

Что проверить, если проблема остаётся:
- правильный `SUPABASE_STORAGE_S3_ENDPOINT` и `SUPABASE_STORAGE_S3_REGION`;
- валидные ключи доступа и имя бакета.

### 6.3. 403 при открытии `s3.cveti-cosmetology.ru/...`

Причина: домен не имеет доступа к бакету (ACL/Policy) или не настроен CNAME/SSL.

Решение:
- либо настроить бакет публичным для чтения под ваш домен,
- либо использовать прямой endpoint:
  `https://s3.ru1.storage.beget.cloud/<bucket>/<path>`

В коде уже есть fallback: если кастомный домен отдаёт 403, возвращаем URL
через endpoint.

### 6.4. `413 Request Entity Too Large`

Причина: лимит Nginx.

Решение: см. раздел 4.2. В коде API лимит тоже 50MB
(`api/routes/admin.py: upload_file`), его можно менять отдельно.

### 6.5. Нельзя изменить баланс вручную

Это **ожидаемое** поведение: прямое изменение баланса отключено.
Нужно создавать транзакции:

`POST /api/admin/users/{id}/transactions`

Если у клиента нет карты лояльности в YClients — транзакция будет отклонена
с понятной ошибкой.

## 7. Быстрый чек‑лист после деплоя

- `GET https://<домен>/webapp` открывается.
- В `docker compose logs app` видно `POST /webhook/telegram 200`.
- Загрузка файлов в админке проходит и URL открывается из браузера.
- В PostgREST нет ошибок по подключению к БД.

## 8. Почему могли быть ошибки

- **Неправильные базовые URL**: PostgREST и S3 используют другие пути, чем Supabase.
- **JWT заголовки** без секрета в PostgREST.
- **Ограничения Nginx** (413).
- **Политики доступа S3** для кастомного домена.

В Cursor ИИ может ошибаться, если не хватает контекста (сети, домены,
настройки хранилища). Поэтому важно фиксировать конфигурацию и логи, а не
полагаться только на догадки.
