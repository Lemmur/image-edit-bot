"""
Тесты для ComfyUIClient (с использованием mock)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.comfyui.client import ComfyUIClient


@pytest.mark.asyncio
async def test_client_initialization():
    """Тест инициализации клиента"""
    client = ComfyUIClient(host="127.0.0.1", port=8188)
    
    assert client.host == "127.0.0.1"
    assert client.port == 8188
    assert client.base_url == "http://127.0.0.1:8188"


@pytest.mark.asyncio
async def test_health_check_success():
    """Тест успешной проверки здоровья"""
    client = ComfyUIClient()
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"system": "ok"})
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with client:
            result = await client.check_health()
        
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure():
    """Тест неудачной проверки здоровья"""
    client = ComfyUIClient()
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        
        async with client:
            result = await client.check_health()
        
        assert result is False


@pytest.mark.asyncio
async def test_queue_prompt():
    """Тест постановки workflow в очередь"""
    client = ComfyUIClient()
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"prompt_id": "test-123"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        async with client:
            workflow = {"test": "workflow"}
            prompt_id = await client.queue_prompt(workflow)
        
        assert prompt_id == "test-123"


@pytest.mark.asyncio
async def test_upload_image():
    """Тест загрузки изображения"""
    client = ComfyUIClient()
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"name": "uploaded.png"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        async with client:
            from pathlib import Path
            result = await client.upload_image(Path("test.png"))
        
        assert result == "uploaded.png"


@pytest.mark.asyncio
async def test_get_image():
    """Тест получения изображения"""
    client = ComfyUIClient()
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"fake_image_data")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with client:
            image_data = await client.get_image("test.png")
        
        assert image_data == b"fake_image_data"


@pytest.mark.asyncio
async def test_get_history():
    """Тест получения истории"""
    client = ComfyUIClient()
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "prompt-123": {
                "outputs": {
                    "9": {
                        "images": [{"filename": "result.png"}]
                    }
                }
            }
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        async with client:
            history = await client.get_history("prompt-123")
        
        assert "prompt-123" in history
        assert history["prompt-123"]["outputs"]["9"]["images"][0]["filename"] == "result.png"
