"""
Тесты для TaskQueue и системы очередей
"""
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from src.queue.task_queue import TaskQueue
from src.models.task import Task, WorkflowParams


@pytest.mark.asyncio
async def test_task_queue_add():
    """Тест добавления задачи в очередь"""
    queue = TaskQueue(max_size=10)
    
    task = Task(
        user_id=123,
        chat_id=456,
        image_path=Path("test.png"),
        workflow_params=WorkflowParams(
            input_image="test.png",
            positive_prompt="test"
        )
    )
    
    position = await queue.add_task(task)
    
    assert position == 1
    assert queue.queue.qsize() == 1


@pytest.mark.asyncio
async def test_task_queue_get():
    """Тест получения задачи из очереди"""
    queue = TaskQueue()
    
    task1 = Task(
        user_id=1,
        chat_id=1,
        image_path=Path("test1.png"),
        workflow_params=WorkflowParams(input_image="test1.png", positive_prompt="test1")
    )
    task2 = Task(
        user_id=2,
        chat_id=2,
        image_path=Path("test2.png"),
        workflow_params=WorkflowParams(input_image="test2.png", positive_prompt="test2")
    )
    
    await queue.add_task(task1)
    await queue.add_task(task2)
    
    retrieved = await queue.get_task()
    
    assert retrieved.user_id == 1  # FIFO
    assert queue.current_task == retrieved


@pytest.mark.asyncio
async def test_task_done_success():
    """Тест успешного завершения задачи"""
    queue = TaskQueue()
    
    task = Task(
        user_id=123,
        chat_id=456,
        image_path=Path("test.png"),
        workflow_params=WorkflowParams(input_image="test.png", positive_prompt="test")
    )
    await queue.add_task(task)
    retrieved = await queue.get_task()
    
    await queue.task_done(retrieved, success=True, result_path=Path("result.png"))
    
    assert retrieved.status == "completed"
    assert retrieved.result_path == Path("result.png")
    assert queue.current_task is None
    assert len(queue.completed_tasks) == 1


@pytest.mark.asyncio
async def test_task_done_failure():
    """Тест неудачного завершения задачи"""
    queue = TaskQueue()
    
    task = Task(
        user_id=123,
        chat_id=456,
        image_path=Path("test.png"),
        workflow_params=WorkflowParams(input_image="test.png", positive_prompt="test")
    )
    await queue.add_task(task)
    retrieved = await queue.get_task()
    
    await queue.task_done(retrieved, success=False, error="Test error")
    
    assert retrieved.status == "failed"
    assert retrieved.error == "Test error"
    assert queue.current_task is None


@pytest.mark.asyncio
async def test_queue_status():
    """Тест получения статуса очереди"""
    queue = TaskQueue()
    
    task = Task(
        user_id=123,
        chat_id=456,
        image_path=Path("test.png"),
        workflow_params=WorkflowParams(input_image="test.png", positive_prompt="test")
    )
    await queue.add_task(task)
    
    status = queue.get_status()
    
    assert status["queue_size"] == 1
    assert status["total_completed"] == 0
    assert status["current_task"] is None


@pytest.mark.asyncio
async def test_queue_max_size():
    """Тест ограничения размера очереди"""
    queue = TaskQueue(max_size=2)
    
    task1 = Task(
        user_id=1,
        chat_id=1,
        image_path=Path("test1.png"),
        workflow_params=WorkflowParams(input_image="test1.png", positive_prompt="test1")
    )
    task2 = Task(
        user_id=2,
        chat_id=2,
        image_path=Path("test2.png"),
        workflow_params=WorkflowParams(input_image="test2.png", positive_prompt="test2")
    )
    task3 = Task(
        user_id=3,
        chat_id=3,
        image_path=Path("test3.png"),
        workflow_params=WorkflowParams(input_image="test3.png", positive_prompt="test3")
    )
    
    await queue.add_task(task1)
    await queue.add_task(task2)
    
    # Третья задача должна быть отклонена
    with pytest.raises(Exception):
        await queue.add_task(task3)


@pytest.mark.asyncio
async def test_find_user_task():
    """Тест поиска задачи пользователя"""
    queue = TaskQueue()
    
    task = Task(
        user_id=123,
        chat_id=456,
        image_path=Path("test.png"),
        workflow_params=WorkflowParams(input_image="test.png", positive_prompt="test")
    )
    await queue.add_task(task)
    
    found = queue.find_user_task(123)
    
    assert found is not None
    assert found.user_id == 123


@pytest.mark.asyncio
async def test_fifo_order():
    """Тест соблюдения FIFO порядка"""
    queue = TaskQueue()
    
    tasks = []
    for i in range(5):
        task = Task(
            user_id=i,
            chat_id=i,
            image_path=Path(f"test{i}.png"),
            workflow_params=WorkflowParams(input_image=f"test{i}.png", positive_prompt=f"test{i}")
        )
        tasks.append(task)
        await queue.add_task(task)
    
    # Проверить порядок извлечения
    for i in range(5):
        retrieved = await queue.get_task()
        assert retrieved.user_id == i
        await queue.task_done(retrieved, success=True)
