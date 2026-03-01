#!/usr/bin/env python3
"""
SE Framework Unified Data Interface Test Script

Tests the unified data management system, including:
- InstanceDataManager core functionality
- Four standard data format access
- Trajectory pool data retrieval
- Data integrity validation
- Backward compatibility checks
"""

import sys
import tempfile
import os
import json
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils.instance_data_manager import InstanceDataManager, InstanceData
from core.utils.traj_pool_manager import TrajPoolManager
from core.utils.traj_extractor import TrajExtractor
from core.utils.llm_client import LLMClient


def create_test_instance(temp_dir: str, instance_name: str) -> str:
    """Create test instance data"""
    instance_dir = Path(temp_dir) / instance_name
    instance_dir.mkdir(exist_ok=True)

    # Create .problem file
    with open(instance_dir / f"{instance_name}.problem", 'w', encoding='utf-8') as f:
        f.write("Fix bug in sphinx documentation generation when handling None docstrings")

    # Create .tra file
    with open(instance_dir / f"{instance_name}.tra", 'w', encoding='utf-8') as f:
        f.write('{"step1": "analyze", "step2": "fix", "step3": "test"}')

    # Create .patch file (takes priority over .pred)
    with open(instance_dir / f"{instance_name}.patch", 'w', encoding='utf-8') as f:
        f.write("diff --git a/file.py b/file.py\n+if docstring is None:\n+    return []")

    # Create .pred file (should be ignored)
    with open(instance_dir / f"{instance_name}.pred", 'w', encoding='utf-8') as f:
        f.write("This should be ignored in favor of .patch")

    # Create .traj file
    with open(instance_dir / f"{instance_name}.traj", 'w', encoding='utf-8') as f:
        f.write("Full trajectory content here...")

    return str(instance_dir)


def test_instance_data_manager():
    """Test InstanceDataManager core functionality"""
    print("1. Testing InstanceDataManager...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test instance
        instance_path = create_test_instance(temp_dir, "test-instance")

        # Test data manager
        manager = InstanceDataManager()
        instance_data = manager.get_instance_data(instance_path)

        # Validate data integrity
        completeness = manager.validate_instance_completeness(instance_data)

        print(f"  Success: Instance data loaded: {instance_data.instance_name}")
        print(f"  Success: Integrity validation: {completeness['completeness_score']}%")

        # Verify .patch takes priority over .pred
        if "diff --git" in instance_data.patch_content:
            print(f"  Success: Correctly using .patch file")
        else:
            print(f"  Failed: Incorrectly using .pred file")
            return False

        return True


def test_four_core_formats():
    """Test four core data formats"""
    print("2. Testing four core data formats...")

    with tempfile.TemporaryDirectory() as temp_dir:
        instance_path = create_test_instance(temp_dir, "format-test")

        manager = InstanceDataManager()
        instance_data = manager.get_instance_data(instance_path)

        # 1. Problem Description
        if instance_data.problem_description:
            print(f"  Success: Problem Description: {len(instance_data.problem_description)} characters")
        else:
            print(f"  Failed: Problem Description missing")
            return False

        # 2. TRA (compressed trajectory)
        if instance_data.tra_content:
            print(f"  Success: TRA Content: {len(instance_data.tra_content)} characters")
        else:
            print(f"  Failed: TRA Content missing")
            return False

        # 3. PATCH (prediction result)
        if instance_data.patch_content:
            print(f"  Success: PATCH Content: {len(instance_data.patch_content)} characters")
        else:
            print(f"  Failed: PATCH Content missing")
            return False

        # 4. TRAJ (raw trajectory)
        if instance_data.traj_content:
            print(f"  Success: TRAJ Content: {len(instance_data.traj_content)} characters")
        else:
            print(f"  Warning: TRAJ Content missing (optional)")

        return True


def test_trajectory_pool():
    """Test trajectory pool data management"""
    print("3. Testing trajectory pool data management...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create trajectory pool
        pool_path = os.path.join(temp_dir, "test.pool")

        # Create mock LLM client (if available)
        llm_client = None
        try:
            test_config = {
                "model": {
                    "name": "openai/deepseek-chat",
                    "api_base": "http://publicshare.a.pinggy.link",
                    "api_key": "EMPTY",
                    "max_output_tokens": 1000
                }
            }
            llm_client = LLMClient.from_se_config(test_config)
            print(f"  Success: LLM client initialized")
        except Exception as e:
            print(f"  Warning: LLM client unavailable, using fallback mode: {e}")

        pool_manager = TrajPoolManager(pool_path, llm_client)
        pool_manager.initialize_pool()

        # Add test data
        pool_manager.add_iteration_summary(
            instance_name="test-instance",
            iteration=1,
            trajectory_content='{"test": "trajectory"}',
            patch_content="test patch content",
            problem_description="Test problem description"
        )

        # Test data retrieval
        manager = InstanceDataManager()
        pool_data = manager.get_traj_pool_data(pool_path, "test-instance")

        if pool_data:
            print(f"  Success: Trajectory pool data retrieved")
            print(f"  Success: Contains data: {list(pool_data.keys())}")

            # Test specific iteration retrieval
            iter_summary = manager.get_instance_iteration_summary(pool_path, "test-instance", 1)
            if iter_summary:
                print(f"  Success: Iteration data retrieved")
            else:
                print(f"  Failed: Iteration data retrieval failed")
                return False
        else:
            print(f"  Failed: Trajectory pool data retrieval failed")
            return False

        return True


def test_backward_compatibility():
    """Test backward compatibility"""
    print("4. Testing backward compatibility...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple test instances
        for i in range(3):
            create_test_instance(temp_dir, f"compat-test-{i+1:03d}")

        extractor = TrajExtractor()

        # Test legacy interface
        legacy_data = extractor.extract_instance_data(temp_dir)
        print(f"  Success: Legacy interface extracted: {len(legacy_data)} instances")

        # Test new interface
        structured_data = extractor.extract_instances_structured(temp_dir)
        print(f"  Success: New interface extracted: {len(structured_data)} instances")

        # Validate consistency
        if len(legacy_data) == len(structured_data):
            print(f"  Success: Legacy and new interface data are consistent")
        else:
            print(f"  Failed: Legacy and new interface data are inconsistent")
            return False

        return True


def test_operator_integration():
    """Test Operator integration mode"""
    print("5. Testing Operator integration mode...")

    with tempfile.TemporaryDirectory() as temp_dir:
        instance_path = create_test_instance(temp_dir, "operator-test")

        # Simulate Operator's standard data access pattern
        manager = InstanceDataManager()

        # Get instance data
        instance_data = manager.get_instance_data(instance_path)

        # Access four core data types
        problem = instance_data.problem_description
        tra_data = instance_data.tra_content
        patch_data = instance_data.patch_content
        traj_data = instance_data.traj_content

        print(f"  Success: Problem access: {'OK' if problem else 'FAIL'}")
        print(f"  Success: TRA access: {'OK' if tra_data else 'FAIL'}")
        print(f"  Success: Patch access: {'OK' if patch_data else 'FAIL'}")
        print(f"  Success: Traj access: {'OK' if traj_data else 'FAIL'}")

        # Validate data integrity
        validation = manager.validate_instance_completeness(instance_data)
        print(f"  Success: Data integrity: {validation['completeness_score']}%")

        return validation['completeness_score'] >= 100


def main():
    """Main test function"""
    print("SE Framework Unified Data Interface Test")
    print("=" * 50)

    tests = [
        ("InstanceDataManager Core Functionality", test_instance_data_manager),
        ("Four Core Data Formats", test_four_core_formats),
        ("Trajectory Pool Data Management", test_trajectory_pool),
        ("Backward Compatibility", test_backward_compatibility),
        ("Operator Integration Mode", test_operator_integration),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 30)
        try:
            success = test_func()
            results.append(success)
            print(f"{'Passed' if success else 'Failed'}")
        except Exception as e:
            print(f"Failed: Test exception: {e}")
            results.append(False)

    # Test summary
    passed = sum(results)
    total = len(results)

    print(f"\nTest Summary")
    print("=" * 50)
    print(f"Pass rate: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("All tests passed! Unified data interface is fully functional.")
        return True
    else:
        print("Some tests failed. Please check system configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
