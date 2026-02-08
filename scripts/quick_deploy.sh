#!/bin/bash
set -eo pipefail

# ==========================================
# 🚀 БЫСТРОЕ РАЗВЕРТЫВАНИЕ БОТА
# ==========================================
# Этот скрипт автоматически устанавливает:
# - ComfyUI + PyTorch + CUDA
# - Модели Qwen Image Edit
# - Telegram бота
# - Systemd сервисы
#
# Использование:
#   sudo bash scripts/quick_deploy.sh
# ==========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BOT_DIR="/opt/image-edit-bot"
GIT_REPO="https://github.com/Lemmur/image-edit-bot.git"

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════╗
║   УСТАНОВКА IMAGE EDIT BOT            ║
║   Powered by ComfyUI + Qwen2-VL       ║
╚═══════════════════════════════════════╝
EOF
echo -e "${NC}"

# Проверка root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Ошибка: Запустите скрипт с правами root${NC}"
    echo "   Используйте: sudo bash scripts/quick_deploy.sh"
    exit 1
fi

# Проверка Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    echo -e "${RED}❌ Ошибка: Этот скрипт работает только на Ubuntu/Debian${NC}"
    exit 1
fi

# Проверка NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}⚠️  Предупреждение: nvidia-smi не найден${NC}"
    echo "   Убедитесь что установлены драйверы NVIDIA"
    read -p "   Продолжить установку? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}📋 План установки:${NC}"
echo "   1. Установка системных зависимостей"
echo "   2. Создание пользователя comfyui"
echo "   3. Клонирование репозитория в ${BOT_DIR}"
echo "   4. Установка ComfyUI"
echo "   5. Скачивание моделей (~25GB)"
echo "   6. Установка кастомных нод"
echo "   7. Установка Telegram бота"
echo "   8. Настройка systemd сервисов"
echo ""
read -p "Продолжить? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Установка отменена"
    exit 0
fi

# ===== ШАГ 1: Системные зависимости =====
echo -e "\n${BLUE}[1/8] Установка системных зависимостей...${NC}"

apt-get update -qq
apt-get install -y -qq \
    git \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    rsync \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    > /dev/null 2>&1

echo -e "${GREEN}✅ Системные зависимости установлены${NC}"

# ===== ШАГ 2: Создание пользователя =====
echo -e "\n${BLUE}[2/8] Создание пользователя comfyui...${NC}"

if ! id -u comfyui &>/dev/null; then
    useradd -m -s /bin/bash comfyui
    echo -e "${GREEN}✅ Пользователь comfyui создан${NC}"
else
    echo -e "${YELLOW}⚠️  Пользователь comfyui уже существует${NC}"
fi

# ===== ШАГ 3: Клонирование репозитория =====
echo -e "\n${BLUE}[3/8] Клонирование репозитория...${NC}"

if [ -d "${BOT_DIR}/.git" ]; then
    echo -e "${YELLOW}⚠️  Репозиторий уже существует в ${BOT_DIR}${NC}"
    echo "   Обновляем код..."
    cd "${BOT_DIR}"
    sudo -u comfyui git fetch origin
    sudo -u comfyui git reset --hard origin/main || sudo -u comfyui git reset --hard origin/master
else
    echo "   Клонирование из ${GIT_REPO}..."
    if [ -d "${BOT_DIR}" ]; then
        rm -rf "${BOT_DIR}"
    fi
    sudo -u comfyui git clone "${GIT_REPO}" "${BOT_DIR}"
    cd "${BOT_DIR}"
fi

echo -e "${GREEN}✅ Репозиторий готов${NC}"

# ===== ШАГ 4: Установка ComfyUI =====
echo -e "\n${BLUE}[4/8] Установка ComfyUI...${NC}"
bash "${BOT_DIR}/scripts/install_comfyui.sh"

# ===== ШАГ 5: Скачивание моделей =====
echo -e "\n${BLUE}[5/8] Скачивание моделей Qwen Image Edit (~25GB)...${NC}"
echo -e "${YELLOW}   Это займет 10-30 минут в зависимости от скорости интернета${NC}"
bash "${BOT_DIR}/scripts/download_models.sh"

# ===== ШАГ 6: Установка кастомных нод =====
echo -e "\n${BLUE}[6/8] Установка кастомных нод ComfyUI...${NC}"
bash "${BOT_DIR}/scripts/install_custom_nodes.sh"

# ===== ШАГ 7: Установка бота =====
echo -e "\n${BLUE}[7/8] Установка Telegram бота...${NC}"
bash "${BOT_DIR}/scripts/install_bot.sh"

# ===== ШАГ 8: Настройка сервисов =====
echo -e "\n${BLUE}[8/8] Настройка systemd сервисов...${NC}"
bash "${BOT_DIR}/scripts/setup_services.sh"

# ===== ЗАВЕРШЕНИЕ =====
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ УСТАНОВКА ЗАВЕРШЕНА!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📝 Следующие шаги:${NC}"
echo ""
echo "1. Отредактируйте конфигурацию:"
echo -e "   ${YELLOW}sudo nano ${BOT_DIR}/.env${NC}"
echo ""
echo "   Минимально необходимо добавить:"
echo "   TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather"
echo ""
echo "2. Запустите ComfyUI:"
echo -e "   ${YELLOW}sudo systemctl start comfyui${NC}"
echo ""
echo "3. Дождитесь загрузки моделей (~60 секунд):"
echo -e "   ${YELLOW}sudo journalctl -u comfyui -f${NC}"
echo "   (Ctrl+C чтобы выйти)"
echo ""
echo "4. Проверьте доступность ComfyUI:"
echo -e "   ${YELLOW}curl http://127.0.0.1:8188/system_stats${NC}"
echo ""
echo "5. Запустите бота:"
echo -e "   ${YELLOW}sudo systemctl start telegram-bot${NC}"
echo ""
echo "6. Проверьте логи бота:"
echo -e "   ${YELLOW}sudo journalctl -u telegram-bot -f${NC}"
echo ""
echo -e "${BLUE}🔧 Полезные команды:${NC}"
echo ""
echo "  Обновление бота из git:"
echo -e "    ${YELLOW}sudo bash ${BOT_DIR}/scripts/update_bot.sh${NC}"
echo ""
echo "  Остановка всех сервисов:"
echo -e "    ${YELLOW}sudo systemctl stop telegram-bot comfyui${NC}"
echo ""
echo "  Просмотр статуса:"
echo -e "    ${YELLOW}systemctl status telegram-bot${NC}"
echo -e "    ${YELLOW}systemctl status comfyui${NC}"
echo ""
echo -e "${GREEN}Готово! 🚀${NC}"
