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
echo "✅ Systemd сервисы созданы и включены"
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
