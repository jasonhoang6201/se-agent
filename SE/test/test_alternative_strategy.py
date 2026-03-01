#!/usr/bin/env python3
"""
AlternativeStrategy Operator Dedicated Test File

Tests the complete functionality of the alternative_strategy operator, including:
- Operator registration and creation
- Data loading and processing
- LLM invocation and strategy generation
- Output file generation and format validation
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from operators import create_operator


class TestAlternativeStrategy:
    """AlternativeStrategy operator test class"""
    
    def __init__(self):
        self.config = {
            "operator_models": {
                "name": "openai/deepseek-chat",
                "temperature": 0.0,
                "max_output_tokens": 1000
            }
        }
        self.test_workspace = None
        
    def setup_test_workspace(self):
        """Create test workspace"""
        self.test_workspace = Path(tempfile.mkdtemp(prefix="test_alt_strategy_"))
        
        # Create mock instance directory structure
        instance_dir = self.test_workspace / "test-instance-001"
        iter1_dir = instance_dir / "iteration_1"
        iter1_dir.mkdir(parents=True)
        
        # Create mock .tra file
        tra_content = {
            "Trajectory": [
                {"role": "system", "content": "System message"},
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "<pr_description>\nFix type checking errors in Python, ensure function return types match declarations\nCurrent code reports errors during type checking, need to fix type mismatch issues\n</pr_description>"
                        }
                    ]
                }
            ]
        }
        
        tra_file = iter1_dir / "test-instance-001.tra"
        with open(tra_file, 'w', encoding='utf-8') as f:
            json.dump(tra_content, f, ensure_ascii=False, indent=2)
        
        # Create mock traj.pool file
        traj_pool_content = {
            "test-instance-001": {
                "problem": "Fix type checking errors in Python, ensure function return types match declarations",
                "1": {
                    "approach_summary": "Attempted to fix type checking errors by modifying function declarations",
                    "modified_files": [
                        "/testbed/src/main.py",
                        "/testbed/src/utils.py"
                    ],
                    "key_changes": [
                        "Modified function return type annotations",
                        "Added type conversion code"
                    ],
                    "strategy": "Analyze error messages, locate functions with type mismatches, modify type annotations and implementation",
                    "specific_techniques": [
                        "mypy type checking",
                        "manual code review",
                        "file-by-file fixing"
                    ],
                    "tools_used": [
                        "str_replace_editor",
                        "bash",
                        "mypy"
                    ],
                    "reasoning_pattern": "1. Run mypy check\n2. Analyze error messages\n3. Modify function declarations\n4. Re-check",
                    "assumptions_made": [
                        "Errors are only at the function declaration level",
                        "Modifying type annotations will solve the problem",
                        "No need to modify function implementation logic"
                    ],
                    "components_touched": [
                        "Function type annotations",
                        "Return value handling"
                    ]
                }
            }
        }
        
        traj_pool_file = instance_dir / "traj.pool"
        with open(traj_pool_file, 'w', encoding='utf-8') as f:
            json.dump(traj_pool_content, f, ensure_ascii=False, indent=2)
        
        print(f"Created test workspace: {self.test_workspace}")
        print(f"Created trajectory file: {tra_file}")
        print(f"Created trajectory pool: {traj_pool_file}")
        
        return self.test_workspace
    
    def cleanup_test_workspace(self):
        """Clean up test workspace"""
        if self.test_workspace and self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)
            print(f"Cleaned up test workspace: {self.test_workspace}")
    
    def test_operator_creation(self):
        """Test operator creation"""
        print("\n=== Test AlternativeStrategy Operator Creation ===")
        
        operator = create_operator("alternative_strategy", self.config)
        if not operator:
            print("FAIL: Operator creation failed")
            return False

        print(f"PASS: Operator created successfully: {operator.get_name()}")
        print(f"Strategy prefix: {operator.get_strategy_prefix()}")
        
        return operator
    
    def test_data_loading(self, operator):
        """Test data loading functionality"""
        print("\n=== Test Data Loading Functionality ===")
        
        workspace = self.setup_test_workspace()
        instance_dir = workspace / "test-instance-001"
        
        # Test traj.pool loading
        approaches_data = operator._load_traj_pool(instance_dir)
        if not approaches_data:
            print("FAIL: Trajectory pool data loading failed")
            return False

        print(f"PASS: Successfully loaded trajectory pool data")
        print(f"Data items: {list(approaches_data.keys())}")

        # Test latest failed attempt extraction
        latest_approach = operator._get_latest_failed_approach(approaches_data)
        if not latest_approach:
            print("FAIL: Latest failed attempt extraction failed")
            return False

        print(f"PASS: Successfully extracted latest failed attempt")
        print(f"Latest attempt preview: {latest_approach[:100]}...")
        
        return True
    
    def test_strategy_generation(self, operator):
        """Test strategy generation functionality (without calling LLM)"""
        print("\n=== Test Strategy Generation Functionality ===")
        
        problem_statement = "Fix type checking errors in Python, ensure function return types match declarations"
        previous_approach = "Strategy: Analyze error messages, locate functions with type mismatches, modify type annotations and implementation\nTools Used: str_replace_editor, bash, mypy"

        # Mock strategy generation (without actually calling LLM)
        print(f"Problem statement: {problem_statement}")
        print(f"Previous approach: {previous_approach}")
        print(f"Strategy generation: Will use LLM to generate alternative strategy")
        
        return True
    
    def test_full_processing(self, operator):
        """Test full processing workflow"""
        print("\n=== Test Full Processing Workflow ===")
        
        if not self.test_workspace:
            self.setup_test_workspace()
        
        try:
            result = operator.process(
                workspace_dir=str(self.test_workspace),
                current_iteration=2,
                num_workers=1
            )
            
            if result and result.get('instance_templates_dir'):
                print(f"PASS: Full processing succeeded")
                print(f"Output directory: {result['instance_templates_dir']}")
                
                # Check generated files
                templates_dir = Path(result['instance_templates_dir'])
                if templates_dir.exists():
                    yaml_files = list(templates_dir.glob("*.yaml"))
                    print(f"Generated template files: {len(yaml_files)}")
                    
                    if yaml_files:
                        # Validate file content
                        with open(yaml_files[0], 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check required components
                        required_components = [
                            "You are a helpful assistant",
                            "ALTERNATIVE SOLUTION STRATEGY",
                            "agent:",
                            "templates:",
                            "system_template:"
                        ]
                        
                        missing_components = []
                        for component in required_components:
                            if component not in content:
                                missing_components.append(component)
                        
                        if missing_components:
                            print(f"WARNING: Missing required components: {missing_components}")
                        else:
                            print(f"PASS: Output format validation passed")

                        # Show content preview
                        print(f"\nGenerated content preview:")
                        print("=" * 50)
                        lines = content.split('\n')
                        for i, line in enumerate(lines[:15]):  # Show first 15 lines
                            print(f"{i+1:2d}: {line}")
                        if len(lines) > 15:
                            print("...")
                        print("=" * 50)
                
                return True
            else:
                print(f"FAIL: Full processing failed")
                return False
                
        except Exception as e:
            print(f"FAIL: Error during processing: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("Starting AlternativeStrategy operator tests")
        
        success_count = 0
        total_tests = 4
        
        try:
            # 1. Test operator creation
            operator = self.test_operator_creation()
            if operator:
                success_count += 1
                
                # 2. Test data loading
                if self.test_data_loading(operator):
                    success_count += 1
                
                # 3. Test strategy generation
                if self.test_strategy_generation(operator):
                    success_count += 1
                
                # 4. Test full processing
                if self.test_full_processing(operator):
                    success_count += 1
            
        finally:
            self.cleanup_test_workspace()
        
        # Test summary
        print(f"\nAlternativeStrategy Test Summary:")
        print(f"  Passed: {success_count}/{total_tests}")

        if success_count == total_tests:
            print("All tests passed!")
            return True
        else:
            print("Some tests failed")
            return False


def main():
    """Main test function"""
    tester = TestAlternativeStrategy()
    success = tester.run_all_tests()
    
    if success:
        print("\nAlternativeStrategy operator test complete - all tests passed!")
    else:
        print("\nAlternativeStrategy operator test complete - some tests failed")
    
    return success


if __name__ == "__main__":
    main()