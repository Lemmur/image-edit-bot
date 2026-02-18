#!/bin/bash
# Установка бота с уже установленным ComfyUI
# Usage: sudo bash scripts/install_with_existing_comfyui.sh /path/to/ComfyUI

set -eo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BOT_DIR="/opt/image-edit-bot"
COMFYUI_DIR="${1:-/opt/ComfyUI}"

echo -e "${GREEN}=== Установка Telegram бота с существующим ComfyUI ===${NC}"
echo ""

# Проверка root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: запустите с sudo${NC}"
    exit 1
fi

# Проверка ComfyUI
echo -e "${YELLOW}Проверка ComfyUI...${NC}"
if [ ! -d "${COMFYUI_DIR}" ]; then
    echo -e "${RED}ComfyUI не найден в ${COMFYUI_DIR}${NC}"
    echo "Укажите путь: sudo bash $0 /path/to/ComfyUI"
    exit 1
fi

if [ ! -f "${COMFYUI_DIR}/main.py" ]; then
    echo -e "${RED}main.py не найден в ${COMFYUI_DIR}${NC}"
    echo "Убедитесь, что это корректная установка ComfyUI"
    exit 1
fi

echo -e "${GREEN}✓ ComfyUI найден: ${COMFYUI_DIR}${NC}"

# Определение директории скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Создание пользователя
echo -e "${YELLOW}Создание пользователя comfyui...${NC}"
if ! id "comfyui" &>/dev/null; then
    useradd -r -s /bin/false comfyui
    echo -e "${GREEN}✓ Пользователь comfyui создан${NC}"
else
    echo -e "${GREEN}✓ Пользователь comfyui уже существует${NC}"
fi

# Создание директории бота
echo -e "${YELLOW}Установка бота в ${BOT_DIR}...${NC}"
mkdir -p "${BOT_DIR}"

# Копирование файлов
if [ "${PROJECT_ROOT}" != "${BOT_DIR}" ]; then
    echo "Копирование файлов проекта..."
    rsync -av --exclude='.git' --exclude='venv' --exclude='data' --exclude='logs' \
        "${PROJECT_ROOT}/" "${BOT_DIR}/"
fi

cd "${BOT_DIR}"

# Создание venv
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Создание Python venv...${NC}"
    python3 -m venv venv
fi

# Установка зависимостей
echo -e "${YELLOW}Установка Python зависимостей...${NC}"
sudo -u comfyui bash << 'EOF'
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
EOF

# Создание рабочих директорий
mkdir -p data/{input,output,temp}
mkdir -p logs

# Создание .env файла
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Создание .env файла...${NC}"
    cat > .env << EOF
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=

# ComfyUI Connection
COMFYUI_HOST=127.0.0.1
COMFYUI_PORT=8188

# ComfyUI Installation (для авто-запуска)
COMFYUI_DIR=${COMFYUI_DIR}
COMFYUI_VENV=${COMFYUI_DIR}/venv
COMFYUI_AUTO_START=true
COMFYUI_ARGS=--cuda-device 0

# Paths
DATA_DIR=data
LOGS_DIR=logs
EOF
    echo -e "${GREEN}✓ .env файл создан${NC}"
else
    echo -e "${GREEN}✓ .env файл уже существует${NC}"
fi

# Права
chown -R comfyui:comfyui "${BOT_DIR}"

# Настройка systemd сервисов
echo -e "${YELLOW}Настройка systemd сервисов...${NC}"

# ComfyUI service (ссылка на существующую установку)
cat > /etc/systemd/system/comfyui.service << EOF
[Unit]
Description=ComfyUI Image Generation Server
After=network.target

[Service]
Type=simple
User=comfyui
Group=comfyui
WorkingDirectory=${COMFYUI_DIR}

ExecStart=${COMFYUI_DIR}/venv/bin/python main.py \\
    --listen 127.0.0.1 \\
    --port 8188 \\
    --disable-auto-launch

Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=comfyui

Environment="CUDA_VISIBLE_DEVICES=0"
Environment="PYTHONUNBUFFERED=1"

NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${COMFYUI_DIR}

[Install]
WantedBy=multi-user.target
EOF

# Telegram Bot service
cat > /etc/systemd/system/telegram-bot.service << EOF
[Unit]
Description=Telegram Image Edit Bot
After=network.target comfyui.service
Wants=comfyui.service

[Service]
Type=simple
User=comfyui
Group=comfyui
WorkingDirectory=${BOT_DIR}

ExecStart=${BOT_DIR}/venv/bin/python -m src.main

Restart=always
RestartSec=15

StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

EnvironmentFile=${BOT_DIR}/.env
Environment="PYTHONUNBUFFERED=1"

NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${BOT_DIR}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable comfyui.service
systemctl enable telegram-bot.service

echo ""
echo -e "${GREEN}✅ Установка завершена!${NC}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
echo ""
echo "1. Отредактируйте .env файл и добавьте токен бота:"
echo "   sudo nano ${BOT_DIR}/.env"
echo ""
echo "2. Запустите ComfyUI:"
echo "   sudo systemctl start comfyui"
echo ""
echo "3. Подождите ~60 сек (загрузка моделей), проверьте:"
echo "   curl http://127.0.0.1:8188/system_stats"
echo ""
echo "4. Запустите бота:"
echo "   sudo systemctl start telegram-bot"
echo ""
echo "5. Проверьте логи:"
echo "   sudo journalctl -u telegram-bot -f"
echo ""
echo -e "${YELLOW}Управление:${NC}"
echo "  sudo systemctl status comfyui      # Статус ComfyUI"
echo "  sudo systemctl status telegram-bot # Статус бота"
echo "  sudo systemctl restart telegram-bot # Перезапуск бота"
echo "  sudo journalctl -u comfyui -f      # Логи ComfyUI"
echo "  sudo journalctl -u telegram-bot -f # Логи бота"
