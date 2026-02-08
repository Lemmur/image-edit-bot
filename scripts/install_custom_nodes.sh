#!/bin/bash
set -eo pipefail

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
echo "✅ Все кастомные ноды установлены"
echo ""
echo "Установленные ноды:"
ls -1d "${CUSTOM_NODES_DIR}"/*/
