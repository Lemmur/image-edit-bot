"""
Тесты для WorkflowManager
"""
import pytest
from pathlib import Path
import json
from src.comfyui.workflow import WorkflowManager
from src.models.task import WorkflowParams


def test_workflow_template_load():
    """Тест загрузки шаблона workflow"""
    workflow_path = Path("workflows/qwen_image_edit.json")
    manager = WorkflowManager(workflow_path)
    
    assert manager.template is not None
    assert isinstance(manager.template, dict)
    assert "78" in manager.template  # LoadImage node


def test_workflow_creation():
    """Тест создания workflow с параметрами"""
    workflow_path = Path("workflows/qwen_image_edit.json")
    manager = WorkflowManager(workflow_path)
    
    params = WorkflowParams(
        input_image="test_image.png",
        positive_prompt="test prompt",
        negative_prompt="test negative",
        steps=10,
        cfg=2.0,
        seed=12345
    )
    
    workflow = manager.create_workflow(params)
    
    # Проверить модификации
    assert workflow["78"]["inputs"]["image"] == "test_image.png"
    assert workflow["119"]["inputs"]["prompt"] == "test prompt"
    assert workflow["77"]["inputs"]["prompt"] == "test negative"
    assert workflow["115"]["inputs"]["value"] == 10
    assert workflow["121"]["inputs"]["cfg"] == 2.0
    assert workflow["117"]["inputs"]["value"] == 12345


def test_workflow_random_seed():
    """Тест генерации случайного seed"""
    workflow_path = Path("workflows/qwen_image_edit.json")
    manager = WorkflowManager(workflow_path)
    
    params = WorkflowParams(
        input_image="test.png",
        positive_prompt="test",
        seed=0  # Random
    )
    
    workflow = manager.create_workflow(params)
    seed = workflow["117"]["inputs"]["value"]
    
    assert seed > 0
    assert seed < 2**32


def test_workflow_immutability():
    """Тест что template не изменяется"""
    workflow_path = Path("workflows/qwen_image_edit.json")
    manager = WorkflowManager(workflow_path)
    
    original_image = manager.template["78"]["inputs"]["image"]
    
    params = WorkflowParams(
        input_image="modified.png",
        positive_prompt="test"
    )
    
    manager.create_workflow(params)
    
    # Template не должен измениться
    assert manager.template["78"]["inputs"]["image"] == original_image


def test_workflow_default_values():
    """Тест использования значений по умолчанию"""
    workflow_path = Path("workflows/qwen_image_edit.json")
    manager = WorkflowManager(workflow_path)
    
    params = WorkflowParams(
        input_image="test.png",
        positive_prompt="minimal test"
    )
    
    workflow = manager.create_workflow(params)
    
    # Проверить значения по умолчанию
    assert workflow["115"]["inputs"]["value"] == 8  # default steps
    assert workflow["121"]["inputs"]["cfg"] == 1.0  # default cfg
    assert "linear/euler" in workflow["120"]["inputs"]["sampler_name"]  # default sampler
