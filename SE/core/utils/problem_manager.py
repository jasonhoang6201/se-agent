#!/usr/bin/env python3
"""
Problem Description Standardized Interface
Provides unified problem description retrieval and management functionality
"""

from pathlib import Path
from typing import Optional, Dict, Any
import json
import re
from core.utils.se_logger import get_se_logger


class ProblemManager:
    """Problem description manager - unified problem retrieval interface"""
    
    def __init__(self):
        self.logger = get_se_logger("problem_manager", emoji="❓")
    
    def get_problem_description(self, instance_path: str, method: str = "auto") -> Optional[str]:
        """
        Get the problem description for an instance

        Args:
            instance_path: Instance directory path or instance name
            method: Retrieval method - 'auto', 'file', 'trajectory', 'json'

        Returns:
            Problem description text, None on failure
        """
        instance_path = Path(instance_path)
        
        if method == "auto":
            # Priority: .problem file > trajectory extraction > JSON config
            return (self._get_from_problem_file(instance_path) or 
                   self._get_from_trajectory(instance_path) or
                   self._get_from_json_config(instance_path))
        elif method == "file":
            return self._get_from_problem_file(instance_path)
        elif method == "trajectory": 
            return self._get_from_trajectory(instance_path)
        elif method == "json":
            return self._get_from_json_config(instance_path)
        else:
            self.logger.error(f"Unknown retrieval method: {method}")
            return None
    
    def _get_from_problem_file(self, instance_path: Path) -> Optional[str]:
        """Get problem description from .problem file"""
        if instance_path.is_file() and instance_path.suffix == ".problem":
            problem_file = instance_path
        else:
            # Find .problem file in the instance directory
            instance_name = instance_path.name
            problem_file = instance_path / f"{instance_name}.problem"
            
        if problem_file.exists():
            try:
                with open(problem_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                self.logger.debug(f"Retrieved from .problem file: {problem_file}")
                return content
            except Exception as e:
                self.logger.error(f"Failed to read .problem file: {e}")
        return None
    
    def _get_from_trajectory(self, instance_path: Path) -> Optional[str]:
        """Extract problem description from trajectory file"""
        instance_name = instance_path.name
        
        # Find .traj or .tra files
        traj_files = list(instance_path.glob(f"{instance_name}.traj"))
        if not traj_files:
            traj_files = list(instance_path.glob(f"{instance_name}.tra"))
            
        if not traj_files:
            return None
            
        try:
            with open(traj_files[0], 'r', encoding='utf-8') as f:
                trajectory_data = json.load(f)
            
            # Extract PR description
            if (len(trajectory_data) > 1 and 
                "content" in trajectory_data[1] and 
                len(trajectory_data[1]["content"]) > 0):
                
                text_content = trajectory_data[1]["content"][0].get("text", "")
                
                # Extract <pr_description> tag content
                pr_match = re.search(r'<pr_description>(.*?)</pr_description>', 
                                   text_content, re.DOTALL)
                if pr_match:
                    problem_text = pr_match.group(1).strip()
                    self.logger.debug(f"Extracted problem description from trajectory file: {traj_files[0]}")
                    return problem_text
                    
        except Exception as e:
            self.logger.error(f"Failed to extract problem description from trajectory file: {e}")
        
        return None
    
    def _get_from_json_config(self, instance_path: Path) -> Optional[str]:
        """Get problem description from JSON config file (to be implemented)"""
        # TODO: Implement retrieval of problem description from instance JSON config file
        return None
    
    def create_problem_file(self, instance_path: str, problem_text: str) -> bool:
        """
        Create a .problem file

        Args:
            instance_path: Instance directory path
            problem_text: Problem description text

        Returns:
            Whether creation was successful
        """
        try:
            instance_path = Path(instance_path)
            instance_name = instance_path.name
            problem_file = instance_path / f"{instance_name}.problem"
            
            with open(problem_file, 'w', encoding='utf-8') as f:
                f.write(problem_text)
            
            self.logger.info(f"Created .problem file: {problem_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create .problem file: {e}")
            return False
    
    def validate_problem_availability(self, instance_path: str) -> Dict[str, Any]:
        """
        Validate the availability of problem description for an instance

        Args:
            instance_path: Instance directory path

        Returns:
            Validation result dictionary
        """
        instance_path = Path(instance_path)
        result = {
            "instance_name": instance_path.name,
            "methods_available": [],
            "primary_source": None,
            "problem_length": 0,
            "problem_preview": None
        }
        
        # Check various retrieval methods
        for method in ["file", "trajectory", "json"]:
            problem = self.get_problem_description(instance_path, method)
            if problem:
                result["methods_available"].append(method)
                if not result["primary_source"]:
                    result["primary_source"] = method
                    result["problem_length"] = len(problem)
                    result["problem_preview"] = problem[:100] + "..." if len(problem) > 100 else problem
        
        return result


# Global instance
_problem_manager = None

def get_problem_manager() -> ProblemManager:
    """Get the global Problem manager instance"""
    global _problem_manager
    if _problem_manager is None:
        _problem_manager = ProblemManager()
    return _problem_manager

def get_problem_description(instance_path: str, method: str = "auto") -> Optional[str]:
    """Convenience function: get problem description"""
    return get_problem_manager().get_problem_description(instance_path, method)

def validate_problem_availability(instance_path: str) -> Dict[str, Any]:
    """Convenience function: validate problem description availability"""
    return get_problem_manager().validate_problem_availability(instance_path)