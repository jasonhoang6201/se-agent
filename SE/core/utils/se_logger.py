#!/usr/bin/env python3
"""
SE Framework Logging Configuration Module

Provides unified logging management for the SE framework, built on the existing SWE-agent logging system.
Log files are saved under each run's output_dir to ensure they do not overlap or overwrite.
"""

from pathlib import Path
from sweagent.utils.log import get_logger, add_file_handler


class SELoggerManager:
    """SE Framework Log Manager"""
    
    def __init__(self):
        self.handler_id = None
        self.log_file_path = None
        
    def setup_logging(self, output_dir: str | Path) -> str:
        """
        Set up the logging system for the SE framework

        Args:
            output_dir: Output directory path (e.g., "SE/trajectories/testt_5/iteration_1")

        Returns:
            Full path to the log file
        """
        output_dir = Path(output_dir)
        
        # Ensure the output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set log file path
        self.log_file_path = output_dir / "se_framework.log"
        
        # Add SE-specific file handler
        self.handler_id = add_file_handler(
            self.log_file_path,
            filter="SE",  # Only log SE-related messages
            level="DEBUG"  # Log all levels: DEBUG, INFO, WARNING, ERROR
        )
        
        return str(self.log_file_path)
    
    def get_se_logger(self, module_name: str, emoji: str = "📋") -> object:
        """
        Get an SE framework-specific logger

        Args:
            module_name: Module name (e.g., "SE.core.utils")
            emoji: Display emoji (used to distinguish different modules)

        Returns:
            Configured logger object
        """
        # Ensure module name starts with SE so that filter="SE" can match
        if not module_name.startswith("SE"):
            module_name = f"SE.{module_name}"
            
        return get_logger(module_name, emoji=emoji)


# Global instance
se_logger_manager = SELoggerManager()


def setup_se_logging(output_dir: str | Path) -> str:
    """
    Shortcut to set up SE logging system

    Args:
        output_dir: Output directory path

    Returns:
        Log file path
    """
    return se_logger_manager.setup_logging(output_dir)


def get_se_logger(module_name: str, emoji: str = "📋") -> object:
    """
    Shortcut to get SE logger

    Args:
        module_name: Module name
        emoji: Display emoji

    Returns:
        Logger object
    """
    return se_logger_manager.get_se_logger(module_name, emoji)