#!/usr/bin/env python3
"""
Test script for the traj_pool_summary operator
"""

import sys
import json
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from SE.operators import create_operator, list_operators


def test_traj_pool_summary():
    """Test the traj_pool_summary operator"""

    print("=== Test traj_pool_summary operator ===")

    # 1. Check if the operator is registered successfully
    operators = list_operators()
    print(f"Registered operators: {operators}")

    if "traj_pool_summary" not in operators:
        print("Failed: traj_pool_summary operator not registered")
        return False

    # 2. Create operator instance
    config = {
        "operator_models": {
            "name": "openai/deepseek-chat",
            "temperature": 0.0
        }
    }
    
    operator = create_operator("traj_pool_summary", config)
    if not operator:
        print("Failed: Could not create operator instance")
        return False

    print(f"Success: Operator created: {operator.get_name()}")
    print(f"Strategy prefix: {operator.get_strategy_prefix()}")

    # 3. Test with real traj.pool data
    test_workspace = "/home/uaih3k9x/630_swe/SE/trajectories/test_20250714_153541"
    
    try:
        result = operator.process(
            workspace_dir=test_workspace,
            current_iteration=2,  # Assume processing iteration 2
            num_workers=1
        )
        
        if result:
            print(f"Success: Operator processing completed")
            print(f"Return result: {result}")

            # Check generated template files
            templates_dir = result.get('instance_templates_dir')
            if templates_dir:
                templates_path = Path(templates_dir)
                if templates_path.exists():
                    yaml_files = list(templates_path.glob("*.yaml"))
                    print(f"Generated template files: {len(yaml_files)}")

                    # Display generated content
                    if yaml_files:
                        with open(yaml_files[0], 'r', encoding='utf-8') as f:
                            content = f.read()
                        print(f"\nGenerated template content preview:")
                        print("=" * 50)
                        print(content)
                        print("=" * 50)

            return True
        else:
            print("Failed: Operator processing failed")
            return False

    except Exception as e:
        print(f"Failed: Error during testing: {e}")
        return False


if __name__ == "__main__":
    success = test_traj_pool_summary()
    if success:
        print("\ntraj_pool_summary operator test passed!")
    else:
        print("\ntraj_pool_summary operator test failed")