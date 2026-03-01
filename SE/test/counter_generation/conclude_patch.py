#!/usr/bin/env python
"""
Analyze patches in filtered_predictions.json using Claude API or OpenAI API for evaluation,
and add analysis results directly to the original filtered_predictions.json file
"""

import os
import json
import sys
import time
import glob
import argparse
import concurrent.futures
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Get the directory of the current script
current_dir = Path(__file__).parent
# Ensure the claude module can be imported
sys.path.insert(0, str(current_dir))

# Import Claude API client
from claude import ClaudeAPI, extract_content

# OpenAI API configuration (hardcoded)
OPENAI_BASE_URL = "your_api_base"
OPENAI_API_KEY = "api_key""
OPENAI_MODEL = "gpt-4o"

# Import OpenAI API (if available)
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Add lock for thread-safe operations
save_lock = threading.Lock()

def load_filtered_predictions(file_path: str) -> Dict[str, Any]:
    """
    Load filtered prediction file

    Args:
        file_path: File path

    Returns:
        Loaded JSON data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        sys.exit(1)

def save_predictions(predictions: Dict[str, Any], file_path: str) -> None:
    """
    Save prediction data to JSON file

    Args:
        predictions: Prediction data
        file_path: Output file path
    """
    try:
        with save_lock:  # Use lock to ensure thread safety
            # Use temporary file then rename to avoid file corruption from write interruption
            temp_file = file_path + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, file_path)
            print(f"Prediction data saved to {file_path}")
    except Exception as e:
        print(f"Error saving data to {file_path}: {e}")

def get_prompt_template() -> str:
    """
    Get the prompt template for patch analysis

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

def analyze_patch_with_openai(
    problem_statement: str, 
    model_patch: str, 
    instance_id: str, 
    api_key: str = OPENAI_API_KEY,
    base_url: str = OPENAI_BASE_URL,
    model: str = OPENAI_MODEL
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

    Returns:
        OpenAI analysis result
    """
    if not OPENAI_AVAILABLE:
        print("Error: openai library not installed, please install using pip install openai")
        return {"error": "openai library not installed"}

    # Get prompt template and fill in
    prompt_template = get_prompt_template()
    prompt = prompt_template.format(
        problem_statement=problem_statement,
        model_patch=model_patch
    )
    
    print(f"Analyzing {instance_id} using OpenAI API...")
    
    retry_count = 0
    max_retries = 3
    
    while retry_count <= max_retries:
        try:
            # Create OpenAI client
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=120  # Set 2-minute timeout
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
                    print(f"Warning: Unable to find JSON format content in OpenAI response: {content[:100]}...")
                    return {"error": "Unable to parse JSON", "raw_content": content}
            except json.JSONDecodeError as e:
                print(f"Error parsing OpenAI JSON response: {e}")
                return {"error": "JSON parse error", "raw_content": content}
                
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = 5 * retry_count  # Exponential backoff
                print(f"Error calling OpenAI API (attempt {retry_count}/{max_retries}): {e}, waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"OpenAI API call failed, max retries reached: {e}")
                return {"error": f"OpenAI API error: {str(e)}"}

def analyze_patch_with_claude(problem_statement: str, model_patch: str, instance_id: str, claude_api: ClaudeAPI) -> Dict[str, Any]:
    """
    Analyze patch using Claude API

    Args:
        problem_statement: Problem description
        model_patch: Model patch
        instance_id: Instance ID
        claude_api: Claude API client

    Returns:
        Claude analysis result
    """
    # Get prompt template and fill in
    prompt_template = get_prompt_template()
    prompt = prompt_template.format(
        problem_statement=problem_statement,
        model_patch=model_patch
    )
    
    print(f"Analyzing {instance_id} using Claude API...")
    
    retry_count = 0
    max_retries = 3
    
    while retry_count <= max_retries:
        try:
            response = claude_api.send_message(
                message=prompt,
                model="claude-3-7-sonnet-20250219",
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
                    print(f"Warning: Unable to find JSON format content in response: {content[:100]}...")
                    return {"error": "Unable to parse JSON", "raw_content": content}
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                return {"error": "JSON parse error", "raw_content": content}
                
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = 5 * retry_count  # Exponential backoff
                print(f"Error calling Claude API (attempt {retry_count}/{max_retries}): {e}, waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"Claude API call failed, max retries reached: {e}")
                return {"error": f"Claude API error: {str(e)}"}

def process_single_entry(
    entry_data: Tuple[str, Dict[str, Any]], 
    predictions: Dict[str, Any],
    conclusion_file: str,
    api_type: str,
    claude_api: Optional[ClaudeAPI] = None,
    force_reprocess: bool = False
) -> None:
    """
    Process a single entry

    Args:
        entry_data: Tuple containing key and data
        predictions: Prediction data dictionary
        conclusion_file: Output file path
        api_type: API type, 'claude' or 'openai'
        claude_api: Claude API client (used when api_type is 'claude')
        force_reprocess: Whether to force reprocessing of entries that already have analysis
    """
    key, instance_data = entry_data
    
    # If this key has already been processed and not force reprocessing, skip
    if "claude_analysis" in instance_data and not force_reprocess:
        print(f"Skipping already processed entry: {key}")
        return
    elif "claude_analysis" in instance_data and force_reprocess:
        print(f"Force reprocessing entry: {key}")

    # Extract problem statement and patch
    if "problem_statement" not in instance_data:
        print(f"Warning: {key} has no problem statement, skipping")
        return
        
    problem_statement = instance_data["problem_statement"]
    model_patch = instance_data["model_patch"]
    
    try:
        # Call the corresponding analysis function based on API type
        if api_type == 'claude' and claude_api:
            analysis = analyze_patch_with_claude(problem_statement, model_patch, key, claude_api)
        elif api_type == 'openai':
            analysis = analyze_patch_with_openai(problem_statement, model_patch, key)
        else:
            print(f"Error: Invalid API configuration")
            return

        # Add analysis results and save
        with save_lock:
            predictions[key]["claude_analysis"] = analysis
            # Use temporary file then rename when saving, to avoid file corruption risk
            temp_file = conclusion_file + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(predictions, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, conclusion_file)
            print(f"Entry {key} processed and saved successfully")
    except Exception as e:
        print(f"Error processing entry {key}: {str(e)}")
        return None

def process_conclusion_file(
    conclusion_file: str, 
    api_type: str, 
    claude_api: Optional[ClaudeAPI] = None, 
    test_mode: bool = False,
    max_workers: int = 3,
    force_reprocess: bool = False
) -> None:
    """
    Process a single conclusion.json file using multi-threaded concurrent processing

    Args:
        conclusion_file: Path to conclusion.json file
        api_type: API type, 'claude' or 'openai'
        claude_api: Claude API client (used when api_type is 'claude')
        test_mode: Whether to only test with the first data entry
        max_workers: Maximum number of concurrent threads
        force_reprocess: Whether to force reprocessing of entries that already have analysis
    """
    print(f"Processing file: {conclusion_file}")

    # Load conclusion.json data
    predictions = load_filtered_predictions(conclusion_file)
    
    # Determine the list of keys to process
    keys_to_process = list(predictions.keys())
    if test_mode:
        # Only process the first entry
        keys_to_process = keys_to_process[0:1]
    
    # Prepare list of entries to process
    entries_to_process = []
    for key in keys_to_process:
        # Add to processing list if force reprocessing or not yet analyzed
        if force_reprocess or "claude_analysis" not in predictions[key]:
            entries_to_process.append((key, predictions[key]))
    
    if not entries_to_process:
        print(f"All entries in file {conclusion_file} have been processed, skipping")
        return

    print(f"File {conclusion_file} has {len(entries_to_process)} entries pending processing")

    # Process entries using sequential + concurrent approach (batch processing)
    batch_size = min(max_workers, len(entries_to_process))
    processed_count = 0
    
    for i in range(0, len(entries_to_process), batch_size):
        batch = entries_to_process[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(entries_to_process) + batch_size - 1)//batch_size}, {len(batch)} entries")

        # Use ThreadPoolExecutor to process current batch
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for entry_data in batch:
                futures.append(
                    executor.submit(
                        process_single_entry,
                        entry_data,
                        predictions,
                        conclusion_file,
                        api_type,
                        claude_api,
                        force_reprocess
                    )
                )
            
            # Wait for current batch to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result(timeout=180)  # Set 3-minute timeout
                    processed_count += 1
                except concurrent.futures.TimeoutError:
                    print(f"Processing entry timed out")
                except Exception as e:
                    print(f"Error processing entry: {e}")

        # Wait between batches to avoid API rate limiting
        if i + batch_size < len(entries_to_process):
            wait_time = 2  # Wait 2 seconds between batches
            print(f"Batch processing complete, waiting {wait_time} seconds before next batch...")
            time.sleep(wait_time)
    
    print(f"File {conclusion_file} processing complete, successfully processed {processed_count}/{len(entries_to_process)} entries")

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

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Analyze patches using LLM API and add results to conclusion.json files")
    parser.add_argument("--base_path", default="/home/uaih3k9x/swebench/evolve_agent/newest_exp_claude37_30-125",
                        help="Base path containing 5 default folders")
    parser.add_argument("--test", action="store_true", help="Test mode: only process the first data entry per file")
    parser.add_argument("--api_type", choices=["claude", "openai"], default="claude",
                        help="API type to use: claude or openai (default)")
    parser.add_argument("--claude_api_key", default="api_key",
                        help="Claude API key")
    parser.add_argument("--max_workers", type=int, default=3,
                        help="Maximum number of concurrent threads, default is 3")
    parser.add_argument("--force", action="store_true",
                        help="Force reprocessing of entries that already have analysis")
    args = parser.parse_args()
    
    # Process based on API type
    if args.api_type == 'claude':
        # Initialize Claude API client
        claude_api = ClaudeAPI(args.claude_api_key)
    else:  # openai
        if not OPENAI_AVAILABLE:
            print("Error: openai library not installed, please install using pip install openai")
            return
        claude_api = None

    # Find all conclusion.json files
    conclusion_files = find_conclusion_files(args.base_path)
    print(f"Found {len(conclusion_files)} conclusion.json files")

    # Process each file (files are processed sequentially)
    for file_path in conclusion_files:
        process_conclusion_file(
            file_path, 
            args.api_type, 
            claude_api, 
            args.test,
            args.max_workers,
            args.force
        )
        
    print("All files processing complete")

if __name__ == "__main__":
    main() 