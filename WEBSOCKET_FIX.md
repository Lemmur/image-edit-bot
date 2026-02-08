# Исправление WebSocket Timeout

## Проблема
ComfyUI успешно обрабатывает изображение, но бот не получает результат:
- ComfyUI завершает обработку за ~224 секунды
- WebSocket не получает финальное событие `executing` с `node=null`
- Бот срабатывает по таймауту (300s)
- Пользователь не получает результат

## Логи ошибки
```
Feb 08 16:33:05 bot comfyui[3715]: Prompt executed in 224.59 seconds
Feb 08 16:34:20 bot telegram-bot[4487]: ERROR | Task 95a80bb6 timed out after 300s
Feb 08 16:34:20 bot telegram-bot[4487]: ERROR | Task 95a80bb6 failed: Processing timeout (300s)
```

## Решение

### 1. History API Fallback
Добавлена проверка через History API параллельно с WebSocket:
- Каждые 10 секунд проверяется History API
- Если задача завершена в истории, но WebSocket молчит - берём результат из истории
- Финальная проверка через History API если outputs пустой

### 2. Изменённые файлы

#### `src/comfyui/websocket.py`
- Добавлен параметр `base_url` для доступа к History API
- Добавлена функция `check_history()` внутри `track_progress()`
- WebSocket ожидание сообщений с таймаутом 5 секунд для периодических проверок
- Каждые 10 секунд проверка истории
- Финальная проверка через History API если outputs пустой

#### `src/queue/processor.py`
- Передача `base_url` в `track_progress()`
- Исправлен `ws_url` (убрал `?clientId=` из базового URL)

### 3. Логика работы

```
┌─────────────────────────────────────────┐
│  WebSocket получение событий            │
│  (с таймаутом 5 сек на recv)            │
└──────────────┬──────────────────────────┘
               │
               ▼
       Получено событие?
               │
       ┌───────┴───────┐
       │               │
      ДА              НЕТ
       │               │
       │               ▼
       │       Прошло 10 сек
       │       с последней
       │       проверки?
       │               │
       │       ┌───────┴────────┐
       │       │                │
       │      ДА               НЕТ
       │       │                │
       │       ▼                ▼
       │   Check History   Continue
       │   API                waiting
       │       │
       │   ┌───┴────┐
       │   │        │
       │ Готово?   Нет
       │   │        │
       │  ДА        │
       │   │        │
       ▼   ▼        ▼
   Обработка   Continue
   события     waiting
       │
       ▼
   executing with
   node=null?
       │
      ДА
       │
       ▼
   Завершение
       │
       ▼
   outputs пустой?
       │
   ┌───┴────┐
   │        │
  ДА       НЕТ
   │        │
   ▼        │
Final       │
History     │
Check       │
   │        │
   └────┬───┘
        │
        ▼
   Возврат
   результата
```

### 4. Преимущества
- ✅ Надёжное получение результата даже если WebSocket пропустил событие
- ✅ Не ломает существующую логику
- ✅ Минимальная дополнительная нагрузка (проверка раз в 10 сек)
- ✅ Работает с текущим API ComfyUI без изменений

### 5. Деплой на сервер

```bash
# 1. Подключиться к серверу
ssh evseev@bot

# 2. Перейти в директорию проекта
cd /home/evseev/image-edit-bot

# 3. Сделать бэкап
cp src/comfyui/websocket.py src/comfyui/websocket.py.backup
cp src/queue/processor.py src/queue/processor.py.backup

# 4. Загрузить новые файлы (через scp или git)
# Вариант 1: Git
git pull origin main

# Вариант 2: SCP (выполнить на локальной машине)
scp src/comfyui/websocket.py evseev@bot:/home/evseev/image-edit-bot/src/comfyui/
scp src/queue/processor.py evseev@bot:/home/evseev/image-edit-bot/src/queue/

# 5. Перезапустить бота
sudo systemctl restart telegram-bot

# 6. Проверить статус
sudo systemctl status telegram-bot

# 7. Проверить логи
sudo journalctl -u telegram-bot -f
```

### 6. Тестирование

1. Отправить изображение боту
2. Отследить логи:
   ```bash
   sudo journalctl -u telegram-bot -f | grep -E "(WebSocket|History|Progress)"
   ```
3. Проверить что появляются логи:
   - `Starting WebSocket progress tracking`
   - Если WebSocket молчит > 10 сек: `Checking History API (WebSocket no activity)...`
   - При завершении: `Progress tracking completed, outputs: ['102']`
4. Проверить что пользователь получил изображение

### 7. Откат при проблемах

```bash
# Если что-то пошло не так
sudo systemctl stop telegram-bot

# Восстановить бэкапы
cp src/comfyui/websocket.py.backup src/comfyui/websocket.py
cp src/queue/processor.py.backup src/queue/processor.py

# Перезапустить
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## Дополнительная диагностика

Если проблема повторится, проверить:

```bash
# 1. История задач в ComfyUI
curl http://127.0.0.1:8188/history | jq

# 2. Текущая очередь
curl http://127.0.0.1:8188/queue | jq

# 3. WebSocket события (в отдельном терминале)
websocat ws://127.0.0.1:8188/ws?clientId=test-client
```
