#!/usr/bin/env python3
"""
Test LLM integration using real trajectory data
"""

import sys
import os
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.llm_client import LLMClient, TrajectorySummarizer
from core.utils.traj_pool_manager import TrajPoolManager

def test_with_real_trajectory():
    """Test with real trajectory data"""

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
    
    print("Testing LLM integration with real trajectory data...")
    
    try:
        # Create LLM client
        llm_client = LLMClient.from_se_config(se_config, use_operator_model=True)
        print(f"LLM client created successfully: {llm_client.config['name']}")

        # Create trajectory pool manager
        pool_path = "/tmp/real_traj_test_pool.json"
        traj_pool_manager = TrajPoolManager(pool_path, llm_client)
        traj_pool_manager.initialize_pool()
        
        # Read real trajectory data
        traj_dir = "trajectories/test_20250714_143856"
        iteration_dirs = ["iteration_1", "iteration_2"]
        
        for i, iter_dir in enumerate(iteration_dirs, 1):
            print(f"\nProcessing {iter_dir}...")

            # Trajectory file paths
            tra_file = f"{traj_dir}/{iter_dir}/sphinx-doc__sphinx-10435/sphinx-doc__sphinx-10435.tra"
            pred_file = f"{traj_dir}/{iter_dir}/sphinx-doc__sphinx-10435/sphinx-doc__sphinx-10435.pred"
            
            # Check if files exist
            if not os.path.exists(tra_file):
                print(f"Trajectory file does not exist: {tra_file}")
                continue
                
            if not os.path.exists(pred_file):
                print(f"Prediction file does not exist: {pred_file}")
                continue
            
            # Read file contents
            with open(tra_file, 'r', encoding='utf-8') as f:
                trajectory_content = f.read()
            
            with open(pred_file, 'r', encoding='utf-8') as f:
                prediction_content = f.read()
            
            print(f"Trajectory content length: {len(trajectory_content)} characters")
            print(f"Prediction content length: {len(prediction_content)} characters")

            # Perform LLM summarization
            summary = traj_pool_manager.summarize_trajectory(
                trajectory_content, prediction_content, i
            )
            
            print(f"Iteration {i} LLM summary successful:")
            print(f"  Approach summary: {summary.get('approach_summary', 'N/A')}")
            print(f"  Modified files: {summary.get('modified_files', 'N/A')}")
            print(f"  Key changes: {summary.get('key_changes', 'N/A')}")
            print(f"  Strategy: {summary.get('strategy', 'N/A')}")
            print(f"  Techniques: {summary.get('specific_techniques', 'N/A')}")
            print(f"  Is fallback: {summary.get('meta', {}).get('is_fallback', False)}")
            
            # Add to trajectory pool
            problem = "Incorrect result with Quaternion.to_rotation_matrix()"
            traj_pool_manager.add_iteration_summary(
                instance_name="sphinx-doc__sphinx-10435",
                iteration=i,
                trajectory_content=trajectory_content,
                prediction_content=prediction_content,
                problem=problem
            )
        
        # Display final statistics
        stats = traj_pool_manager.get_pool_stats()
        print(f"\nFinal trajectory pool statistics: {stats}")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    try:
        os.remove(pool_path)
        print(f"\nCleaning up temporary file: {pool_path}")
    except:
        pass

if __name__ == "__main__":
    test_with_real_trajectory()