# ComfyUI Workflow Node Mapping

Документация для модификации узлов в `workflows/qwen_image_edit.json`

## Критические узлы (модифицируются в runtime)

| Node ID | Class Type | Parameter | Type | Description |
|---------|------------|-----------|------|-------------|
| **78** | LoadImage | `inputs.image` | string | Имя загруженного изображения |
| **119** | TextEncodeQwenImageEditPlus | `inputs.prompt` | string | Positive prompt (что добавить) |
| **77** | TextEncodeQwenImageEdit | `inputs.prompt` | string | Negative prompt (чего избегать) |
| **117** | PrimitiveInt | `inputs.value` | int | Seed (0 = random) |
| **115** | INTConstant | `inputs.value` | int | Количество шагов сэмплинга |
| **121** | ClownsharKSampler_Beta | `inputs.cfg` | float | CFG scale (обычно 1.0-2.0) |
| **121** | ClownsharKSampler_Beta | `inputs.sampler_name` | string | Sampler (linear/euler, etc) |
| **121** | ClownsharKSampler_Beta | `inputs.scheduler` | string | Scheduler (simple, etc) |
| **121** | ClownsharKSampler_Beta | `inputs.eta` | float | Eta parameter (0.0-1.0) |
| **121** | ClownsharKSampler_Beta | `inputs.denoise` | float | Denoise strength (0.0-1.0) |

## Узлы с connections (НЕ модифицируются напрямую)

| Node ID | Parameter | Connection | Comment |
|---------|-----------|------------|---------|
| **121** | `inputs.steps` | `["115", 0]` | Берет значение из Node 115 |
| **121** | `inputs.seed` | `["117", 0]` | Берет значение из Node 117 |

## Статические узлы (остаются неизменными)

| Node ID | Class Type | Description |
|---------|------------|-------------|
| **118** | CheckpointLoaderSimple | Загрузка модели Qwen-Rapid-AIO-NSFW-v11.4 |
| **103** | Power Lora Loader | Загрузка LoRA (next-scene_lora-v2-3000) |
| **93** | ImageScaleToTotalPixels | Масштабирование до 1MP |
| **66** | ModelSamplingAuraFlow | Model sampling с shift=3.0 |
| **75** | CFGNorm | CFG нормализация |
| **88** | VAEEncode | Кодирование изображения в latent |
| **8** | VAEDecode | Декодирование latent в изображение |
| **102** | Image Saver Simple | Сохранение результата (откуда берем outputs) |
| **106** | Image Saver Metadata | Метаданные для сохранения |

## Output Node

**Node 102** (Image Saver Simple) - результирующие изображения берутся из:
```json
{
  "outputs": {
    "102": {
      "images": [
        {
          "filename": "2026-02-08-123000_QwenRapid_12345.webp",
          "subfolder": "qwen_edit/2026-02-08",
          "type": "output"
        }
      ]
    }
  }
}
```

## Валидация

Проверяемые Node IDs в `WorkflowManager.validate_template()`:
- ✅ 78 - LoadImage
- ✅ 118 - CheckpointLoaderSimple
- ✅ 119 - TextEncodeQwenImageEditPlus
- ✅ 77 - TextEncodeQwenImageEdit
- ✅ 117 - PrimitiveInt (seed)
- ✅ 115 - INTConstant (steps)
- ✅ 121 - ClownsharKSampler_Beta
- ✅ 102 - Image Saver Simple (output)

## Примечания

1. **Seed генерация**: Если `seed <= 0`, генерируется random seed в диапазоне `[0, 2^32-1]`
2. **Deep copy**: Всегда используется `copy.deepcopy(template)` для избежания мутации оригинального шаблона
3. **Steps connection**: Node 121 получает steps через connection от Node 115, поэтому мы модифицируем Node 115
4. **Seed connection**: Node 121 получает seed через connection от Node 117, поэтому мы модифицируем Node 117
