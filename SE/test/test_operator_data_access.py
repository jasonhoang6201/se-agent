#!/usr/bin/env python3
"""
SE Framework Simulated Operator Test Script

Since specific operators are not yet implemented, this script simulates
operator standard data access patterns to validate the completeness
and usability of the data interface.
"""

import sys
import tempfile
import os
import json
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils.instance_data_manager import InstanceDataManager
from core.utils.traj_pool_manager import TrajPoolManager


class MockOperator:
    """Mock operator demonstrating standard data access patterns"""

    def __init__(self, name: str):
        self.name = name
        self.manager = InstanceDataManager()

    def process_instance(self, instance_path: str, traj_pool_path: str = None) -> dict:
        """Simulate the standard workflow for an operator processing a single instance"""

        print(f"  {self.name} processing instance: {Path(instance_path).name}")

        # 1. Get complete instance data
        instance_data = self.manager.get_instance_data(instance_path)

        # 2. Access four core data formats
        problem = instance_data.problem_description
        tra_content = instance_data.tra_content
        patch_content = instance_data.patch_content
        traj_content = instance_data.traj_content

        print(f"    Problem description: {'OK' if problem else 'FAIL'} ({len(problem) if problem else 0} chars)")
        print(f"    TRA data: {'OK' if tra_content else 'FAIL'} ({len(tra_content) if tra_content else 0} chars)")
        print(f"    PATCH data: {'OK' if patch_content else 'FAIL'} ({len(patch_content) if patch_content else 0} chars)")
        print(f"    TRAJ data: {'OK' if traj_content else 'FAIL'} ({len(traj_content) if traj_content else 0} chars)")

        # 3. Get trajectory pool historical data (if available)
        pool_data = None
        if traj_pool_path:
            instance_name = instance_data.instance_name
            pool_data = self.manager.get_traj_pool_data(traj_pool_path, instance_name)
            if pool_data:
                iterations = [k for k in pool_data.keys() if k.isdigit()]
                print(f"    Trajectory pool data: OK ({len(iterations)} iterations)")
            else:
                print(f"    Trajectory pool data: FAIL")

        # 4. Data integrity validation
        completeness = self.manager.validate_instance_completeness(instance_data)
        print(f"    Data integrity: {completeness['completeness_score']}%")

        # 5. Simulate operator logic
        result = self._mock_operator_logic(problem, tra_content, patch_content, pool_data)

        return {
            "instance_name": instance_data.instance_name,
            "completeness": completeness['completeness_score'],
            "processing_result": result,
            "has_pool_data": pool_data is not None
        }

    def _mock_operator_logic(self, problem: str, tra_content: str, patch_content: str, pool_data: dict) -> str:
        """Simulate the core logic of an operator"""

        if not problem or not tra_content or not patch_content:
            return "Data incomplete, cannot process"

        # Simulate processing logic for different operator types
        if "crossover" in self.name.lower():
            return f"Generate crossover strategy based on historical trajectories (problem length: {len(problem)}, trajectory data: {len(tra_content)})"
        elif "conclusion" in self.name.lower():
            return f"Generate convergence guidance based on multiple attempts (trajectory pool data: {'available' if pool_data else 'unavailable'})"
        elif "summary" in self.name.lower():
            iterations = len([k for k in pool_data.keys() if k.isdigit()]) if pool_data else 0
            return f"Generate risk analysis based on {iterations} historical attempts"
        else:
            return f"Generic strategy generation (data integrity check passed)"


def create_mock_workspace(temp_dir: str) -> tuple:
    """Create a mock workspace"""

    workspace = Path(temp_dir)

    # Create multiple instances
    instances = []
    for i in range(3):
        instance_name = f"mock-instance-{i+1:03d}"
        instance_dir = workspace / instance_name
        instance_dir.mkdir(exist_ok=True)

        # Create .problem file
        with open(instance_dir / f"{instance_name}.problem", 'w', encoding='utf-8') as f:
            f.write(f"Fix issue #{i+1} in the codebase documentation system")

        # Create .tra file
        tra_data = {
            "compressed_trajectory": f"instance_{i+1}_trajectory_data",
            "steps": ["analyze", "implement", "test"],
            "result": "completed"
        }
        with open(instance_dir / f"{instance_name}.tra", 'w', encoding='utf-8') as f:
            json.dump(tra_data, f, indent=2)

        # Create .patch file
        with open(instance_dir / f"{instance_name}.patch", 'w', encoding='utf-8') as f:
            f.write(f"diff --git a/file{i+1}.py b/file{i+1}.py\n+# Fix for issue {i+1}\n+fixed_code_here()")

        # Create .traj file
        with open(instance_dir / f"{instance_name}.traj", 'w', encoding='utf-8') as f:
            f.write(f"Full trajectory for instance {i+1}...\nDetailed execution log here...")

        instances.append(str(instance_dir))

    # Create trajectory pool
    pool_path = workspace / "mock.pool"
    pool_data = {}

    for i, instance_name in enumerate([f"mock-instance-{i+1:03d}" for i in range(3)]):
        pool_data[instance_name] = {
            "problem": f"Fix issue #{i+1} in the codebase documentation system",
            "1": {
                "approach_summary": f"Attempted to fix issue {i+1} using method A",
                "modified_files": [f"/path/to/file{i+1}.py"],
                "strategy": f"Direct modification approach for issue {i+1}",
                "tools_used": ["str_replace_editor", "bash"],
                "reasoning_pattern": "analyze -> implement -> test"
            },
            "2": {
                "approach_summary": f"Alternative approach for issue {i+1} using method B",
                "modified_files": [f"/path/to/file{i+1}.py", f"/path/to/config{i+1}.json"],
                "strategy": f"Configuration-based approach for issue {i+1}",
                "tools_used": ["str_replace_editor", "find", "grep"],
                "reasoning_pattern": "research -> configure -> validate"
            }
        }

    with open(pool_path, 'w', encoding='utf-8') as f:
        json.dump(pool_data, f, indent=2, ensure_ascii=False)

    return instances, str(pool_path)


def test_crossover_operator():
    """Test Crossover operator data access pattern"""
    print("1. Testing Crossover operator data access pattern")

    with tempfile.TemporaryDirectory() as temp_dir:
        instances, pool_path = create_mock_workspace(temp_dir)

        operator = MockOperator("CrossoverOperator")
        results = []

        for instance_path in instances:
            result = operator.process_instance(instance_path, pool_path)
            results.append(result)

        # Validate results
        success = all(r['completeness'] >= 100 for r in results)
        print(f"  {'Passed' if success else 'Failed'}: All instance data integrity: {success}")

        return success


def test_conclusion_operator():
    """Test Conclusion operator data access pattern"""
    print("2. Testing Conclusion operator data access pattern")

    with tempfile.TemporaryDirectory() as temp_dir:
        instances, pool_path = create_mock_workspace(temp_dir)

        operator = MockOperator("ConclusionOperator")
        results = []

        for instance_path in instances:
            result = operator.process_instance(instance_path, pool_path)
            results.append(result)

        # Validate trajectory pool data access
        success = all(r['has_pool_data'] for r in results)
        print(f"  {'Passed' if success else 'Failed'}: Trajectory pool data access: {success}")

        return success


def test_summary_operator():
    """Test Summary operator data access pattern"""
    print("3. Testing Summary operator data access pattern")

    with tempfile.TemporaryDirectory() as temp_dir:
        instances, pool_path = create_mock_workspace(temp_dir)

        operator = MockOperator("SummaryOperator")
        results = []

        for instance_path in instances:
            result = operator.process_instance(instance_path, pool_path)
            results.append(result)
            print(f"    Processing result: {result['processing_result']}")

        # Validate processing success
        success = all("historical attempts" in r['processing_result'] for r in results)
        print(f"  {'Passed' if success else 'Failed'}: Historical data analysis: {success}")

        return success


def test_data_format_standards():
    """Test data format standards"""
    print("4. Testing data format standards")

    with tempfile.TemporaryDirectory() as temp_dir:
        instances, pool_path = create_mock_workspace(temp_dir)

        manager = InstanceDataManager()
        format_checks = []

        for instance_path in instances:
            instance_data = manager.get_instance_data(instance_path)

            # Check four core formats
            checks = {
                "problem_text": isinstance(instance_data.problem_description, str),
                "tra_json": instance_data.tra_content and '{' in instance_data.tra_content,
                "patch_diff": instance_data.patch_content and 'diff --git' in instance_data.patch_content,
                "traj_text": isinstance(instance_data.traj_content, str)
            }

            format_checks.append(all(checks.values()))
            print(f"    Instance {instance_data.instance_name}: {checks}")

        success = all(format_checks)
        print(f"  {'Passed' if success else 'Failed'}: Data format standards: {success}")

        return success


def test_priority_mechanisms():
    """Test priority mechanisms"""
    print("5. Testing file priority mechanisms")

    with tempfile.TemporaryDirectory() as temp_dir:
        instance_dir = Path(temp_dir) / "priority-test"
        instance_dir.mkdir()

        # Create .patch and .pred files
        with open(instance_dir / "priority-test.patch", 'w') as f:
            f.write("patch content - should be used")

        with open(instance_dir / "priority-test.pred", 'w') as f:
            f.write("pred content - should be ignored")

        # Create .problem file
        with open(instance_dir / "priority-test.problem", 'w') as f:
            f.write("problem from file")

        # Create .tra file (containing problem description)
        tra_data = {
            "Trajectory": [
                {"role": "user", "content": [{"text": "<pr_description>\nproblem from trajectory\n</pr_description>"}]}
            ]
        }
        with open(instance_dir / "priority-test.tra", 'w') as f:
            json.dump(tra_data, f)

        manager = InstanceDataManager()
        instance_data = manager.get_instance_data(str(instance_dir))

        # Validate priority
        patch_priority = "patch content" in instance_data.patch_content
        problem_priority = instance_data.problem_description == "problem from file"

        print(f"    PATCH priority: {'Passed' if patch_priority else 'Failed'} (.patch > .pred)")
        print(f"    Problem priority: {'Passed' if problem_priority else 'Failed'} (.problem > trajectory)")

        success = patch_priority and problem_priority
        print(f"  {'Passed' if success else 'Failed'}: Priority mechanisms: {success}")

        return success


def main():
    """Main test function"""
    print("SE Framework Simulated Operator Test")
    print("Test scope: operator data access patterns, format standards, priority mechanisms")
    print("=" * 60)

    tests = [
        ("Crossover Operator Data Access", test_crossover_operator),
        ("Conclusion Operator Data Access", test_conclusion_operator),
        ("Summary Operator Data Access", test_summary_operator),
        ("Data Format Standards", test_data_format_standards),
        ("Priority Mechanisms", test_priority_mechanisms),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 40)
        try:
            success = test_func()
            results.append(success)
        except Exception as e:
            print(f"Failed: Test exception: {e}")
            results.append(False)

    # Test summary
    passed = sum(results)
    total = len(results)

    print(f"\nTest Summary")
    print("=" * 60)
    print(f"Pass rate: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("All tests passed! Operator data access interface is fully functional.")
        return True
    else:
        print("Some tests failed. Operator implementation must follow data access standards.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
