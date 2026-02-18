#!/bin/bash
set -eo pipefail

# Конфигурация (можно переопределить через переменные окружения)
COMFYUI_DIR="${COMFYUI_DIR:-/opt/ComfyUI}"
BOT_DIR="${BOT_DIR:-/opt/image-edit-bot}"
COMFYUI_HOST="${COMFYUI_HOST:-127.0.0.1}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"
COMFYUI_ARGS="${COMFYUI_ARGS:---disable-auto-launch}"

echo "Настройка systemd сервисов..."
echo "  ComfyUI: ${COMFYUI_DIR}"
echo "  Bot: ${BOT_DIR}"
echo "  ComfyUI URL: http://${COMFYUI_HOST}:${COMFYUI_PORT}"

# Проверка существования ComfyUI
if [ ! -d "${COMFYUI_DIR}" ]; then
    echo "⚠️  ComfyUI не найден в ${COMFYUI_DIR}"
    echo "   Установите ComfyUI или укажите путь через COMFYUI_DIR"
fi

# ComfyUI service (только если ComfyUI установлен)
if [ -d "${COMFYUI_DIR}" ]; then
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
    --listen ${COMFYUI_HOST} \\
    --port ${COMFYUI_PORT} \\
    ${COMFYUI_ARGS}

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
    echo "✅ ComfyUI service создан"
else
    echo "⏭️  ComfyUI service пропущен (ComfyUI не установлен)"
fi

# Telegram Bot service
cat > /etc/systemd/system/telegram-bot.service << EOF
[Unit]
Description=Telegram Image Edit Bot
After=network.target
EOF

# Добавляем зависимость от ComfyUI только если ComfyUI установлен локально
if [ -d "${COMFYUI_DIR}" ]; then
    cat >> /etc/systemd/system/telegram-bot.service << EOF
After=network.target comfyui.service
Wants=comfyui.service
EOF
else
    cat >> /etc/systemd/system/telegram-bot.service << EOF
After=network.target
EOF
fi

cat >> /etc/systemd/system/telegram-bot.service << EOF

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

echo "✅ Telegram Bot service создан"

# Перечитать конфигурацию
systemctl daemon-reload

# Включить автозапуск
if [ -d "${COMFYUI_DIR}" ]; then
    systemctl enable comfyui.service
fi
systemctl enable telegram-bot.service

echo ""
echo "✅ Systemd сервисы созданы и включены"
echo ""
echo "Управление:"
if [ -d "${COMFYUI_DIR}" ]; then
    echo "  sudo systemctl start comfyui        # Запуск ComfyUI"
fi
echo "  sudo systemctl start telegram-bot    # Запуск бота"
if [ -d "${COMFYUI_DIR}" ]; then
    echo "  sudo systemctl status comfyui        # Статус ComfyUI"
fi
echo "  sudo systemctl status telegram-bot   # Статус бота"
if [ -d "${COMFYUI_DIR}" ]; then
    echo "  sudo journalctl -u comfyui -f        # Логи ComfyUI"
fi
echo "  sudo journalctl -u telegram-bot -f   # Логи бота"
echo ""
echo "Перезапуск после обновления кода:"
echo "  cd ${BOT_DIR} && git pull && sudo systemctl restart telegram-bot"
