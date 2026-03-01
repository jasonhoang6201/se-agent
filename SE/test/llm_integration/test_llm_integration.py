#!/usr/bin/env python3
"""
Test LLM integration with the trajectory pool manager
"""

import sys
import os
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.llm_client import LLMClient, TrajectorySummarizer
from core.utils.traj_pool_manager import TrajPoolManager

def test_llm_integration():
    """Test LLM integration functionality"""

    # Simulated SE configuration
    se_config = {
        "model": {
            "name": "openai/deepseek-chat",
            "api_base": "http://publicshare.a.pinggy.link", 
            "api_key": "EMPTY",
            "max_input_tokens": 128000,
            "max_output_tokens": 64000
        },
        "operator_models": {
            "name": "openai/deepseek-chat",
            "api_base": "http://publicshare.a.pinggy.link",
            "api_key": "EMPTY", 
            "max_input_tokens": 128000,
            "max_output_tokens": 64000
        }
    }
    
    print("Testing LLM client creation...")
    try:
        llm_client = LLMClient.from_se_config(se_config, use_operator_model=True)
        print(f"LLM client created successfully: {llm_client.config['name']}")
    except Exception as e:
        print(f"LLM client creation failed: {e}")
        return
    
    print("\nTesting trajectory pool manager...")
    try:
        # Create temporary trajectory pool
        pool_path = "/tmp/test_traj_pool.json"
        traj_pool_manager = TrajPoolManager(pool_path, llm_client)
        traj_pool_manager.initialize_pool()
        print(f"Trajectory pool manager created successfully: {pool_path}")
    except Exception as e:
        print(f"Trajectory pool manager creation failed: {e}")
        return
    
    print("\nTesting trajectory summarization...")
    try:
        # Simulated trajectory data
        trajectory_content = """
        {
            "history": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Fix the quaternion rotation matrix bug"},
                {"role": "assistant", "content": "I'll analyze the quaternion.py file..."},
                {"role": "user", "content": "Good, what did you find?"},
                {"role": "assistant", "content": "The issue is with the sign of sin(x) in the rotation matrix"}
            ]
        }
        """
        
        prediction_content = """
        The bug was in the to_rotation_matrix() method where one of the sin(x) terms 
        should be negative. I fixed it by changing the sign in the matrix construction.
        """
        
        summary = traj_pool_manager.summarize_trajectory(
            trajectory_content, prediction_content, 1
        )
        
        print(f"Trajectory summarization successful:")
        print(f"  Approach summary: {summary.get('approach_summary', 'N/A')}")
        print(f"  Modified files: {summary.get('modified_files', 'N/A')}")
        print(f"  Key changes: {summary.get('key_changes', 'N/A')}")
        print(f"  Is fallback: {summary.get('meta', {}).get('is_fallback', False)}")

    except Exception as e:
        print(f"Trajectory summarization failed: {e}")
    
    print("\nTesting add iteration summary...")
    try:
        traj_pool_manager.add_iteration_summary(
            instance_name="test-instance",
            iteration=1,
            trajectory_content=trajectory_content,
            prediction_content=prediction_content,
            problem="Fix quaternion rotation matrix bug"
        )
        print("Iteration summary added successfully")

        # Check pool statistics
        stats = traj_pool_manager.get_pool_stats()
        print(f"  Pool statistics: {stats}")

    except Exception as e:
        print(f"Iteration summary addition failed: {e}")
    
    # Cleanup
    try:
        os.remove(pool_path)
        print(f"\nCleaning up temporary file: {pool_path}")
    except:
        pass

if __name__ == "__main__":
    test_llm_integration()