#!/usr/bin/env python3
"""
Test the unified problem description retrieval interface
"""

import sys
from pathlib import Path

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import get_problem_description, validate_problem_availability

def test_problem_interface():
    """Test unified problem description interface"""

    print("Testing unified problem description retrieval interface...")

    # Test directory - use instances from Demo_Structure
    test_instance = "trajectories/Demo_Structure/iteration_1/sphinx-doc__sphinx-8548"

    if not Path(test_instance).exists():
        print(f"Failed: Test instance directory does not exist: {test_instance}")
        return

    print(f"\nTest instance: {test_instance}")

    # 1. Validate problem description availability
    print("\n1. Validating problem description availability...")
    try:
        validation = validate_problem_availability(test_instance)
        print(f"Success: Validation result:")
        print(f"  Instance name: {validation['instance_name']}")
        print(f"  Available methods: {validation['methods_available']}")
        print(f"  Primary source: {validation['primary_source']}")
        print(f"  Content length: {validation['problem_length']}")
        print(f"  Content preview: {validation['problem_preview']}")
    except Exception as e:
        print(f"Failed: Validation error: {e}")

    # 2. Test automatic retrieval
    print("\n2. Testing automatic retrieval...")
    try:
        problem_auto = get_problem_description(test_instance)
        if problem_auto:
            print(f"Success: Automatic retrieval succeeded: {len(problem_auto)} characters")
            print(f"  Preview: {problem_auto[:100]}...")
        else:
            print("Failed: Automatic retrieval failed")
    except Exception as e:
        print(f"Failed: Automatic retrieval exception: {e}")

    # 3. Test various methods
    methods = ['file', 'trajectory', 'json']
    for method in methods:
        print(f"\n3. Testing {method} method...")
        try:
            problem = get_problem_description(test_instance, method=method)
            if problem:
                print(f"Success: {method} method succeeded: {len(problem)} characters")
            else:
                print(f"Warning: {method} method returned no result")
        except Exception as e:
            print(f"Failed: {method} method exception: {e}")

    print("\nUnified problem description interface test completed")

if __name__ == "__main__":
    test_problem_interface()
