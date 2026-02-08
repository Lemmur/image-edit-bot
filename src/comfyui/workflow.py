"""ComfyUI Workflow Manager - управление и модификация workflow JSON"""

from typing import Dict, Any
from pathlib import Path
import json
import copy
import random

from loguru import logger

from src.models.task import WorkflowParams


class WorkflowManager:
    """Управление и модификация ComfyUI workflow"""
    
    def __init__(self, template_path: Path, ui_workflow_path: Path = None):
        """
        Инициализация workflow manager
        
        Args:
            template_path: Путь к базовому workflow JSON файлу (API формат)
            ui_workflow_path: Путь к UI workflow (для extra_pnginfo)
        """
        self.template_path = template_path
        self.template = self._load_template()
        
        # Загружаем UI workflow для extra_pnginfo (если есть)
        self.ui_workflow_path = ui_workflow_path
        self.ui_workflow = None
        if ui_workflow_path and ui_workflow_path.exists():
            self.ui_workflow = self._load_ui_workflow()
            logger.info(f"UI workflow loaded from {ui_workflow_path}")
        
        logger.info(f"Workflow template loaded from {template_path}")
        logger.debug(f"Template nodes: {list(self.template.keys())}")
    
    def _load_template(self) -> Dict[str, Any]:
        """
        Загрузка базового workflow шаблона из JSON файла (API формат)
        
        Returns:
            Workflow JSON как dict
            
        Raises:
            FileNotFoundError: Если файл шаблона не найден
            json.JSONDecodeError: Если JSON невалидный
        """
        if not self.template_path.exists():
            raise FileNotFoundError(f"Workflow template not found: {self.template_path}")
        
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            logger.debug(f"Template loaded: {len(template)} nodes")
            return template
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse workflow template: {e}")
            raise
    
    def _load_ui_workflow(self) -> Dict[str, Any]:
        """
        Загрузка UI workflow (для extra_pnginfo)
        
        Returns:
            UI workflow JSON как dict
            
        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: Если JSON невалидный
        """
        if not self.ui_workflow_path.exists():
            raise FileNotFoundError(f"UI workflow not found: {self.ui_workflow_path}")
        
        try:
            with open(self.ui_workflow_path, 'r', encoding='utf-8') as f:
                ui_workflow = json.load(f)
            logger.debug(f"UI workflow loaded: {ui_workflow.get('last_node_id', 'unknown')} nodes")
            return ui_workflow
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse UI workflow: {e}")
            raise
    
    def create_workflow(self, params: WorkflowParams) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Создание workflow с параметрами пользователя
        
        Модифицирует узлы workflow на основе параметров:
        - Node 78 (LoadImage): входное изображение
        - Node 119 (TextEncodeQwenImageEditPlus): positive prompt
        - Node 77 (TextEncodeQwenImageEdit): negative prompt
        - Node 117 (PrimitiveInt): seed
        - Node 115 (INTConstant): steps
        - Node 121 (ClownsharKSampler_Beta): cfg, sampler, scheduler, eta, denoise
        
        Args:
            params: Параметры для генерации workflow
            
        Returns:
            Tuple (workflow_api, extra_pnginfo):
                - workflow_api: API формат workflow для ComfyUI
                - extra_pnginfo: Metadata с UI workflow (для нод типа WidgetToString)
        """
        logger.info("Creating workflow with user parameters")
        logger.debug(f"Params: image={params.input_image}, prompt='{params.positive_prompt[:50]}...', steps={params.steps}")
        
        # Deep copy чтобы не мутировать оригинальный template
        workflow = copy.deepcopy(self.template)
        
        # Модификация узлов
        self._set_input_image(workflow, params.input_image)
        self._set_prompts(workflow, params.positive_prompt, params.negative_prompt)
        self._set_seed(workflow, params.seed)
        self._set_steps(workflow, params.steps)
        self._set_sampling_params(workflow, params)
        
        # Формируем extra_pnginfo с UI workflow (если есть)
        extra_pnginfo = {}
        if self.ui_workflow:
            extra_pnginfo["workflow"] = self.ui_workflow
        
        logger.success("✅ Workflow created successfully")
        return workflow, extra_pnginfo
    
    def _set_input_image(self, workflow: Dict, image_name: str) -> None:
        """
        Установка входного изображения (Node 78 - LoadImage)
        
        Args:
            workflow: Workflow dict для модификации
            image_name: Имя загруженного изображения
        """
        if "78" not in workflow:
            logger.warning("Node 78 (LoadImage) not found in workflow")
            return
        
        workflow["78"]["inputs"]["image"] = image_name
        logger.debug(f"Set input image: {image_name}")
    
    def _set_prompts(self, workflow: Dict, positive: str, negative: str) -> None:
        """
        Установка промптов
        
        Args:
            workflow: Workflow dict для модификации
            positive: Positive prompt (что добавить/изменить)
            negative: Negative prompt (чего избегать)
        """
        # Node 119 - TextEncodeQwenImageEditPlus (positive)
        if "119" in workflow:
            workflow["119"]["inputs"]["prompt"] = positive
            logger.debug(f"Set positive prompt: '{positive[:50]}...'")
        else:
            logger.warning("Node 119 (TextEncodeQwenImageEditPlus) not found")
        
        # Node 77 - TextEncodeQwenImageEdit (negative)
        if "77" in workflow:
            workflow["77"]["inputs"]["prompt"] = negative
            logger.debug(f"Set negative prompt: '{negative[:50]}...'")
        else:
            logger.warning("Node 77 (TextEncodeQwenImageEdit) not found")
    
    def _set_seed(self, workflow: Dict, seed: int) -> None:
        """
        Установка seed (Node 117 - PrimitiveInt)
        
        Если seed <= 0, генерируется случайный seed
        
        Args:
            workflow: Workflow dict для модификации
            seed: Seed значение (0 = random)
        """
        # Генерация random seed если 0
        if seed <= 0:
            seed = random.randint(0, 2**32 - 1)
            logger.debug(f"Generated random seed: {seed}")
        
        if "117" in workflow:
            workflow["117"]["inputs"]["value"] = seed
            logger.debug(f"Set seed: {seed}")
        else:
            logger.warning("Node 117 (PrimitiveInt - seed) not found")
    
    def _set_steps(self, workflow: Dict, steps: int) -> None:
        """
        Установка количества шагов сэмплинга
        
        Args:
            workflow: Workflow dict для модификации
            steps: Количество шагов (обычно 4-20)
        """
        # Node 115 - INTConstant (steps)
        if "115" in workflow:
            workflow["115"]["inputs"]["value"] = steps
            logger.debug(f"Set steps (Node 115): {steps}")
        else:
            logger.warning("Node 115 (INTConstant - steps) not found")
        
        # Node 121 также имеет steps в inputs (подключен к Node 115)
        # но мы не модифицируем его напрямую, так как он использует connection
        # Однако на всякий случай можно установить и там
        if "121" in workflow:
            # Проверяем что steps это число а не connection
            current_steps = workflow["121"]["inputs"].get("steps")
            if isinstance(current_steps, list):
                # Это connection типа ["115", 0], не трогаем
                logger.debug(f"Node 121 steps is connection: {current_steps}")
            else:
                # Если это число, устанавливаем
                workflow["121"]["inputs"]["steps"] = steps
                logger.debug(f"Set steps (Node 121): {steps}")
    
    def _set_sampling_params(self, workflow: Dict, params: WorkflowParams) -> None:
        """
        Установка параметров сэмплинга (Node 121 - ClownsharKSampler_Beta)
        
        Args:
            workflow: Workflow dict для модификации
            params: Параметры workflow
        """
        if "121" not in workflow:
            logger.warning("Node 121 (ClownsharKSampler_Beta) not found")
            return
        
        node_121 = workflow["121"]["inputs"]
        
        # Обновляем параметры
        node_121["cfg"] = params.cfg
        node_121["sampler_name"] = params.sampler
        node_121["scheduler"] = params.scheduler
        node_121["eta"] = params.eta
        node_121["denoise"] = params.denoise
        
        logger.debug(f"Set sampling params: cfg={params.cfg}, sampler={params.sampler}, "
                    f"scheduler={params.scheduler}, eta={params.eta}, denoise={params.denoise}")
    
    def validate_template(self) -> bool:
        """
        Валидация шаблона - проверка наличия всех необходимых узлов
        
        Returns:
            True если все критические узлы присутствуют
        """
        required_nodes = {
            "78": "LoadImage",
            "118": "CheckpointLoaderSimple",
            "119": "TextEncodeQwenImageEditPlus",
            "77": "TextEncodeQwenImageEdit",
            "117": "PrimitiveInt (seed)",
            "115": "INTConstant (steps)",
            "121": "ClownsharKSampler_Beta",
            "102": "Image Saver Simple"
        }
        
        missing_nodes = []
        for node_id, node_name in required_nodes.items():
            if node_id not in self.template:
                missing_nodes.append(f"{node_id} ({node_name})")
        
        if missing_nodes:
            logger.error(f"Template validation failed! Missing nodes: {', '.join(missing_nodes)}")
            return False
        
        logger.success("✅ Template validation passed")
        return True
    
    def get_node_info(self, node_id: str) -> Dict[str, Any]:
        """
        Получение информации о конкретном узле
        
        Args:
            node_id: ID узла
            
        Returns:
            Информация о узле или пустой dict
        """
        return self.template.get(node_id, {})
