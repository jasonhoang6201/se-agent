import json
from typing import List, Dict, Optional
import requests
import os
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'
)

def step_count_filter(traj: Dict, min_steps: int = 3, max_steps: int = 30) -> bool:
    """Filter whether trajectory step count is within a reasonable range"""
    steps = traj.get('steps', [])
    return min_steps <= len(steps) <= max_steps

def has_long_repetition(traj: Dict, max_repeat: int = 3) -> bool:
    """Determine whether the trajectory contains consecutive repeated content"""
    steps = traj.get('steps', [])
    last_content = None
    repeat_count = 1
    for step in steps:
        content = step.get('content', '').strip()
        if content == last_content and content:
            repeat_count += 1
            if repeat_count > max_repeat:
                return True
        else:
            repeat_count = 1
        last_content = content
    return False

def code_edit_ratio(traj: Dict, min_ratio: float = 0.2) -> bool:
    """Determine whether the ratio of code editing steps meets the threshold"""
    steps = traj.get('steps', [])
    if not steps:
        return False
    edit_keywords = [k.lower() for k in ['edit', 'change', 'patch', 'diff', 'apply', 'rewrite', 'fix']]
    edit_count = sum(
        any(k in step.get('content', '').lower() for k in edit_keywords)
        for step in steps
    )
    return (edit_count / len(steps)) >= min_ratio

def filter_non_empty(trajectories: List[Dict]) -> List[Dict]:
    """Filter out empty content"""
    return [t for t in trajectories if t.get('content', '').strip()]

def filter_unique(trajectories: List[Dict]) -> List[Dict]:
    """Deduplicate content"""
    seen = set()
    unique_trajs = []
    for traj in trajectories:
        content = traj.get('content', '').strip()
        if content and content not in seen:
            seen.add(content)
            unique_trajs.append(traj)
    return unique_trajs

def filter_length(trajectories: List[Dict], min_len: int = 10) -> List[Dict]:
    """Filter out trajectories with content that is too short"""
    return [t for t in trajectories if len(t.get('content', '').strip()) >= min_len]

def filter_bad_keywords(trajectories: List[Dict]) -> List[Dict]:
    """Filter out trajectories containing negative keywords"""
    bad_keywords = ['cannot solve', 'error', 'not supported', 'sorry', "i don't know", 'failed', 'unable to', 'cannot', 'unsolved']
    def is_bad(traj):
        content = traj.get('content', '').lower()
        return any(k in content for k in bad_keywords)
    return [t for t in trajectories if not is_bad(t)]

def filter_step_count(trajectories: List[Dict]) -> List[Dict]:
    """Filter out trajectories with unreasonable step counts"""
    return [t for t in trajectories if step_count_filter(t)]

def filter_long_repetition(trajectories: List[Dict]) -> List[Dict]:
    """Filter out trajectories with long repetitions"""
    return [t for t in trajectories if not has_long_repetition(t)]

def filter_code_edit_ratio(trajectories: List[Dict]) -> List[Dict]:
    """Filter out trajectories that do not meet the code edit ratio threshold"""
    return [t for t in trajectories if code_edit_ratio(t)]

def filter_trajectories(trajectories: List[Dict]) -> List[Dict]:
    """Multi-step trajectory filtering, returns a list of valid trajectories"""
    filtered = filter_non_empty(trajectories)
    filtered = filter_unique(filtered)
    filtered = filter_length(filtered)
    filtered = filter_bad_keywords(filtered)
    filtered = filter_step_count(filtered)
    filtered = filter_long_repetition(filtered)
    filtered = filter_code_edit_ratio(filtered)
    return filtered


def deepseek_r1_select(problem_statement: str, trajectories: list) -> int:
    """Call DeepSeek R1 API to select the best trajectory, returns index"""
    prompt = (
        "You are an expert agent evaluator. Given a problem statement and several agent trajectories, "
        "your task is to select the trajectory that best solves the problem.\n\n"
        f"Problem Statement:\n{problem_statement}\n\n"
        "Agent Trajectories:\n"
    )
    for idx, traj in enumerate(trajectories):
        prompt += f"==== Trajectory {idx} ====\n" + json.dumps(traj, ensure_ascii=False) + "\n"
    prompt += (
        "\nPlease answer ONLY with the index (starting from 0) of the best trajectory. "
        "Do not output any explanation, punctuation, prefix, suffix, or any other content. "
        "Only output a single integer. If unsure, choose the closest one. If you cannot judge, output 0."
    )

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY":
        logging.error("DEEPSEEK_API_KEY environment variable is not set. Unable to call DeepSeek API. Please set a valid API Key.")
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 10,
        "temperature": 0.0
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        # More robust response format validation
        if not (isinstance(result, dict) and 'choices' in result and result['choices'] and 'message' in result['choices'][0] and 'content' in result['choices'][0]['message']):
            logging.error(f"Unexpected API response format: {result}")
            return 0
        reply = result['choices'][0]['message']['content'].strip()
        match = re.match(r"^\s*(\d+)\s*$", reply)
        if match:
            idx = int(match.group(1))
        else:
            logging.warning(f"Unable to extract a standalone number from reply, reply content: {reply}")
            idx = 0
    except Exception as e:
        logging.error(f"Failed to call DeepSeek R1 API: {e}")
        idx = 0
    return idx


def select_best_trajectory(problem_statement: str, trajectories: List[Dict]) -> Optional[Dict]:
    """Filter and select the best trajectory, returns the best trajectory dict or None"""
    filtered_trajectories = filter_trajectories(trajectories)
    contents = [traj.get('content', '') for traj in filtered_trajectories]
    if not contents:
        logging.info("No valid trajectories after filtering, returning None.")
        return None
    best_idx = deepseek_r1_select(problem_statement, contents)
    if 0 <= best_idx < len(filtered_trajectories):
        return filtered_trajectories[best_idx]
    else:
        logging.warning(f"best_idx out of range: {best_idx}, number of trajectories: {len(filtered_trajectories)}, returning None.")
        return None


def process_file(input_path: str, output_path: str):
    """Batch process file, selecting the best trajectory for each line"""
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:
        for lineno, line in enumerate(fin, 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                problem_statement = data.get('problem_statement', '')
                trajectories = data.get('trajectories', [])
                best_traj = select_best_trajectory(problem_statement, trajectories)
                if best_traj is None:
                    data['best_trajectory'] = None
                else:
                    data['best_trajectory'] = best_traj
                fout.write(json.dumps(data, ensure_ascii=False) + '\n')
                # Flush every 10 lines for efficiency
                if lineno % 10 == 0:
                    fout.flush()
            except Exception as e:
                logging.error(f"Failed to process line {lineno}: {e}, content: {line.strip()}")
                continue
        fout.flush()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Select best trajectory based on DeepSeek R1')
    parser.add_argument('--input', type=str, default='input.jsonl', help='Input file path')
    parser.add_argument('--output', type=str, default='output.jsonl', help='Output file path')
    args = parser.parse_args()
    if not os.path.exists(args.input):
        logging.error(f"Input file does not exist: {args.input}")
        exit(1)
    # Check API Key before starting
    if not os.environ.get("DEEPSEEK_API_KEY"):
        logging.error("DEEPSEEK_API_KEY environment variable not detected, program terminated.")
        exit(1)
    process_file(args.input, args.output)
