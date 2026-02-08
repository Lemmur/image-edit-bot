#!/bin/bash
set -euo pipefail

BOT_DIR="/opt/image-edit-bot"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

echo "Установка Telegram бота..."

# Создание директории если нужно
mkdir -p "${BOT_DIR}"

# Если это запуск из клонированного репо — копируем
if [ "${PROJECT_ROOT}" != "${BOT_DIR}" ]; then
    echo "Копирование файлов проекта в ${BOT_DIR}..."
    rsync -av --exclude='.git' --exclude='venv' --exclude='data' --exclude='logs' \
        "${PROJECT_ROOT}/" "${BOT_DIR}/"
fi

cd "${BOT_DIR}"

# Создание venv
if [ ! -d "venv" ]; then
    echo "Создание Python venv..."
    python3 -m venv venv
fi

source venv/bin/activate

# Установка зависимостей
echo "Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Создание рабочих директорий
mkdir -p data/{input,output,temp}
mkdir -p logs

# Конфигурация
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте .env файл!"
    echo "   nano ${BOT_DIR}/.env"
    echo "   Добавьте TELEGRAM_BOT_TOKEN"
fi

# Права
chown -R comfyui:comfyui "${BOT_DIR}"

echo ""
echo "✅ Telegram бот установлен в ${BOT_DIR}"
