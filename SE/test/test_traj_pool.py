#!/usr/bin/env python3
"""
Standalone test script for trajectory pool and prompt system
"""

import sys
import tempfile
import os
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.traj_pool_manager import TrajPoolManager
from core.utils.traj_summarizer import TrajSummarizer


def test_traj_summarizer():
    """Test trajectory summarizer"""
    print("=== Test TrajSummarizer ===")

    summarizer = TrajSummarizer()

    # Mock trajectory and prediction data
    mock_trajectory = {
        "trajectory": [
            {"action": "str_replace", "observation": "File modified"},
            {"action": "bash", "observation": "Test passed"}
        ],
        "info": {"exit_status": "submission"}
    }

    mock_prediction = {
        "instance_id": "test_123",
        "model_patch": "some patch content",
        "reasoning": "solution approach"
    }

    import json
    trajectory_content = json.dumps(mock_trajectory, indent=2)
    prediction_content = json.dumps(mock_prediction, indent=2)

    print("1. System Prompt:")
    print(summarizer.get_system_prompt()[:200] + "...")

    print("\n2. User Prompt:")
    user_prompt = summarizer.format_user_prompt(trajectory_content, prediction_content)
    print(user_prompt[:300] + "...")

    print("\n3. Fallback Summary:")
    fallback = summarizer.create_fallback_summary(trajectory_content, prediction_content, 1)
    print(json.dumps(fallback, indent=2))

    print("\n4. Response Validation:")
    is_valid = summarizer.validate_response_format(fallback)
    print(f"Fallback summary is valid: {is_valid}")


def test_traj_pool_manager():
    """Test trajectory pool manager"""
    print("\n=== Test TrajPoolManager ===")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        pool_path = os.path.join(temp_dir, "test_traj.pool")
        manager = TrajPoolManager(pool_path)

        print(f"1. Initialize trajectory pool: {pool_path}")
        manager.initialize_pool()

        print("2. Add test data")
        # Mock data
        test_instances = [
            ("sphinx-doc__sphinx-8548", "Mock trajectory content 1", "Mock prediction content 1"),
            ("sphinx-doc__sphinx-8551", "Mock trajectory content 2", "Mock prediction content 2")
        ]

        for instance_name, traj_content, pred_content in test_instances:
            for iteration in [1, 2]:
                manager.add_iteration_summary(
                    instance_name=instance_name,
                    iteration=iteration,
                    trajectory_content=traj_content,
                    prediction_content=pred_content
                )
                print(f"   Added: {instance_name} iteration {iteration}")

        print("3. Trajectory pool statistics")
        stats = manager.get_pool_stats()
        print(f"   Total instances: {stats['total_instances']}")
        print(f"   Total iterations: {stats['total_iterations']}")
        print(f"   Instance list: {stats['instances']}")

        print("4. Get specific instance summary")
        instance_summary = manager.get_instance_summary("sphinx-doc__sphinx-8548")
        if instance_summary:
            print(f"   sphinx-doc__sphinx-8548 has {len(instance_summary)} iterations")
            for iter_num, summary in instance_summary.items():
                approach = summary.get('approach_summary', 'N/A') if isinstance(summary, dict) else str(summary)[:50]
                print(f"     Iteration {iter_num}: {approach}")

        print(f"5. Pool file content preview")
        pool_data = manager.load_pool()
        print(f"   File size: {len(str(pool_data))} characters")

        # Display the first iteration of the first instance as an example
        if pool_data:
            first_instance = list(pool_data.keys())[0]
            first_iteration = list(pool_data[first_instance].keys())[0]
            first_summary = pool_data[first_instance][first_iteration]
            print(f"   Example summary: {first_instance} iteration {first_iteration}")
            if isinstance(first_summary, dict):
                print(f"     Strategy: {first_summary.get('strategy', 'N/A')}")
                print(f"     Techniques: {first_summary.get('specific_techniques', 'N/A')}")


def main():
    """Main test function"""
    print("Trajectory pool and prompt system test")
    print("=" * 50)

    try:
        test_traj_summarizer()
        test_traj_pool_manager()

        print("\nAll tests completed!")

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
