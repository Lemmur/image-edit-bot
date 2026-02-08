#!/bin/bash
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} Qwen Image Edit Bot — Full Server Setup  ${NC}"
echo -e "${GREEN}========================================${NC}"

# Переменные
COMFYUI_DIR="/opt/ComfyUI"
BOT_DIR="/opt/image-edit-bot"
SERVICE_USER="comfyui"

# Проверка root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Запустите от root: sudo bash scripts/setup_server.sh${NC}"
    exit 1
fi

# Проверка GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}NVIDIA драйвер не установлен!${NC}"
    exit 1
fi

echo -e "${GREEN}GPU обнаружен:${NC}"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

echo ""
read -p "Продолжить установку? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi

# 1. Системные зависимости
echo -e "${YELLOW}[1/7] Установка системных зависимостей...${NC}"
apt update
apt install -y python3 python3-venv python3-pip git wget curl

# 2. Создание пользователя
echo -e "${YELLOW}[2/7] Создание пользователя ${SERVICE_USER}...${NC}"
if ! id "${SERVICE_USER}" &>/dev/null; then
    useradd -r -s /bin/bash -d "${COMFYUI_DIR}" "${SERVICE_USER}"
    usermod -aG video "${SERVICE_USER}"
    echo -e "${GREEN}Пользователь ${SERVICE_USER} создан${NC}"
else
    echo -e "${GREEN}Пользователь ${SERVICE_USER} уже существует${NC}"
fi

# 3. Установка ComfyUI
echo -e "${YELLOW}[3/7] Установка ComfyUI...${NC}"
bash scripts/install_comfyui.sh

# 4. Скачивание моделей
echo -e "${YELLOW}[4/7] Скачивание моделей (~25GB, это займёт время)...${NC}"
bash scripts/download_models.sh

# 5. Установка кастомных нод
echo -e "${YELLOW}[5/7] Установка кастомных нод ComfyUI...${NC}"
bash scripts/install_custom_nodes.sh

# 6. Установка бота
echo -e "${YELLOW}[6/7] Установка Telegram бота...${NC}"
bash scripts/install_bot.sh

# 7. Настройка systemd
echo -e "${YELLOW}[7/7] Настройка systemd сервисов...${NC}"
bash scripts/setup_services.sh

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Установка завершена!                  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Следующие шаги:"
echo -e "  1. Отредактируйте ${BOT_DIR}/.env"
echo -e "     ${YELLOW}sudo -u ${SERVICE_USER} nano ${BOT_DIR}/.env${NC}"
echo -e ""
echo -e "  2. Запустите ComfyUI:"
echo -e "     ${YELLOW}sudo systemctl start comfyui${NC}"
echo -e ""
echo -e "  3. Подождите ~60 сек и проверьте:"
echo -e "     ${YELLOW}curl http://127.0.0.1:8188/system_stats${NC}"
echo -e ""
echo -e "  4. Запустите бота:"
echo -e "     ${YELLOW}sudo systemctl start telegram-bot${NC}"
echo -e ""
echo -e "  5. Проверьте логи:"
echo -e "     ${YELLOW}sudo journalctl -u comfyui -f${NC}"
echo -e "     ${YELLOW}sudo journalctl -u telegram-bot -f${NC}"
