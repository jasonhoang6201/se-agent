#!/usr/bin/env python3

"""
Trajectory Pool Summary Operator

Analyzes historical failed attempts in the trajectory pool, identifies common blind spots and risk points,
and generates concise risk-aware problem solving guidance.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from operators import TemplateOperator


class TrajPoolSummaryOperator(TemplateOperator):
    """Trajectory pool summary operator, generates risk-aware problem solving guidance"""
    
    def get_name(self) -> str:
        return "traj_pool_summary"
    
    def get_strategy_prefix(self) -> str:
        return "RISK-AWARE PROBLEM SOLVING GUIDANCE"
    
    def _discover_instances(self, workspace_dir: Path, current_iteration: int) -> List[Dict[str, Any]]:
        """
        Override instance discovery logic to directly find traj.pool files in the workspace directory

        Args:
            workspace_dir: Workspace directory path
            current_iteration: Current iteration number

        Returns:
            List of instance information
        """
        instances = []
        
        # Directly find traj.pool file in the workspace directory
        traj_pool_file = workspace_dir / "traj.pool"
        if not traj_pool_file.exists():
            self.logger.warning(f"traj.pool file does not exist: {traj_pool_file}")
            return instances

        # Load traj.pool data
        try:
            with open(traj_pool_file, 'r', encoding='utf-8') as f:
                pool_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load traj.pool {traj_pool_file}: {e}")
            return instances

        # Create instance info for each instance
        for instance_name, instance_data in pool_data.items():
            if isinstance(instance_data, dict) and len(instance_data) > 0:
                # Check if there are numeric keys (iteration data)
                has_iteration_data = any(key.isdigit() for key in instance_data.keys())
                if has_iteration_data:
                    instances.append({
                        'instance_name': instance_name,
                        'instance_dir': workspace_dir,  # Use workspace directory as instance directory
                        'trajectory_file': traj_pool_file,  # Use traj.pool file
                        'previous_iteration': current_iteration - 1,
                        'pool_data': instance_data  # Attach pool data
                    })
        
        self.logger.info(f"Found {len(instances)} processable instances")
        return instances

    def _extract_problem_statement(self, trajectory_data: Dict[str, Any]) -> str:
        """
        Override problem statement extraction, return placeholder
        because we directly use the problem statement from pool_data in _generate_content
        """
        return "placeholder"
    
    def _load_traj_pool(self, instance_dir: Path) -> Dict[str, Any]:
        """Load trajectory pool data - adapted for SE framework's traj.pool format"""
        traj_pool_file = instance_dir / "traj.pool"
        
        if not traj_pool_file.exists():
            self.logger.warning(f"traj.pool file does not exist: {traj_pool_file}")
            return {}

        try:
            with open(traj_pool_file, 'r', encoding='utf-8') as f:
                pool_data = json.load(f)
            
            # SE framework traj.pool format: {instance_name: {problem: str, "1": {data}, "2": {data}}}
            # Extract data for the first instance
            for instance_name, instance_data in pool_data.items():
                if isinstance(instance_data, dict):
                    return instance_data
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to load traj.pool {traj_pool_file}: {e}")
            return {}

    def _format_approaches_data(self, approaches_data: Dict[str, Any]) -> str:
        """Format historical attempt data into concise text"""
        formatted_text = ""
        
        for key, data in approaches_data.items():
            if key == "problem":
                continue
                
            if isinstance(data, dict):
                formatted_text += f"\nATTEMPT {key}:\n"
                formatted_text += f"Strategy: {data.get('strategy', 'N/A')}\n"
                formatted_text += f"Files Modified: {', '.join(data.get('modified_files', []))}\n"
                formatted_text += f"Key Changes: {'; '.join(data.get('key_changes', []))}\n"
                formatted_text += f"Tools: {', '.join(data.get('tools_used', []))}\n"
                formatted_text += f"Assumptions: {'; '.join(data.get('assumptions_made', []))}\n"
        
        return formatted_text
    
    def _generate_risk_aware_guidance(self, problem_statement: str, approaches_data: Dict[str, Any]) -> str:
        """Generate concise risk-aware guidance"""
        
        system_prompt = """You are a software engineering consultant specializing in failure analysis. Analyze failed attempts and provide concise, actionable guidance for avoiding common pitfalls.

Your output will be used as system prompt guidance, so be direct and specific.

Focus on:
1. Key blind spots to avoid
2. Critical risk points
3. Brief strategic approach

IMPORTANT: 
- Keep response under 200 words total
- Use plain text, no formatting
- Be specific and actionable
- Focus on risk avoidance"""
        
        formatted_attempts = self._format_approaches_data(approaches_data)
        
        prompt = f"""Analyze these failed attempts and provide concise guidance:

PROBLEM:
{problem_statement[:300]}...

FAILED ATTEMPTS:
{formatted_attempts[:800]}...

Provide concise guidance in this structure:

BLIND SPOTS TO AVOID:
[List 2-3 key systematic limitations observed]

CRITICAL RISKS:
[List 2-3 specific failure patterns to watch for]

STRATEGIC APPROACH:
[2-3 sentences on how to approach this problem differently]

Keep total response under 200 words. Be specific and actionable."""
        
        return self._call_llm_api(prompt, system_prompt)
    
    def _generate_content(self, instance_info: Dict[str, Any], problem_statement: str, trajectory_data: Dict[str, Any]) -> str:
        """Generate trajectory pool summary content"""
        instance_name = instance_info['instance_name']
        
        # Directly use the attached pool data
        approaches_data = instance_info.get('pool_data', {})
        if not approaches_data:
            self.logger.warning(f"Skipping {instance_name}: no trajectory pool data")
            return ""
        
        # Use placeholder problem statement (since current traj.pool format has no problem field)
        pool_problem = f"Instance {instance_name} software engineering problem"
        
        # Get all iteration data (numeric keys)
        iteration_data = {k: v for k, v in approaches_data.items() 
                         if k.isdigit() and isinstance(v, dict)}
        
        if not iteration_data:
            self.logger.warning(f"Skipping {instance_name}: no valid iteration data")
            return ""
        
        self.logger.info(f"Analyzing {instance_name}: {len(iteration_data)} historical attempts")
        
        # Generate risk-aware guidance
        guidance = self._generate_risk_aware_guidance(pool_problem, iteration_data)
        
        if not guidance:
            # If LLM call fails, provide simplified default guidance
            guidance = "Be careful with changes that affect multiple files. Test each change incrementally. Focus on understanding the problem before implementing solutions."
        
        return guidance


# Register operator
from operators import register_operator
register_operator("traj_pool_summary", TrajPoolSummaryOperator)