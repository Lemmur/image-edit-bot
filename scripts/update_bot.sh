#!/bin/bash
set -eo pipefail

BOT_DIR="/opt/image-edit-bot"
GIT_REPO="https://github.com/Lemmur/image-edit-bot.git"

echo "🔄 Обновление Telegram бота..."

# Проверка что директория существует
if [ ! -d "${BOT_DIR}" ]; then
    echo "❌ Ошибка: Бот не установлен в ${BOT_DIR}"
    echo "   Запустите сначала: sudo bash scripts/quick_deploy.sh"
    exit 1
fi

cd "${BOT_DIR}"

# Проверка что это git репозиторий
if [ ! -d ".git" ]; then
    echo "⚠️  Предупреждение: ${BOT_DIR} не является git репозиторием"
    echo "   Инициализация git..."
    sudo -u comfyui git init
    sudo -u comfyui git remote add origin "${GIT_REPO}"
fi

# Сохранить локальные изменения (если есть)
echo "📦 Сохранение локальных изменений..."
if ! sudo -u comfyui git diff-index --quiet HEAD 2>/dev/null; then
    sudo -u comfyui git stash push -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)"
    echo "   Локальные изменения сохранены в stash"
fi

# Получить обновления
echo "⬇️  Загрузка обновлений из репозитория..."
sudo -u comfyui git fetch origin

# Обновить код
echo "🔧 Применение обновлений..."
sudo -u comfyui git reset --hard origin/main || sudo -u comfyui git reset --hard origin/master

# Обновить зависимости Python
if [ -f "requirements.txt" ]; then
    echo "📚 Обновление Python зависимостей..."
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    deactivate
fi

# Проверить изменения в конфигурации
if [ -f ".env.example" ] && [ -f ".env" ]; then
    echo "📝 Проверка конфигурации..."
    # Показать новые переменные из .env.example, которых нет в .env
    NEW_VARS=$(comm -23 <(grep -v '^#' .env.example | cut -d= -f1 | sort) <(grep -v '^#' .env | cut -d= -f1 | sort) 2>/dev/null || true)
    if [ -n "$NEW_VARS" ]; then
        echo "   ⚠️  Обнаружены новые переменные в .env.example:"
        echo "$NEW_VARS" | sed 's/^/      - /'
        echo "   Проверьте и добавьте их в .env при необходимости"
    fi
fi

# Права
echo "🔐 Проверка прав..."
chown -R comfyui:comfyui "${BOT_DIR}"

# Перезапуск бота
echo "🔄 Перезапуск бота..."
if systemctl is-active --quiet telegram-bot; then
    systemctl restart telegram-bot
    echo "   ✅ Бот перезапущен"
else
    echo "   ⚠️  Бот не был запущен, запускаем..."
    systemctl start telegram-bot
fi

# Проверка статуса
sleep 2
if systemctl is-active --quiet telegram-bot; then
    echo ""
    echo "✅ Обновление выполнено успешно!"
    echo ""
    echo "Просмотр логов:"
    echo "  sudo journalctl -u telegram-bot -f"
    echo ""
    
    # Показать последние несколько строк лога
    echo "Последние строки лога:"
    journalctl -u telegram-bot -n 5 --no-pager
else
    echo ""
    echo "❌ Ошибка: Бот не запустился после обновления"
    echo "Проверьте логи:"
    echo "  sudo journalctl -u telegram-bot -n 50"
    exit 1
fi
