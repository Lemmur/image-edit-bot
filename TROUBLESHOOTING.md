# 🔧 Устранение неполадок

## Ошибка: "bash: line 70: cho: command not found"

### Причина
На сервере установлена устаревшая версия скриптов с опечаткой.

### Решение

#### Вариант 1: Обновление через git (рекомендуется)
Если репозиторий уже клонирован на сервере:

```bash
# Перейти в директорию бота
cd /opt/image-edit-bot

# Обновить код из репозитория
sudo -u comfyui git fetch origin
sudo -u comfyui git reset --hard origin/main

# Или использовать скрипт обновления
sudo bash /opt/image-edit-bot/scripts/update_bot.sh
```

#### Вариант 2: Переустановка
Если git не настроен:

```bash
# Удалить старую версию
sudo rm -rf /opt/image-edit-bot

# Запустить установку заново с актуальной версией
sudo bash scripts/quick_deploy.sh
```

#### Вариант 3: Ручная проверка и исправление
Проверьте файл на сервере:

```bash
# Найти строки с опечаткой
grep -n "^\s*cho\s" /opt/image-edit-bot/scripts/*.sh

# Если найдено - отредактируйте файл
sudo nano /opt/image-edit-bot/scripts/quick_deploy.sh

# Замените "cho" на "echo" в проблемной строке
```

---

## Проверка синтаксиса перед развертыванием

### Python файлы
```bash
python3 scripts/check_syntax.py
```

### Bash скрипты
```bash
bash scripts/check_bash_syntax.sh
```

---

## Типичные проблемы установки

### 1. NVIDIA драйверы не найдены
**Ошибка:** `nvidia-smi: command not found`

**Решение:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit

# Проверка
nvidia-smi
```

### 2. Недостаточно места на диске
**Проверка:**
```bash
df -h /opt
```

Требуется минимум **30GB** свободного места для моделей.

### 3. ComfyUI не запускается
**Проверка логов:**
```bash
sudo journalctl -u comfyui -n 100 --no-pager
```

**Частые причины:**
- Модели не загружены полностью
- Нехватка VRAM (нужно минимум 12GB)
- Python зависимости не установлены

**Решение:**
```bash
# Переустановить зависимости
cd /opt/ComfyUI
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Telegram бот не отвечает
**Проверка:**
```bash
# Логи бота
sudo journalctl -u telegram-bot -n 100 --no-pager

# Проверить .env
sudo cat /opt/image-edit-bot/.env | grep TELEGRAM_BOT_TOKEN
```

**Решение:**
1. Убедитесь, что `TELEGRAM_BOT_TOKEN` настроен в `.env`
2. Проверьте, что ComfyUI запущен и доступен:
   ```bash
   curl http://127.0.0.1:8188/system_stats
   ```

### 5. Ошибки при скачивании моделей
**Если загрузка прервалась:**
```bash
# Скрипт поддерживает возобновление
sudo bash /opt/image-edit-bot/scripts/download_models.sh
```

**Ручная загрузка:**
```bash
cd /opt/ComfyUI/models/checkpoints
wget -c https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO/resolve/main/v23/Qwen-Rapid-AIO-NSFW-v23.safetensors
```

---

## Полезные команды

### Управление сервисами
```bash
# Запуск
sudo systemctl start comfyui
sudo systemctl start telegram-bot

# Остановка
sudo systemctl stop telegram-bot
sudo systemctl stop comfyui

# Перезапуск
sudo systemctl restart telegram-bot

# Автозапуск
sudo systemctl enable comfyui telegram-bot

# Статус
systemctl status comfyui
systemctl status telegram-bot
```

### Логи
```bash
# Следить за логами в реальном времени
sudo journalctl -u comfyui -f
sudo journalctl -u telegram-bot -f

# Последние 50 строк
sudo journalctl -u telegram-bot -n 50

# Логи за последний час
sudo journalctl -u comfyui --since "1 hour ago"
```

### Проверка ресурсов
```bash
# GPU
nvidia-smi

# Память и CPU
htop

# Дисковое пространство
df -h

# Размер директорий
du -sh /opt/ComfyUI/models/*
```

---

## Контрольный список перед запуском

- [ ] NVIDIA драйверы установлены (`nvidia-smi` работает)
- [ ] Минимум 30GB свободного места
- [ ] Модели загружены полностью
- [ ] `.env` файл настроен (TELEGRAM_BOT_TOKEN)
- [ ] ComfyUI запускается без ошибок
- [ ] `curl http://127.0.0.1:8188/system_stats` возвращает JSON

---

## Полная переустановка

Если ничего не помогает:

```bash
# 1. Остановить сервисы
sudo systemctl stop telegram-bot comfyui
sudo systemctl disable telegram-bot comfyui

# 2. Удалить старую установку
sudo rm -rf /opt/ComfyUI
sudo rm -rf /opt/image-edit-bot
sudo rm /etc/systemd/system/comfyui.service
sudo rm /etc/systemd/system/telegram-bot.service
sudo systemctl daemon-reload

# 3. Удалить пользователя (опционально)
sudo userdel -r comfyui

# 4. Запустить установку заново
git clone https://github.com/YOUR_USERNAME/image-edit-bot.git
cd image-edit-bot
sudo bash scripts/quick_deploy.sh
```
