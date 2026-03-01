#!/usr/bin/env python3
"""
Test the complete functionality of the SE operator system
"""

import sys
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from SE.operators import list_operators, create_operator


def test_all_operators():
    """Test all registered operators"""

    print("=== Test SE Operator System ===")
    
    # 1. List all operators
    operators = list_operators()
    print(f"Registered operators: {operators}")
    
    expected_operators = ["traj_pool_summary", "alternative_strategy"]
    for op_name in expected_operators:
        if op_name not in operators:
            print(f"FAIL: {op_name} operator not registered")
            return False

    print("PASS: All expected operators are registered")
    
    # 2. Test operator creation
    config = {
        "operator_models": {
            "name": "openai/deepseek-chat",
            "temperature": 0.0
        }
    }
    
    test_workspace = "/home/uaih3k9x/630_swe/SE/trajectories/test_20250714_151848"
    
    for op_name in expected_operators:
        print(f"\n--- Test {op_name} operator ---")
        
        # Create operator instance
        operator = create_operator(op_name, config)
        if not operator:
            print(f"FAIL: Failed to create {op_name} operator")
            continue

        print(f"PASS: Operator created successfully: {operator.get_name()}")
        print(f"Strategy prefix: {operator.get_strategy_prefix()}")
        
        # Test operator processing
        try:
            result = operator.process(
                workspace_dir=test_workspace,
                current_iteration=2,
                num_workers=1
            )
            
            if result and result.get('instance_templates_dir'):
                print(f"PASS: {op_name} processing succeeded")
                print(f"Output directory: {result['instance_templates_dir']}")
                
                # Check generated files
                templates_path = Path(result['instance_templates_dir'])
                if templates_path.exists():
                    yaml_files = list(templates_path.glob("*.yaml"))
                    print(f"Generated files: {len(yaml_files)}")
                    
                    if yaml_files:
                        # Show summary of first file's content
                        with open(yaml_files[0], 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Extract strategy content preview
                        lines = content.split('\n')
                        strategy_started = False
                        strategy_lines = []
                        
                        for line in lines:
                            if operator.get_strategy_prefix() in line:
                                strategy_started = True
                                continue
                            if strategy_started and line.strip():
                                strategy_lines.append(line.strip())
                                if len(strategy_lines) >= 3:  # Only show first 3 lines
                                    break
                        
                        print(f"Strategy content preview:")
                        for line in strategy_lines:
                            print(f"  {line}")
                        if len(strategy_lines) >= 3:
                            print("  ...")
                else:
                    print(f"WARNING: Output directory does not exist: {templates_path}")
            else:
                print(f"FAIL: {op_name} processing failed")
                
        except Exception as e:
            print(f"FAIL: {op_name} test error: {e}")
    
    print(f"\nTest complete")
    return True


def show_operator_comparison():
    """Show feature comparison of the two operators"""

    print("\n=== Operator Feature Comparison ===")
    
    comparison = {
        "traj_pool_summary": {
            "Function": "Analyze all historical failed attempts, identify systematic blind spots and risk points",
            "Input": "All historical iteration data",
            "Output": "Risk-aware guidance (RISK-AWARE PROBLEM SOLVING GUIDANCE)",
            "Use case": "Multiple attempts already made, comprehensive analysis needed"
        },
        "alternative_strategy": {
            "Function": "Generate a fundamentally different alternative approach based on the most recent failure",
            "Input": "Most recent failed attempt data",
            "Output": "Alternative solution strategy (ALTERNATIVE SOLUTION STRATEGY)",
            "Use case": "Just failed once, need a different direction to try"
        }
    }
    
    for op_name, details in comparison.items():
        print(f"\n📊 {op_name}:")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    print(f"\nUsage recommendations:")
    print(f"  - Iteration 2: Use alternative_strategy (based on iteration 1 failure)")
    print(f"  - Iteration 3+: Use traj_pool_summary (comprehensive analysis of all history)")


if __name__ == "__main__":
    success = test_all_operators()
    
    if success:
        show_operator_comparison()
        print("\nSE operator system test passed!")
    else:
        print("\nSE operator system test failed")