#!/usr/bin/env python
"""
Add problem descriptions to the filtered_predictions.json file

This script iterates through the filtered_predictions.json file, retrieves corresponding problem
descriptions from the SWE-bench dataset based on instance IDs, and adds problem descriptions
to each entry in filtered_predictions.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import glob

# Add project root directory to path for importing sweagent module
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Import SWE-bench related functions
from datasets import load_dataset


def get_problem_statements(subset: str = "verified", split: str = "test") -> Dict[str, str]:
    """
    Retrieve problem descriptions from the SWE-bench dataset

    Args:
        subset: Dataset subset, options are "lite", "verified", "full"
        split: Dataset split, options are "dev", "test"

    Returns:
        Dictionary mapping instance IDs to problem descriptions
    """
    dataset_name = ""
    if subset == "full":
        dataset_name = "princeton-nlp/SWE-Bench"
    elif subset == "verified":
        dataset_name = "princeton-nlp/SWE-Bench_Verified"
    elif subset == "lite":
        dataset_name = "princeton-nlp/SWE-Bench_Lite"
    else:
        raise ValueError(f"Unsupported dataset subset: {subset}")

    print(f"Loading dataset: {dataset_name}, split: {split}")
    ds = load_dataset(dataset_name, split=split)
    
    # Create mapping from instance ID to problem description
    problem_statements = {}
    for instance in ds:
        instance_id = instance["instance_id"]
        problem_statement = instance["problem_statement"]
        problem_statements[instance_id] = problem_statement
    
    print(f"Loaded {len(problem_statements)} problem descriptions from dataset")
    return problem_statements


def update_filtered_predictions(
    filtered_predictions_path: str,
    problem_statements: Dict[str, str],
    output_path: str = None
) -> None:
    """
    Update the filtered_predictions.json file by adding problem descriptions

    Args:
        filtered_predictions_path: Path to filtered_predictions.json
        problem_statements: Mapping from instance IDs to problem descriptions
        output_path: Output file path; if None, overwrites the original file
    """
    # Read filtered_predictions.json
    with open(filtered_predictions_path, 'r', encoding='utf-8') as f:
        filtered_predictions = json.load(f)
    
    # Add problem descriptions to each entry
    not_found_instances = []
    updated_count = 0
    for instance_id, instance_data in filtered_predictions.items():
        if instance_id in problem_statements:
            instance_data["problem_statement"] = problem_statements[instance_id]
            updated_count += 1
        else:
            not_found_instances.append(instance_id)
    
    # Report instances where problem descriptions were not found
    if not_found_instances:
        print(f"Warning: Problem descriptions not found for the following instances: {', '.join(not_found_instances)}")

    print(f"Updated problem descriptions for {updated_count} instances in total")

    # Save updated data
    if output_path is None:
        output_path = filtered_predictions_path
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_predictions, f, ensure_ascii=False, indent=2)
    
    print(f"Problem descriptions have been added to {output_path}")


def main():
    """Main function"""
    # Command line argument parsing
    import argparse
    parser = argparse.ArgumentParser(description="Add problem descriptions to pred.json files and save as conclusion.json")
    parser.add_argument("--base_path", default="/home/uaih3k9x/swebench/evolve_agent/newest_exp_claude37_30-125",
                        help="Base path containing 5 folders")
    parser.add_argument("--subset", default="verified", choices=["lite", "verified", "full"],
                        help="SWE-bench dataset subset (default: verified)")
    parser.add_argument("--split", default="test", choices=["dev", "test"],
                        help="SWE-bench dataset split (default: test)")
    args = parser.parse_args() 
    
    # Get problem descriptions from SWE-bench
    problem_statements = get_problem_statements(subset=args.subset, split=args.split)
    
    # Find all matching pred.json files
    # Assuming the 5 folders are named default_1, default_2, ...
    processed_count = 0
    for i in range(1, 6):
        folder_pattern = f"{args.base_path}/default_{i}/*/"
        timestamp_folders = glob.glob(folder_pattern)
        
        for timestamp_folder in timestamp_folders:
            pred_file = os.path.join(timestamp_folder, "preds.json")
            if os.path.exists(pred_file):
                conclusion_file = os.path.join(timestamp_folder, "conclusion.json")
                print(f"Processing file: {pred_file}")
                print(f"Output file: {conclusion_file}")

                # Update pred.json and save as conclusion.json
                update_filtered_predictions(pred_file, problem_statements, conclusion_file)
                processed_count += 1
    
    print(f"Processing complete, processed {processed_count} files in total")


if __name__ == "__main__":
    main() 