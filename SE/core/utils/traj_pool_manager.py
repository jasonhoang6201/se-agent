#!/usr/bin/env python3
"""
Trajectory Pool Manager
Manages trajectory summaries for each instance across multi-iteration execution
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from core.utils.se_logger import get_se_logger


class TrajPoolManager:
    """Trajectory pool manager"""
    
    def __init__(self, pool_path: str, llm_client=None):
        """
        Initialize the trajectory pool manager

        Args:
            pool_path: Path to the traj.pool file
            llm_client: LLM client instance for trajectory summarization
        """
        self.pool_path = Path(pool_path)
        self.llm_client = llm_client
        self.logger = get_se_logger("traj_pool", emoji="🏊")
        
    def initialize_pool(self) -> None:
        """Initialize the trajectory pool file"""
        try:
            # Ensure the directory exists
            self.pool_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If the file does not exist, create an empty trajectory pool
            if not self.pool_path.exists():
                initial_pool = {}
                with open(self.pool_path, 'w', encoding='utf-8') as f:
                    json.dump(initial_pool, f, ensure_ascii=False, indent=2)
                self.logger.info(f"Initialized trajectory pool: {self.pool_path}")
            else:
                self.logger.info(f"Trajectory pool already exists: {self.pool_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize trajectory pool: {e}")
            raise
    
    def load_pool(self) -> Dict[str, Any]:
        """Load trajectory pool data"""
        try:
            if not self.pool_path.exists():
                self.logger.warning("Trajectory pool file does not exist, returning empty pool")
                return {}
                
            with open(self.pool_path, 'r', encoding='utf-8') as f:
                pool_data = json.load(f)
            
            self.logger.debug(f"Loaded trajectory pool: {len(pool_data)} instances")
            return pool_data
            
        except Exception as e:
            self.logger.error(f"Failed to load trajectory pool: {e}")
            return {}
    
    def save_pool(self, pool_data: Dict[str, Any]) -> None:
        """Save trajectory pool data"""
        try:
            with open(self.pool_path, 'w', encoding='utf-8') as f:
                json.dump(pool_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"Saved trajectory pool: {len(pool_data)} instances")
            
        except Exception as e:
            self.logger.error(f"Failed to save trajectory pool: {e}")
            raise
    
    def summarize_trajectory(self, trajectory_content: str, patch_content: str, iteration: int) -> Dict[str, Any]:
        """
        Summarize trajectory content

        Args:
            trajectory_content: .tra file content
            patch_content: .patch/.pred file content or "FAILED_NO_PATCH"
            iteration: Iteration number

        Returns:
            Trajectory summary dictionary
        """
        from .traj_summarizer import TrajSummarizer
        from .llm_client import TrajectorySummarizer
        
        summarizer = TrajSummarizer()
        
        # Check if this is a failed instance
        is_failed = patch_content == "FAILED_NO_PATCH"
        
        try:
            # If LLM client is available, use LLM for summarization
            if self.llm_client is not None:
                traj_summarizer = TrajectorySummarizer(self.llm_client)
                summary = traj_summarizer.summarize_trajectory(
                    trajectory_content, patch_content, iteration
                )
                # Add special markers for failed instances
                if is_failed:
                    summary["strategy_status"] = "FAILED"
                    summary["failure_reason"] = "No patch/prediction generated (likely due to cost limit or early termination)"
                self.logger.debug(f"LLM trajectory summary (iteration {iteration}): {summary.get('approach_summary', 'N/A')}")
                return summary
            else:
                # Use fallback summary when no LLM client is available
                self.logger.info(f"LLM client not configured, using fallback summary (iteration {iteration})")
                summary = summarizer.create_fallback_summary(trajectory_content, patch_content, iteration)
                self.logger.debug(f"Fallback trajectory summary (iteration {iteration}): {summary.get('approach_summary', 'N/A')}")
                return summary
            
        except Exception as e:
            self.logger.error(f"Trajectory summarization failed: {e}")
            # Return error summary
            return {
                "error": "summarization_failed",
                "details": str(e),
                "iteration": iteration,
                "fallback_summary": f"Failed to summarize trajectory for iteration {iteration}"
            }
    
    def add_iteration_summary(self, instance_name: str, iteration: int, 
                            trajectory_content: str, patch_content: str, 
                            problem_description: str = None) -> None:
        """
        Add an iteration summary for the specified instance

        Args:
            instance_name: Instance name
            iteration: Iteration number
            trajectory_content: .tra file content
            patch_content: .patch/.pred file content (prediction result)
            problem_description: Problem description (optional)
        """
        try:
            # Load existing pool data
            pool_data = self.load_pool()
            
            # Ensure instance exists
            if instance_name not in pool_data:
                pool_data[instance_name] = {}
            
            # If this is the first time adding this instance, add the problem field
            if "problem" not in pool_data[instance_name] and problem_description:
                pool_data[instance_name]["problem"] = problem_description
            
            # Generate trajectory summary
            summary = self.summarize_trajectory(trajectory_content, patch_content, iteration)
            
            # Add to pool
            pool_data[instance_name][str(iteration)] = summary
            
            # Save pool data
            self.save_pool(pool_data)
            
            self.logger.info(f"Added trajectory summary: {instance_name} iteration {iteration}")
            
        except Exception as e:
            self.logger.error(f"Failed to add trajectory summary: {e}")
            raise
    
    def get_instance_summary(self, instance_name: str) -> Optional[Dict[str, str]]:
        """
        Get all iteration summaries for the specified instance

        Args:
            instance_name: Instance name

        Returns:
            Dictionary of iteration summaries for the instance, key is iteration number, value is summary
        """
        try:
            pool_data = self.load_pool()
            return pool_data.get(instance_name)
            
        except Exception as e:
            self.logger.error(f"Failed to get instance summary: {e}")
            return None
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get trajectory pool statistics"""
        try:
            pool_data = self.load_pool()
            
            total_instances = len(pool_data)
            total_iterations = sum(len(iterations) for iterations in pool_data.values())
            
            stats = {
                "total_instances": total_instances,
                "total_iterations": total_iterations,
                "instances": list(pool_data.keys())
            }
            
            self.logger.debug(f"Trajectory pool stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get trajectory pool stats: {e}")
            return {"total_instances": 0, "total_iterations": 0, "instances": []}