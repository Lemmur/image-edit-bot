"""ComfyUI WebSocket обработчик прогресса"""

from typing import Dict, Optional, Callable, Awaitable
import json
import asyncio

import websockets
import aiohttp
from loguru import logger


async def track_progress(
    ws_url: str,
    client_id: str,
    prompt_id: str,
    callback: Optional[Callable[[int, int], Awaitable[None]]] = None,
    timeout: int = 300,
    base_url: Optional[str] = None
) -> Dict:
    """
    Отслеживание прогресса выполнения через WebSocket с fallback на History API
    
    Подключается к ComfyUI WebSocket и ожидает завершения задачи,
    вызывая callback при обновлении прогресса. Если WebSocket не получает
    событие завершения, проверяет History API каждые 10 секунд.
    
    Args:
        ws_url: WebSocket URL (ws://127.0.0.1:8188/ws)
        client_id: UUID клиента (должен совпадать с client_id из queue_prompt)
        prompt_id: ID задачи из queue_prompt()
        callback: Async функция callback(current_step, total_steps) для обновления UI
        timeout: Таймаут в секундах (default 300 = 5 минут)
        base_url: Base URL для History API (http://127.0.0.1:8188)
    
    Returns:
        Финальный результат выполнения с outputs
        
    Raises:
        asyncio.TimeoutError: Превышен таймаут
        websockets.WebSocketException: Ошибка WebSocket соединения
        
    WebSocket Message Types:
        - {"type": "status"} - общий статус очереди
        - {"type": "progress", "data": {"value": X, "max": Y}} - прогресс генерации
        - {"type": "executing", "data": {"node": "121", "prompt_id": "..."}} - начало выполнения узла
        - {"type": "executed", "data": {"node": "102", "output": {...}}} - узел завершен
    """
    logger.info(f"Starting WebSocket progress tracking for prompt_id={prompt_id}")
    
    # Извлекаем base_url из ws_url если не передан
    if not base_url:
        # ws://127.0.0.1:8188/ws -> http://127.0.0.1:8188
        base_url = ws_url.replace("ws://", "http://").split("/ws")[0]
    
    full_ws_url = f"{ws_url}?clientId={client_id}"
    outputs = {}
    current_node = None
    last_history_check = asyncio.get_event_loop().time()
    history_check_interval = 10  # Проверяем history каждые 10 секунд
    
    async def check_history() -> Optional[Dict]:
        """Проверка результата через History API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/history/{prompt_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        return None
                    
                    history = await response.json()
                    if prompt_id not in history:
                        return None
                    
                    task_history = history[prompt_id]
                    status = task_history.get("status", {})
                    
                    # Проверяем статус выполнения
                    if status.get("completed", False):
                        logger.info(f"✅ Task completed (via History API)")
                        task_outputs = task_history.get("outputs", {})
                        return task_outputs
                    
                    return None
        except Exception as e:
            logger.debug(f"History check failed: {e}")
            return None
    
    try:
        async with asyncio.timeout(timeout):
            async with websockets.connect(full_ws_url) as ws:
                logger.debug(f"WebSocket connected: {full_ws_url}")
                
                while True:
                    try:
                        # Ждем сообщение с таймаутом для периодической проверки history
                        try:
                            message_str = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            # Периодически проверяем history API
                            current_time = asyncio.get_event_loop().time()
                            if current_time - last_history_check >= history_check_interval:
                                logger.debug("Checking History API (WebSocket no activity)...")
                                history_outputs = await check_history()
                                if history_outputs:
                                    outputs = history_outputs
                                    logger.success(f"✅ Got result via History API fallback")
                                    break
                                last_history_check = current_time
                            continue
                        
                        message = json.loads(message_str)
                        msg_type = message.get("type")
                        
                        # Обработка различных типов сообщений
                        if msg_type == "status":
                            # Общий статус очереди
                            data = message.get("data", {})
                            status = data.get("status", {})
                            exec_info = status.get("exec_info", {})
                            queue_remaining = exec_info.get("queue_remaining", 0)
                            logger.debug(f"Queue status: {queue_remaining} tasks remaining")
                        
                        elif msg_type == "progress":
                            # Прогресс генерации (обычно для KSampler)
                            data = message.get("data", {})
                            value = data.get("value", 0)
                            max_value = data.get("max", 1)
                            
                            logger.info(f"Progress: {value}/{max_value} ({int(value/max_value*100)}%)")
                            
                            # Вызов callback если передан
                            if callback:
                                try:
                                    await callback(value, max_value)
                                except Exception as e:
                                    logger.warning(f"Callback error: {e}")
                        
                        elif msg_type == "executing":
                            # Начало выполнения узла
                            data = message.get("data", {})
                            node = data.get("node")
                            task_prompt_id = data.get("prompt_id")
                            
                            # Проверяем что это наша задача
                            if task_prompt_id == prompt_id:
                                if node is None:
                                    # node=null означает завершение выполнения
                                    logger.success(f"✅ Execution completed for prompt_id={prompt_id}")
                                    break
                                else:
                                    current_node = node
                                    logger.debug(f"Executing node: {node}")
                        
                        elif msg_type == "execution_cached":
                            # Узлы взяты из кэша (можно игнорировать)
                            data = message.get("data", {})
                            cached_nodes = data.get("nodes", [])
                            logger.debug(f"Cached nodes: {cached_nodes}")
                        
                        elif msg_type == "executed":
                            # Узел завершен с результатом
                            data = message.get("data", {})
                            node = data.get("node")
                            output = data.get("output", {})
                            task_prompt_id = data.get("prompt_id")
                            
                            # Проверяем что это наша задача
                            if task_prompt_id == prompt_id:
                                # Сохраняем outputs для node 102 (Image Saver)
                                if output:
                                    outputs[node] = output
                                    logger.debug(f"Node {node} executed with output: {output}")
                        
                        elif msg_type == "execution_error":
                            # Ошибка выполнения
                            data = message.get("data", {})
                            error_node = data.get("node")
                            exception_message = data.get("exception_message", "Unknown error")
                            logger.error(f"Execution error on node {error_node}: {exception_message}")
                            raise RuntimeError(f"ComfyUI execution error: {exception_message}")
                        
                        else:
                            # Неизвестный тип сообщения
                            logger.debug(f"Unknown message type: {msg_type}")
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode WebSocket message: {e}")
                        continue
                
                # Проверяем что получили результат
                if not outputs:
                    logger.warning("No outputs received via WebSocket, checking History API...")
                    # Финальная проверка через history
                    history_outputs = await check_history()
                    if history_outputs:
                        outputs = history_outputs
                        logger.success(f"✅ Retrieved outputs via History API: {list(outputs.keys())}")
                    else:
                        logger.error("❌ No outputs found in History API either")
                        return {"outputs": {}, "status": "completed_no_output"}
                
                logger.success(f"✅ Progress tracking completed, outputs: {list(outputs.keys())}")
                return {
                    "prompt_id": prompt_id,
                    "outputs": outputs,
                    "status": "completed"
                }
    
    except asyncio.TimeoutError:
        logger.error(f"❌ WebSocket timeout after {timeout}s for prompt_id={prompt_id}")
        raise asyncio.TimeoutError(f"Execution timeout after {timeout} seconds")
    
    except websockets.WebSocketException as e:
        logger.error(f"❌ WebSocket error: {e}")
        raise
    
    except Exception as e:
        logger.error(f"❌ Unexpected error during progress tracking: {e}")
        raise


async def track_progress_simple(
    ws_url: str,
    client_id: str,
    prompt_id: str,
    timeout: int = 300,
    base_url: Optional[str] = None
) -> Dict:
    """
    Упрощенная версия track_progress без callback
    
    Args:
        ws_url: WebSocket URL
        client_id: UUID клиента
        prompt_id: ID задачи
        timeout: Таймаут в секундах
        base_url: Base URL для History API
        
    Returns:
        Финальный результат выполнения
    """
    return await track_progress(
        ws_url,
        client_id,
        prompt_id,
        callback=None,
        timeout=timeout,
        base_url=base_url
    )
