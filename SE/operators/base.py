#!/usr/bin/env python3

"""
SE Operators Base Classes

Based on Aeon generators design philosophy, provides a modular operator system for the SE project.
Supports two base operator types:
- TemplateOperator: Returns instance_templates_dir (system prompt templates)
- EnhanceOperator: Returns enhance_history_filter_json (history enhancement configuration)
"""

import abc
import yaml
import json
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from sweagent.agent.models import get_model, GenericAPIModelConfig
from sweagent.tools.tools import ToolConfig
from core.utils.se_logger import get_se_logger


class BaseOperator(abc.ABC):
    """SE operator base class, defines common functionality and interfaces"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize operator

        Args:
            config: Configuration containing operator_models and other settings
        """
        self.config = config
        self.model = None  # LLM model instance, lazily initialized
        self.logger = get_se_logger(f"operator.{self.get_name()}", emoji="🔧")
        
    def _setup_model(self) -> None:
        """Set up LLM model instance (reusing Aeon generators model configuration approach)"""
        if self.model is not None:
            return
            
        # Use operator_models config (if exists), otherwise fall back to model config
        model_config_data = self.config.get('operator_models', self.config.get('model', {}))
        
        # Create model config without cost limits (operators are not cost-limited)
        model_config = GenericAPIModelConfig(
            name=model_config_data.get('name', 'anthropic/claude-sonnet-4-20250514'),
            api_base=model_config_data.get('api_base'),
            api_key=model_config_data.get('api_key'),
            max_input_tokens=model_config_data.get('max_input_tokens'),
            max_output_tokens=model_config_data.get('max_output_tokens'),
            # No cost limit for operators
            per_instance_cost_limit=0,
            total_cost_limit=0,
            temperature=model_config_data.get('temperature', 0.0),
            top_p=model_config_data.get('top_p', 1.0),
        )
        
        # Create minimal tool config (disable function calling)
        tools = ToolConfig(
            commands=[],
            use_function_calling=False,
            submit_command="submit"
        )
        
        self.model = get_model(model_config, tools)
        self.logger.info(f"LLM model initialized: {model_config.name}")
    
    def _call_llm_api(self, prompt: str, system_prompt: str = "") -> str:
        """
        Call LLM API (reusing Aeon generators call approach)

        Args:
            prompt: User prompt
            system_prompt: System prompt

        Returns:
            LLM-generated response text
        """
        self._setup_model()
        
        # Build message history
        history = []
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})
        history.append({"role": "user", "content": prompt})
        
        try:
            response = self.model.query(history)
            message = response.get("message", "")
            return message if message else ""
        except Exception as e:
            self.logger.error(f"LLM API call failed: {e}")
            return ""
    
    def _discover_instances(self, workspace_dir: Path, current_iteration: int) -> List[Dict[str, Any]]:
        """
        Discover list of processable instances

        Args:
            workspace_dir: Workspace directory path
            current_iteration: Current iteration number

        Returns:
            List of instance information, each element contains: {
                'instance_name': str,
                'instance_dir': Path,
                'trajectory_file': Path,
                'previous_iteration': int
            }
        """
        instances = []
        previous_iteration = current_iteration - 1
        
        if previous_iteration < 1:
            self.logger.warning(f"Invalid previous iteration number: {previous_iteration}")
            return instances
        
        # Find previous iteration output directory
        prev_iter_dir = workspace_dir / f"iteration_{previous_iteration}"
        if not prev_iter_dir.exists():
            self.logger.warning(f"Previous iteration directory does not exist: {prev_iter_dir}")
            return instances
        
        # Find all instance directories in previous iteration
        for instance_dir in prev_iter_dir.iterdir():
            if not instance_dir.is_dir() or instance_dir.name.startswith('.'):
                continue
            
            # Find .tra trajectory files
            tra_files = list(instance_dir.glob("*.tra"))
            if not tra_files:
                continue
            
            # Use the first .tra file found
            trajectory_file = tra_files[0]
            
            instances.append({
                'instance_name': instance_dir.name,
                'instance_dir': instance_dir,
                'trajectory_file': trajectory_file,
                'previous_iteration': previous_iteration
            })
        
        self.logger.info(f"Found {len(instances)} processable instances")
        return instances
    
    def _load_trajectory_data(self, trajectory_file: Path) -> Dict[str, Any]:
        """
        Load trajectory data (reusing Aeon generators data loading logic)

        Args:
            trajectory_file: Trajectory file path

        Returns:
            Trajectory data dictionary
        """
        try:
            with open(trajectory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load trajectory file {trajectory_file}: {e}")
            return {}
    
    def _extract_problem_statement(self, trajectory_data: Dict[str, Any]) -> str:
        """
        Extract problem statement from trajectory data (reusing Aeon generators extraction logic)

        Args:
            trajectory_data: Trajectory data dictionary

        Returns:
            Problem statement text
        """
        import re
        
        try:
            trajectory = trajectory_data.get('Trajectory', [])
            if len(trajectory) >= 2:
                user_item = trajectory[1]  # Second item (index 1)
                if user_item.get('role') == 'user' and 'content' in user_item:
                    content = user_item['content']
                    
                    # Extract text content
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get('text', '')
                    elif isinstance(content, str):
                        text = content
                    else:
                        return ""
                    
                    # Extract content within <pr_description> tags
                    match = re.search(r'<pr_description>\s*(.*?)\s*</pr_description>', text, re.DOTALL)
                    if match:
                        return match.group(1).strip()
            return ""
        except Exception as e:
            self.logger.error(f"Failed to extract problem statement: {e}")
            return ""
    
    def _process_single_instance(self, instance_info: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """
        Process a single instance (concrete logic implemented in subclasses)

        Args:
            instance_info: Instance information dictionary

        Returns:
            (instance_name, generated_content) or None indicating processing failure
        """
        instance_name = instance_info['instance_name']
        try:
            # Load trajectory data
            trajectory_data = self._load_trajectory_data(instance_info['trajectory_file'])
            if not trajectory_data:
                self.logger.warning(f"Skipping {instance_name}: unable to load trajectory data")
                return None
            
            # Extract problem statement
            problem_statement = self._extract_problem_statement(trajectory_data)
            if not problem_statement:
                self.logger.warning(f"Skipping {instance_name}: unable to extract problem statement")
                return None
            
            # Call subclass generation logic
            generated_content = self._generate_content(instance_info, problem_statement, trajectory_data)
            if not generated_content:
                self.logger.warning(f"Skipping {instance_name}: content generation failed")
                return None
            
            return (instance_name, generated_content)
            
        except Exception as e:
            self.logger.error(f"Error processing instance {instance_name}: {e}")
            return None
    
    @abc.abstractmethod
    def get_name(self) -> str:
        """Get operator name"""
        pass
    
    @abc.abstractmethod
    def _generate_content(self, instance_info: Dict[str, Any], problem_statement: str, trajectory_data: Dict[str, Any]) -> str:
        """
        Generate content (core logic implemented by subclasses)

        Args:
            instance_info: Instance information
            problem_statement: Problem statement
            trajectory_data: Trajectory data

        Returns:
            Generated content string
        """
        pass
    
    @abc.abstractmethod
    def process(self, workspace_dir: str, current_iteration: int, num_workers: int = 1) -> Optional[Dict[str, str]]:
        """
        Main entry method for processing operator logic

        Args:
            workspace_dir: Workspace directory path
            current_iteration: Current iteration number
            num_workers: Number of concurrent workers

        Returns:
            Parameter dictionary returned by the operator, e.g. {'instance_templates_dir': 'path'} or None indicating failure
        """
        pass


class TemplateOperator(BaseOperator):
    """
    Template operator base class, used to generate system prompt templates
    Returns instance_templates_dir parameter
    """
    
    def _create_output_dir(self, workspace_dir: Path, current_iteration: int) -> Path:
        """
        Create output directory

        Args:
            workspace_dir: Workspace directory path
            current_iteration: Current iteration number

        Returns:
            Output directory path
        """
        # Output to the current iteration's system_prompt directory
        output_dir = workspace_dir / f"iteration_{current_iteration}" / "system_prompt"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Created output directory: {output_dir}")
        return output_dir
    
    def _create_yaml_content(self, strategy_content: str) -> str:
        """
        Create YAML-formatted system prompt content (reusing Aeon generators format)

        Args:
            strategy_content: Strategy content text

        Returns:
            YAML-formatted configuration content
        """
        # Standard prefix
        prefix = "You are a helpful assistant that can interact with a terminal to solve software engineering tasks."
        
        # Combine prefix and strategy content
        full_content = f"{prefix}\n\n{self.get_strategy_prefix()}:\n\n{strategy_content}"
        
        # Create YAML structure
        yaml_content = {
            'agent': {
                'templates': {
                    'system_template': full_content
                }
            }
        }
        
        return yaml.dump(yaml_content, default_flow_style=False, allow_unicode=True, width=1000)
    
    def _save_instance_template(self, instance_name: str, content: str, output_dir: Path) -> None:
        """
        Save instance template file

        Args:
            instance_name: Instance name
            content: Generated content
            output_dir: Output directory
        """
        yaml_content = self._create_yaml_content(content)
        output_file = output_dir / f"{instance_name}.yaml"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        self.logger.debug(f"Saved template file: {output_file}")
    
    @abc.abstractmethod
    def get_strategy_prefix(self) -> str:
        """Get strategy prefix identifier (e.g. 'ALTERNATIVE SOLUTION STRATEGY')"""
        pass
    
    def process(self, workspace_dir: str, current_iteration: int, num_workers: int = 1) -> Optional[Dict[str, str]]:
        """
        Process template operator logic

        Args:
            workspace_dir: Workspace directory path
            current_iteration: Current iteration number
            num_workers: Number of concurrent workers

        Returns:
            {'instance_templates_dir': 'path'} or None indicating failure
        """
        workspace_path = Path(workspace_dir)
        
        self.logger.info(f"Starting to process {self.get_name()} operator")
        self.logger.info(f"Workspace directory: {workspace_path}")
        self.logger.info(f"Current iteration: {current_iteration}")
        self.logger.info(f"Concurrency: {num_workers}")
        
        # Discover instances
        instances = self._discover_instances(workspace_path, current_iteration)
        if not instances:
            self.logger.warning("No processable instances found")
            return None
        
        # Create output directory
        output_dir = self._create_output_dir(workspace_path, current_iteration)
        
        # Process instances in parallel
        processed_count = 0
        failed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_instance = {
                executor.submit(self._process_single_instance, instance_info): instance_info['instance_name']
                for instance_info in instances
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_instance):
                instance_name = future_to_instance[future]
                try:
                    result = future.result()
                    if result is not None:
                        name, content = result
                        self._save_instance_template(name, content, output_dir)
                        processed_count += 1
                        self.logger.debug(f"Successfully processed instance: {name}")
                    else:
                        failed_count += 1
                        self.logger.warning(f"Failed to process instance: {instance_name}")
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Exception while processing instance {instance_name}: {e}")
        
        self.logger.info(f"Processing complete: {processed_count} succeeded, {failed_count} failed")
        
        if processed_count == 0:
            self.logger.error("No instances were successfully processed")
            return None
        
        # Return instance_templates_dir
        return {'instance_templates_dir': str(output_dir)}


class EnhanceOperator(BaseOperator):
    """
    Enhancement operator base class, used to generate history enhancement configuration
    Returns enhance_history_filter_json parameter
    """

    def process(self, workspace_dir: str, current_iteration: int, num_workers: int = 1) -> Optional[Dict[str, str]]:
        """
        Process enhancement operator logic (not yet developed)

        Args:
            workspace_dir: Workspace directory path
            current_iteration: Current iteration number
            num_workers: Number of concurrent workers

        Returns:
            {'enhance_history_filter_json': 'path'} or None indicating failure
        """
        # TODO: This type of operator is not yet fully developed
        self.logger.warning("EnhanceOperator type operator is not yet fully developed")
        return None