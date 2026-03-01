#!/usr/bin/env python
"""
Script for reading and printing prediction file contents

This script reads the preds.json file at the specified path and prints its content structure.
Used for analyzing prediction results and extracting needed information.
"""

import json
import os
from pathlib import Path


def read_predictions(file_path):
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
        return None
    except json.JSONDecodeError:
        print(f"Error: File {file_path} is not valid JSON format")
        return None
    except Exception as e:
        print(f"Error occurred while reading file: {str(e)}")
        return None


def main():
    """Main function"""
    # Prediction file path
    # 用于充当反例 meaning "used as counter-examples"
    pred_file_path = "/home/uaih3k9x/swebench/evolve_agent/trajectories/uaih3k9x/default__deepseek/用于充当反例/preds.json"

    # Read prediction file
    predictions = read_predictions(pred_file_path)
    
    if predictions:
        print(f"Successfully read prediction file: {pred_file_path}")
        print(f"File contains {len(predictions)} prediction results")

        # Iterate and output prediction contents
        for i, (instance_id, pred_data) in enumerate(predictions.items()):
            print(f"\n--- Prediction {i+1}: {instance_id} ---")

            # Output basic information of prediction data
            if isinstance(pred_data, dict):
                print(f"Prediction data keys: {', '.join(pred_data.keys())}")

                # If model_patch field exists, print its summary
                if "model_patch" in pred_data:
                    patch = pred_data["model_patch"]
                    if patch:
                        patch_preview = patch[:200] + "..." if len(patch) > 200 else patch
                        print(f"Patch content summary: {patch_preview}")
                    else:
                        print("Patch content is empty")

                # If submission field exists, print its summary
                if "submission" in pred_data:
                    submission = pred_data["submission"]
                    if submission:
                        submission_preview = submission[:200] + "..." if len(submission) > 200 else submission
                        print(f"Submission content summary: {submission_preview}")
                    else:
                        print("Submission content is empty")

                # If exit_status field exists, print exit status
                if "exit_status" in pred_data:
                    print(f"Exit status: {pred_data['exit_status']}")
            else:
                print(f"Prediction data type: {type(pred_data)}")


if __name__ == "__main__":
    main() 