# Инструкция по деплою исправления WidgetToString

## Проблема
Ошибка `TypeError: 'NoneType' object is not subscriptable` в ноде WidgetToString

## Решение
Добавлена поддержка `extra_pnginfo` с UI workflow

---

## Шаги для деплоя на сервер

### 1. Загрузить обновлённые файлы на сервер

```bash
# Подключиться к серверу
ssh user@your-server

# Перейти в директорию проекта
cd /path/to/image-edit-bot

# Создать резервную копию (опционально)
cp -r . ../image-edit-bot-backup-$(date +%Y%m%d)

# Загрузить изменения с Git (если используете)
git pull origin main
```

**ИЛИ** скопировать файлы вручную:

```bash
# С локальной машины
scp src/comfyui/workflow.py user@server:/path/to/image-edit-bot/src/comfyui/
scp src/comfyui/client.py user@server:/path/to/image-edit-bot/src/comfyui/
scp src/queue/processor.py user@server:/path/to/image-edit-bot/src/queue/
scp src/main.py user@server:/path/to/image-edit-bot/src/
scp "Qwen Image Edit Rapid.json" user@server:/path/to/image-edit-bot/
```

### 2. Проверить наличие UI workflow файла на сервере

```bash
# На сервере
cd /path/to/image-edit-bot
ls -lh "Qwen Image Edit Rapid.json"
```

**КРИТИЧНО**: Файл `Qwen Image Edit Rapid.json` ДОЛЖЕН существовать в корневой директории проекта!

### 3. Перезапустить бота

```bash
# Остановить бота
sudo systemctl stop image-edit-bot

# Проверить статус
sudo systemctl status image-edit-bot

# Запустить бота
sudo systemctl start image-edit-bot

# Проверить логи
sudo journalctl -u image-edit-bot -f
```

### 4. Проверить логи при запуске

Вы должны увидеть в логах:

```
✅ UI workflow loaded from Qwen Image Edit Rapid.json
```

**ЕСЛИ ВИДИТЕ:**
```
⚠️ UI workflow file not found: Qwen Image Edit Rapid.json
```

**ДЕЙСТВИЯ:**
1. Убедитесь что файл существует: `ls -lh "Qwen Image Edit Rapid.json"`
2. Проверьте права доступа: `chmod 644 "Qwen Image Edit Rapid.json"`
3. Проверьте путь в [`src/main.py:90`](src/main.py#L90)

### 5. Проверить работу при отправке запроса

При обработке задачи в логах должно появиться:

```
✅ extra_pnginfo includes UI workflow
✅ Including extra_pnginfo with keys: ['workflow']
```

**ЕСЛИ ВИДИТЕ:**
```
⚠️ extra_pnginfo is EMPTY - UI workflow not loaded!
⚠️ extra_pnginfo is EMPTY - this may cause WidgetToString errors!
```

**ДЕЙСТВИЯ:**
1. Проверьте что UI workflow загрузился при старте (шаг 4)
2. Перезапустите бота (шаг 3)

---

## Альтернативный метод: Использование скрипта обновления

Если у вас есть скрипт `scripts/update_bot.sh`:

```bash
# На сервере
cd /path/to/image-edit-bot
sudo ./scripts/update_bot.sh
```

---

## Проверка корректности исправления

### Тест 1: Проверка синтаксиса
```bash
python3 -m py_compile src/comfyui/workflow.py src/comfyui/client.py src/queue/processor.py src/main.py
```

### Тест 2: Отправка тестового изображения через бота

1. Отправьте изображение боту в Telegram
2. Добавьте промпт
3. Проверьте логи ComfyUI:

**РАНЬШЕ (ошибка):**
```
TypeError: 'NoneType' object is not subscriptable
```

**СЕЙЧАС (успех):**
```
got prompt
model weight dtype torch.float8_e4m3fn
Prompt executed in XX.XX seconds
```

---

## Откат изменений (если что-то пошло не так)

```bash
cd /path/to/image-edit-bot

# Восстановить из резервной копии
cp ../image-edit-bot-backup-YYYYMMDD/src/comfyui/workflow.py src/comfyui/
cp ../image-edit-bot-backup-YYYYMMDD/src/comfyui/client.py src/comfyui/
cp ../image-edit-bot-backup-YYYYMMDD/src/queue/processor.py src/queue/
cp ../image-edit-bot-backup-YYYYMMDD/src/main.py src/

# Перезапустить
sudo systemctl restart image-edit-bot
```

---

## Чеклист деплоя

- [ ] Файлы обновлены на сервере
- [ ] `Qwen Image Edit Rapid.json` существует в корне проекта
- [ ] Бот перезапущен
- [ ] В логах видно: `✅ UI workflow loaded from Qwen Image Edit Rapid.json`
- [ ] При обработке задачи видно: `✅ Including extra_pnginfo with keys: ['workflow']`
- [ ] Тестовое изображение обработано без ошибок
- [ ] Ошибка `TypeError: 'NoneType' object is not subscriptable` больше не появляется

---

## Поддержка

Если проблема сохраняется после деплоя:

1. Проверьте логи бота: `sudo journalctl -u image-edit-bot -f`
2. Проверьте логи ComfyUI: `sudo journalctl -u comfyui -f`
3. Убедитесь что все warning'и из логов устранены
4. Проверьте что файл `Qwen Image Edit Rapid.json` существует и доступен для чтения

Для дополнительной отладки включите DEBUG логирование в [`src/utils/logger.py`](src/utils/logger.py)
