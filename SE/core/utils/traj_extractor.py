#!/usr/bin/env python3
"""
Trajectory Data Extractor
Extracts instance data from SWE-agent output directories using the unified Instance data management interface
"""

from pathlib import Path
from typing import List, Tuple, Optional
from core.utils.se_logger import get_se_logger
from core.utils.instance_data_manager import get_instance_data_manager, InstanceData


class TrajExtractor:
    """Trajectory Data Extractor - Based on unified Instance data management"""
    
    def __init__(self):
        self.logger = get_se_logger("traj_extractor", emoji="📁")
        self.instance_manager = get_instance_data_manager()
    
    def extract_instance_data(self, iteration_dir: str) -> List[Tuple[str, Optional[str], str, str]]:
        """
        Extract data for all instances from an iteration directory

        Args:
            iteration_dir: Path to the iteration directory

        Returns:
            List[Tuple[instance_name, problem_description, tra_content, patch_content]]

        Note:
            Return format maintains backward compatibility; extract_instances_structured() is recommended
        """
        instances = self.instance_manager.get_iteration_instances(iteration_dir)
        results = []
        
        for instance in instances:
            if instance.tra_content:
                # If .tra file exists, include this instance (even without .patch file)
                patch_content = instance.patch_content or "FAILED_NO_PATCH"
                results.append((
                    instance.instance_name,
                    instance.problem_description,
                    instance.tra_content,
                    patch_content
                ))
            else:
                # Only skip instances without .tra files
                self.logger.warning(f"Instance {instance.instance_name} missing .tra file, skipping")
        
        self.logger.info(f"Extracted {len(results)} instance data entries from {iteration_dir} (including failed instances)")
        return results
    
    def extract_instances_structured(self, iteration_dir: str) -> List[InstanceData]:
        """
        Recommended new interface: extract structured instance data

        Args:
            iteration_dir: Path to the iteration directory

        Returns:
            List of InstanceData objects
        """
        return self.instance_manager.get_iteration_instances(iteration_dir)
    
    def get_instance_completeness_report(self, iteration_dir: str) -> dict:
        """
        Generate a completeness report for all instances in an iteration directory

        Args:
            iteration_dir: Path to the iteration directory

        Returns:
            Completeness report dictionary
        """
        instances = self.instance_manager.get_iteration_instances(iteration_dir)
        
        report = {
            "total_instances": len(instances),
            "complete_instances": 0,
            "incomplete_instances": [],
            "file_availability": {
                "problem": 0,
                "tra": 0,
                "traj": 0,
                "patch": 0
            },
            "instances_detail": []
        }
        
        for instance in instances:
            validation = self.instance_manager.validate_instance_completeness(instance)
            report["instances_detail"].append(validation)
            
            if validation["completeness_score"] == 100:
                report["complete_instances"] += 1
            else:
                report["incomplete_instances"].append({
                    "name": instance.instance_name,
                    "missing": validation["missing_data"],
                    "score": validation["completeness_score"]
                })
            
            # Count file availability
            if validation["has_problem"]:
                report["file_availability"]["problem"] += 1
            if validation["has_tra"]:
                report["file_availability"]["tra"] += 1
            if validation["has_traj"]:
                report["file_availability"]["traj"] += 1
            if validation["has_patch"]:
                report["file_availability"]["patch"] += 1
        
        return report