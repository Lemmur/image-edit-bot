#!/usr/bin/env python3
"""
Скрипт для управления ComfyUI - запуск, остановка, проверка статуса

Использование:
    python scripts/manage_comfyui.py start
    python scripts/manage_comfyui.py stop
    python scripts/manage_comfyui.py status
    python scripts/manage_comfyui.py restart
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

from src.comfyui.launcher import ComfyUILauncher
from src.comfyui.client import ComfyUIClient


async def get_config():
    """Получение конфигурации из .env"""
    load_dotenv()
    
    comfyui_dir = os.getenv("COMFYUI_DIR")
    if not comfyui_dir:
        logger.error("COMFYUI_DIR not set in .env")
        sys.exit(1)
    
    return {
        "dir": Path(comfyui_dir),
        "host": os.getenv("COMFYUI_HOST", "127.0.0.1"),
        "port": int(os.getenv("COMFYUI_PORT", "8188")),
        "venv": Path(os.getenv("COMFYUI_VENV")) if os.getenv("COMFYUI_VENV") else None,
        "args": os.getenv("COMFYUI_ARGS", "")
    }


async def start_comfyui():
    """Запуск ComfyUI"""
    config = await get_config()
    
    launcher = ComfyUILauncher(
        comfyui_dir=config["dir"],
        host=config["host"],
        port=config["port"],
        venv_path=config["venv"],
        extra_args=config["args"]
    )
    
    if not launcher.validate_installation():
        sys.exit(1)
    
    # Проверяем, не запущен ли уже
    client = ComfyUIClient(host=config["host"], port=config["port"])
    await client.connect()
    
    if await client.check_health():
        logger.success(f"✅ ComfyUI already running at http://{config['host']}:{config['port']}")
        await client.close()
        return
    
    await client.close()
    
    # Запускаем
    logger.info(f"Starting ComfyUI from {config['dir']}...")
    if await launcher.start():
        logger.success(f"✅ ComfyUI started at http://{config['host']}:{config['port']}")
        logger.info("Press Ctrl+C to stop")
        
        # Ждем завершения
        try:
            await launcher.wait()
        except KeyboardInterrupt:
            logger.info("\nStopping ComfyUI...")
            await launcher.stop()
    else:
        logger.error("Failed to start ComfyUI")
        sys.exit(1)


async def stop_comfyui():
    """Остановка ComfyUI (если запущен через этот скрипт)"""
    logger.warning("Note: This only works if ComfyUI was started via this script")
    logger.info("To stop a manually started ComfyUI, use: pkill -f 'python.*main.py.*--port 8188'")
    
    # Проверяем статус
    config = await get_config()
    client = ComfyUIClient(host=config["host"], port=config["port"])
    await client.connect()
    
    if await client.check_health():
        logger.info(f"ComfyUI is running at http://{config['host']}:{config['port']}")
        logger.info("To stop it, find the process and kill it:")
        logger.info(f"  ps aux | grep 'main.py.*{config['port']}'")
    else:
        logger.info("ComfyUI is not running")
    
    await client.close()


async def check_status():
    """Проверка статуса ComfyUI"""
    config = await get_config()
    
    logger.info(f"ComfyUI directory: {config['dir']}")
    logger.info(f"Checking http://{config['host']}:{config['port']}...")
    
    client = ComfyUIClient(host=config["host"], port=config["port"])
    await client.connect()
    
    if await client.check_health():
        logger.success(f"✅ ComfyUI is running")
        
        # Получаем системную статистику
        try:
            stats = await client.get_system_stats()
            logger.info(f"System stats: {stats}")
        except Exception as e:
            logger.warning(f"Could not get system stats: {e}")
    else:
        logger.error("❌ ComfyUI is not running")
        logger.info(f"To start: python scripts/manage_comfyui.py start")
    
    await client.close()


async def restart_comfyui():
    """Перезапуск ComfyUI"""
    logger.info("Restarting ComfyUI...")
    
    # Для перезапуска нужно убить процесс
    config = await get_config()
    
    client = ComfyUIClient(host=config["host"], port=config["port"])
    await client.connect()
    
    if await client.check_health():
        logger.warning("ComfyUI is running. Please stop it manually first:")
        logger.info(f"  pkill -f 'python.*main.py.*--port {config['port']}'")
        logger.info("Then run: python scripts/manage_comfyui.py start")
    else:
        logger.info("ComfyUI is not running, starting...")
        await start_comfyui()
    
    await client.close()


def print_usage():
    """Вывод справки"""
    print(__doc__)
    print("Commands:")
    print("  start   - Start ComfyUI")
    print("  stop    - Show instructions to stop ComfyUI")
    print("  status  - Check if ComfyUI is running")
    print("  restart - Restart ComfyUI")
    print()
    print("Environment variables (set in .env):")
    print("  COMFYUI_DIR      - Path to ComfyUI installation (required)")
    print("  COMFYUI_HOST     - Host to listen on (default: 127.0.0.1)")
    print("  COMFYUI_PORT     - Port to listen on (default: 8188)")
    print("  COMFYUI_VENV     - Path to Python venv (optional)")
    print("  COMFYUI_ARGS     - Additional launch arguments (optional)")


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        await start_comfyui()
    elif command == "stop":
        await stop_comfyui()
    elif command == "status":
        await check_status()
    elif command == "restart":
        await restart_comfyui()
    elif command in ("-h", "--help", "help"):
        print_usage()
    else:
        logger.error(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
