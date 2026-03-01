#!/usr/bin/env python3

"""
Alternative Strategy Operator

Generates a fundamentally different alternative solution strategy based on the most recent failed attempt,
avoiding repetition of the same erroneous approaches.
"""

import json
from pathlib import Path
from typing import Dict, Any
from operators import TemplateOperator


class AlternativeStrategyOperator(TemplateOperator):
    """Alternative strategy operator, generates orthogonal solutions based on the most recent failed attempt"""
    
    def get_name(self) -> str:
        return "alternative_strategy"
    
    def get_strategy_prefix(self) -> str:
        return "ALTERNATIVE SOLUTION STRATEGY"
    
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
    
    def _get_latest_failed_approach(self, approaches_data: Dict[str, Any]) -> str:
        """Get detailed information about the most recent failed attempt"""
        if not approaches_data:
            return ""
        
        # Find the maximum iteration number
        iteration_nums = []
        for key in approaches_data.keys():
            if key != "problem" and key.isdigit():
                iteration_nums.append(int(key))
        
        if not iteration_nums:
            return ""
        
        latest_iteration = max(iteration_nums)
        latest_data = approaches_data.get(str(latest_iteration), {})
        
        # Format information about the most recent attempt
        approach_summary = []
        approach_summary.append(f"Strategy: {latest_data.get('strategy', 'N/A')}")
        
        # Check if this is a failed instance
        if latest_data.get('strategy_status') == 'FAILED':
            approach_summary.append(f"STATUS: FAILED - {latest_data.get('failure_reason', 'Unknown failure')}")
        
        if latest_data.get('modified_files'):
            approach_summary.append(f"Modified Files: {', '.join(latest_data['modified_files'])}")
        
        if latest_data.get('key_changes'):
            approach_summary.append(f"Key Changes: {'; '.join(latest_data['key_changes'])}")
            
        if latest_data.get('tools_used'):
            approach_summary.append(f"Tools Used: {', '.join(latest_data['tools_used'])}")
            
        if latest_data.get('reasoning_pattern'):
            approach_summary.append(f"Reasoning Pattern: {latest_data['reasoning_pattern']}")
            
        if latest_data.get('assumptions_made'):
            approach_summary.append(f"Assumptions: {'; '.join(latest_data['assumptions_made'])}")
        
        return "\n".join(approach_summary)
    
    def _generate_alternative_strategy(self, problem_statement: str, previous_approach: str) -> str:
        """Generate a fundamentally different alternative strategy"""
        
        system_prompt = """You are an expert software engineering strategist specializing in breakthrough problem-solving. Your task is to generate a fundamentally different approach to a software engineering problem, based on analyzing a previous failed attempt.

You will be given a problem and a previous approach that FAILED (possibly due to cost limits, early termination, or strategic inadequacy). Create a completely orthogonal strategy that:
1. Uses different investigation paradigms (e.g., runtime analysis vs static analysis)
2. Approaches from unconventional angles (e.g., user impact vs code structure)
3. Employs alternative tools and techniques
4. Follows different logical progression

CRITICAL: Your strategy must be architecturally dissimilar to avoid the same limitations and blind spots.

SPECIAL FOCUS: If the previous approach failed due to early termination or cost limits, prioritize:
- More focused, direct approaches
- Faster problem identification techniques
- Incremental validation methods
- Minimal viable change strategies

IMPORTANT: 
- Respond with plain text, no formatting
- Keep response under 200 words for system prompt efficiency
- Focus on cognitive framework rather than code specifics
- Provide actionable strategic guidance"""

        prompt = f"""Generate a radically different solution strategy:

PROBLEM:
{problem_statement[:400]}...

PREVIOUS FAILED APPROACH:
{previous_approach[:600]}...

Requirements for alternative strategy:
1. Adopt different investigation paradigm (e.g., empirical vs theoretical)
2. Start from alternative entry point (e.g., dependencies vs core logic)
3. Use non-linear logical sequence (e.g., symptom-to-cause vs cause-to-symptom)
4. Integrate unconventional techniques (e.g., profiling, fuzzing, visualization)
5. Prioritize overlooked aspects (e.g., performance, edge cases, integration)

Provide a concise strategic framework that enables an AI agent to approach this problem through an entirely different methodology. Focus on WHY this approach differs and HOW it circumvents previous limitations.

Keep response under 200 words."""

        return self._call_llm_api(prompt, system_prompt)
    
    def _generate_content(self, instance_info: Dict[str, Any], problem_statement: str, trajectory_data: Dict[str, Any]) -> str:
        """Generate alternative strategy content"""
        instance_dir = instance_info['instance_dir']
        instance_name = instance_info['instance_name']
        
        # Load trajectory pool data (from workspace_dir, computed via instance_dir)
        workspace_dir = instance_dir.parent.parent
        approaches_data = self._load_traj_pool(workspace_dir)
        if not approaches_data:
            self.logger.warning(f"Skipping {instance_name}: no trajectory pool data")
            return ""
        
        # Get the most recent failed attempt
        latest_approach = self._get_latest_failed_approach(approaches_data)
        if not latest_approach:
            self.logger.warning(f"Skipping {instance_name}: no recent failed attempt data")
            return ""
        
        self.logger.info(f"Analyzing {instance_name}: generating alternative strategy based on most recent failed attempt")
        
        # Generate alternative strategy
        strategy = self._generate_alternative_strategy(problem_statement, latest_approach)
        
        if not strategy:
            # If LLM call fails, provide a simple default alternative strategy
            strategy = "Try a more direct approach: focus on the specific error message, search for similar issues in the codebase, and make minimal targeted changes rather than broad modifications."
        
        return strategy


# Register operator
from operators import register_operator
register_operator("alternative_strategy", AlternativeStrategyOperator)