#!/usr/bin/env python3

"""
SE Operators Registry System

Provides dynamic registration and retrieval of operators, supports finding operator classes by name.
"""

from typing import Dict, Type, Optional
from .base import BaseOperator


class OperatorRegistry:
    """Operator registry, manages all available operator classes"""
    
    def __init__(self):
        self._operators: Dict[str, Type[BaseOperator]] = {}
    
    def register(self, name: str, operator_class: Type[BaseOperator]) -> None:
        """
        Register an operator class

        Args:
            name: Operator name
            operator_class: Operator class
        """
        if not issubclass(operator_class, BaseOperator):
            raise ValueError(f"Operator class {operator_class} must inherit from BaseOperator")
        
        self._operators[name] = operator_class
        print(f"Registered operator: {name} -> {operator_class.__name__}")
    
    def get(self, name: str) -> Optional[Type[BaseOperator]]:
        """
        Get an operator class

        Args:
            name: Operator name

        Returns:
            Operator class or None
        """
        return self._operators.get(name)
    
    def list_operators(self) -> Dict[str, str]:
        """
        List all registered operators

        Returns:
            Mapping of operator names to class names
        """
        return {name: cls.__name__ for name, cls in self._operators.items()}
    
    def create_operator(self, name: str, config: Dict) -> Optional[BaseOperator]:
        """
        Create an operator instance

        Args:
            name: Operator name
            config: Operator configuration

        Returns:
            Operator instance or None
        """
        operator_class = self.get(name)
        if operator_class is None:
            print(f"Operator not found: {name}")
            return None
        
        try:
            return operator_class(config)
        except Exception as e:
            print(f"Failed to create operator {name}: {e}")
            return None


# Global operator registry
_global_registry = OperatorRegistry()


def register_operator(name: str, operator_class: Type[BaseOperator]) -> None:
    """
    Register an operator to the global registry

    Args:
        name: Operator name
        operator_class: Operator class
    """
    _global_registry.register(name, operator_class)


def get_operator_class(name: str) -> Optional[Type[BaseOperator]]:
    """
    Get an operator class from the global registry

    Args:
        name: Operator name

    Returns:
        Operator class or None
    """
    return _global_registry.get(name)


def create_operator(name: str, config: Dict) -> Optional[BaseOperator]:
    """
    Create an operator instance from the global registry

    Args:
        name: Operator name
        config: Operator configuration

    Returns:
        Operator instance or None
    """
    return _global_registry.create_operator(name, config)


def list_operators() -> Dict[str, str]:
    """
    List all registered operators

    Returns:
        Mapping of operator names to class names
    """
    return _global_registry.list_operators()


def get_registry() -> OperatorRegistry:
    """Get the global registry instance"""
    return _global_registry