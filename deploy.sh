#!/bin/bash

# Скрипт для деплоя на VPS
# Использование: ./deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Начинаем деплой CVETI на VPS..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Устанавливаем..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker установлен. Перезайдите в систему для применения изменений."
    exit 1
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Устанавливаем..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose установлен"
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаём из .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Файл .env создан. НЕОБХОДИМО ЗАПОЛНИТЬ ВСЕ ПЕРЕМЕННЫЕ!"
        echo "📝 Отредактируйте .env файл: nano .env"
        exit 1
    else
        echo "❌ Файл .env.example не найден!"
        exit 1
    fi
fi

# Останавливаем старые контейнеры
echo "🛑 Останавливаем старые контейнеры..."
docker-compose down || true

# Получаем последние изменения из git
echo "📥 Получаем последние изменения из git..."
git pull origin main

# Собираем и запускаем контейнеры
echo "🔨 Собираем Docker образ..."
docker-compose build --no-cache

echo "🚀 Запускаем контейнеры..."
docker-compose up -d

# Показываем логи
echo "📋 Логи контейнера (Ctrl+C для выхода):"
docker-compose logs -f
