#!/usr/bin/env python3
"""
SE Framework Test Suite - Unified Data Management System Tests

Runs all data management related tests, validating the core data access
functionality of the SE framework.
Supports individual or batch test modes.
"""

import sys
import argparse
import subprocess
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SETestSuite:
    """SE Framework Test Suite"""

    def __init__(self):
        self.test_results = {}
        self.test_dir = Path(__file__).parent

    def run_unified_data_interface_test(self):
        """Run unified data interface test"""
        print("Starting unified data interface test")
        print("=" * 60)

        test_script = self.test_dir / "test_unified_data_interface.py"

        try:
            result = subprocess.run(
                [sys.executable, str(test_script)],
                capture_output=True,
                text=True,
                timeout=120
            )

            success = result.returncode == 0

            # Display test output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            self.test_results['unified_data_interface'] = {
                'success': success,
                'description': 'Unified data interface - InstanceDataManager, four core formats, trajectory pool'
            }

            return success

        except subprocess.TimeoutExpired:
            print("Failed: Test timed out")
            self.test_results['unified_data_interface'] = {
                'success': False,
                'description': 'Unified data interface - test timed out'
            }
            return False
        except Exception as e:
            print(f"Failed: Test execution failed: {e}")
            self.test_results['unified_data_interface'] = {
                'success': False,
                'description': 'Unified data interface - execution failed'
            }
            return False

    def run_operator_data_access_test(self):
        """Run operator data access test"""
        print("\nStarting operator data access test")
        print("=" * 60)

        test_script = self.test_dir / "test_operator_data_access.py"

        try:
            result = subprocess.run(
                [sys.executable, str(test_script)],
                capture_output=True,
                text=True,
                timeout=120
            )

            success = result.returncode == 0

            # Display test output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            self.test_results['operator_data_access'] = {
                'success': success,
                'description': 'Operator data access - simulating Crossover, Conclusion, Summary operators'
            }

            return success

        except subprocess.TimeoutExpired:
            print("Failed: Test timed out")
            self.test_results['operator_data_access'] = {
                'success': False,
                'description': 'Operator data access - test timed out'
            }
            return False
        except Exception as e:
            print(f"Failed: Test execution failed: {e}")
            self.test_results['operator_data_access'] = {
                'success': False,
                'description': 'Operator data access - execution failed'
            }
            return False

    def run_data_format_validation_test(self):
        """Run data format validation test"""
        print("\nStarting data format validation test")
        print("=" * 60)

        try:
            from core.utils.instance_data_manager import InstanceDataManager
            from core.utils.traj_pool_manager import TrajPoolManager
            from core.utils.traj_extractor import TrajExtractor

            # Basic import test
            print("Success: Core modules imported successfully")

            # Interface availability test
            manager = InstanceDataManager()
            extractor = TrajExtractor()

            print("Success: Core classes instantiated successfully")

            # Method signature test
            required_methods = [
                'get_instance_data',
                'get_traj_pool_data',
                'get_instance_iteration_summary',
                'validate_instance_completeness'
            ]

            missing_methods = []
            for method in required_methods:
                if not hasattr(manager, method):
                    missing_methods.append(method)

            if missing_methods:
                print(f"Failed: Missing required methods: {missing_methods}")
                success = False
            else:
                print("Success: All required methods exist")
                success = True

            self.test_results['data_format_validation'] = {
                'success': success,
                'description': 'Data format validation - core classes and method availability'
            }

            return success

        except ImportError as e:
            print(f"Failed: Module import failed: {e}")
            self.test_results['data_format_validation'] = {
                'success': False,
                'description': 'Data format validation - module import failed'
            }
            return False
        except Exception as e:
            print(f"Failed: Validation failed: {e}")
            self.test_results['data_format_validation'] = {
                'success': False,
                'description': 'Data format validation - validation failed'
            }
            return False

    def run_legacy_compatibility_test(self):
        """Run legacy compatibility test"""
        print("\nStarting legacy compatibility test")
        print("=" * 60)

        try:
            # Test if legacy test scripts are still available
            old_tests = [
                'test_alternative_strategy.py',
                'test_traj_pool_summary.py'
            ]

            existing_tests = []
            for test_file in old_tests:
                test_path = self.test_dir / test_file
                if test_path.exists():
                    existing_tests.append(test_file)

            print(f"Success: Found legacy test files: {existing_tests}")

            if existing_tests:
                print("Warning: Legacy test files exist, recommend updating to new data access interface")
                success = True  # Exist but need updating
            else:
                print("Success: No legacy test file conflicts")
                success = True

            self.test_results['legacy_compatibility'] = {
                'success': success,
                'description': f'Legacy compatibility - found {len(existing_tests)} old test files'
            }

            return success

        except Exception as e:
            print(f"Failed: Compatibility test failed: {e}")
            self.test_results['legacy_compatibility'] = {
                'success': False,
                'description': 'Legacy compatibility - test failed'
            }
            return False

    def generate_test_report(self):
        """Generate test report"""
        print("\n" + "=" * 80)
        print("SE Framework Data Management System Test Report")
        print("=" * 80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])

        print(f"Overall result: {passed_tests}/{total_tests} passed")
        print()

        # Detailed results
        for test_name, result in self.test_results.items():
            status = "Passed" if result['success'] else "Failed"
            print(f"{status} {test_name}: {result['description']}")

        print()

        # Overall assessment
        if passed_tests == total_tests:
            print("All tests passed! SE framework data management system is fully functional.")
            print("Suggestion: You can start implementing specific operator functionality")
            overall_success = True
        elif passed_tests > total_tests // 2:
            print(f"Most tests passed ({passed_tests}/{total_tests}).")
            print("Suggestion: Fix failed tests before starting operator development")
            overall_success = False
        else:
            print("Most tests failed. SE framework data management system has issues.")
            print("Suggestion: Prioritize fixing the data access interface")
            overall_success = False

        return overall_success

    def run_full_test_suite(self):
        """Run the full test suite"""
        print("Starting SE framework data management system full test")
        print("Test scope: unified data interface, operator data access, format validation, legacy compatibility")
        print()

        # 1. Data format validation test
        self.run_data_format_validation_test()

        # 2. Unified data interface test
        self.run_unified_data_interface_test()

        # 3. Operator data access test
        self.run_operator_data_access_test()

        # 4. Legacy compatibility test
        self.run_legacy_compatibility_test()

        # 5. Generate test report
        overall_success = self.generate_test_report()

        return overall_success


def main():
    """Main function: parse command line arguments and run tests"""

    parser = argparse.ArgumentParser(description='SE Framework Data Management System Test Suite')
    parser.add_argument('--test', choices=['unified_data', 'operator_access', 'format_validation', 'legacy_compat', 'all'],
                       default='all', help='Specify which test to run')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    suite = SETestSuite()

    if args.test == 'all':
        # Run full test suite
        success = suite.run_full_test_suite()
    elif args.test == 'unified_data':
        # Test unified data interface only
        success = suite.run_unified_data_interface_test()
        suite.generate_test_report()
    elif args.test == 'operator_access':
        # Test operator data access only
        success = suite.run_operator_data_access_test()
        suite.generate_test_report()
    elif args.test == 'format_validation':
        # Test data format validation only
        success = suite.run_data_format_validation_test()
        suite.generate_test_report()
    elif args.test == 'legacy_compat':
        # Test legacy compatibility only
        success = suite.run_legacy_compatibility_test()
        suite.generate_test_report()
    else:
        print(f"Failed: Unknown test type: {args.test}")
        success = False

    # Return exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
