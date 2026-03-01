#!/usr/bin/env python3
"""
SE Framework Multi-Iteration Execution Script (Enhanced Version)
Supports strategy-driven multi-iteration SWE-agent execution

Features:
- Comprehensive configuration validation and error handling
- Iteration-level recovery mechanism
- User-friendly error messages and progress tracking
- Automatic cleanup and reset functionality
"""

import sys
import json
import yaml
import subprocess
import tempfile
import os
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Add SE directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Version information
VERSION = "2.0.0"
DESCRIPTION = "SE Framework Enhanced Runner"

# Import SE logging system and trajectory processor
from core.utils.se_logger import setup_se_logging, get_se_logger
from core.utils.trajectory_processor import TrajectoryProcessor
from core.utils.traj_pool_manager import TrajPoolManager
from core.utils.traj_extractor import TrajExtractor

# Import operator system
from operators import create_operator, list_operators


class SERunException(Exception):
    """SE framework execution exception base class"""
    pass


class ConfigValidationError(SERunException):
    """Configuration validation error"""
    pass


class IterationRecoveryError(SERunException):
    """Iteration recovery error"""
    pass


def validate_config(config_path: str) -> Dict[str, Any]:
    """
    Validate configuration file validity

    Args:
        config_path: Configuration file path

    Returns:
        Validated configuration dictionary

    Raises:
        ConfigValidationError: Configuration validation failed
    """
    config_path = Path(config_path)

    # Check if configuration file exists
    if not config_path.exists():
        raise ConfigValidationError(f"Configuration file does not exist: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Configuration file format error: {e}")
    except Exception as e:
        raise ConfigValidationError(f"Failed to read configuration file: {e}")

    # Validate required fields
    required_fields = ['base_config', 'model', 'instances', 'output_dir', 'strategy']
    for field in required_fields:
        if field not in config:
            raise ConfigValidationError(f"Configuration file missing required field: {field}")

    # Validate model configuration
    if 'name' not in config['model']:
        raise ConfigValidationError("Model configuration missing 'name' field")

    # Validate instances configuration
    instances = config['instances']
    if 'json_file' not in instances:
        raise ConfigValidationError("Instances configuration missing 'json_file' field")

    # Check if instance file exists (supports relative paths)
    instances_path = Path(instances['json_file'])
    if not instances_path.is_absolute():
        # Relative to project root directory (630_swe)
        project_root = Path(__file__).parent.parent
        instances_path = project_root / instances_path

    if not instances_path.exists():
        raise ConfigValidationError(f"Instance file does not exist: {instances_path}")

    # Validate instance file contents
    try:
        with open(instances_path, 'r', encoding='utf-8') as f:
            instances_data = json.load(f)

        key = instances.get('key', 'instances')
        if key not in instances_data:
            raise ConfigValidationError(f"Key not found in instance file: {key}")

        instance_list = instances_data[key]
        if not isinstance(instance_list, list) or len(instance_list) == 0:
            raise ConfigValidationError(f"Instance list is empty or has incorrect format")

    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Instance file JSON format error: {e}")
    except Exception as e:
        raise ConfigValidationError(f"Failed to validate instance file: {e}")

    # Validate base configuration file (supports relative paths)
    base_config_path = Path(config['base_config'])
    if not base_config_path.is_absolute():
        # Relative to project root directory (630_swe)
        project_root = Path(__file__).parent.parent
        base_config_path = project_root / base_config_path

    if not base_config_path.exists():
        raise ConfigValidationError(f"Base configuration file does not exist: {base_config_path}")

    # Validate strategy configuration
    strategy = config['strategy']
    if 'iterations' not in strategy:
        raise ConfigValidationError("Strategy configuration missing 'iterations' field")

    iterations = strategy['iterations']
    if not isinstance(iterations, list) or len(iterations) == 0:
        raise ConfigValidationError("Iterations configuration is empty or has incorrect format")

    # Validate each iteration configuration (supports relative paths)
    for i, iteration in enumerate(iterations, 1):
        if 'base_config' not in iteration:
            raise ConfigValidationError(f"Iteration {i} missing 'base_config' field")

        iter_base_config = Path(iteration['base_config'])
        if not iter_base_config.is_absolute():
            # Relative to project root directory (630_swe)
            project_root = Path(__file__).parent.parent
            iter_base_config = project_root / iter_base_config

        if not iter_base_config.exists():
            raise ConfigValidationError(f"Iteration {i} base_config does not exist: {iter_base_config}")

    print(f"Configuration validation passed: {len(iterations)} iterations, {len(instance_list)} instances")
    return config


def check_existing_workspace(output_dir: str) -> Tuple[bool, List[int]]:
    """
    Check if workspace already exists; if so, return the list of completed iterations

    Args:
        output_dir: Output directory

    Returns:
        (workspace_exists, completed_iterations)
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return False, []

    completed_iterations = []

    # Check each iteration directory
    for item in output_path.iterdir():
        if item.is_dir() and item.name.startswith('iteration_'):
            try:
                iter_num = int(item.name.split('_')[1])

                # Check if this iteration is complete
                # Determined by checking for preds.json or run_batch_exit_statuses.yaml
                if (item / 'preds.json').exists() or (item / 'run_batch_exit_statuses.yaml').exists():
                    completed_iterations.append(iter_num)
            except (ValueError, IndexError):
                continue

    completed_iterations.sort()
    return len(completed_iterations) > 0, completed_iterations


def cleanup_incomplete_iteration(output_dir: str, iteration_num: int) -> None:
    """
    Clean up incomplete iteration directory

    Args:
        output_dir: Output directory
        iteration_num: Iteration number
    """
    iteration_dir = Path(output_dir) / f"iteration_{iteration_num}"
    if iteration_dir.exists():
        print(f"Cleaning up incomplete iteration directory: {iteration_dir}")
        shutil.rmtree(iteration_dir)


def safe_create_directory(dir_path: str) -> None:
    """
    Safely create directory with error handling

    Args:
        dir_path: Directory path
    """
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise SERunException(f"No permission to create directory: {dir_path}")
    except Exception as e:
        raise SERunException(f"Failed to create directory: {dir_path}, error: {e}")


def call_operator(operator_name, workspace_dir, current_iteration, se_config, logger):
    """
    Call the specified operator for processing

    Args:
        operator_name: Operator name
        workspace_dir: Workspace root directory (without iteration number)
        current_iteration: Current iteration number
        se_config: SE configuration dictionary
        logger: Logger instance

    Returns:
        Parameter dictionary returned by the operator (e.g., {'instance_templates_dir': 'path'}) or None on failure
    """
    try:
        logger.info(f"Starting operator call: {operator_name}")

        # Dynamically create operator instance
        operator = create_operator(operator_name, se_config)
        if not operator:
            logger.error(f"Unable to create operator instance: {operator_name}")
            return None

        logger.info(f"Successfully created operator instance: {operator.__class__.__name__}")

        # Call operator.process() method
        result = operator.process(
            workspace_dir=workspace_dir,
            current_iteration=current_iteration,
            num_workers=se_config.get('num_workers', 1)
        )

        if result:
            logger.info(f"Operator {operator_name} executed successfully, returned: {list(result.keys())}")
            return result
        else:
            logger.warning(f"Operator {operator_name} executed successfully but returned empty result")
            return None

    except Exception as e:
        logger.error(f"Operator {operator_name} execution failed: {e}", exc_info=True)
        return None


def create_temp_config(iteration_params, base_config_path):
    """
    Create temporary configuration file for a single iteration

    Args:
        iteration_params: Iteration parameter dictionary
        base_config_path: Base configuration file path

    Returns:
        Temporary configuration file path
    """
    # Create configuration in test_claude.yaml-like format
    # So that swe_iterator.py will correctly merge base_config
    temp_config = {
        'base_config': base_config_path,
        'model': iteration_params['model'],
        'instances': iteration_params['instances'],
        'output_dir': iteration_params['output_dir'],
        'suffix': 'iteration_run',
        'num_workers': iteration_params.get('num_workers', 1)  # Use passed num_workers, default to 1
    }

    # Handle extra parameters returned by operator
    # Operator may return instance_templates_dir or enhance_history_filter_json, etc.
    operator_params = iteration_params.get('operator_params', {})
    if operator_params:
        # Add operator-returned parameters to temporary config
        temp_config.update(operator_params)
        print(f"Operator parameters: {list(operator_params.keys())}")

    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.yaml', prefix='se_iteration_')
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
            yaml.dump(temp_config, temp_file, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        # If fdopen succeeded, no need to manually close temp_fd since the with statement handles it
        # If fdopen failed, need to manually close
        try:
            os.close(temp_fd)
        except:
            pass
        # Delete the possibly created temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
        raise e

    return temp_path


def call_swe_iterator(iteration_params, logger, dry_run=False):
    """
    Call swe_iterator.py to execute a single iteration

    Args:
        iteration_params: Iteration parameter dictionary
        logger: Logger instance
        dry_run: Whether in demo mode

    Returns:
        Execution result
    """
    base_config_path = iteration_params['base_config']

    try:
        # Create temporary configuration file
        logger.debug(f"Creating temporary configuration file based on: {base_config_path}")
        temp_config_path = create_temp_config(iteration_params, base_config_path)

        logger.info(f"Temporary configuration file: {temp_config_path}")

        # Print actual configuration parameters for confirmation (shown regardless of demo mode)
        print("Actual execution configuration:")
        try:
            with open(temp_config_path, 'r', encoding='utf-8') as f:
                temp_config_content = yaml.safe_load(f)

            # Display key parameters
            print(f"  - base_config: {temp_config_content.get('base_config', 'N/A')}")
            print(f"  - model.name: {temp_config_content.get('model', {}).get('name', 'N/A')}")
            print(f"  - instances.json_file: {temp_config_content.get('instances', {}).get('json_file', 'N/A')}")
            print(f"  - output_dir: {temp_config_content.get('output_dir', 'N/A')}")
            print(f"  - num_workers: {temp_config_content.get('num_workers', 'N/A')}")
            print(f"  - suffix: {temp_config_content.get('suffix', 'N/A')}")

            logger.debug(f"Temporary configuration content: {json.dumps(temp_config_content, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"  Warning: Unable to read configuration file: {e}")

        if dry_run:
            logger.warning("Demo mode: skipping actual execution")
            return {"status": "skipped", "reason": "dry_run"}

        # Call swe_iterator.py
        logger.info("Starting SWE-agent iteration execution")

        # Dynamically determine SE framework root directory and project root directory
        se_root = Path(__file__).parent  # SE directory
        project_root = se_root.parent    # 630_swe directory
        swe_iterator_path = se_root / "core" / "swe_iterator.py"

        print(f"Executing command: python {swe_iterator_path} {temp_config_path}")
        print(f"Working directory: {project_root}")
        print("=" * 60)

        cmd = ["python", str(swe_iterator_path), temp_config_path]

        # Do not use capture_output, let SWE-agent output display directly
        result = subprocess.run(
            cmd,
            cwd=str(project_root),  # Use dynamically determined project root directory
            text=True
        )

        print("=" * 60)
        if result.returncode == 0:
            logger.info("Iteration execution succeeded")
            print("Iteration execution succeeded")
            return {"status": "success"}
        else:
            logger.error(f"Iteration execution failed, return code: {result.returncode}")
            print(f"Iteration execution failed, return code: {result.returncode}")
            return {"status": "failed", "returncode": result.returncode}

    except Exception as e:
        logger.error(f"Error calling swe_iterator: {e}", exc_info=True)
        return {"status": "error", "exception": str(e)}
    finally:
        # Clean up temporary files
        try:
            if 'temp_config_path' in locals():
                os.unlink(temp_config_path)
                logger.debug(f"Cleaned up temporary file: {temp_config_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file: {e}")


def main():
    """Main function: strategy-driven multi-iteration execution (enhanced version)"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description=f'{DESCRIPTION} v{VERSION}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s --config SE/configs/se_configs/test_claude.yaml
  %(prog)s --config config.yaml --mode demo
  %(prog)s --config config.yaml --resume
  %(prog)s --config config.yaml --clean-restart
        """
    )
    parser.add_argument('--config', default="SE/configs/se_configs/test_deepseek_se.yaml",
                       help='SE configuration file path')
    parser.add_argument('--mode', choices=['demo', 'execute'], default='execute',
                       help='Run mode: demo=demo mode, execute=direct execution')
    parser.add_argument('--resume', action='store_true',
                       help='Resume mode: continue execution from last interruption point')
    parser.add_argument('--clean-restart', action='store_true',
                       help='Clean restart: delete existing workspace and start over')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate configuration file, do not execute')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    args = parser.parse_args()

    # Check argument conflicts
    if args.resume and args.clean_restart:
        print("Error: --resume and --clean-restart cannot be used together")
        sys.exit(1)

    print(f"=== {DESCRIPTION} v{VERSION} ===")
    print(f"Configuration file: {args.config}")
    print(f"Run mode: {args.mode}")
    if args.resume:
        print("Resume mode: continuing from last interruption point")
    if args.clean_restart:
        print("Clean restart: deleting existing workspace")

    try:
        # Validate configuration file
        print("\nValidating configuration file...")
        config = validate_config(args.config)

        if args.validate_only:
            print("Configuration validation passed, exiting")
            return

        # Generate timestamp and replace output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = config['output_dir'].replace("{timestamp}", timestamp)

        # Check workspace state
        workspace_exists, completed_iterations = check_existing_workspace(output_dir)
        start_iteration = 1

        if workspace_exists:
            print(f"\nFound existing workspace: {output_dir}")
            print(f"Completed iterations: {completed_iterations}")

            if args.clean_restart:
                print("Clean restart mode: deleting existing workspace")
                shutil.rmtree(output_dir)
                safe_create_directory(output_dir)
            elif args.resume:
                if completed_iterations:
                    start_iteration = max(completed_iterations) + 1
                    print(f"Resume mode: starting from iteration {start_iteration}")

                    # Clean up possibly incomplete next iteration
                    cleanup_incomplete_iteration(output_dir, start_iteration)
                else:
                    print("Resume mode: no completed iterations found, starting from iteration 1")
            else:
                print("Warning: workspace already exists, please choose:")
                print("  --resume : continue from interruption point")
                print("  --clean-restart : clean restart")
                print("  or manually delete the workspace directory")
                sys.exit(1)
        else:
            # Create new workspace
            safe_create_directory(output_dir)

        # Set up logging system
        log_file = setup_se_logging(output_dir)
        print(f"Log file: {log_file}")

        # Get logger instance
        logger = get_se_logger("basic_run", emoji="")
        logger.info("SE framework multi-iteration execution started")
        logger.debug(f"Using configuration file: {args.config}")
        logger.info(f"Generated timestamp: {timestamp}")
        logger.info(f"Actual output directory: {output_dir}")

        # Initialize trajectory pool manager
        traj_pool_path = os.path.join(output_dir, "traj.pool")

        # Create LLM client for trajectory summarization
        llm_client = None
        try:
            from core.utils.llm_client import LLMClient
            # Use operator_models config; if not available, use main model config
            llm_client = LLMClient.from_se_config(config, use_operator_model=True)
            logger.info(f"LLM client initialized successfully: {llm_client.config['name']}")
        except Exception as e:
            logger.warning(f"LLM client initialization failed, will use fallback summarization: {e}")

        traj_pool_manager = TrajPoolManager(traj_pool_path, llm_client)
        traj_pool_manager.initialize_pool()
        logger.info(f"Trajectory pool initialized: {traj_pool_path}")
        print(f"Trajectory pool: {traj_pool_path}")

        print(f"\nConfiguration overview:")
        print(f"  Base config: {config['base_config']}")
        print(f"  Model: {config['model']['name']}")
        print(f"  Instance file: {config['instances']['json_file']}")
        print(f"  Output directory: {output_dir}")
        print(f"  Number of iterations: {len(config['strategy']['iterations'])}")

        # Execute iterations in strategy (supports resume)
        iterations = config['strategy']['iterations']
        total_iterations = len(iterations)

        print(f"\nStarting execution: {total_iterations} total iterations, starting from iteration {start_iteration}")

        for i in range(start_iteration, total_iterations + 1):
            iteration = iterations[i - 1]  # Array index starts from 0
            logger.info(f"Starting iteration {i}")
            print(f"\n=== Iteration {i} invocation ===")

            # Build iteration parameters
            # Note: Only the following three parameters change between iterations:
            # 1. base_config - Each iteration uses a different SWE-agent base configuration
            # 2. operator - Each iteration may use a different operator strategy
            # 3. output_dir - Each iteration has an independent output directory
            # Other parameters (model, instances, num_workers) remain consistent across all iterations
            iteration_output_dir = f"{output_dir}/iteration_{i}"
            iteration_params = {
                "base_config": iteration['base_config'],      # Variable: SWE base config
                "operator": iteration.get('operator'),       # Variable: operator strategy
                "model": config['model'],                     # Fixed: model config
                "instances": config['instances'],             # Fixed: instance config
                "output_dir": iteration_output_dir,           # Variable: iteration output directory
                "num_workers": config.get('num_workers', 1)  # Fixed: concurrency config
            }

            # Handle extra parameters returned by operator
            operator_name = iteration.get('operator')
            if operator_name:
                print(f"Calling operator: {operator_name}")
                logger.info(f"Executing operator: {operator_name}")

                # Call operator processing (pass workspace_dir instead of iteration_output_dir)
                operator_result = call_operator(operator_name, output_dir, i, config, logger)
                if operator_result:
                    iteration_params['operator_params'] = operator_result
                    print(f"Operator {operator_name} executed successfully")
                    print(f"Generated parameters: {list(operator_result.keys())}")
                else:
                    print(f"Warning: Operator {operator_name} execution failed, continuing without enhancement")
                    logger.warning(f"Operator {operator_name} execution failed, continuing without enhancement")
            else:
                print(f"No operator processing")
                logger.debug(f"Iteration {i} has no operator processing")

            logger.debug(f"Iteration {i} parameters: {json.dumps(iteration_params, ensure_ascii=False)}")
            print(f"Using config: {iteration['base_config']}")
            print(f"Operator: {iteration.get('operator', 'None')}")
            print(f"Output directory: {iteration_output_dir}")

            # Execute based on mode
            if args.mode == 'execute':
                logger.info(f"Direct execution mode: iteration {i}")
                result = call_swe_iterator(iteration_params, logger, dry_run=False)
                print(f"Execution result: {result['status']}")

                # If iteration succeeded, generate .tra files
                if result['status'] == 'success':
                    logger.info(f"Starting .tra file generation for iteration {i}")
                    try:
                        processor = TrajectoryProcessor()
                        iteration_dir = Path(iteration_output_dir)

                        # Process current iteration directory
                        tra_stats = processor.process_iteration_directory(iteration_dir)

                        if tra_stats and tra_stats.get('total_tra_files', 0) > 0:
                            logger.info(f"Iteration {i} .tra file generation complete: "
                                      f"{tra_stats['total_tra_files']} files, "
                                      f"~{tra_stats['total_tokens']} tokens")
                            print(f"Generated {tra_stats['total_tra_files']} .tra files")

                            # Update trajectory pool
                            logger.info(f"Starting trajectory pool update: iteration {i}")
                            try:
                                # Extract instance info and .tra/.patch file contents from actual data
                                extractor = TrajExtractor()
                                instance_data_list = extractor.extract_instance_data(iteration_dir)

                                if instance_data_list:
                                    for instance_name, problem_description, trajectory_content, patch_content in instance_data_list:
                                        traj_pool_manager.add_iteration_summary(
                                            instance_name=instance_name,
                                            iteration=i,
                                            trajectory_content=trajectory_content,
                                            patch_content=patch_content,
                                            problem_description=problem_description
                                        )

                                    logger.info(f"Successfully extracted and processed {len(instance_data_list)} instances")
                                else:
                                    logger.warning(f"Iteration {i} found no valid instance data")
                                    print("Warning: no valid instance data found")

                                # Display trajectory pool statistics
                                pool_stats = traj_pool_manager.get_pool_stats()
                                logger.info(f"Trajectory pool update complete: {pool_stats['total_instances']} instances, "
                                          f"{pool_stats['total_iterations']} total iterations")
                                print(f"Trajectory pool update: {pool_stats['total_instances']} instances, "
                                      f"{pool_stats['total_iterations']} total iterations")

                            except Exception as pool_error:
                                logger.error(f"Iteration {i} trajectory pool update failed: {pool_error}")
                                print(f"Warning: trajectory pool update failed: {pool_error}")
                                # Do not interrupt the entire flow due to trajectory pool update failure
                        else:
                            logger.warning(f"Iteration {i} did not generate .tra files")
                            print("Warning: no .tra files generated (possibly no valid trajectories)")

                    except Exception as tra_error:
                        logger.error(f"Iteration {i} .tra file generation failed: {tra_error}")
                        print(f"Warning: .tra file generation failed: {tra_error}")
                        # Do not interrupt the entire flow due to .tra file generation failure

                if result['status'] == 'failed':
                    logger.error(f"Iteration {i} execution failed, stopping subsequent iterations")
                    break
            else:  # demo mode
                logger.info(f"Demo mode: iteration {i}")
                result = call_swe_iterator(iteration_params, logger, dry_run=True)
                print(f"Demo result: {result['status']}")
                print("Demo mode: skipping .tra file generation")

        logger.info("All iterations preparation complete")

        # Display final trajectory pool statistics
        try:
            final_pool_stats = traj_pool_manager.get_pool_stats()
            logger.info(f"Final trajectory pool statistics: {final_pool_stats}")
        except Exception as e:
            logger.warning(f"Failed to get trajectory pool statistics: {e}")
            final_pool_stats = {"total_instances": 0, "total_iterations": 0}

        print(f"\nExecution summary:")
        print(f"  Parsed {len(iterations)} iteration configurations")
        print(f"  Timestamp: {timestamp}")
        print(f"  Log file: {log_file}")
        print(f"  Trajectory pool: {final_pool_stats['total_instances']} instances, "
              f"{final_pool_stats['total_iterations']} total iterations")
        print(f"  Trajectory pool file: {traj_pool_path}")

        logger.info("SE framework multi-iteration execution complete")

    except ConfigValidationError as e:
        print(f"Configuration validation failed: {e}")
        print("\nSuggestions:")
        print("  1. Check configuration file path and format")
        print("  2. Ensure all required fields are filled in")
        print("  3. Verify that file paths are correct")
        sys.exit(1)

    except SERunException as e:
        print(f"SE framework execution error: {e}")
        if 'logger' in locals():
            logger.error(f"SE framework execution error: {e}", exc_info=True)
        sys.exit(1)

    except KeyboardInterrupt:
        print(f"\nUser interrupted execution")
        if 'logger' in locals():
            logger.warning("User interrupted execution")
        print(f"Tip: use --resume to continue execution from the interruption point")
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}")
        if 'logger' in locals():
            logger.error(f"Unexpected error: {e}", exc_info=True)
        print("\nSuggestions:")
        print("  1. Check system environment and dependencies")
        print("  2. Review the detailed log file")
        print("  3. Ensure sufficient disk space and permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()
