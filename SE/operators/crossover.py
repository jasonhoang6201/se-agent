#!/usr/bin/env python3

"""
Crossover Operator

When the trajectory pool has 2 or more valid entries, combines characteristics of two trajectories to generate a new strategy.
When there are insufficient valid entries, logs an error and skips processing.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from operators import TemplateOperator


class CrossoverOperator(TemplateOperator):
    """Crossover operator, combines characteristics of two trajectories to generate a new strategy"""
    
    def get_name(self) -> str:
        return "crossover"
    
    def get_strategy_prefix(self) -> str:
        return "CROSSOVER STRATEGY"
    
    def _load_traj_pool(self, workspace_dir: Path) -> Dict[str, Any]:
        """Load trajectory pool data"""
        traj_pool_file = workspace_dir / "traj.pool"
        
        if not traj_pool_file.exists():
            self.logger.warning(f"traj.pool file does not exist: {traj_pool_file}")
            return {}

        try:
            with open(traj_pool_file, 'r', encoding='utf-8') as f:
                pool_data = json.load(f)

            # Return data for the first instance
            for instance_name, instance_data in pool_data.items():
                if isinstance(instance_data, dict):
                    return instance_data
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to load traj.pool {traj_pool_file}: {e}")
            return {}
    
    def _get_valid_iterations(self, approaches_data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Get valid iteration data"""
        valid_iterations = []
        
        for key, data in approaches_data.items():
            if key == "problem":
                continue
                
            if isinstance(data, dict) and key.isdigit():
                # Check if basic strategy information exists
                if data.get('strategy') or data.get('modified_files') or data.get('key_changes'):
                    valid_iterations.append((key, data))
        
        # Sort by iteration number
        valid_iterations.sort(key=lambda x: int(x[0]))
        
        return valid_iterations
    
    def _format_trajectory_data(self, iteration_key: str, data: Dict[str, Any]) -> str:
        """Format a single trajectory data entry"""
        formatted_parts = []
        
        formatted_parts.append(f"ITERATION {iteration_key}:")
        
        if data.get('strategy'):
            formatted_parts.append(f"Strategy: {data['strategy']}")
        
        if data.get('strategy_status'):
            formatted_parts.append(f"Status: {data['strategy_status']}")
            if data.get('failure_reason'):
                formatted_parts.append(f"Failure Reason: {data['failure_reason']}")
        
        if data.get('modified_files'):
            formatted_parts.append(f"Modified Files: {', '.join(data['modified_files'])}")
        
        if data.get('key_changes'):
            formatted_parts.append(f"Key Changes: {'; '.join(data['key_changes'])}")
        
        if data.get('tools_used'):
            formatted_parts.append(f"Tools Used: {', '.join(data['tools_used'])}")
        
        if data.get('reasoning_pattern'):
            formatted_parts.append(f"Reasoning Pattern: {data['reasoning_pattern']}")
        
        if data.get('assumptions_made'):
            formatted_parts.append(f"Assumptions: {'; '.join(data['assumptions_made'])}")
        
        return "\n".join(formatted_parts)
    
    def _generate_crossover_strategy(self, problem_statement: str, trajectory1: str, trajectory2: str) -> str:
        """Generate crossover strategy"""
        
        system_prompt = """You are an expert software engineering strategy consultant specializing in synthesis and optimization. Your task is to analyze two different approaches to a software engineering problem and create a superior hybrid strategy that combines their strengths while avoiding their weaknesses.

You will be given a problem and two different approaches that have been tried. Your job is to:
1. Identify the strengths and effective elements of each approach
2. Recognize common pitfalls or limitations shared by both approaches
3. Synthesize a new strategy that leverages the best aspects of both while addressing their shortcomings
4. Create an approach that is more robust and comprehensive than either individual strategy

CRITICAL: Your strategy should be a thoughtful synthesis, not just a simple combination. Focus on how the approaches can complement each other and cover each other's blind spots.

IMPORTANT: 
- Respond with plain text, no formatting
- Keep response under 250 words for system prompt efficiency
- Focus on strategic synthesis rather than technical details
- Provide actionable guidance that builds on both approaches"""
        
        prompt = f"""Analyze these two approaches and create a superior hybrid strategy:

PROBLEM:
{problem_statement[:400]}...

APPROACH 1:
{trajectory1[:600]}...

APPROACH 2:
{trajectory2[:600]}...

Create a crossover strategy that:
1. Combines the most effective elements from both approaches
2. Addresses the limitations observed in each approach
3. Covers blind spots that neither approach addressed individually
4. Provides a more comprehensive and robust solution methodology

Requirements for the hybrid strategy:
- Synthesize complementary strengths (e.g., if one approach excels at analysis and another at implementation, combine both)
- Mitigate shared weaknesses (e.g., if both approaches rush to implementation, emphasize planning)
- Fill coverage gaps (e.g., if both focus on code but ignore testing, integrate testing)
- Create synergistic effects where the combination is more powerful than individual parts

The strategy should be conceptual yet actionable, providing a framework that an AI agent can follow to achieve better results than either approach alone. Focus on WHY this synthesis is superior and HOW it leverages the best of both worlds while mitigating their individual shortcomings."""
        
        return self._call_llm_api(prompt, system_prompt)
    
    def _generate_content(self, instance_info: Dict[str, Any], problem_statement: str, trajectory_data: Dict[str, Any]) -> str:
        """Generate crossover strategy content"""
        instance_name = instance_info['instance_name']
        
        # Load trajectory pool data (from workspace_dir, computed via instance_dir)
        workspace_dir = instance_info['instance_dir'].parent.parent
        approaches_data = self._load_traj_pool(workspace_dir)
        if not approaches_data:
            self.logger.warning(f"Skipping {instance_name}: no trajectory pool data")
            return ""
        
        # Get valid iteration data
        valid_iterations = self._get_valid_iterations(approaches_data)
        
        if len(valid_iterations) < 2:
            self.logger.error(f"Skipping {instance_name}: insufficient valid trajectory pool entries (need>=2, actual={len(valid_iterations)})")
            return ""
        
        # Select the two most recent trajectories for crossover
        # Could choose the last two or the two with best results; here we choose the last two
        iteration1_key, iteration1_data = valid_iterations[-2]
        iteration2_key, iteration2_data = valid_iterations[-1]
        
        # Format trajectory data
        trajectory1_formatted = self._format_trajectory_data(iteration1_key, iteration1_data)
        trajectory2_formatted = self._format_trajectory_data(iteration2_key, iteration2_data)
        
        self.logger.info(f"Analyzing {instance_name}: crossing iterations {iteration1_key} and {iteration2_key}")
        
        # Generate crossover strategy
        strategy = self._generate_crossover_strategy(
            problem_statement, 
            trajectory1_formatted, 
            trajectory2_formatted
        )
        
        if not strategy:
            # If LLM call fails, provide default crossover strategy
            strategy = f"""Synthesize the most effective elements from both previous approaches. Start with the stronger analytical method from the first approach, then apply the more focused implementation technique from the second approach. Address the common limitations observed in both attempts by adding intermediate validation steps. This hybrid approach combines thorough analysis with targeted action, while incorporating safeguards against the pitfalls encountered in both previous attempts."""
        
        return strategy


# Register operator
from operators import register_operator
register_operator("crossover", CrossoverOperator)