#!/usr/bin/env python
"""
Check and fix the claude_analysis field in conclusion.json files,
ensuring all required keys exist and have values, regenerating analysis results that don't meet requirements
"""

import os
import json
import sys
import time
import glob
import argparse
import concurrent.futures
import threading
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set

# Get the directory of the current script
current_dir = Path(__file__).parent
# Ensure the claude module can be imported
sys.path.insert(0, str(current_dir))

# Import Claude API client
from claude import ClaudeAPI, extract_content

# OpenAI API configuration
OPENAI_BASE_URL = "your_api_base"
OPENAI_API_KEY = "api_key""
OPENAI_MODEL = "gpt-4o"

# Claude API configuration
CLAUDE_API_KEY = "api_key"
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"
CLAUDE_BASE_URL = "https://api.anthropic.com/v1/messages"

# Import OpenAI API (if available)
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Locks for thread safety
save_lock = threading.Lock()
print_lock = threading.Lock()  # Lock for printing
stats_lock = threading.Lock()  # Lock for updating statistics

# Statistics
stats = {
    "total_items": 0,
    "processed_items": 0,
    "fixed_items": 0,
    "skipped_items": 0,
    "failed_items": 0,
    "empty_patch_items": 0,  # Track items with empty model_patch
    "start_time": None,
    "end_time": None,
    "item_times": {}  # Track processing time for each item
}

# Required analysis fields
REQUIRED_KEYS = {
    "approach_summary",
    "modified_files",
    "key_changes",
    "strategy",
    "specific_technique_from_first_solution",
    "specific_files_or_functions",
    "assumptions_made_in_first_solution",
    "component_not_touched_in_first_solution",
    "different_perspective"
}

def log_message(message: str):
    """
    Thread-safe log printing

    Args:
        message: Message to print
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with print_lock:
        print(f"[{timestamp}] {message}")

def load_filtered_predictions(file_path: str) -> Dict[str, Any]:
    """
    Load filtered prediction file

    Args:
        file_path: File path

    Returns:
        Loaded JSON data
    """
    try:
        log_message(f"Loading file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_message(f"Error loading file {file_path}: {e}")
        sys.exit(1)

def save_predictions(predictions: Dict[str, Any], file_path: str) -> None:
    """
    Save prediction data to JSON file

    Args:
        predictions: Prediction data
        file_path: Output file path
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)
        log_message(f"Prediction data saved to {file_path}")
    except Exception as e:
        log_message(f"Error saving data to {file_path}: {e}")

def get_prompt_template() -> str:
    """
    Get the prompt template for patch analysis (for cases with model_patch)

    Returns:
        Prompt template string
    """
    return """
You are an AI assistant specialized in analyzing code patches. I will provide a GitHub issue (problem_statement) and a corresponding patch. Your task is to analyze this patch and provide detailed insights that could help develop an alternative solution.

Follow these steps:
1. Analyze the patch file and understand the changes made
2. Determine the core methods and techniques used to solve the problem
3. Identify the main files and sections that were modified
4. Identify key assumptions and limitations in the current solution

Return your analysis in JSON format with the following fields:
- approach_summary: Summary of the main approach used in the first solution
- modified_files: List of files that were modified
- key_changes: Description of key code changes in the patch
- strategy: The core solution strategy at an abstract level
- specific_technique_from_first_solution: Specific technique used that should be avoided in alternative solutions
- specific_files_or_functions: Files or functions that should not be modified in the same way
- assumptions_made_in_first_solution: Assumptions made in the first solution
- component_not_touched_in_first_solution: Components or key functions not touched but potentially relevant
- different_perspective: A different perspective for looking at the problem

The following examples are provided only for reference to illustrate the expected level of detail and abstraction for each field. Your analysis should be based on your own understanding of the patch and problem:

approach_summary example: "Added a conditional check to handle MultiOutputClassifier by accessing classes through the estimators_ attribute"
modified_files example: ["sklearn/model_selection/_validation.py"]
key_changes example: "Added a condition to check if estimator has 'estimators_' attribute, then uses estimator.estimators_[i_label].classes_ instead of estimator.classes_[i_label] for MultiOutputClassifier"
strategy example: "Component-specific exception handling" (instead of "Interface extension to provide unified attribute access")
specific_technique_from_first_solution example: "Direct attribute checking with hasattr() and conditional branching"
specific_files_or_functions example: "_fit_and_predict function in sklearn/model_selection/_validation.py"
assumptions_made_in_first_solution example: "Assumes that only MultiOutputClassifier needs special handling for classes_ attribute access"
component_not_touched_in_first_solution example: "MultiOutputClassifier class in sklearn/multioutput.py which could implement classes_ attribute directly"
different_perspective example: "API consistency perspective: make MultiOutputClassifier conform to the same interface as other classifiers instead of modifying the validation module"

Problem:
{problem_statement}
Patch:
{model_patch}
"""

def get_empty_patch_prompt_template() -> str:
    """
    Get the prompt template for empty patch analysis (for cases where model_patch is empty)

    Returns:
        Prompt template string
    """
    return """
You are an AI assistant specialized in analyzing unsuccessful solution attempts for code problems. I will provide a GitHub issue (problem_statement) that has been attempted but did not result in a successful patch submission. Your task is to analyze why a solution might have failed and provide insights that could help develop a successful solution.

Context: When a solution attempt fails to produce a valid patch, it often indicates one of these problems:
1. Too many ineffective operations were attempted
2. The approach was overly complex and not sufficiently targeted
3. The solution contained circular logic or infinite loops
4. The problem was misunderstood (either oversimplified or overcomplicated)
5. The approach missed the fundamental issue

Based on the problem statement alone, provide your analysis in JSON format with the following fields:
- approach_summary: "No successful patch was submitted. This likely indicates difficulties in implementing a working solution."
- modified_files: List of files that would likely need to be modified based on the problem description
- key_changes: Description of changes that would likely be needed to solve the problem
- strategy: A suggested core solution strategy at an abstract level
- specific_technique_from_first_solution: "No specific technique to avoid since no working solution was submitted, but likely pitfalls include [your analysis]"
- specific_files_or_functions: Specific files or functions that would likely need to be modified
- assumptions_made_in_first_solution: "The unsuccessful attempt likely made assumptions such as [your analysis]"
- component_not_touched_in_first_solution: Components or key functions that might be relevant but overlooked
- different_perspective: A different perspective or approach that might lead to a successful solution

Problem:
{problem_statement}

Note: Remember, there was no successful patch submitted for this problem. Your analysis should focus on why previous attempts might have failed and what approaches might be more successful.
"""

def analyze_patch_with_openai(
    problem_statement: str, 
    model_patch: str, 
    instance_id: str, 
    api_key: str = OPENAI_API_KEY,
    base_url: str = OPENAI_BASE_URL,
    model: str = OPENAI_MODEL,
    is_empty_patch: bool = False
) -> Dict[str, Any]:
    """
    Analyze patch using OpenAI API

    Args:
        problem_statement: Problem description
        model_patch: Model patch
        instance_id: Instance ID
        api_key: OpenAI API key
        base_url: OpenAI API base URL
        model: Model name
        is_empty_patch: Whether the patch is empty (model_patch is empty)

    Returns:
        OpenAI analysis result
    """
    if not OPENAI_AVAILABLE:
        log_message("Error: openai library not installed, please install using pip install openai")
        return {"error": "openai library not installed"}
    
    # Get prompt template and fill in
    if is_empty_patch:
        prompt_template = get_empty_patch_prompt_template()
        prompt = prompt_template.format(
            problem_statement=problem_statement
        )
        log_message(f"Analyzing empty patch {instance_id} using OpenAI API...")
    else:
        prompt_template = get_prompt_template()
        prompt = prompt_template.format(
            problem_statement=problem_statement,
            model_patch=model_patch
        )
        log_message(f"Analyzing patch {instance_id} using OpenAI API...")
    
    try:
        # Create OpenAI client
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )
        
        # Extract content
        content = response.choices[0].message.content

        # Try to parse JSON response
        try:
            # If the returned content contains extra text surrounding JSON, extract the JSON part
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_content = content[start_idx:end_idx]
                return json.loads(json_content)
            else:
                log_message(f"Warning: Unable to find JSON format content in OpenAI response: {content[:100]}...")
                return {"error": "Unable to parse JSON", "raw_content": content}
        except json.JSONDecodeError as e:
            log_message(f"Error parsing OpenAI JSON response: {e}")
            return {"error": "JSON parse error", "raw_content": content}
            
    except Exception as e:
        log_message(f"Error calling OpenAI API: {e}")
        return {"error": f"OpenAI API error: {str(e)}"}

def analyze_patch_with_claude(
    problem_statement: str, 
    model_patch: str, 
    instance_id: str, 
    claude_api: ClaudeAPI,
    is_empty_patch: bool = False
) -> Dict[str, Any]:
    """
    Analyze patch using Claude API

    Args:
        problem_statement: Problem description
        model_patch: Model patch
        instance_id: Instance ID
        claude_api: Claude API client
        is_empty_patch: Whether the patch is empty (model_patch is empty)

    Returns:
        Claude analysis result
    """
    # Get prompt template and fill in
    if is_empty_patch:
        prompt_template = get_empty_patch_prompt_template()
        prompt = prompt_template.format(
            problem_statement=problem_statement
        )
        log_message(f"Analyzing empty patch {instance_id} using Claude API...")
    else:
        prompt_template = get_prompt_template()
        prompt = prompt_template.format(
            problem_statement=problem_statement,
            model_patch=model_patch
        )
        log_message(f"Analyzing patch {instance_id} using Claude API...")
    
    # Directly use send_message method
    response = claude_api.send_message(
        message=prompt,
        model=CLAUDE_MODEL,  # Use global variable
        temperature=0.3,
        max_tokens=4000
    )
    
    content = extract_content(response)
    
    # Try to parse JSON response
    try:
        # If Claude's response contains extra text surrounding JSON, we need to extract the JSON part
        # Here we use a simple method: find the content between the first { and last }
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_content = content[start_idx:end_idx]
            return json.loads(json_content)
        else:
            log_message(f"Warning: Unable to find JSON format content in response: {content[:100]}...")
            return {"error": "Unable to parse JSON", "raw_content": content}
    except json.JSONDecodeError as e:
        log_message(f"Error parsing JSON response: {e}")
        return {"error": "JSON parse error", "raw_content": content}

def is_valid_analysis(analysis: Dict[str, Any]) -> bool:
    """
    Check if analysis result is valid (contains all required keys with non-empty values)

    Args:
        analysis: Analysis result

    Returns:
        Whether it is valid
    """
    # Check for errors
    if "error" in analysis:
        return False
    
    # Check if all required keys exist and have non-empty values
    for key in REQUIRED_KEYS:
        if key not in analysis:
            return False
        
        value = analysis[key]
        # Check if value is empty
        if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
            return False
    
    return True

def fix_analysis_item(
    key: str,
    instance_data: Dict[str, Any],
    api_type: str,
    claude_api: Optional[ClaudeAPI] = None,
    rate_limit_delay: float = 1.0
) -> Tuple[str, bool, Optional[Dict[str, Any]]]:
    """
    Check and fix a single analysis item

    Args:
        key: Key of the prediction item
        instance_data: Prediction item data
        api_type: API type, 'claude' or 'openai'
        claude_api: Claude API client (used when api_type is 'claude')
        rate_limit_delay: Delay between API calls (seconds)

    Returns:
        Tuple (key, whether fix is needed, new analysis result (if fix needed))
    """
    # Record processing start time
    start_time = time.time()
    
    # Update statistics
    with stats_lock:
        stats["item_times"][key] = {"start_time": start_time}

    # Check if claude_analysis exists
    if "claude_analysis" not in instance_data:
        log_message(f"Warning: {key} has no claude_analysis field, skipping")
        with stats_lock:
            stats["failed_items"] += 1
            stats["processed_items"] += 1
            stats["item_times"][key]["end_time"] = time.time()
            stats["item_times"][key]["success"] = False
            stats["item_times"][key]["error"] = "No claude_analysis field"
        return key, False, None
    
    # Check if analysis result is valid
    analysis = instance_data["claude_analysis"]
    if is_valid_analysis(analysis):
        log_message(f"Analysis result for {key} is valid, no fix needed")
        with stats_lock:
            stats["skipped_items"] += 1
            stats["processed_items"] += 1
            stats["item_times"][key]["end_time"] = time.time()
            stats["item_times"][key]["success"] = True
            duration = stats["item_times"][key]["end_time"] - stats["item_times"][key]["start_time"]
            stats["item_times"][key]["duration"] = duration
        return key, False, None
    
    # If analysis result is invalid, need to regenerate
    log_message(f"Analysis result for {key} is invalid, needs regeneration")

    # Extract problem statement and patch
    if "problem_statement" not in instance_data:
        log_message(f"Warning: {key} is missing problem statement, cannot regenerate")
        with stats_lock:
            stats["failed_items"] += 1
            stats["processed_items"] += 1
            stats["item_times"][key]["end_time"] = time.time()
            stats["item_times"][key]["success"] = False
            stats["item_times"][key]["error"] = "Missing problem statement"
        return key, False, None
    
    problem_statement = instance_data["problem_statement"]
    
    # Check if model_patch is empty
    is_empty_patch = False
    if "model_patch" not in instance_data or not instance_data["model_patch"]:
        log_message(f"model_patch for {key} is empty, using empty patch template")
        model_patch = ""
        is_empty_patch = True
        with stats_lock:
            stats["empty_patch_items"] += 1
    else:
        model_patch = instance_data["model_patch"]
    
    try:
        # Regenerate analysis based on API type
        if api_type == 'claude' and claude_api:
            new_analysis = analyze_patch_with_claude(
                problem_statement, 
                model_patch, 
                key, 
                claude_api,
                is_empty_patch
            )
        elif api_type == 'openai':
            new_analysis = analyze_patch_with_openai(
                problem_statement, 
                model_patch, 
                key,
                is_empty_patch=is_empty_patch
            )
        else:
            log_message(f"Error: Invalid API configuration")
            with stats_lock:
                stats["failed_items"] += 1
                stats["processed_items"] += 1
                stats["item_times"][key]["end_time"] = time.time()
                stats["item_times"][key]["success"] = False
                stats["item_times"][key]["error"] = "Invalid API configuration"
            return key, False, None
        
        # Check if new analysis result is valid
        if is_valid_analysis(new_analysis):
            log_message(f"Successfully regenerated analysis result for {key}")
            with stats_lock:
                stats["fixed_items"] += 1
                stats["processed_items"] += 1
                stats["item_times"][key]["end_time"] = time.time()
                stats["item_times"][key]["success"] = True
                duration = stats["item_times"][key]["end_time"] - stats["item_times"][key]["start_time"]
                stats["item_times"][key]["duration"] = duration
            
            # Avoid too frequent API calls
            time.sleep(rate_limit_delay)

            return key, True, new_analysis
        else:
            log_message(f"Regenerated analysis result is still invalid: {key}")
            with stats_lock:
                stats["failed_items"] += 1
                stats["processed_items"] += 1
                stats["item_times"][key]["end_time"] = time.time()
                stats["item_times"][key]["success"] = False
                stats["item_times"][key]["error"] = "Regenerated analysis result is invalid"
            
            # Avoid too frequent API calls
            time.sleep(rate_limit_delay)

            return key, False, None

    except Exception as e:
        import traceback
        log_message(f"Error processing {key}: {str(e)}")
        log_message(traceback.format_exc())
        
        # Update statistics
        with stats_lock:
            stats["failed_items"] += 1
            stats["processed_items"] += 1
            stats["item_times"][key]["end_time"] = time.time()
            stats["item_times"][key]["success"] = False
            stats["item_times"][key]["error"] = str(e)
            duration = stats["item_times"][key]["end_time"] - stats["item_times"][key]["start_time"]
            stats["item_times"][key]["duration"] = duration

        return key, False, None

def fix_conclusion_file(
    conclusion_file: str, 
    api_type: str, 
    claude_api: Optional[ClaudeAPI] = None, 
    test_mode: bool = False,
    max_workers: int = 4,
    rate_limit_delay: float = 1.0,
    test_item: Optional[str] = None
) -> None:
    """
    Fix analysis results in conclusion.json file

    Args:
        conclusion_file: Path to conclusion.json file
        api_type: API type, 'claude' or 'openai'
        claude_api: Claude API client (used when api_type is 'claude')
        test_mode: Whether to only test with the first data entry
        max_workers: Maximum number of concurrent worker threads
        rate_limit_delay: Delay between API calls (seconds)
        test_item: Test a specific item ID
    """
    log_message(f"Fixing file: {conclusion_file}")

    # Load conclusion.json data
    predictions = load_filtered_predictions(conclusion_file)
    
    # If a specific test item is specified
    if test_item:
        if test_item in predictions:
            log_message(f"Testing item {test_item}")
            # Update statistics
            with stats_lock:
                stats["total_items"] = 1
            
            # Fix single item
            key, need_fix, new_analysis = fix_analysis_item(
                test_item,
                predictions[test_item],
                api_type,
                claude_api,
                rate_limit_delay
            )
            
            # If fix is needed and there is a new analysis result
            if need_fix and new_analysis:
                # Save result
                with save_lock:
                    predictions[test_item]["claude_analysis"] = new_analysis
                    save_predictions(predictions, conclusion_file)
                log_message(f"Test item result saved")
            return
        else:
            log_message(f"Error: Item {test_item} not found")
            return
    
    # Determine the list of keys to process
    keys_to_process = list(predictions.keys())
    if test_mode:
        # Only process the first entry
        keys_to_process = keys_to_process[0:1]

    # Update statistics
    with stats_lock:
        stats["total_items"] = len(keys_to_process)
        stats["start_time"] = time.time()
    
    # Print start time
    start_timestamp = datetime.datetime.fromtimestamp(stats["start_time"]).strftime("%Y-%m-%d %H:%M:%S")
    log_message(f"Starting to fix {len(keys_to_process)} items, time: {start_timestamp}")

    # Process concurrently using thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_key = {
            executor.submit(
                fix_analysis_item, key, predictions[key], api_type, claude_api, rate_limit_delay
            ): key for key in keys_to_process
        }
        
        # Process completed tasks
        completed = 0
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            completed += 1
            
            # Calculate progress percentage
            progress = (completed / len(keys_to_process)) * 100
            log_message(f"Progress: {progress:.2f}% ({completed}/{len(keys_to_process)})")
            
            try:
                item_key, need_fix, new_analysis = future.result()
                # If fix is needed and there is a new analysis result
                if need_fix and new_analysis:
                    with save_lock:
                        # Update predictions in memory
                        predictions[item_key]["claude_analysis"] = new_analysis
                        # Save updated predictions
                        save_predictions(predictions, conclusion_file)
                        log_message(f"Fixed and saved analysis result for {item_key}")
            except Exception as e:
                log_message(f"Error processing {key}: {str(e)}")
                import traceback
                log_message(traceback.format_exc())
    
    # Update statistics
    with stats_lock:
        stats["end_time"] = time.time()

    # Calculate total processing time
    if stats["start_time"] and stats["end_time"]:
        total_duration = stats["end_time"] - stats["start_time"]
        end_timestamp = datetime.datetime.fromtimestamp(stats["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
        log_message(f"File {conclusion_file} fix complete, total time {total_duration:.2f} seconds")
        log_message(f"End time: {end_timestamp}")
        log_message(f"Statistics: total items {stats['total_items']}, processed {stats['processed_items']}, "
                  f"fixed {stats['fixed_items']}, skipped {stats['skipped_items']}, empty patches {stats['empty_patch_items']}, failed {stats['failed_items']}")
    else:
        log_message(f"File {conclusion_file} fix complete")

def find_conclusion_files(base_path: str) -> list:
    """
    Find all matching conclusion.json files

    Args:
        base_path: Base path

    Returns:
        List of file paths
    """
    conclusion_files = []
    
    # Iterate through 5 default folders
    for i in range(1, 6):
        folder_pattern = f"{base_path}/default_{i}/*/"
        timestamp_folders = glob.glob(folder_pattern)
        
        for timestamp_folder in timestamp_folders:
            conclusion_file = os.path.join(timestamp_folder, "conclusion.json")
            if os.path.exists(conclusion_file):
                conclusion_files.append(conclusion_file)
    
    return conclusion_files

def print_time_stats():
    """
    Print time statistics
    """
    if not stats["item_times"]:
        log_message("No time statistics available")
        return
    
    # Calculate average, minimum and maximum times
    durations = []
    for item_id, time_info in stats["item_times"].items():
        if "duration" in time_info:
            durations.append(time_info["duration"])
    
    if durations:
        avg_time = sum(durations) / len(durations)
        min_time = min(durations)
        max_time = max(durations)
        
        log_message(f"Time statistics:")
        log_message(f"  Average processing time: {avg_time:.2f} seconds")
        log_message(f"  Minimum processing time: {min_time:.2f} seconds")
        log_message(f"  Maximum processing time: {max_time:.2f} seconds")
        log_message(f"  Total items processed: {len(durations)}")

    # Print overall processing time
    if stats["start_time"] and stats["end_time"]:
        total_duration = stats["end_time"] - stats["start_time"]
        log_message(f"  Total processing time: {total_duration:.2f} seconds")

def start_tmux_session(session_name, command):
    """
    Start a tmux session and run a command

    Args:
        session_name: Session name
        command: Command to run
    """
    try:
        # Check if session with same name exists
        check_cmd = ["tmux", "has-session", "-t", session_name]
        result = subprocess.run(check_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        
        if result.returncode == 0:
            log_message(f"Session {session_name} already exists, closing it")
            kill_cmd = ["tmux", "kill-session", "-t", session_name]
            subprocess.run(kill_cmd)
        
        # Create new session
        create_cmd = ["tmux", "new-session", "-d", "-s", session_name]
        subprocess.run(create_cmd)
        
        # Run command in session
        run_cmd = ["tmux", "send-keys", "-t", session_name, command, "C-m"]
        subprocess.run(run_cmd)
        
        log_message(f"Started tmux session {session_name} and running command: {command}")
        log_message(f"Use 'tmux attach-session -t {session_name}' to view progress")
        
        return True
    except Exception as e:
        log_message(f"Error starting tmux session: {e}")
        return False

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fix claude_analysis fields in conclusion.json files")
    parser.add_argument("--base_path", default="/home/uaih3k9x/swebench/evolve_agent/exp_claude37_0-30",
                        help="Base path containing 5 default folders")
    parser.add_argument("--scan_dir", help="Specify directory path to scan, will process all conclusion.json files under it")
    parser.add_argument("--test", action="store_true", help="Test mode: only process the first data entry per file")
    parser.add_argument("--api_type", choices=["claude", "openai"], default="openai",
                        help="API type to use: claude or openai (default)")
    parser.add_argument("--claude_api_key", default=CLAUDE_API_KEY,
                        help="Claude API key")
    parser.add_argument("--specific_file", help="Directly process a specific preds.json or conclusion.json file instead of scanning directory")
    parser.add_argument("--max_workers", type=int, default=4, help="Maximum number of concurrent threads")
    parser.add_argument("--rate_limit_delay", type=float, default=1.0,
                       help="Delay time between API requests (seconds) to avoid rate limiting")
    parser.add_argument("--test_item", help="Process a specific item ID for testing")
    parser.add_argument("--tmux", action="store_true", help="Run in a tmux session")
    parser.add_argument("--tmux_session", default="fix_analysis", help="tmux session name")
    args = parser.parse_args()
    
    # If tmux mode is specified, start tmux session
    if args.tmux:
        # Build the same command but without the --tmux parameter
        cmd_parts = sys.argv.copy()
        cmd = " ".join([p for p in cmd_parts if p != "--tmux"])
        
        # Start tmux session
        start_tmux_session(args.tmux_session, cmd)
        return
    
    # Record start time
    log_message("Starting script execution")

    # Process based on API type
    if args.api_type == 'claude':
        # Initialize Claude API client
        claude_api = ClaudeAPI(args.claude_api_key)
    else:  # openai
        if not OPENAI_AVAILABLE:
            log_message("Error: openai library not installed, please install using pip install openai")
            return
        # Initialize OpenAI client
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        claude_api = None
    
    # If a specific file is specified
    if args.specific_file:
        if os.path.exists(args.specific_file):
            log_message(f"Directly processing specified file: {args.specific_file}")
            fix_conclusion_file(
                args.specific_file,
                args.api_type,
                claude_api,
                args.test,
                args.max_workers,
                args.rate_limit_delay,
                args.test_item
            )
        else:
            log_message(f"Error: Specified file {args.specific_file} does not exist")

        # Print time statistics
        print_time_stats()
        return
    
    # If a scan directory is specified
    if args.scan_dir:
        if os.path.exists(args.scan_dir):
            log_message(f"Starting directory scan: {args.scan_dir}")
            # Use glob to recursively find all conclusion.json files
            conclusion_files = glob.glob(os.path.join(args.scan_dir, "**", "conclusion.json"), recursive=True)
            log_message(f"Found {len(conclusion_files)} conclusion.json files")
            
            # Process each file
            for file_path in conclusion_files:
                fix_conclusion_file(
                    file_path, 
                    args.api_type, 
                    claude_api, 
                    args.test,
                    args.max_workers,
                    args.rate_limit_delay
                )
        else:
            log_message(f"Error: Specified scan directory {args.scan_dir} does not exist")

        # Print time statistics
        print_time_stats()
        return
    
    # Find all conclusion.json files
    conclusion_files = find_conclusion_files(args.base_path)
    log_message(f"Found {len(conclusion_files)} conclusion.json files")

    # Process each file
    for file_path in conclusion_files:
        fix_conclusion_file(
            file_path, 
            args.api_type, 
            claude_api, 
            args.test,
            args.max_workers,
            args.rate_limit_delay
        )
    
    # Print time statistics
    print_time_stats()
    log_message("All files fix complete")

if __name__ == "__main__":
    main() 