#!/bin/bash
set -eo pipefail

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

echo ""
echo "✅ Скачивание моделей завершено"
