#!/usr/bin/env python3

"""
SE Framework Utils Package

SE framework utilities module providing logging management, trajectory processing, and other core functionality.
"""

from .se_logger import setup_se_logging, get_se_logger
from .trajectory_processor import TrajectoryProcessor, process_trajectory_files, extract_problems_from_workspace
from .traj_pool_manager import TrajPoolManager
from .traj_summarizer import TrajSummarizer
from .traj_extractor import TrajExtractor
from .llm_client import LLMClient, TrajectorySummarizer
from .problem_manager import ProblemManager, get_problem_manager, get_problem_description, validate_problem_availability
from .instance_data_manager import (
    InstanceData, InstanceDataManager, get_instance_data_manager, 
    get_instance_data, get_iteration_instances, get_traj_pool_data
)

__all__ = [
    # Logging system
    'setup_se_logging',
    'get_se_logger', 
    # Trajectory processing
    'TrajectoryProcessor',
    'process_trajectory_files',
    'extract_problems_from_workspace',
    'TrajPoolManager',
    'TrajSummarizer',
    'TrajExtractor',
    # LLM integration
    'LLMClient',
    'TrajectorySummarizer',
    # Problem management (unified interface)
    'ProblemManager',
    'get_problem_manager', 
    'get_problem_description', 
    'validate_problem_availability',
    # Instance data management (unified data flow)
    'InstanceData',
    'InstanceDataManager',
    'get_instance_data_manager',
    'get_instance_data',
    'get_iteration_instances',
    'get_traj_pool_data'
]