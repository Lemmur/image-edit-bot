# Исправление ошибки WidgetToString - Сводка

## 🎯 Проблема
```
TypeError: 'NoneType' object is not subscriptable
File: /opt/ComfyUI/custom_nodes/ComfyUI-KJNodes/nodes/nodes.py, line 848
Code: workflow = extra_pnginfo["workflow"]
```

## 🔧 Решение
Добавлена передача UI workflow через `extra_pnginfo` в API запросе к ComfyUI.

---

## 📦 Изменённые файлы

### Основной код
- ✅ [`src/comfyui/workflow.py`](src/comfyui/workflow.py) - загрузка UI workflow, возврат tuple
- ✅ [`src/comfyui/client.py`](src/comfyui/client.py) - передача extra_pnginfo в API
- ✅ [`src/queue/processor.py`](src/queue/processor.py) - распаковка tuple, передача extra_pnginfo
- ✅ [`src/main.py`](src/main.py) - инициализация с ui_workflow_path

### Тесты
- ✅ [`tests/test_workflow.py`](tests/test_workflow.py) - обновлены все тесты
- ✅ [`tests/test_client.py`](tests/test_client.py) - добавлен тест extra_pnginfo

### Документация
- ✅ [`CHANGELOG.md`](CHANGELOG.md) - полное описание изменений
- ✅ [`DEPLOY_FIX.md`](DEPLOY_FIX.md) - пошаговая инструкция деплоя

### Критический файл
- ✅ `Qwen Image Edit Rapid.json` - UI формат workflow (ОБЯЗАТЕЛЕН на сервере!)

---

## 🚀 Деплой на сервер

### Вариант 1: Git Pull + Перезапуск
```bash
# На сервере
cd /opt/image-edit-bot
sudo -u comfyui git pull origin main
sudo systemctl restart telegram-bot

# Проверка логов
sudo journalctl -u telegram-bot -f
```

**Ожидаемый лог:**
```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
```

### Вариант 2: Скрипт обновления
```bash
sudo bash /opt/image-edit-bot/scripts/update_bot.sh
```

### Вариант 3: Ручное копирование
Если git не настроен на сервере:
```bash
# Скопировать файлы
scp src/comfyui/workflow.py server:/opt/image-edit-bot/src/comfyui/
scp src/comfyui/client.py server:/opt/image-edit-bot/src/comfyui/
scp src/queue/processor.py server:/opt/image-edit-bot/src/queue/
scp src/main.py server:/opt/image-edit-bot/src/
scp "Qwen Image Edit Rapid.json" server:/opt/image-edit-bot/

# На сервере
sudo chown -R comfyui:comfyui /opt/image-edit-bot
sudo systemctl restart telegram-bot
```

---

## ✅ Проверка корректности

### 1. Проверка наличия UI workflow
```bash
ls -lh "/opt/image-edit-bot/Qwen Image Edit Rapid.json"
# Должен вывести: -rw-rw-r-- ... 49K ... Qwen Image Edit Rapid.json
```

### 2. Проверка логов при старте
```bash
sudo journalctl -u telegram-bot -n 50 | grep -i "workflow"
```

**Ожидается:**
```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
Workflow template loaded from workflows/qwen_image_edit.json
```

**НЕ должно быть:**
```
⚠️ UI workflow file not found
⚠️ extra_pnginfo is EMPTY
```

### 3. Проверка при обработке задачи
Отправьте тестовое изображение боту и смотрите логи:

```bash
sudo journalctl -u telegram-bot -f
```

**Ожидается:**
```
✅ extra_pnginfo includes UI workflow
✅ Including extra_pnginfo with keys: ['workflow']
```

**Ожидается в логах ComfyUI:**
```bash
sudo journalctl -u comfyui -f
```

```
got prompt
model weight dtype torch.float8_e4m3fn
Prompt executed in XX.XX seconds  # БЕЗ TypeError!
```

---

## 🐛 Отладка проблем

### Проблема: "UI workflow file not found"

**Решение:**
```bash
cd /opt/image-edit-bot
ls -lh "Qwen Image Edit Rapid.json"
# Если файла нет - скопировать с локальной машины
scp "Qwen Image Edit Rapid.json" server:/opt/image-edit-bot/
sudo chown comfyui:comfyui "Qwen Image Edit Rapid.json"
sudo chmod 644 "Qwen Image Edit Rapid.json"
sudo systemctl restart telegram-bot
```

### Проблема: "extra_pnginfo is EMPTY"

**Причины:**
1. UI workflow файл не загрузился (см. выше)
2. Бот не перезапущен после обновления кода
3. Кэш Python модулей

**Решение:**
```bash
# Очистить Python кэш
sudo find /opt/image-edit-bot -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Перезапустить бота
sudo systemctl restart telegram-bot

# Полный перезапуск (включая ComfyUI)
sudo systemctl restart telegram-bot comfyui
```

### Проблема: Ошибка все еще возникает

**Проверьте что изменения применились:**
```bash
# Проверить версию файла
sudo grep -n "ui_workflow_path" /opt/image-edit-bot/src/comfyui/workflow.py
# Должно найти строки с ui_workflow_path

sudo grep -n "extra_pnginfo" /opt/image-edit-bot/src/comfyui/client.py
# Должно найти строки с extra_pnginfo
```

---

## 📊 Технические детали

### API запрос ДО исправления
```json
{
  "prompt": { /* API формат */ },
  "client_id": "..."
  // extra_pnginfo отсутствует ❌
}
```

### API запрос ПОСЛЕ исправления
```json
{
  "prompt": { /* API формат */ },
  "client_id": "...",
  "extra_pnginfo": {
    "workflow": { /* UI формат с nodes, links и т.д. */ }
  }
}
```

---

## 📝 Чеклист

- [ ] Код обновлён на сервере
- [ ] Файл `Qwen Image Edit Rapid.json` существует
- [ ] Бот перезапущен
- [ ] Лог показывает: `✅ UI workflow loaded`
- [ ] Лог показывает: `✅ Including extra_pnginfo`
- [ ] Тестовое изображение обработано без ошибок
- [ ] TypeError больше не появляется в логах ComfyUI

---

## 🔗 Дополнительно

- Полная документация: [`CHANGELOG.md`](CHANGELOG.md)
- Инструкция деплоя: [`DEPLOY_FIX.md`](DEPLOY_FIX.md)
- Troubleshooting: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
