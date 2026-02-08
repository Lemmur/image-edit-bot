# 🐛 Руководство по отладке бота

## 📋 Просмотр логов

### 1. Логи Telegram бота

```bash
# Просмотр в реальном времени (live)
sudo journalctl -u telegram-bot -f

# Последние 100 строк
sudo journalctl -u telegram-bot -n 100

# Последние строки с временными метками
sudo journalctl -u telegram-bot -n 50 --no-pager

# Поиск по ключевому слову
sudo journalctl -u telegram-bot | grep -i "workflow"
sudo journalctl -u telegram-bot | grep -i "extra_pnginfo"
sudo journalctl -u telegram-bot | grep -i "error"
```

### 2. Логи ComfyUI

```bash
# Просмотр в реальном времени
sudo journalctl -u comfyui -f

# Последние 100 строк
sudo journalctl -u comfyui -n 100

# Поиск ошибок
sudo journalctl -u comfyui | grep -i "exception\|error\|traceback"
```

### 3. Оба сервиса одновременно

```bash
# В реальном времени
sudo journalctl -u telegram-bot -u comfyui -f

# Последние 50 строк каждого
sudo journalctl -u telegram-bot -u comfyui -n 50
```

---

## 🔍 Проверка исправления WidgetToString

### При запуске бота

```bash
sudo systemctl restart telegram-bot
sudo journalctl -u telegram-bot -f
```

**Ищите эти строки:**

✅ **ХОРОШО (исправление работает):**
```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
Workflow template loaded from workflows/qwen_image_edit.json
Template nodes: ['78', '118', '103', ...]
```

❌ **ПЛОХО (проблема с файлом):**
```
⚠️ UI workflow file not found: Qwen Image Edit Rapid.json
⚠️ No UI workflow path provided - extra_pnginfo will be empty
```

### При обработке изображения

Отправьте изображение боту и смотрите логи:

```bash
sudo journalctl -u telegram-bot -u comfyui -f
```

**В логах telegram-bot ищите:**

✅ **ХОРОШО:**
```
Creating workflow with user parameters
✅ extra_pnginfo includes UI workflow
✅ Workflow created successfully
Queueing prompt to ComfyUI...
✅ Including extra_pnginfo with keys: ['workflow']
extra_pnginfo['workflow'] contains 121 nodes
✅ Prompt queued: abc123-def456
```

❌ **ПЛОХО:**
```
⚠️ extra_pnginfo is EMPTY - UI workflow not loaded!
⚠️ extra_pnginfo is EMPTY - this may cause WidgetToString errors!
```

**В логах comfyui ищите:**

✅ **ХОРОШО:**
```
got prompt
model weight dtype torch.float8_e4m3fn, manual cast: torch.float32
model_type FLUX
Using pytorch attention in VAE
...
Prompt executed in XX.XX seconds
```

❌ **ПЛОХО (старая ошибка):**
```
got prompt
!!! Exception during processing !!! 'NoneType' object is not subscriptable
Traceback (most recent call last):
  ...
  File "/opt/ComfyUI/custom_nodes/ComfyUI-KJNodes/nodes/nodes.py", line 848
    workflow = extra_pnginfo["workflow"]
TypeError: 'NoneType' object is not subscriptable
```

---

## 🔧 Включение DEBUG режима

### Временно (до перезапуска)

```bash
# Остановить бота
sudo systemctl stop telegram-bot

# Запустить вручную с DEBUG
cd /opt/image-edit-bot
sudo -u comfyui /opt/image-edit-bot/venv/bin/python -m src.main
# Логи будут в терминале, Ctrl+C чтобы остановить
```

### Постоянно (в файле конфигурации)

Отредактируйте [`src/utils/logger.py`](src/utils/logger.py):

```python
# Найдите строку с уровнем логирования
logger.add(
    sys.stdout,
    level="INFO",  # ← Измените на "DEBUG"
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
```

После изменения:
```bash
sudo systemctl restart telegram-bot
```

---

## 🎯 Конкретная диагностика проблемы

### Проверка 1: Файл UI workflow существует?

```bash
ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
```

**Ожидается:**
```
-rw-rw-r-- 1 comfyui comfyui 49K Feb  8 14:13 Qwen Image Edit Rapid.json
```

**Если "No such file":**
```bash
# Скопировать с локальной машины
scp "Qwen Image Edit Rapid.json" server:/opt/image-edit-bot/
sudo chown comfyui:comfyui "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
sudo chmod 644 "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
```

### Проверка 2: Код обновился?

```bash
# Проверить что новый код на месте
grep -n "ui_workflow_path" /opt/image-edit-bot/src/comfyui/workflow.py

# Должно найти строки типа:
# 17:    def __init__(self, template_path: Path, ui_workflow_path: Path = None):
# 23:            ui_workflow_path: Путь к UI workflow (для extra_pnginfo)
```

```bash
# Проверить client.py
grep -n "extra_pnginfo" /opt/image-edit-bot/src/comfyui/client.py

# Должно найти строки типа:
# 154:    async def queue_prompt(self, workflow: Dict, extra_pnginfo: Optional[Dict] = None) -> str:
```

**Если не находит:**
```bash
# Код не обновился, нужно обновить
cd /opt/image-edit-bot
sudo -u comfyui git pull origin main
sudo systemctl restart telegram-bot
```

### Проверка 3: Кэш Python

```bash
# Очистить все __pycache__
sudo find /opt/image-edit-bot -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Перезапустить
sudo systemctl restart telegram-bot
```

### Проверка 4: Права доступа

```bash
# Установить правильные права
sudo chown -R comfyui:comfyui /opt/image-edit-bot
sudo chmod -R 755 /opt/image-edit-bot
sudo chmod 644 "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
```

---

## 📊 Сохранение логов в файл

### Для отправки разработчику

```bash
# Логи telegram-bot
sudo journalctl -u telegram-bot -n 500 > ~/bot-logs.txt

# Логи comfyui
sudo journalctl -u comfyui -n 500 > ~/comfyui-logs.txt

# Логи обоих с сегодняшними записями
sudo journalctl -u telegram-bot -u comfyui --since today > ~/full-logs.txt
```

### Мониторинг с записью в файл

```bash
# Запись логов в файл + вывод в терминал
sudo journalctl -u telegram-bot -f | tee ~/bot-live.log
```

---

## 🚨 Быстрая диагностика (одна команда)

```bash
echo "=== Проверка файла ===" && \
ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json" && \
echo "" && \
echo "=== Проверка кода ===" && \
grep -c "ui_workflow_path" /opt/image-edit-bot/src/comfyui/workflow.py && \
echo "" && \
echo "=== Статус сервиса ===" && \
systemctl is-active telegram-bot && \
echo "" && \
echo "=== Последние 10 строк лога ===" && \
sudo journalctl -u telegram-bot -n 10 --no-pager
```

---

## 📞 Получение помощи

При создании issue включите:

1. **Версия кода:**
   ```bash
   cd /opt/image-edit-bot && git log -1 --oneline
   ```

2. **Логи telegram-bot (последние 100 строк):**
   ```bash
   sudo journalctl -u telegram-bot -n 100 --no-pager
   ```

3. **Логи comfyui (если есть ошибка):**
   ```bash
   sudo journalctl -u comfyui -n 100 --no-pager
   ```

4. **Результат проверок:**
   ```bash
   ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
   grep -c "ui_workflow_path" /opt/image-edit-bot/src/comfyui/workflow.py
   ```
