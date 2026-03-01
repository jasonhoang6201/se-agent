#!/usr/bin/env python3
"""
Fix existing traj.pool files by adding real data
"""

import sys
import json
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.traj_extractor import TrajExtractor
from core.utils.traj_pool_manager import TrajPoolManager


def fix_traj_pool(base_dir: str):
    """
    Fix the traj.pool file in the specified directory

    Args:
        base_dir: Base directory containing iteration directories and traj.pool
    """
    base_path = Path(base_dir)
    pool_path = base_path / "traj.pool"

    if not base_path.exists():
        print(f"Failed: Directory does not exist: {base_path}")
        return

    if not pool_path.exists():
        print(f"Failed: traj.pool file does not exist: {pool_path}")
        return

    print(f"Fixing trajectory pool: {pool_path}")

    # Back up the original file
    backup_path = pool_path.with_suffix('.pool.backup')
    try:
        import shutil
        shutil.copy2(pool_path, backup_path)
        print(f"Backup created: {backup_path}")
    except Exception as e:
        print(f"Warning: Backup failed: {e}")

    # Create new manager and extractor
    manager = TrajPoolManager(str(pool_path))
    extractor = TrajExtractor()

    # Reinitialize the pool
    manager.initialize_pool()

    # Find all iteration directories
    iteration_dirs = []
    for item in base_path.iterdir():
        if item.is_dir() and item.name.startswith('iteration_'):
            try:
                iteration_num = int(item.name.split('_')[1])
                iteration_dirs.append((iteration_num, item))
            except (ValueError, IndexError):
                continue

    iteration_dirs.sort(key=lambda x: x[0])  # Sort by iteration number

    print(f"Found {len(iteration_dirs)} iteration directories")

    total_instances = 0
    total_iterations = 0

    # Process each iteration
    for iteration_num, iteration_dir in iteration_dirs:
        print(f"\nProcessing iteration {iteration_num}: {iteration_dir}")

        # Extract data
        instance_data_list = extractor.extract_instance_data_from_directory(iteration_dir)

        if instance_data_list:
            for instance_name, problem, trajectory_content, prediction_content in instance_data_list:
                # Add to pool
                manager.add_iteration_summary(
                    instance_name=instance_name,
                    iteration=iteration_num,
                    trajectory_content=trajectory_content,
                    prediction_content=prediction_content,
                    problem=problem
                )
                print(f"  Added: {instance_name}")
                total_iterations += 1

            total_instances += len(instance_data_list)
        else:
            print(f"  Warning: No valid data found in iteration {iteration_num}")

    # Display final results
    final_stats = manager.get_pool_stats()
    print(f"\nFix completed:")
    print(f"  Total instances: {final_stats['total_instances']}")
    print(f"  Total iterations: {final_stats['total_iterations']}")
    print(f"  Instance list: {final_stats['instances']}")

    # Display file size
    try:
        file_size = pool_path.stat().st_size
        print(f"  File size: {file_size:,} bytes")
    except Exception as e:
        print(f"  Failed to get file size: {e}")

    # Display example of the first instance
    if final_stats['instances']:
        first_instance = final_stats['instances'][0]
        instance_summary = manager.get_instance_summary(first_instance)
        print(f"\n{first_instance} example:")

        if instance_summary and "problem" in instance_summary:
            problem_preview = instance_summary["problem"][:100] + "..." if len(instance_summary["problem"]) > 100 else instance_summary["problem"]
            print(f"  Problem: {problem_preview}")

        for key, value in instance_summary.items():
            if key != "problem" and key.isdigit():
                if isinstance(value, dict):
                    approach = value.get('approach_summary', 'N/A')
                    strategy = value.get('strategy', 'N/A')
                    print(f"  Iteration {key}: {approach} (strategy: {strategy})")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Fix existing traj.pool files')
    parser.add_argument('directory',
                        default='/home/uaih3k9x/630_swe/SE/trajectories/test_20250714_142331',
                        nargs='?',
                        help='Base directory containing traj.pool and iteration directories')

    args = parser.parse_args()

    print("Traj Pool Repair Tool")
    print("=" * 50)
    print(f"Target directory: {args.directory}")

    try:
        fix_traj_pool(args.directory)
        print("\nRepair completed!")

    except Exception as e:
        print(f"\nRepair failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
