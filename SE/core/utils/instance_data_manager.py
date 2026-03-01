#!/usr/bin/env python3
"""
Instance Data Manager
Provides a unified instance data retrieval interface for operators, including problem, tra, patch, traj_pool and other core data
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import json
from core.utils.se_logger import get_se_logger
from core.utils.problem_manager import get_problem_description


class InstanceData:
    """Complete data encapsulation for a single instance"""
    
    def __init__(self, instance_name: str, instance_path: str):
        self.instance_name = instance_name
        self.instance_path = Path(instance_path)
        
        # Core data
        self.problem_description: Optional[str] = None
        self.tra_content: Optional[str] = None  # Compressed trajectory
        self.traj_content: Optional[str] = None  # Raw trajectory
        self.patch_content: Optional[str] = None  # Prediction result (.pred or .patch)

        # Metadata
        self.available_files: List[str] = []
        self.data_sources: Dict[str, str] = {}
        
    def __repr__(self):
        return f"InstanceData(name='{self.instance_name}', path='{self.instance_path}')"


class InstanceDataManager:
    """Instance data manager - provides a unified data retrieval interface for operators"""
    
    def __init__(self):
        self.logger = get_se_logger("instance_data", emoji="📦")
        
    def get_instance_data(self, instance_path: str, load_all: bool = True) -> InstanceData:
        """
        Get complete data for an instance

        Args:
            instance_path: Instance directory path
            load_all: Whether to load all data immediately, False for lazy loading

        Returns:
            InstanceData object
        """
        instance_path = Path(instance_path)
        instance_name = instance_path.name
        
        instance_data = InstanceData(instance_name, str(instance_path))
        
        # Scan available files
        instance_data.available_files = self._scan_available_files(instance_path, instance_name)
        
        if load_all:
            # Load all data immediately
            instance_data.problem_description = self._load_problem_description(instance_path)
            instance_data.tra_content = self._load_tra_content(instance_path, instance_name)
            instance_data.traj_content = self._load_traj_content(instance_path, instance_name)
            instance_data.patch_content = self._load_patch_content(instance_path, instance_name)
        
        return instance_data
    
    def get_iteration_instances(self, iteration_dir: str) -> List[InstanceData]:
        """
        Get data for all instances in an iteration directory

        Args:
            iteration_dir: Iteration directory path

        Returns:
            List of InstanceData objects
        """
        iteration_path = Path(iteration_dir)
        instances = []
        
        if not iteration_path.exists():
            self.logger.error(f"Iteration directory does not exist: {iteration_dir}")
            return instances
        
        for instance_path in iteration_path.iterdir():
            if instance_path.is_dir():
                instance_data = self.get_instance_data(str(instance_path))
                instances.append(instance_data)
        
        self.logger.info(f"Retrieved {len(instances)} instance data entries from {iteration_dir}")
        return instances
    
    def get_traj_pool_data(self, traj_pool_path: str, instance_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific instance from the trajectory pool

        Args:
            traj_pool_path: Path to the traj.pool file
            instance_name: Instance name

        Returns:
            Complete data for the instance in the trajectory pool, including problem and all iteration summaries
        """
        try:
            with open(traj_pool_path, 'r', encoding='utf-8') as f:
                pool_data = json.load(f)
            
            instance_pool_data = pool_data.get(instance_name)
            if instance_pool_data:
                self.logger.debug(f"Retrieved instance data from trajectory pool: {instance_name}")
                return instance_pool_data
            else:
                self.logger.warning(f"Instance not found in trajectory pool: {instance_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to read trajectory pool: {e}")
            return None
    
    def get_instance_iteration_summary(self, traj_pool_path: str, instance_name: str, 
                                     iteration: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get summary data for a specific iteration of an instance

        Args:
            traj_pool_path: Path to the traj.pool file
            instance_name: Instance name
            iteration: Iteration number

        Returns:
            Summary data for the specific iteration
        """
        pool_data = self.get_traj_pool_data(traj_pool_path, instance_name)
        if pool_data:
            iteration_key = str(iteration)
            if iteration_key in pool_data:
                return pool_data[iteration_key]
            else:
                self.logger.warning(f"Iteration {iteration} not found for instance {instance_name}")
        return None
    
    def validate_instance_completeness(self, instance_data: InstanceData) -> Dict[str, Any]:
        """
        Validate the completeness of instance data

        Args:
            instance_data: Instance data object

        Returns:
            Validation result dictionary
        """
        result = {
            "instance_name": instance_data.instance_name,
            "has_problem": instance_data.problem_description is not None,
            "has_tra": instance_data.tra_content is not None,
            "has_traj": instance_data.traj_content is not None,
            "has_patch": instance_data.patch_content is not None,
            "available_files": instance_data.available_files,
            "completeness_score": 0,
            "missing_data": []
        }
        
        # Calculate completeness score
        core_data = ["has_problem", "has_tra", "has_patch"]
        available_count = sum(1 for key in core_data if result[key])
        result["completeness_score"] = (available_count / len(core_data)) * 100
        
        # Record missing data
        data_mapping = {
            "has_problem": "problem_description",
            "has_tra": "tra_content", 
            "has_traj": "traj_content",
            "has_patch": "patch_content"
        }
        
        for key, data_name in data_mapping.items():
            if not result[key]:
                result["missing_data"].append(data_name)
        
        return result
    
    def _scan_available_files(self, instance_path: Path, instance_name: str) -> List[str]:
        """Scan available files in the instance directory"""
        extensions = ['.problem', '.tra', '.traj', '.pred', '.patch']
        available = []
        
        for ext in extensions:
            file_path = instance_path / f"{instance_name}{ext}"
            if file_path.exists():
                available.append(ext[1:])  # Remove the dot
        
        return available
    
    def _load_problem_description(self, instance_path: Path) -> Optional[str]:
        """Load problem description"""
        try:
            return get_problem_description(str(instance_path))
        except Exception as e:
            self.logger.error(f"Failed to load problem description: {e}")
            return None
    
    def _load_tra_content(self, instance_path: Path, instance_name: str) -> Optional[str]:
        """Load .tra file content"""
        tra_file = instance_path / f"{instance_name}.tra"
        return self._read_file_safe(tra_file)
    
    def _load_traj_content(self, instance_path: Path, instance_name: str) -> Optional[str]:
        """Load .traj file content"""
        traj_file = instance_path / f"{instance_name}.traj"
        return self._read_file_safe(traj_file)
    
    def _load_patch_content(self, instance_path: Path, instance_name: str) -> Optional[str]:
        """Load prediction result content - .patch preferred, .pred as fallback"""
        # Priority: .patch > .pred
        for ext in ['.patch', '.pred']:
            file_path = instance_path / f"{instance_name}{ext}"
            content = self._read_file_safe(file_path)
            if content is not None:
                self.logger.debug(f"Loaded prediction content: {file_path}")
                return content
        
        self.logger.warning(f"Prediction file not found: {instance_path}/{instance_name}.[patch|pred]")
        return None
    
    def _read_file_safe(self, file_path: Path) -> Optional[str]:
        """Safely read file content"""
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Truncate overly long content
            max_length = 50000  # Set a reasonable maximum length
            if len(content) > max_length:
                self.logger.debug(f"File content truncated: {file_path} ({len(content)} -> {max_length})")
                content = content[:max_length]
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return None


# Global instance
_instance_data_manager = None

def get_instance_data_manager() -> InstanceDataManager:
    """Get the global Instance data manager instance"""
    global _instance_data_manager
    if _instance_data_manager is None:
        _instance_data_manager = InstanceDataManager()
    return _instance_data_manager

def get_instance_data(instance_path: str, load_all: bool = True) -> InstanceData:
    """Convenience function: get instance data"""
    return get_instance_data_manager().get_instance_data(instance_path, load_all)

def get_iteration_instances(iteration_dir: str) -> List[InstanceData]:
    """Convenience function: get iteration instance list"""
    return get_instance_data_manager().get_iteration_instances(iteration_dir)

def get_traj_pool_data(traj_pool_path: str, instance_name: str) -> Optional[Dict[str, Any]]:
    """Convenience function: get trajectory pool instance data"""
    return get_instance_data_manager().get_traj_pool_data(traj_pool_path, instance_name)