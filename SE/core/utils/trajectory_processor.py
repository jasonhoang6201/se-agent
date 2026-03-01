#!/usr/bin/env python3

"""
SE Framework Trajectory Processor

Provides trajectory file processing for the SE framework, generating simplified .tra files after each iteration.
Based on converter_old.py logic, adapted to the SE framework directory structure.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
# Lazy import to avoid circular import issues
# from .se_logger import get_se_logger


class TrajectoryProcessor:
    """Trajectory file processor for generating simplified .tra files"""

    def __init__(self):
        """Initialize the trajectory processor"""
        # Lazy import to avoid circular imports
        try:
            from .se_logger import get_se_logger
            self.logger = get_se_logger("trajectory_processor", emoji="🎬")
        except ImportError:
            # If import fails, use standard logging
            import logging
            self.logger = logging.getLogger("trajectory_processor")
            self.logger.setLevel(logging.INFO)
    
    def _count_tokens(self, text: str) -> int:
        """Simple approximate token counting algorithm"""
        if not text or not isinstance(text, str):
            return 0
        # Basic token counting - split by whitespace and common punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return len(tokens)
    
    def _truncate_text(self, text: str, first_percent: float = 0.2, last_percent: float = 0.1) -> str:
        """
        Truncate text content using character percentage constraints

        Args:
            text: Text to truncate
            first_percent: Percentage to keep from the beginning (default 20%)
            last_percent: Percentage to keep from the end (default 10%)

        Returns:
            Truncated text
        """
        if not text or not isinstance(text, str):
            return text
            
        text_length = len(text)
        
        # Only truncate content that is long enough
        if text_length < 300:
            return text
        
        # Calculate head length (20%, constrained to 30-150 characters)
        first_length = int(text_length * first_percent)
        first_length = max(30, min(150, first_length))
        
        # Calculate tail length (10%, constrained to 30-100 characters)
        last_length = int(text_length * last_percent)
        last_length = max(30, min(100, last_length))
        
        # Check if truncation is worthwhile (skip if keeping more than 80%)
        truncated_length = first_length + last_length + len("... [TRUNCATED] ...")
        if truncated_length >= text_length * 0.8:
            return text
            
        # Extract head and tail parts
        first_part = text[:first_length]
        last_part = text[-last_length:]
        
        # Combine with truncation marker
        return f"{first_part}... [TRUNCATED] ...{last_part}"
    
    def _truncate_tool_content(self, content) -> str:
        """Truncate tool output content"""
        if not content:
            return content
            
        # Handle list format: [{"type": "text", "text": "..."}]
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict) and "text" in first_item:
                text_content = first_item["text"]
                if isinstance(text_content, str):
                    return self._truncate_text(text_content)
        
        # Handle string format
        if isinstance(content, str):
            return self._truncate_text(content)
        
        return content
    
    def _create_tra_from_traj(self, traj_file: Path, tra_file: Path) -> Dict[str, int]:
        """
        Create .tra file from .traj file, keeping only history role/content

        Args:
            traj_file: Path to the original trajectory file
            tra_file: Path to the target .tra file

        Returns:
            Processing statistics dictionary
        """
        try:
            with open(traj_file, 'r', encoding='utf-8') as f:
                traj_data = json.load(f)
            
            # Extract and simplify history
            history = traj_data.get('history', [])
            simplified_history = []
            total_tokens = 0
            original_tokens = 0  # Original token count
            
            for item in history:
                if 'role' not in item:
                    continue
                    
                simplified_item = {
                    'role': item['role']
                }
                
                # First count the tokens of the original content
                for field in ['content', 'thought', 'action']:
                    if field in item and item[field]:
                        original_field_str = str(item[field]) if item[field] else ""
                        original_tokens += self._count_tokens(original_field_str)
                
                # Process different fields based on role type
                if item['role'] == 'assistant':
                    # assistant role: extract thought instead of content
                    if 'thought' in item and item['thought']:
                        simplified_item['thought'] = item['thought']
                    
                    # Include action and apply truncation
                    if 'action' in item and item['action']:
                        original_action = item['action']
                        action = original_action
                        
                        # Apply truncation to str_replace_editor or long actions (>350 chars)
                        if isinstance(action, str):
                            if 'str_replace_editor' in action or len(action) > 350:
                                action = self._truncate_text(action)
                        elif isinstance(action, dict):
                            action_str = str(action)
                            if 'str_replace_editor' in action_str or len(action_str) > 350:
                                action = self._truncate_text(action_str)
                        
                        simplified_item['action'] = action
                        
                else:
                    # Non-assistant roles: use content
                    if 'content' in item and item['content']:
                        original_content = item['content']
                        content = original_content
                        
                        # Apply truncation to long observation results from tool role
                        if item['role'] == 'tool':
                            content = self._truncate_tool_content(content)
                        
                        simplified_item['content'] = content
                
                # Only add items with meaningful content (not just role)
                if len(simplified_item) > 1:
                    simplified_history.append(simplified_item)
                    
                    # Count tokens of compressed fields
                    for field in ['content', 'thought', 'action']:
                        if field in simplified_item:
                            field_str = str(simplified_item[field]) if simplified_item[field] else ""
                            total_tokens += self._count_tokens(field_str)
            
            # Create .tra file content
            tra_data = {
                'Trajectory': simplified_history
            }
            
            # Write .tra file
            with open(tra_file, 'w', encoding='utf-8') as f:
                json.dump(tra_data, f, indent=2)
            
            # Calculate saved tokens
            saved_tokens = original_tokens - total_tokens
            compression_ratio = (saved_tokens / original_tokens * 100) if original_tokens > 0 else 0
            
            return {
                'total_tokens': total_tokens,
                'original_tokens': original_tokens,
                'saved_tokens': saved_tokens,
                'compression_ratio': compression_ratio,
                'history_items': len(simplified_history)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create .tra file {traj_file}: {e}")
            return {
                'total_tokens': 0,
                'original_tokens': 0,
                'saved_tokens': 0,
                'compression_ratio': 0,
                'history_items': 0
            }
    
    def process_iteration_directory(self, iteration_dir: Path) -> Dict[str, Any]:
        """
        Process a single iteration directory, generating .tra files for all instances

        Args:
            iteration_dir: Path to the iteration directory (e.g., iteration_1/)

        Returns:
            Processing result statistics
        """
        self.logger.info(f"Starting to process iteration directory: {iteration_dir}")
        
        if not iteration_dir.exists() or not iteration_dir.is_dir():
            self.logger.warning(f"Directory does not exist or is not a directory: {iteration_dir}")
            return {}

        processing_stats = {
            'iteration_dir': str(iteration_dir),
            'processed_instances': [],
            'total_tokens': 0,
            'total_tra_files': 0,
            'failed_instances': []
        }
        
        # Iterate over all instance directories
        for instance_dir in iteration_dir.iterdir():
            if not instance_dir.is_dir() or instance_dir.name.startswith('.'):
                continue

            # Find .traj files
            traj_files = list(instance_dir.glob("*.traj"))
            if not traj_files:
                self.logger.debug(f"Instance {instance_dir.name} has no .traj files")
                continue
            
            instance_stats = {
                'instance_name': instance_dir.name,
                'tra_files_created': [],
                'total_tokens': 0,
                'total_history_items': 0
            }
            
            # Process each .traj file
            for traj_file in traj_files:
                tra_file = instance_dir / (traj_file.stem + '.tra')
                
                # Generate .tra file
                file_stats = self._create_tra_from_traj(traj_file, tra_file)
                
                if file_stats['history_items'] > 0:
                    instance_stats['tra_files_created'].append({
                        'traj_file': traj_file.name,
                        'tra_file': tra_file.name,
                        'tokens': file_stats['total_tokens'],
                        'original_tokens': file_stats['original_tokens'],
                        'saved_tokens': file_stats['saved_tokens'],
                        'compression_ratio': file_stats['compression_ratio'],
                        'history_items': file_stats['history_items']
                    })
                    instance_stats['total_tokens'] += file_stats['total_tokens']
                    instance_stats['total_history_items'] += file_stats['history_items']
                    
                    # More detailed logging with savings info
                    self.logger.info(f"Created {tra_file.name}: {file_stats['history_items']} history items, "
                                   f"{file_stats['total_tokens']} tokens "
                                   f"(original: {file_stats['original_tokens']}, "
                                   f"saved: {file_stats['saved_tokens']}, "
                                   f"compression ratio: {file_stats['compression_ratio']:.1f}%)")
                else:
                    processing_stats['failed_instances'].append({
                        'instance_name': instance_dir.name,
                        'traj_file': traj_file.name,
                        'reason': 'No valid history items'
                    })
            
            if instance_stats['tra_files_created']:
                processing_stats['processed_instances'].append(instance_stats)
                processing_stats['total_tokens'] += instance_stats['total_tokens']
                processing_stats['total_tra_files'] += len(instance_stats['tra_files_created'])
                
                self.logger.info(f"Instance {instance_dir.name}: created "
                               f"{len(instance_stats['tra_files_created'])} .tra file(s)")
        
        # Log processing results
        self.logger.info(f"Iteration processing complete: created {processing_stats['total_tra_files']} .tra file(s), "
                        f"total ~{processing_stats['total_tokens']} tokens")

        if processing_stats['failed_instances']:
            self.logger.warning(f"Number of failed instances: {len(processing_stats['failed_instances'])}")
        
        return processing_stats
    
    def process_workspace_directory(self, workspace_dir: Path, target_iterations: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Process all iterations in the entire workspace directory

        Args:
            workspace_dir: Path to the workspace directory
            target_iterations: List of specific iterations to process; None means process all

        Returns:
            Overall processing result statistics
        """
        self.logger.info(f"Starting to process workspace directory: {workspace_dir}")
        
        if not workspace_dir.exists() or not workspace_dir.is_dir():
            self.logger.error(f"Workspace directory does not exist: {workspace_dir}")
            return {}
        
        workspace_stats = {
            'workspace_dir': str(workspace_dir),
            'iterations_processed': [],
            'total_tokens': 0,
            'total_tra_files': 0,
            'processing_errors': []
        }
        
        # Find all iteration directories
        iteration_pattern = re.compile(r'^iteration_(\d+)$')
        iteration_dirs = []
        
        for item in workspace_dir.iterdir():
            if item.is_dir():
                match = iteration_pattern.match(item.name)
                if match:
                    iteration_num = int(match.group(1))
                    if target_iterations is None or iteration_num in target_iterations:
                        iteration_dirs.append((iteration_num, item))
        
        # Sort by iteration number
        iteration_dirs.sort(key=lambda x: x[0])
        
        if not iteration_dirs:
            self.logger.warning("No iteration directories found")
            return workspace_stats
        
        # Process each iteration
        for iteration_num, iteration_dir in iteration_dirs:
            try:
                iteration_stats = self.process_iteration_directory(iteration_dir)
                if iteration_stats:
                    workspace_stats['iterations_processed'].append({
                        'iteration_number': iteration_num,
                        'stats': iteration_stats
                    })
                    workspace_stats['total_tokens'] += iteration_stats['total_tokens']
                    workspace_stats['total_tra_files'] += iteration_stats['total_tra_files']
            except Exception as e:
                error_info = {
                    'iteration_number': iteration_num,
                    'iteration_dir': str(iteration_dir),
                    'error': str(e)
                }
                workspace_stats['processing_errors'].append(error_info)
                self.logger.error(f"Error processing iteration_{iteration_num}: {e}")
        
        # Final statistics
        processed_iterations = len(workspace_stats['iterations_processed'])
        self.logger.info(f"Workspace processing complete: {processed_iterations} iteration(s), "
                        f"{workspace_stats['total_tra_files']} .tra file(s), "
                        f"~{workspace_stats['total_tokens']} tokens")
        
        return workspace_stats
    
    def extract_problem_from_tra(self, tra_file: Path, problem_file: Path) -> bool:
        """
        Extract problem description from .tra file and save as .problem file

        Args:
            tra_file: Path to the .tra file
            problem_file: Path to the target .problem file

        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            with open(tra_file, 'r', encoding='utf-8') as f:
                tra_data = json.load(f)
            
            # Locate Trajectory[1]["content"][0]["text"]
            trajectory = tra_data.get('Trajectory', [])
            if len(trajectory) < 2:
                self.logger.warning(f"Abnormal tra file format, trajectory length insufficient: {tra_file}")
                return False
            
            user_entry = trajectory[1]
            if user_entry.get('role') != 'user':
                self.logger.warning(f"trajectory[1] is not a user role: {tra_file}")
                return False
            
            content = user_entry.get('content', [])
            if not isinstance(content, list) or len(content) == 0:
                self.logger.warning(f"Abnormal user content format: {tra_file}")
                return False
            
            text_content = content[0].get('text', '')
            if not text_content:
                self.logger.warning(f"Text content not found: {tra_file}")
                return False
            
            # Use regex to extract content from <pr_description> tags
            import re
            match = re.search(r'<pr_description>\s*(.*?)\s*</pr_description>', text_content, re.DOTALL)
            if not match:
                self.logger.warning(f"pr_description tag not found: {tra_file}")
                return False
            
            problem_description = match.group(1).strip()
            if not problem_description:
                self.logger.warning(f"pr_description content is empty: {tra_file}")
                return False
            
            # Write .problem file
            with open(problem_file, 'w', encoding='utf-8') as f:
                f.write(problem_description)
            
            # Statistics
            problem_tokens = self._count_tokens(problem_description)
            self.logger.info(f"Extracted problem: {problem_file.name} ({problem_tokens} tokens)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract problem {tra_file}: {e}")
            return False
    
    def process_problems_in_iteration(self, iteration_dir: Path) -> Dict[str, Any]:
        """
        Extract problem files for all instances in an iteration directory

        Args:
            iteration_dir: Path to the iteration directory

        Returns:
            Extraction result statistics
        """
        self.logger.info(f"Starting to extract problems from iteration directory: {iteration_dir}")
        
        if not iteration_dir.exists() or not iteration_dir.is_dir():
            self.logger.warning(f"Directory does not exist or is not a directory: {iteration_dir}")
            return {}

        problem_stats = {
            'iteration_dir': str(iteration_dir),
            'problems_extracted': [],
            'total_problems': 0,
            'failed_extractions': []
        }
        
        # Iterate over all instance directories
        for instance_dir in iteration_dir.iterdir():
            if not instance_dir.is_dir() or instance_dir.name.startswith('.'):
                continue

            # Find .tra files
            tra_files = list(instance_dir.glob("*.tra"))
            if not tra_files:
                self.logger.debug(f"Instance {instance_dir.name} has no .tra files")
                continue

            # Process each .tra file (usually only one)
            for tra_file in tra_files:
                problem_file = instance_dir / (instance_dir.name + '.problem')
                
                success = self.extract_problem_from_tra(tra_file, problem_file)
                
                if success:
                    problem_stats['problems_extracted'].append({
                        'instance_name': instance_dir.name,
                        'tra_file': tra_file.name,
                        'problem_file': problem_file.name
                    })
                    problem_stats['total_problems'] += 1
                else:
                    problem_stats['failed_extractions'].append({
                        'instance_name': instance_dir.name,
                        'tra_file': tra_file.name,
                        'reason': 'Problem extraction failed'
                    })
        
        self.logger.info(f"Problem extraction complete: {problem_stats['total_problems']} succeeded, "
                        f"{len(problem_stats['failed_extractions'])} failed")
        
        return problem_stats


def process_trajectory_files(workspace_dir: str, iterations: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Convenience function: process trajectory files

    Args:
        workspace_dir: Path to the workspace directory
        iterations: List of iterations to process; None means process all

    Returns:
        Processing result statistics
    """
    processor = TrajectoryProcessor()
    return processor.process_workspace_directory(Path(workspace_dir), iterations)


def extract_problems_from_workspace(workspace_dir: str, iterations: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Convenience function: extract problem files from workspace

    Args:
        workspace_dir: Path to the workspace directory
        iterations: List of iterations to process; None means process all

    Returns:
        Extraction result statistics
    """
    import re
    
    processor = TrajectoryProcessor()
    workspace_path = Path(workspace_dir)
    
    if not workspace_path.exists():
        return {'error': f'Workspace directory does not exist: {workspace_path}'}
    
    # Find iteration directories
    iteration_pattern = re.compile(r'^iteration_(\d+)$')
    iteration_dirs = []
    
    for item in workspace_path.iterdir():
        if item.is_dir():
            match = iteration_pattern.match(item.name)
            if match:
                iteration_num = int(match.group(1))
                if iterations is None or iteration_num in iterations:
                    iteration_dirs.append((iteration_num, item))
    
    iteration_dirs.sort(key=lambda x: x[0])
    
    workspace_results = {
        'workspace_dir': str(workspace_path),
        'iterations_processed': [],
        'total_problems': 0,
        'total_failed': 0
    }
    
    for iteration_num, iteration_dir in iteration_dirs:
        problem_stats = processor.process_problems_in_iteration(iteration_dir)
        if problem_stats:
            workspace_results['iterations_processed'].append({
                'iteration_number': iteration_num,
                'stats': problem_stats
            })
            workspace_results['total_problems'] += problem_stats.get('total_problems', 0)
            workspace_results['total_failed'] += len(problem_stats.get('failed_extractions', []))
    
    return workspace_results


# Usage example
if __name__ == "__main__":
    # Example: process Demo_Structure directory
    demo_workspace = "/home/uaih3k9x/630_swe/SE/trajectories/Demo_Structure"
    
    processor = TrajectoryProcessor()
    results = processor.process_workspace_directory(Path(demo_workspace))
    
    print("Processing results:")
    print(f"- Iterations processed: {len(results['iterations_processed'])}")
    print(f"- .tra files created: {results['total_tra_files']}")
    print(f"- Total tokens: ~{results['total_tokens']}")