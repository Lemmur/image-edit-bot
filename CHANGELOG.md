# Changelog

## [2026-02-08] - Исправление ошибки NoneType в WidgetToString

### Проблема
ComfyUI возвращал ошибку при выполнении workflow:
```
TypeError: 'NoneType' object is not subscriptable
File "/opt/ComfyUI/custom_nodes/ComfyUI-KJNodes/nodes/nodes.py", line 848
workflow = extra_pnginfo["workflow"]
```

### Причина
Нода `WidgetToString` из `ComfyUI-KJNodes` требует доступ к `extra_pnginfo["workflow"]` для извлечения информации о виджетах, но мы не передавали `extra_pnginfo` в API запросе к ComfyUI.

### Решение
Добавлена поддержка `extra_pnginfo` с UI workflow для совместимости с custom нодами:

#### 1. Модифицирован `WorkflowManager` ([`src/comfyui/workflow.py`](src/comfyui/workflow.py))
- Добавлен параметр `ui_workflow_path` в конструктор
- Добавлен метод `_load_ui_workflow()` для загрузки UI формата workflow
- Метод `create_workflow()` теперь возвращает `tuple[Dict, Dict]`:
  - `workflow` - API формат для ComfyUI (node_id → inputs)
  - `extra_pnginfo` - метаданные с UI workflow (для custom нод)

#### 2. Модифицирован `ComfyUIClient` ([`src/comfyui/client.py`](src/comfyui/client.py))
- Добавлен параметр `extra_pnginfo` в метод `queue_prompt()`
- `extra_pnginfo` включается в payload при отправке в ComfyUI API

#### 3. Обновлен `TaskProcessor` ([`src/queue/processor.py`](src/queue/processor.py))
- Распаковка результата `create_workflow()` на `workflow, extra_pnginfo`
- Передача `extra_pnginfo` в `queue_prompt()`

#### 4. Обновлена инициализация в [`src/main.py`](src/main.py)
- `WorkflowManager` инициализируется с путем к UI workflow:
  ```python
  ui_workflow_path = Path("Qwen Image Edit Rapid.json")
  self.workflow_manager = WorkflowManager(workflow_path, ui_workflow_path)
  ```

#### 5. Обновлены тесты
- [`tests/test_workflow.py`](tests/test_workflow.py) - все тесты обновлены для распаковки tuple
- [`tests/test_client.py`](tests/test_client.py) - добавлен тест `test_queue_prompt_with_extra_pnginfo`

### Формат данных

**API формат** (для ComfyUI execution):
```json
{
  "78": {
    "class_type": "LoadImage",
    "inputs": {"image": "input.jpg"}
  }
}
```

**UI формат** (для extra_pnginfo):
```json
{
  "id": "...",
  "nodes": [...],
  "links": [...],
  "last_node_id": 121
}
```

**API запрос к ComfyUI**:
```json
{
  "prompt": { /* API формат */ },
  "client_id": "...",
  "extra_pnginfo": {
    "workflow": { /* UI формат */ }
  }
}
```

### Проверка
```bash
python3 -m py_compile src/comfyui/workflow.py src/comfyui/client.py src/queue/processor.py src/main.py
```

### Backwards Compatibility
✅ Обратная совместимость сохранена:
- Если `ui_workflow_path` не указан или файл не существует, `extra_pnginfo` будет пустым dict
- `queue_prompt()` работает без `extra_pnginfo` (опциональный параметр)

### Зависимые файлы
- `Qwen Image Edit Rapid.json` - UI формат workflow (экспортирован из ComfyUI)
- `workflows/qwen_image_edit.json` - API формат workflow

---

## Дополнительные замечания
Нода **WidgetToString** (Node 104) используется для динамического извлечения значений виджетов из других нод во время выполнения. Для корректной работы ей требуется полная информация о workflow в UI формате через `extra_pnginfo`.
