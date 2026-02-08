# 🖥️ Полная установка сервера: ComfyUI + Модели + Бот + Сервисы

> Этот документ — пошаговая инструкция по подготовке сервера с нуля.
> Все скрипты будут созданы в `scripts/` и включены в репозиторий.

---

## Предварительные требования

- Ubuntu 22.04+ или Debian 12+
- NVIDIA RTX 3090 (24GB VRAM)
- NVIDIA Driver 535+ установлен
- CUDA 12.4+ установлен
- Python 3.10+
- Git
- ~50 GB свободного места

### Проверка GPU перед началом

```bash
nvidia-smi
# Должен показать RTX 3090 и версию драйвера

python3 --version
# Python 3.10+
```

---

## Скрипты в репозитории

В проекте будут следующие скрипты:

```
scripts/
├── setup_server.sh          # Полная установка всего (main скрипт)
├── install_comfyui.sh       # Установка ComfyUI
├── download_models.sh       # Скачивание моделей
├── install_custom_nodes.sh  # Установка кастомных нод
├── install_bot.sh           # Установка бота
├── setup_services.sh        # Создание systemd сервисов
└── test_comfyui.py          # Тест ComfyUI API
```

---

## scripts/setup_server.sh — Главный скрипт

```bash
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
```

---

## scripts/install_comfyui.sh

```bash
#!/bin/bash
set -euo pipefail

COMFYUI_DIR="/opt/ComfyUI"

if [ -d "${COMFYUI_DIR}" ]; then
    echo "ComfyUI уже установлен в ${COMFYUI_DIR}"
    echo "Обновляем..."
    cd "${COMFYUI_DIR}"
    git pull
else
    echo "Клонирование ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "${COMFYUI_DIR}"
    cd "${COMFYUI_DIR}"
fi

# Создание виртуального окружения
if [ ! -d "${COMFYUI_DIR}/venv" ]; then
    echo "Создание Python venv..."
    python3 -m venv venv
fi

source venv/bin/activate

# Установка PyTorch с CUDA
echo "Установка PyTorch + CUDA..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Установка зависимостей ComfyUI
echo "Установка зависимостей ComfyUI..."
pip install -r requirements.txt

# Создание необходимых директорий
mkdir -p models/checkpoints
mkdir -p models/text_encoders
mkdir -p models/vae
mkdir -p models/loras/qwen_edit
mkdir -p input
mkdir -p output
mkdir -p temp

# Установка прав
chown -R comfyui:comfyui "${COMFYUI_DIR}"

echo "ComfyUI установлен в ${COMFYUI_DIR}"
```

---

## scripts/download_models.sh

```bash
#!/bin/bash
set -euo pipefail

COMFYUI_DIR="/opt/ComfyUI"
MODELS_DIR="${COMFYUI_DIR}/models"

echo "========================================="
echo "  Скачивание моделей для Qwen Image Edit"
echo "========================================="

# Функция для скачивания с проверкой
download_model() {
    local url="$1"
    local dest="$2"
    local name="$3"
    
    if [ -f "${dest}" ]; then
        echo "[SKIP] ${name} уже скачан"
        return
    fi
    
    echo "[DOWNLOAD] ${name}..."
    echo "  URL: ${url}"
    echo "  Dest: ${dest}"
    
    # wget с прогрессом и возобновлением
    wget -c --show-progress -O "${dest}" "${url}"
    
    echo "[OK] ${name} скачан"
}

# 1. Checkpoint (~13GB)
echo ""
echo "--- Checkpoint ---"
download_model \
    "https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO/resolve/main/v23/Qwen-Rapid-AIO-NSFW-v23.safetensors" \
    "${MODELS_DIR}/checkpoints/Qwen-Rapid-AIO-NSFW-v11.4.safetensors" \
    "Qwen Checkpoint (v11.4)"

# 2. Text Encoder (~7.5GB)
echo ""
echo "--- Text Encoder ---"
download_model \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
    "${MODELS_DIR}/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
    "Qwen 2.5 VL 7B Text Encoder (FP8)"

# 3. VAE (~160MB)
echo ""
echo "--- VAE ---"
download_model \
    "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors" \
    "${MODELS_DIR}/vae/qwen_image_vae.safetensors" \
    "Qwen Image VAE"

# 4. LoRA
echo ""
echo "--- LoRA ---"
download_model \
    "https://huggingface.co/camenduru/Qwen-Loras/resolve/main/next-scene_lora-v2-3000.safetensors" \
    "${MODELS_DIR}/loras/qwen_edit/next-scene_lora-v2-3000.safetensors" \
    "Next Scene LoRA v2"

# Установка прав
chown -R comfyui:comfyui "${MODELS_DIR}"

echo ""
echo "========================================="
echo "  Все модели скачаны!"
echo "========================================="
echo ""

# Проверка размеров
echo "Проверка файлов:"
for f in \
    "${MODELS_DIR}/checkpoints/Qwen-Rapid-AIO-NSFW-v11.4.safetensors" \
    "${MODELS_DIR}/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
    "${MODELS_DIR}/vae/qwen_image_vae.safetensors"; do
    if [ -f "$f" ]; then
        size=$(du -h "$f" | cut -f1)
        echo "  ✅ $(basename $f) — ${size}"
    else
        echo "  ❌ $(basename $f) — НЕ НАЙДЕН"
    fi
done
```

---

## scripts/install_custom_nodes.sh

```bash
#!/bin/bash
set -euo pipefail

COMFYUI_DIR="/opt/ComfyUI"
CUSTOM_NODES_DIR="${COMFYUI_DIR}/custom_nodes"

echo "Установка кастомных нод ComfyUI..."

cd "${CUSTOM_NODES_DIR}"

# Функция клонирования/обновления
install_node() {
    local repo="$1"
    local name="$2"
    
    local dir_name=$(basename "${repo}" .git)
    
    if [ -d "${dir_name}" ]; then
        echo "[UPDATE] ${name}..."
        cd "${dir_name}"
        git pull
        cd ..
    else
        echo "[INSTALL] ${name}..."
        git clone "${repo}"
    fi
    
    # Установка requirements если есть
    if [ -f "${dir_name}/requirements.txt" ]; then
        echo "  Установка зависимостей ${name}..."
        "${COMFYUI_DIR}/venv/bin/pip" install -r "${dir_name}/requirements.txt"
    fi
}

# 1. RES4LYF (ClownsharKSampler_Beta, CFGNorm)
install_node \
    "https://github.com/ClownsharkBatwing/RES4LYF" \
    "RES4LYF (ClownsharKSampler)"

# 2. KJNodes (INTConstant, WidgetToString)
install_node \
    "https://github.com/kijai/ComfyUI-KJNodes" \
    "KJNodes"

# 3. Image Saver (Image Saver Simple, Metadata)
install_node \
    "https://github.com/alexopus/ComfyUI-Image-Saver" \
    "ComfyUI Image Saver"

# 4. rgthree (Power Lora Loader)
install_node \
    "https://github.com/rgthree/rgthree-comfy" \
    "rgthree-comfy"

# Права
chown -R comfyui:comfyui "${CUSTOM_NODES_DIR}"

echo ""
echo "Все кастомные ноды установлены ✅"
echo ""
echo "Установленные ноды:"
ls -1d "${CUSTOM_NODES_DIR}"/*/
```

---

## scripts/install_bot.sh

```bash
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
echo "Telegram бот установлен в ${BOT_DIR} ✅"
```

---

## scripts/setup_services.sh

```bash
#!/bin/bash
set -euo pipefail

echo "Настройка systemd сервисов..."

# ComfyUI service
cat > /etc/systemd/system/comfyui.service << 'EOF'
[Unit]
Description=ComfyUI Image Generation Server
After=network.target

[Service]
Type=simple
User=comfyui
Group=comfyui
WorkingDirectory=/opt/ComfyUI

ExecStart=/opt/ComfyUI/venv/bin/python main.py \
    --listen 127.0.0.1 \
    --port 8188 \
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
ReadWritePaths=/opt/ComfyUI

[Install]
WantedBy=multi-user.target
EOF

# Telegram Bot service
cat > /etc/systemd/system/telegram-bot.service << 'EOF'
[Unit]
Description=Telegram Image Edit Bot
After=network.target comfyui.service
Wants=comfyui.service

[Service]
Type=simple
User=comfyui
Group=comfyui
WorkingDirectory=/opt/image-edit-bot

ExecStart=/opt/image-edit-bot/venv/bin/python -m src.main

Restart=always
RestartSec=15

StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

EnvironmentFile=/opt/image-edit-bot/.env
Environment="PYTHONUNBUFFERED=1"

NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/image-edit-bot

[Install]
WantedBy=multi-user.target
EOF

# Перечитать конфигурацию
systemctl daemon-reload

# Включить автозапуск
systemctl enable comfyui.service
systemctl enable telegram-bot.service

echo ""
echo "Systemd сервисы созданы и включены ✅"
echo ""
echo "Управление:"
echo "  sudo systemctl start comfyui        # Запуск ComfyUI"
echo "  sudo systemctl start telegram-bot    # Запуск бота"
echo "  sudo systemctl status comfyui        # Статус ComfyUI"
echo "  sudo systemctl status telegram-bot   # Статус бота"
echo "  sudo journalctl -u comfyui -f        # Логи ComfyUI"
echo "  sudo journalctl -u telegram-bot -f   # Логи бота"
echo ""
echo "Перезапуск после обновления кода:"
echo "  cd /opt/image-edit-bot && git pull && sudo systemctl restart telegram-bot"
```

---

## Полный порядок установки на чистом сервере

```
1. ssh root@your-server-ip

2. Проверить GPU:
   nvidia-smi

3. Клонировать наш репозиторий:
   cd /tmp
   git clone https://github.com/YOUR_USER/image-edit-bot.git
   cd image-edit-bot

4. Запустить полную установку:
   sudo bash scripts/setup_server.sh
   
   Это выполнит:
    [1/7] apt install python3 git wget...
    [2/7] Создаст пользователя comfyui
    [3/7] Установит ComfyUI + PyTorch
    [4/7] Скачает модели (~25GB, ~15 мин)
    [5/7] Установит кастомные ноды
    [6/7] Установит бота + зависимости
    [7/7] Создаст systemd сервисы

5. Настроить .env:
   sudo -u comfyui nano /opt/image-edit-bot/.env
   → вписать TELEGRAM_BOT_TOKEN

6. Запустить:
   sudo systemctl start comfyui
   # Подождать 60 сек
   curl http://127.0.0.1:8188/system_stats
   sudo systemctl start telegram-bot

7. Проверить:
   sudo journalctl -u telegram-bot -f
   → Отправить фото боту в Telegram
```

---

## Обновление кода бота после git push

```bash
ssh user@server
cd /opt/image-edit-bot
sudo -u comfyui git pull origin main
sudo systemctl restart telegram-bot
sudo journalctl -u telegram-bot -f  # проверить логи
```
