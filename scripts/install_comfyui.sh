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

echo "✅ ComfyUI установлен в ${COMFYUI_DIR}"
