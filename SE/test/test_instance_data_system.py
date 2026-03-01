#!/usr/bin/env python3
"""
Test the unified Instance data management system
Verify that the new data flow interfaces work correctly
"""

import sys
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import (
    get_instance_data, get_iteration_instances, get_traj_pool_data,
    get_instance_data_manager, InstanceData
)

def test_instance_data_management():
    """Test Instance data management system"""

    print("Testing unified Instance data management system...")
    
    # Test directories
    test_iteration = "trajectories/Demo_Structure/iteration_1"
    test_instance = "trajectories/Demo_Structure/iteration_1/sphinx-doc__sphinx-8548"
    test_pool = "trajectories/Demo_Structure/traj.pool"
    
    # 1. Test single instance data retrieval
    print("\n1. Testing single instance data retrieval...")
    try:
        instance_data = get_instance_data(test_instance)
        print(f"PASS: Instance data retrieval succeeded: {instance_data.instance_name}")
        print(f"  Problem: {'✓' if instance_data.problem_description else '✗'}")
        print(f"  TRA: {'✓' if instance_data.tra_content else '✗'}")
        print(f"  TRAJ: {'✓' if instance_data.traj_content else '✗'}")
        print(f"  Patch: {'✓' if instance_data.patch_content else '✗'}")
        print(f"  Available files: {instance_data.available_files}")

        if instance_data.problem_description:
            print(f"  Problem preview: {instance_data.problem_description[:100]}...")
        
    except Exception as e:
        print(f"FAIL: Single instance data retrieval failed: {e}")
    
    # 2. Test iteration instance list retrieval
    print("\n2. Testing iteration instance list retrieval...")
    try:
        instances = get_iteration_instances(test_iteration)
        print(f"PASS: Iteration instances retrieval succeeded: {len(instances)} instances")

        for i, instance in enumerate(instances[:3]):  # Only show first 3
            print(f"  Instance {i+1}: {instance.instance_name}")
            print(f"    Data completeness: Problem={bool(instance.problem_description)}, "
                  f"TRA={bool(instance.tra_content)}, Patch={bool(instance.patch_content)}")

        if len(instances) > 3:
            print(f"  ... {len(instances) - 3} more instances")
            
    except Exception as e:
        print(f"FAIL: Iteration instance list retrieval failed: {e}")
    
    # 3. Test data completeness validation
    print("\n3. Testing data completeness validation...")
    try:
        manager = get_instance_data_manager()
        instance_data = get_instance_data(test_instance)
        validation = manager.validate_instance_completeness(instance_data)
        
        print(f"PASS: Completeness validation:")
        print(f"  Instance: {validation['instance_name']}")
        print(f"  Completeness score: {validation['completeness_score']}%")
        print(f"  Missing data: {validation['missing_data']}")
        print(f"  Available files: {validation['available_files']}")
        
    except Exception as e:
        print(f"FAIL: Data completeness validation failed: {e}")
    
    # 4. Test trajectory pool data retrieval
    print("\n4. Testing trajectory pool data retrieval...")
    try:
        if Path(test_pool).exists():
            pool_data = get_traj_pool_data(test_pool, "sphinx-doc__sphinx-8548")
            if pool_data:
                print(f"PASS: Trajectory pool data retrieval succeeded")
                print(f"  Problem: {pool_data.get('problem', 'N/A')[:100]}...")
                iterations = [k for k in pool_data.keys() if k.isdigit()]
                print(f"  Number of iterations: {len(iterations)}")
            else:
                print("WARNING: Specified instance not found in trajectory pool")
        else:
            print("WARNING: Trajectory pool file does not exist")
            
    except Exception as e:
        print(f"FAIL: Trajectory pool data retrieval failed: {e}")
    
    # 5. Test batch completeness report
    print("\n5. Testing batch completeness report...")
    try:
        from core.utils.traj_extractor import TrajExtractor
        extractor = TrajExtractor()
        report = extractor.get_instance_completeness_report(test_iteration)
        
        print(f"PASS: Completeness report generated successfully:")
        print(f"  Total instances: {report['total_instances']}")
        print(f"  Complete instances: {report['complete_instances']}")
        print(f"  Incomplete instances: {len(report['incomplete_instances'])}")
        print(f"  File availability:")
        for file_type, count in report['file_availability'].items():
            percentage = (count / report['total_instances']) * 100 if report['total_instances'] > 0 else 0
            print(f"    {file_type}: {count}/{report['total_instances']} ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"FAIL: Batch completeness report failed: {e}")
    
    print("\nInstance data management system test complete")

if __name__ == "__main__":
    test_instance_data_management()