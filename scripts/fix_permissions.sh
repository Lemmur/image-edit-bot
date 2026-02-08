#!/bin/bash
# Скрипт для исправления прав доступа к директориям бота

BOT_DIR="/opt/image-edit-bot"
DATA_DIR="$BOT_DIR/data"

echo "🔧 Fixing permissions for bot directories..."

# Создать директории если не существуют
mkdir -p "$DATA_DIR/input"
mkdir -p "$DATA_DIR/output"
mkdir -p "$DATA_DIR/temp"

# Установить владельца ubuntu для всех директорий
sudo chown -R ubuntu:ubuntu "$BOT_DIR"

# Установить права: rwxr-xr-x для директорий
sudo chmod -R 755 "$DATA_DIR"

# Установить права: rw-r--r-- для файлов
find "$DATA_DIR" -type f -exec chmod 644 {} \;

# Дать полные права на data директорию
sudo chmod -R 775 "$DATA_DIR"

echo "✅ Permissions fixed!"
echo ""
echo "Directory structure:"
ls -la "$DATA_DIR"
