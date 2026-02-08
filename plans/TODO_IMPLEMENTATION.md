# 📋 План реализации — пошаговый TODO

> Этот документ — чеклист для Code mode. Каждый пункт — отдельный атомарный коммит.

---

## Phase 0: Инфраструктура проекта

- [ ] Создать структуру директорий проекта, удалить пустую `plans/config-templates/`
- [ ] Создать `requirements.txt` с зависимостями
- [ ] Создать `.env.example` с шаблоном переменных
- [ ] Создать `config.yaml` с дефолтными параметрами workflow (включая default negative prompt)
- [ ] Создать `.gitignore` для Python + data/logs/venv/.env
- [ ] **КРИТИЧНО**: Конвертировать `Qwen Image Edit Rapid.json` из UI-формата в API-формат (`workflows/qwen_image_edit.json`). UI-формат использует `type`/`pos`/`size`/`links`. API-формат использует node ID как ключ + `class_type` + `inputs` с конкретными значениями.

---

## Phase 1: Core — Конфигурация и утилиты

- [ ] Реализовать `src/models/config.py` — pydantic-модели конфигурации
- [ ] Реализовать `src/utils/config_loader.py` — загрузка .env + config.yaml
- [ ] Реализовать `src/utils/logger.py` — setup loguru
- [ ] Реализовать `src/models/task.py` — dataclass Task + WorkflowParams (с default negative prompt из workflow)

---

## Phase 2: ComfyUI клиент

- [ ] Реализовать `src/comfyui/client.py` — REST клиент (upload image, queue prompt, get history, get image, check_health)
- [ ] Реализовать `src/comfyui/client.py` — health check с retry loop при старте (ComfyUI может грузить модели ~60 сек)
- [ ] Реализовать `src/comfyui/websocket.py` — WebSocket обработчик прогресса с таймаутом (default 300 сек)
- [ ] Реализовать `src/comfyui/workflow.py` — WorkflowManager (загрузка API-формата шаблона, модификация узлов по node ID)
- [ ] Создать `scripts/test_comfyui.py` — standalone тест подключения к ComfyUI API

---

## Phase 3: Очередь задач

- [ ] Реализовать `src/queue/task_queue.py` — asyncio.Queue обертка
- [ ] Реализовать `src/queue/processor.py` — TaskProcessor (цикл обработки задач с timeout и error recovery)

---

## Phase 4: Telegram Bot

- [ ] Реализовать `src/bot/states.py` — FSM состояния (ImageEditStates)
- [ ] Реализовать `src/bot/keyboards.py` — inline клавиатуры для настроек
- [ ] Реализовать `src/bot/filters.py` — фильтры (whitelist пользователей, rate limiting)
- [ ] Реализовать `src/bot/handlers.py` — обработчики команд и сообщений
- [ ] Реализовать `src/bot/handlers.py` — поддержка photo И document (Telegram сжимает photo до 1280px; document сохраняет оригинал)
- [ ] Реализовать `src/storage/file_manager.py` — управление файлами (скачивание, автоочистка по расписанию)

---

## Phase 5: Точка входа и интеграция

- [ ] Реализовать `src/main.py` — сборка всех компонентов, запуск бота + processor
- [ ] Реализовать `src/main.py` — graceful shutdown (SIGTERM/SIGINT → завершить текущую задачу → остановиться)
- [ ] Реализовать `src/__init__.py` и все промежуточные `__init__.py`

---

## Phase 6: Деплой и серверная инфраструктура

- [ ] Создать `scripts/setup_server.sh` — главный скрипт полной установки сервера
- [ ] Создать `scripts/install_comfyui.sh` — установка ComfyUI + PyTorch + CUDA
- [ ] Создать `scripts/download_models.sh` — скачивание checkpoint, text encoder, VAE, LoRA
- [ ] Создать `scripts/install_custom_nodes.sh` — установка кастомных нод (RES4LYF, KJNodes, Image Saver, rgthree)
- [ ] Создать `scripts/install_bot.sh` — установка бота, venv, зависимости
- [ ] Создать `scripts/setup_services.sh` — создание systemd сервисов (comfyui.service + telegram-bot.service)

---

## Phase 7: Документация и тесты

- [ ] Обновить `README.md` с инструкциями по установке и запуску
- [ ] Создать `tests/test_workflow.py` — тест конвертации и модификации workflow JSON
- [ ] Создать `tests/test_client.py` — тест ComfyUI клиента (mock)
- [ ] Создать `tests/test_queue.py` — тест системы очередей

---

## ⚠️ Важные нюансы (обнаружены при ревью)

1. **Workflow API формат**: ComfyUI API НЕ принимает UI-формат JSON. Нужна конвертация: `type` → `class_type`, числовые `link` → конкретные значения в `inputs`. Это делается один раз при подготовке шаблона.

2. **Telegram photo vs document**: При отправке как photo Telegram сжимает до 1280px. Для полного качества нужно поддержать отправку как document.

3. **Default negative prompt**: В workflow уже есть: `ugly, blurry, distorted, artifacts, bad, wrong, low quality, anime, digital art, semirealistic, cartoon, manga, drawing, fake, unreal`. Должен быть в config.yaml.

4. **ComfyUI startup delay**: Модель грузится ~30-60 сек. Бот должен retry health check при старте.

5. **Generation timeout**: Если ComfyUI зависнет — нужен таймаут (300 сек по умолчанию).

6. **Graceful shutdown**: При `systemctl stop` текущая задача должна завершиться, а не оборваться.

7. **File cleanup**: Автоочистка старых файлов из `data/` по расписанию (каждые N часов).

---

## Порядок коммитов

```
1. chore: project structure and configs
2. chore: convert workflow to API format
3. feat: config loader and logger
4. feat: ComfyUI API client with health check and timeout
5. feat: workflow manager
6. feat: task queue and processor with graceful shutdown
7. feat: telegram bot handlers (photo + document support)
8. feat: main entry point with signal handling
9. ops: systemd services and server install scripts
10. docs: README and setup guide
11. test: unit tests
```
