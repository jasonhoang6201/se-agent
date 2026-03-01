"""
System Template Hook - Dynamically load custom system_template for specific instances

Provides custom system prompt injection based on instance ID.
Loads instance-specific YAML configuration files from a specified directory to dynamically modify the agent's system_template.
"""

import logging
from pathlib import Path
from typing import Dict, Any
import yaml

from sweagent.agent.hooks.abstract import AbstractAgentHook
from sweagent.utils.log import get_logger


class SystemTemplateHook(AbstractAgentHook):
    """Hook that dynamically loads instance-specific system templates.
    
    This hook loads custom system_template configurations from YAML files
    based on instance IDs, allowing for per-instance customization of agent behavior.
    """
    
    def __init__(self, instance_id: str, instance_templates_dir: Path):
        """Initialize the system template hook.
        
        Args:
            instance_id: The instance identifier
            instance_templates_dir: Directory containing instance-specific template files
        """
        self.instance_id = instance_id
        self.instance_templates_dir = Path(instance_templates_dir)
        self.logger = get_logger("system-template", emoji="📝")
        self.template_loaded = False
        
    def on_init(self, *, agent) -> None:
        """Called when agent is initialized. Load and apply custom template if available.
        
        Args:
            agent: The agent instance being initialized
        """
        template_file = self.instance_templates_dir / f"{self.instance_id}.yaml"
        
        if not template_file.exists():
            self.logger.info(f"No custom template file found for instance {self.instance_id}: {template_file}")
            return
            
        try:
            self.logger.info(f"Loading custom template for instance {self.instance_id}: {template_file}")
            
            with open(template_file, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
            
            # Extract system_template
            system_template = self._extract_system_template(template_config)
            
            if system_template:
                # Update the agent's system_template
                if hasattr(agent, 'templates') and hasattr(agent.templates, 'system_template'):
                    original_template = agent.templates.system_template
                    agent.templates.system_template = system_template
                    self.template_loaded = True
                    self.logger.info(f"Successfully applied custom system_template for instance {self.instance_id}")
                    self.logger.debug(f"Original template length: {len(original_template)}, new template length: {len(system_template)}")
                else:
                    self.logger.warning(f"Agent does not have templates.system_template attribute, cannot apply custom template")
            else:
                self.logger.warning(f"No valid system_template found in template file: {template_file}")
                
        except Exception as e:
            self.logger.error(f"Error loading custom template for instance {self.instance_id}: {e}")
    
    def _extract_system_template(self, config: Dict[str, Any]) -> str:
        """Extract system_template from loaded YAML configuration.
        
        Args:
            config: Loaded YAML configuration
            
        Returns:
            The system_template string if found, empty string otherwise
        """
        # Try multiple possible path structures
        paths_to_try = [
            ["agent", "templates", "system_template"],
            ["templates", "system_template"], 
            ["system_template"],
            ["agent", "system_template"]
        ]
        
        for path in paths_to_try:
            current = config
            try:
                for key in path:
                    current = current[key]
                if isinstance(current, str) and current.strip():
                    self.logger.debug(f"Found system_template at path {' -> '.join(path)}")
                    return current.strip()
            except (KeyError, TypeError):
                continue
        
        self.logger.debug("No system_template found in any of the possible paths")
        return ""
    
    def on_model_query(self, *, messages, agent: str = "", instance_id: str = None, **kwargs) -> None:
        """Called before model query. Log template usage if loaded.
            A test interface.
        
        Args:
            messages: The conversation messages
            agent: The agent name
            instance_id: The instance identifier (optional, falls back to self.instance_id)
            **kwargs: Additional arguments
        """
        if self.template_loaded and len(messages) == 1:  # Only log on the first query
            _id = instance_id or self.instance_id
            self.logger.info(f"Instance {_id} is using custom system_template")