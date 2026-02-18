"""ComfyUI Launcher - управление запуском внешней установки ComfyUI"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


class ComfyUILauncher:
    """Управление запуском и остановкой ComfyUI"""
    
    def __init__(
        self,
        comfyui_dir: Path,
        host: str = "127.0.0.1",
        port: int = 8188,
        venv_path: Optional[Path] = None,
        extra_args: str = ""
    ):
        """
        Инициализация лаунчера
        
        Args:
            comfyui_dir: Путь к директории ComfyUI
            host: Хост для прослушивания
            port: Порт для прослушивания
            venv_path: Путь к Python venv (опционально)
            extra_args: Дополнительные аргументы запуска
        """
        self.comfyui_dir = Path(comfyui_dir)
        self.host = host
        self.port = port
        self.venv_path = Path(venv_path) if venv_path else self.comfyui_dir / "venv"
        self.extra_args = extra_args
        
        self.process: Optional[asyncio.subprocess.Process] = None
        self._stdout_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        
    def validate_installation(self) -> bool:
        """
        Проверка валидности установки ComfyUI
        
        Returns:
            True если установка валидна
        """
        if not self.comfyui_dir.exists():
            logger.error(f"ComfyUI directory not found: {self.comfyui_dir}")
            return False
        
        main_py = self.comfyui_dir / "main.py"
        if not main_py.exists():
            logger.error(f"ComfyUI main.py not found: {main_py}")
            return False
        
        # Проверяем venv
        if self.venv_path and not self.venv_path.exists():
            logger.warning(f"Venv not found at {self.venv_path}, will use system Python")
            
        logger.info(f"✅ ComfyUI installation validated at {self.comfyui_dir}")
        return True
    
    def _get_python_executable(self) -> str:
        """Получить путь к Python исполняемому файлу"""
        if self.venv_path:
            if sys.platform == "win32":
                python_path = self.venv_path / "Scripts" / "python.exe"
            else:
                python_path = self.venv_path / "bin" / "python"
            
            if python_path.exists():
                return str(python_path)
        
        # Fallback на системный Python
        return sys.executable
    
    def _build_command(self) -> list:
        """Построение команды запуска"""
        python = self._get_python_executable()
        main_py = self.comfyui_dir / "main.py"
        
        cmd = [
            python,
            str(main_py),
            "--listen", self.host,
            "--port", str(self.port),
        ]
        
        # Добавляем дополнительные аргументы
        if self.extra_args:
            # Разбиваем строку на аргументы, учитывая кавычки
            import shlex
            cmd.extend(shlex.split(self.extra_args))
        
        return cmd
    
    async def start(self) -> bool:
        """
        Запуск ComfyUI в отдельном процессе
        
        Returns:
            True если запуск успешен
        """
        if not self.validate_installation():
            return False
        
        if self.process and self.process.returncode is None:
            logger.warning("ComfyUI is already running")
            return True
        
        cmd = self._build_command()
        logger.info(f"Starting ComfyUI: {' '.join(cmd)}")
        
        try:
            # Запуск процесса
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.comfyui_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Наследуем переменные окружения
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            
            # Запускаем задачи для чтения вывода
            self._stdout_task = asyncio.create_task(self._read_stdout())
            self._stderr_task = asyncio.create_task(self._read_stderr())
            
            logger.success(f"✅ ComfyUI process started (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start ComfyUI: {e}")
            return False
    
    async def _read_stdout(self):
        """Чтение stdout процесса ComfyUI"""
        if not self.process or not self.process.stdout:
            return
        
        try:
            async for line in self.process.stdout:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    logger.info(f"[ComfyUI] {decoded}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading ComfyUI stdout: {e}")
    
    async def _read_stderr(self):
        """Чтение stderr процесса ComfyUI"""
        if not self.process or not self.process.stderr:
            return
        
        try:
            async for line in self.process.stderr:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    # Некоторые сообщения ComfyUI идут в stderr
                    if "error" in decoded.lower() or "exception" in decoded.lower():
                        logger.error(f"[ComfyUI] {decoded}")
                    else:
                        logger.debug(f"[ComfyUI stderr] {decoded}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading ComfyUI stderr: {e}")
    
    async def stop(self, timeout: int = 30):
        """
        Остановка ComfyUI
        
        Args:
            timeout: Таймаут ожидания завершения в секундах
        """
        if not self.process or self.process.returncode is not None:
            logger.info("ComfyUI is not running")
            return
        
        logger.info("Stopping ComfyUI...")
        
        # Отменяем задачи чтения
        if self._stdout_task:
            self._stdout_task.cancel()
        if self._stderr_task:
            self._stderr_task.cancel()
        
        try:
            # Отправляем SIGTERM
            self.process.terminate()
            
            # Ждем завершения
            try:
                await asyncio.wait_for(self.process.wait(), timeout=timeout)
                logger.success("✅ ComfyUI stopped gracefully")
            except asyncio.TimeoutError:
                # Принудительное завершение
                logger.warning("ComfyUI didn't stop in time, killing...")
                self.process.kill()
                await self.process.wait()
                logger.success("✅ ComfyUI killed")
                
        except ProcessLookupError:
            logger.warning("ComfyUI process already terminated")
        except Exception as e:
            logger.error(f"Error stopping ComfyUI: {e}")
    
    def is_running(self) -> bool:
        """Проверка, запущен ли процесс"""
        return self.process is not None and self.process.returncode is None
    
    async def wait(self) -> int:
        """
        Ожидание завершения процесса
        
        Returns:
            Код возврата процесса
        """
        if self.process:
            return await self.process.wait()
        return -1
