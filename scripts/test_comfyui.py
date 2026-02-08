#!/usr/bin/env python3
"""Тест подключения к ComfyUI API"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в path для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.comfyui.client import ComfyUIClient
from src.comfyui.workflow import WorkflowManager
from src.models.task import WorkflowParams
from loguru import logger


async def test_health_check(client: ComfyUIClient) -> bool:
    """Тест 1: Проверка доступности ComfyUI"""
    logger.info("=" * 60)
    logger.info("TEST 1: Health Check")
    logger.info("=" * 60)
    
    if await client.check_health():
        logger.success("✅ ComfyUI is running and accessible")
        return True
    else:
        logger.error("❌ ComfyUI is not available!")
        logger.info("Make sure ComfyUI is running on http://127.0.0.1:8188")
        return False


async def test_system_stats(client: ComfyUIClient) -> bool:
    """Тест 2: Получение статистики системы"""
    logger.info("=" * 60)
    logger.info("TEST 2: System Stats")
    logger.info("=" * 60)
    
    try:
        stats = await client.get_system_stats()
        logger.info(f"System stats received:")
        logger.info(f"  - Devices: {stats.get('system', {}).get('devices', 'N/A')}")
        logger.info(f"  - RAM: {stats.get('system', {}).get('ram_total', 'N/A')}")
        logger.success("✅ System stats retrieved successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to get system stats: {e}")
        return False


async def test_workflow_manager() -> bool:
    """Тест 3: Загрузка и валидация workflow template"""
    logger.info("=" * 60)
    logger.info("TEST 3: Workflow Manager")
    logger.info("=" * 60)
    
    try:
        template_path = Path("workflows/qwen_image_edit.json")
        
        if not template_path.exists():
            logger.error(f"❌ Workflow template not found: {template_path}")
            return False
        
        # Инициализация manager
        manager = WorkflowManager(template_path)
        logger.info(f"✅ Template loaded from {template_path}")
        
        # Валидация
        if not manager.validate_template():
            logger.error("❌ Template validation failed")
            return False
        
        # Создание тестового workflow
        test_params = WorkflowParams(
            input_image="test.jpg",
            positive_prompt="make it beautiful",
            negative_prompt="ugly, blurry",
            steps=8,
            seed=12345
        )
        
        workflow = manager.create_workflow(test_params)
        
        # Проверки
        assert workflow["78"]["inputs"]["image"] == "test.jpg", "Input image not set"
        assert workflow["119"]["inputs"]["prompt"] == "make it beautiful", "Positive prompt not set"
        assert workflow["77"]["inputs"]["prompt"] == "ugly, blurry", "Negative prompt not set"
        assert workflow["117"]["inputs"]["value"] == 12345, "Seed not set"
        assert workflow["115"]["inputs"]["value"] == 8, "Steps not set"
        
        logger.success("✅ Workflow manager tests passed")
        logger.info(f"  - Template nodes: {len(manager.template)}")
        logger.info(f"  - Modified workflow nodes: {len(workflow)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Workflow manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_wait_for_ready(client: ComfyUIClient) -> bool:
    """Тест 4: Ожидание готовности ComfyUI (с retry)"""
    logger.info("=" * 60)
    logger.info("TEST 4: Wait for Ready (Retry Logic)")
    logger.info("=" * 60)
    
    # Проверяем с малым количеством попыток для быстрого теста
    if await client.wait_for_ready(max_attempts=3, delay=2):
        logger.success("✅ ComfyUI is ready")
        return True
    else:
        logger.warning("⚠️  ComfyUI not ready (this may be expected if server is starting)")
        return False


async def test_upload_image(client: ComfyUIClient) -> bool:
    """Тест 5: Загрузка тестового изображения (опционально)"""
    logger.info("=" * 60)
    logger.info("TEST 5: Image Upload (Optional)")
    logger.info("=" * 60)
    
    # Ищем любое изображение для теста
    test_image_paths = [
        Path("data/input/test.jpg"),
        Path("data/input/test.png"),
        Path("test.jpg"),
        Path("test.png"),
    ]
    
    test_image = None
    for path in test_image_paths:
        if path.exists():
            test_image = path
            break
    
    if not test_image:
        logger.warning("⚠️  No test image found, skipping upload test")
        logger.info("   Create data/input/test.jpg to test image upload")
        return True  # Not a failure, just skipped
    
    try:
        result = await client.upload_image(test_image)
        logger.success(f"✅ Image uploaded: {result}")
        logger.info(f"  - Filename: {result.get('name')}")
        logger.info(f"  - Subfolder: {result.get('subfolder', '(root)')}")
        logger.info(f"  - Type: {result.get('type')}")
        return True
    except Exception as e:
        logger.error(f"❌ Image upload failed: {e}")
        return False


async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Starting ComfyUI integration tests...")
    logger.info("")
    
    results = {}
    
    # Тест workflow manager (не требует ComfyUI)
    results["workflow_manager"] = await test_workflow_manager()
    logger.info("")
    
    # Тесты требующие запущенный ComfyUI
    async with ComfyUIClient(host="127.0.0.1", port=8188) as client:
        results["health_check"] = await test_health_check(client)
        logger.info("")
        
        if results["health_check"]:
            results["system_stats"] = await test_system_stats(client)
            logger.info("")
            
            results["wait_for_ready"] = await test_wait_for_ready(client)
            logger.info("")
            
            results["upload_image"] = await test_upload_image(client)
            logger.info("")
    
    # Итоги
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("")
    logger.info(f"Total: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.success("🎉 All tests passed!")
        return True
    else:
        logger.warning(f"⚠️  {total_tests - passed_tests} test(s) failed")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
