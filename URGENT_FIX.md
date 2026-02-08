# 🚨 СРОЧНОЕ ИСПРАВЛЕНИЕ - UI workflow не загружается

## Проблема из логов

В логах есть:
```
✅ Including extra_pnginfo with keys: ['workflow']  ← extra_pnginfo передаётся
```

Но ошибка всё равно возникает:
```
TypeError: 'NoneType' object is not subscriptable  ← extra_pnginfo["workflow"] = None
```

**Это значит:** `extra_pnginfo` содержит ключ `"workflow"`, но значение этого ключа = `None`!

---

## Причина

В логах НЕТ строки:
```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
```

Это значит файл **НЕ ЗАГРУЗИЛСЯ** при запуске бота!

---

## СРОЧНЫЕ ДЕЙСТВИЯ

### 1. Проверить логи запуска бота

```bash
# Перезапустить бота и смотреть логи
sudo systemctl restart telegram-bot && sudo journalctl -u telegram-bot -f
```

**Ищите в первых строках:**

❌ **ПЛОХО (файл НЕ найден):**
```
⚠️ UI workflow file not found: Qwen Image Edit Rapid.json
⚠️ No UI workflow path provided - extra_pnginfo will be empty
```

✅ **ХОРОШО (файл найден):**
```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
Workflow template loaded from workflows/qwen_image_edit.json
```

### 2. Если файл НЕ найден

```bash
# Проверить существование файла
ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
```

**Если "No such file":**

#### Вариант А: Скопировать с локальной машины

```bash
# С локальной машины
scp "Qwen Image Edit Rapid.json" server:/tmp/
```

```bash
# На сервере
sudo mv /tmp/"Qwen Image Edit Rapid.json" /opt/image-edit-bot/
sudo chown comfyui:comfyui "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
sudo chmod 644 "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
```

#### Вариант Б: Загрузить из репозитория

```bash
# На сервере
cd /opt/image-edit-bot
sudo -u comfyui git pull origin main

# Проверить что файл появился
ls -lh "Qwen Image Edit Rapid.json"
```

### 3. Обновить код бота на сервере

```bash
cd /opt/image-edit-bot
sudo -u comfyui git pull origin main
```

### 4. Перезапустить и проверить

```bash
# Перезапустить
sudo systemctl restart telegram-bot

# Смотреть логи
sudo journalctl -u telegram-bot -f
```

**Теперь ДОЛЖНЫ увидеть:**

```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
Workflow template loaded from workflows/qwen_image_edit.json
Template nodes: ['78', '118', '103', '104', '93', ...]
```

### 5. Тест - отправить изображение

После перезапуска отправьте изображение боту.

**Должны увидеть в логах:**

```
Creating workflow with user parameters
✅ extra_pnginfo includes UI workflow (121 nodes)  ← НОВАЯ СТРОКА!
✅ Workflow created successfully
Returning: workflow=23 nodes, extra_pnginfo=with workflow
Queueing prompt to ComfyUI...
✅ Including extra_pnginfo with 121 nodes in workflow  ← ОБНОВЛЁННАЯ СТРОКА!
```

**В логах ComfyUI:**
```
got prompt
model weight dtype torch.float8_e4m3fn
Prompt executed in XX.XX seconds  ← БЕЗ ОШИБКИ!
```

---

## Быстрая диагностика (одна команда)

```bash
echo "=== 1. Проверка файла ===" && \
ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json" 2>&1 && \
echo "" && \
echo "=== 2. Проверка кода ===" && \
(grep -m 1 "ui_workflow_path = Path" /opt/image-edit-bot/src/main.py || echo "ОШИБКА: код не обновлён") && \
echo "" && \
echo "=== 3. Перезапуск бота ===" && \
sudo systemctl restart telegram-bot && sleep 2 && \
echo "" && \
echo "=== 4. Логи запуска (поиск UI workflow) ===" && \
sudo journalctl -u telegram-bot -n 50 --no-pager | grep -i "workflow\|extra_pnginfo" || echo "НЕТ упоминаний workflow в логах!"
```

---

## Если всё ещё не работает

### Проверка 1: Путь в src/main.py

```bash
grep -A 2 "ui_workflow_path" /opt/image-edit-bot/src/main.py
```

**Должно быть:**
```python
ui_workflow_path = Path("Qwen Image Edit Rapid.json")  # UI формат для extra_pnginfo
self.workflow_manager = WorkflowManager(workflow_path, ui_workflow_path)
```

**Если НЕТ этой строки** - код не обновился:
```bash
cd /opt/image-edit-bot
sudo -u comfyui git status
sudo -u comfyui git pull origin main --force
sudo systemctl restart telegram-bot
```

### Проверка 2: Рабочая директория

```bash
# Проверить из какой директории запускается бот
sudo systemctl cat telegram-bot | grep WorkingDirectory
```

**Должно быть:**
```
WorkingDirectory=/opt/image-edit-bot
```

Если WorkingDirectory другой или не указан:
```bash
# Отредактировать service файл
sudo nano /etc/systemd/system/telegram-bot.service

# Добавить/исправить строку
WorkingDirectory=/opt/image-edit-bot

# Перечитать конфигурацию
sudo systemctl daemon-reload
sudo systemctl restart telegram-bot
```

### Проверка 3: Абсолютный путь

Если проблема сохраняется, используйте абсолютный путь.

Отредактировать `/opt/image-edit-bot/src/main.py`:

```python
# БЫЛО:
ui_workflow_path = Path("Qwen Image Edit Rapid.json")

# СДЕЛАТЬ:
ui_workflow_path = Path("/opt/image-edit-bot/Qwen Image Edit Rapid.json")
```

Затем:
```bash
sudo systemctl restart telegram-bot
```

---

## Контрольная проверка после всех действий

```bash
# 1. Файл существует?
ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json"

# 2. Код обновлён?
grep "ui_workflow_path" /opt/image-edit-bot/src/main.py

# 3. Бот запущен?
systemctl is-active telegram-bot

# 4. UI workflow загрузился?
sudo journalctl -u telegram-bot -n 100 | grep "UI workflow loaded"

# 5. Отправить тестовое изображение и проверить:
sudo journalctl -u telegram-bot -u comfyui -f
```

**Успех = нет ошибки TypeError в логах ComfyUI!**
