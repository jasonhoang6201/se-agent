#!/usr/bin/env python
"""
Script for filtering and saving prediction results

This script filters prediction results for specified IDs from the prediction file and saves them to a new file.
"""

import json
import os
from pathlib import Path
from typing import Dict, Set, Any


def read_predictions(file_path: str) -> Dict[str, Any]:
    """
    Read and parse the prediction file

    Args:
        file_path: Path to the prediction file

    Returns:
        Parsed JSON data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File {file_path} does not exist")
        return {}
    except json.JSONDecodeError:
        print(f"Error: File {file_path} is not valid JSON format")
        return {}
    except Exception as e:
        print(f"Error occurred while reading file: {str(e)}")
        return {}


def filter_predictions(predictions: Dict[str, Any], target_ids: Set[str]) -> Dict[str, Any]:
    """
    Filter prediction results, keeping only predictions for specified IDs

    Args:
        predictions: Dictionary of all prediction results
        target_ids: Set of target IDs

    Returns:
        Filtered prediction results dictionary
    """
    filtered_predictions = {}
    i = 0
    for instance_id, pred_data in predictions.items():
        if instance_id  not in target_ids:
            filtered_predictions[instance_id] = pred_data
            print(i, end=" ")
        i += 1
    
    return filtered_predictions


def save_predictions(predictions: Dict[str, Any], output_path: str) -> None:
    """
    Save prediction results to the specified file

    Args:
        predictions: Prediction results dictionary
        output_path: Output file path
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved {len(predictions)} prediction results to {output_path}")
    except Exception as e:
        print(f"Error occurred while saving file: {str(e)}")


def main():
    """Main function"""
    # Target instance ID set
    target_ids = {
        "django__django-11551",
        "django__django-14672",
        "django__django-15930",
        "django__django-16082",
        "django__django-13012",
        "django__django-12193",
        "django__django-11299",
        "django__django-11749",
        "django__django-12143",
        "django__django-7530",
        "sphinx-doc__sphinx-9281"
    }
    
    # Prediction file path - users can modify as needed
    # 用于充当反例 meaning "used as counter-examples"
    pred_file_path = "/home/uaih3k9x/swebench/evolve_agent/trajectories/uaih3k9x/default__deepseek/用于充当反例/preds.json"
    
    # Output file path
    output_dir = Path("counter_generation")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "filtered_predictions.json"
    
    # Read prediction file
    print(f"Reading prediction file: {pred_file_path}")
    predictions = read_predictions(pred_file_path)
    
    if predictions:
        print(f"Successfully read prediction file, contains {len(predictions)} prediction results")

        # Filter predictions
        filtered_predictions = filter_predictions(predictions, target_ids)
        print(f"Filtered down to {len(filtered_predictions)} matching prediction results")

        # Save filtered predictions
        save_predictions(filtered_predictions, output_path)
    else:
        print("No prediction results found, please check if the prediction file path is correct")


if __name__ == "__main__":
    main() 