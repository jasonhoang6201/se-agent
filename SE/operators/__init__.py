#!/usr/bin/env python3

"""
SE Operators Package

Unified entry point for the operator system, providing operator registration and access functionality.
"""

from .base import BaseOperator, TemplateOperator, EnhanceOperator
from .registry import (
    register_operator, 
    get_operator_class, 
    create_operator, 
    list_operators,
    get_registry
)

# Import concrete operator implementations
from .traj_pool_summary import TrajPoolSummaryOperator
from .alternative_strategy import AlternativeStrategyOperator
from .trajectory_analyzer import TrajectoryAnalyzerOperator
from .crossover import CrossoverOperator

# Import other operator implementations later
# from .conclusion import ConclusionOperator
# from .summary_bug import SummaryBugOperator

__all__ = [
    'BaseOperator',
    'TemplateOperator', 
    'EnhanceOperator',
    'register_operator',
    'get_operator_class',
    'create_operator',
    'list_operators',
    'get_registry',
    'TrajPoolSummaryOperator',
    'AlternativeStrategyOperator',
    'TrajectoryAnalyzerOperator',
    'CrossoverOperator'
]