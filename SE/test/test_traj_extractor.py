#!/usr/bin/env python3
"""
Test TrajExtractor and updated TrajPoolManager
"""

import sys
import tempfile
import os
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.traj_extractor import TrajExtractor
from core.utils.traj_pool_manager import TrajPoolManager


def test_real_data_extraction():
    """Test extracting data from actual run results"""
    print("=== Test Real Data Extraction ===")
    
    # Use the actual run results directory mentioned
    test_dir = Path("/home/uaih3k9x/630_swe/SE/trajectories/test_20250714_142331/iteration_1")
    
    if not test_dir.exists():
        print(f"WARNING: Test directory does not exist: {test_dir}")
        return
    
    extractor = TrajExtractor()
    
    print(f"1. Extracting data from directory: {test_dir}")
    instance_data_list = extractor.extract_instance_data_from_directory(test_dir)

    print(f"2. Extracted {len(instance_data_list)} instances")
    
    for instance_name, problem, tra_content, pred_content in instance_data_list:
        print(f"\nInstance: {instance_name}")
        print(f"  Problem length: {len(problem) if problem else 0} chars")
        print(f"  Trajectory length: {len(tra_content)} chars")
        print(f"  Prediction length: {len(pred_content)} chars")
        
        if problem:
            problem_preview = problem[:100] + "..." if len(problem) > 100 else problem
            print(f"  Problem preview: {problem_preview}")
        
        # Test trajectory pool manager
        with tempfile.TemporaryDirectory() as temp_dir:
            pool_path = os.path.join(temp_dir, "test_real.pool")
            manager = TrajPoolManager(pool_path)
            manager.initialize_pool()
            
            # Add data
            manager.add_iteration_summary(
                instance_name=instance_name,
                iteration=1,
                trajectory_content=tra_content,
                prediction_content=pred_content,
                problem=problem
            )
            
            # Check results
            pool_data = manager.load_pool()
            instance_pool_data = pool_data.get(instance_name, {})
            
            print(f"  Trajectory pool fields: {list(instance_pool_data.keys())}")
            if "problem" in instance_pool_data:
                print(f"  PASS: Problem field added")
            if "1" in instance_pool_data:
                iteration_summary = instance_pool_data["1"]
                if isinstance(iteration_summary, dict):
                    print(f"  PASS: Iteration 1 summary contains {len(iteration_summary)} fields")
                    print(f"  Strategy: {iteration_summary.get('strategy', 'N/A')}")
                    print(f"  Approach: {iteration_summary.get('approach_summary', 'N/A')}")


def test_multiple_iterations():
    """Test multi-iteration data"""
    print("\n=== Test Multi-Iteration Data ===")
    
    base_dir = Path("/home/uaih3k9x/630_swe/SE/trajectories/test_20250714_142331")
    
    if not base_dir.exists():
        print(f"WARNING: Base directory does not exist: {base_dir}")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        pool_path = os.path.join(temp_dir, "test_multi.pool")
        manager = TrajPoolManager(pool_path)
        manager.initialize_pool()
        extractor = TrajExtractor()
        
        # Process multiple iterations
        for iteration in [1, 2]:
            iteration_dir = base_dir / f"iteration_{iteration}"
            if iteration_dir.exists():
                print(f"\nProcessing iteration {iteration}:")
                instance_data_list = extractor.extract_instance_data_from_directory(iteration_dir)
                
                for instance_name, problem, tra_content, pred_content in instance_data_list:
                    manager.add_iteration_summary(
                        instance_name=instance_name,
                        iteration=iteration,
                        trajectory_content=tra_content,
                        prediction_content=pred_content,
                        problem=problem
                    )
                    print(f"  PASS: Added {instance_name} iteration {iteration}")
        
        # Show final statistics
        stats = manager.get_pool_stats()
        print(f"\nFinal statistics:")
        print(f"  Total instances: {stats['total_instances']}")
        print(f"  Total iterations: {stats['total_iterations']}")
        print(f"  Instance list: {stats['instances']}")
        
        # Show complete data for the first instance
        if stats['instances']:
            first_instance = stats['instances'][0]
            instance_summary = manager.get_instance_summary(first_instance)
            print(f"\n{first_instance} complete data:")
            if instance_summary and "problem" in instance_summary:
                problem_preview = instance_summary["problem"][:100] + "..." if len(instance_summary["problem"]) > 100 else instance_summary["problem"]
                print(f"  Problem: {problem_preview}")

            for key, value in instance_summary.items():
                if key != "problem" and key.isdigit():
                    print(f"  Iteration {key}: {value.get('approach_summary', 'N/A') if isinstance(value, dict) else str(value)[:50]}")


def main():
    """Main test function"""
    print("TrajExtractor and TrajPoolManager integration test")
    print("=" * 60)
    
    try:
        test_real_data_extraction()
        test_multiple_iterations()
        
        print("\nAll tests complete!")

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()