#!/usr/bin/env python3

"""
SE Framework - .tra File Generation Tool

Standalone command-line tool for generating .tra files for existing trajectory directories.
Can process a single iteration directory or an entire workspace directory.
"""

import sys
import argparse
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from SE.core.utils.trajectory_processor import TrajectoryProcessor
from SE.core.utils.se_logger import setup_se_logging, get_se_logger


def main():
    """Main function: .tra file generation command-line tool"""
    
    parser = argparse.ArgumentParser(
        description='SE Framework - .tra File Generation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Process entire workspace directory
  python SE/core/utils/generate_tra_files.py SE/trajectories/Demo_Structure

  # Process a specific iteration directory
  python SE/core/utils/generate_tra_files.py SE/trajectories/Demo_Structure/iteration_1 --single-iteration

  # Process only specific iterations
  python SE/core/utils/generate_tra_files.py SE/trajectories/Demo_Structure --iterations 1 2

  # Force regeneration (overwrite existing .tra files)
  python SE/core/utils/generate_tra_files.py SE/trajectories/Demo_Structure --force
        """
    )
    
    parser.add_argument('target_dir',
                       help='Target directory path (workspace directory or iteration directory)')
    parser.add_argument('--single-iteration', action='store_true',
                       help='Specify that target_dir is a single iteration directory (e.g. iteration_1/)')
    parser.add_argument('--iterations', type=int, nargs='+',
                       help='Specify iteration numbers to process (only effective when processing workspace)')
    parser.add_argument('--force', action='store_true',
                       help='Force regeneration, overwrite existing .tra files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Only show files that would be processed, without actually generating')
    parser.add_argument('--extract-problems', action='store_true',
                       help='Also extract problem description files (.problem)')
    parser.add_argument('--problems-only', action='store_true',
                       help='Only extract problem files, do not generate .tra files')
    
    args = parser.parse_args()
    
    # Validate target directory
    target_path = Path(args.target_dir)
    if not target_path.exists():
        print(f"Error: Target directory does not exist: {target_path}")
        return 1
        
    if not target_path.is_dir():
        print(f"Error: Target path is not a directory: {target_path}")
        return 1
    
    # Set up logging system
    if args.single_iteration:
        log_dir = target_path.parent
    else:
        log_dir = target_path
    
    log_file = setup_se_logging(log_dir)
    logger = get_se_logger("generate_tra_files", emoji="🎬")
    
    print("=== SE Framework - .tra File Generation Tool ===")
    print(f"Target directory: {target_path}")
    print(f"Processing mode: {'single iteration' if args.single_iteration else 'workspace'}")
    print(f"Log file: {log_file}")
    
    if args.dry_run:
        print("DRY RUN mode - analyze only, do not generate files")
    elif args.problems_only:
        print("PROBLEMS mode - extract problem files only")
    elif args.extract_problems:
        print("Enhanced mode - generate .tra and .problem files")
    
    try:
        processor = TrajectoryProcessor()
        
        if args.single_iteration:
            # Process single iteration directory
            logger.info(f"Starting to process single iteration directory: {target_path}")
            
            if args.dry_run:
                # Dry run: only show files that would be processed
                _show_traj_files(target_path)
                return 0
            
            if args.problems_only:
                # Extract problem files only
                problem_result = processor.process_problems_in_iteration(target_path)
                if problem_result and problem_result.get('total_problems', 0) > 0:
                    print(f"Problem extraction complete!")
                    print(f"  - Extracted .problem files: {problem_result['total_problems']}")
                    if problem_result['failed_extractions']:
                        print(f"  - Failed extractions: {len(problem_result['failed_extractions'])}")
                else:
                    print("No problem files extracted")
                    return 1
            else:
                # Generate .tra files
                result = processor.process_iteration_directory(target_path)
                
                if result and result.get('total_tra_files', 0) > 0:
                    print(f".tra file processing complete!")
                    print(f"  - Created .tra files: {result['total_tra_files']}")
                    print(f"  - Total tokens: ~{result['total_tokens']}")
                    print(f"  - Processed instances: {len(result['processed_instances'])}")

                    if result['failed_instances']:
                        print(f"  - Failed instances: {len(result['failed_instances'])}")

                    # If needed, also extract problem files
                    if args.extract_problems:
                        print("\nStarting problem file extraction...")
                        problem_result = processor.process_problems_in_iteration(target_path)
                        if problem_result and problem_result.get('total_problems', 0) > 0:
                            print(f"Problem extraction complete!")
                            print(f"  - Extracted .problem files: {problem_result['total_problems']}")
                            if problem_result['failed_extractions']:
                                print(f"  - Failed extractions: {len(problem_result['failed_extractions'])}")
                        else:
                            print("No problem files extracted")

                else:
                    print("No .tra files generated")
                    return 1
                
        else:
            # Process entire workspace directory
            logger.info(f"Starting to process workspace directory: {target_path}")
            
            if args.dry_run:
                # Dry run: show all iterations and files that would be processed
                _show_workspace_overview(target_path, args.iterations)
                return 0
            
            result = processor.process_workspace_directory(target_path, args.iterations)
            
            if result and result.get('total_tra_files', 0) > 0:
                print(f"Processing complete!")
                print(f"  - Processed iterations: {len(result['iterations_processed'])}")
                print(f"  - Created .tra files: {result['total_tra_files']}")
                print(f"  - Total tokens: ~{result['total_tokens']}")

                if result['processing_errors']:
                    print(f"  - Processing errors: {len(result['processing_errors'])}")
                    for error in result['processing_errors']:
                        print(f"    * iteration_{error['iteration_number']}: {error['error']}")
            else:
                print("No .tra files generated")
                return 1
        
        logger.info(".tra file generation complete")
        return 0
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _show_traj_files(iteration_dir: Path):
    """Show .traj files in iteration directory (dry run mode)"""
    print(f"\n.traj files found in {iteration_dir}:")
    
    instance_count = 0
    traj_count = 0
    
    for instance_dir in iteration_dir.iterdir():
        if not instance_dir.is_dir() or instance_dir.name.startswith('.'):
            continue
            
        traj_files = list(instance_dir.glob("*.traj"))
        if traj_files:
            instance_count += 1
            print(f"  📁 {instance_dir.name}/")
            for traj_file in traj_files:
                tra_file = instance_dir / (traj_file.stem + '.tra')
                exists = "✅" if tra_file.exists() else "➕"
                print(f"    {exists} {traj_file.name} -> {tra_file.name}")
                traj_count += 1
    
    if traj_count == 0:
        print("    (No .traj files found)")
    else:
        print(f"\nStats: {instance_count} instances, {traj_count} .traj files")


def _show_workspace_overview(workspace_dir: Path, target_iterations=None):
    """Show workspace directory overview (dry run mode)"""
    print(f"\nWorkspace directory overview: {workspace_dir}")
    
    import re
    iteration_pattern = re.compile(r'^iteration_(\d+)$')
    iterations = []
    
    for item in workspace_dir.iterdir():
        if item.is_dir():
            match = iteration_pattern.match(item.name)
            if match:
                iteration_num = int(match.group(1))
                if target_iterations is None or iteration_num in target_iterations:
                    iterations.append((iteration_num, item))
    
    iterations.sort(key=lambda x: x[0])
    
    if not iterations:
        print("    (No iteration directories found)")
        return
    
    total_instances = 0
    total_traj_files = 0
    
    for iteration_num, iteration_dir in iterations:
        print(f"\n  📂 iteration_{iteration_num}/")
        
        instance_count = 0
        traj_count = 0
        
        for instance_dir in iteration_dir.iterdir():
            if not instance_dir.is_dir() or instance_dir.name.startswith('.'):
                continue
                
            traj_files = list(instance_dir.glob("*.traj"))
            if traj_files:
                instance_count += 1
                traj_count += len(traj_files)
        
        print(f"    {instance_count} instances, {traj_count} .traj files")
        total_instances += instance_count
        total_traj_files += traj_count
    
    print(f"\nTotal: {len(iterations)} iterations, {total_instances} instances, {total_traj_files} .traj files")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)