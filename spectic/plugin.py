"""
This module provides IDE plugin support for spectic.

It helps IDEs like PyCharm, VSCode with Pylance, and others
to better understand spectic classes and provide better autocompletion.
"""
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

import sys

T = TypeVar("T")


# Define the hook that helps mypy understand @spec
def spectic_spec_hook(cls: Type[T]) -> Type[T]:
    """This is a hook for the mypy plugin to understand @spec."""
    return cls


# Placeholder for PyCharm plugin
class PycharmPlugin:
    """Placeholder for PyCharm plugin support."""
    
    @staticmethod
    def get_type_analyzer_hook() -> Callable[[Type[Any]], None]:
        """Return a hook for PyCharm type analyzer."""
        def analyze_type(cls: Type[Any]) -> None:
            pass
        return analyze_type
    
    @staticmethod
    def get_method_hook() -> Callable[[str, Type[Any]], None]:
        """Return a hook for PyCharm method analyzer."""
        def analyze_method(method_name: str, cls: Type[Any]) -> None:
            pass
        return analyze_method


# Auto-initialization for IDEs
if 'pycharm' in sys.modules or any('pycharm' in m for m in sys.modules):
    plugin = PycharmPlugin()
    
# For VS Code / Pylance integration
if 'pylance' in sys.modules or any('pylance' in m for m in sys.modules):
    # Define a helper for Pylance
    def infer_type_for_pylance(obj: Any, cls: Type[T]) -> T:
        """Helper for Pylance type inference."""
        return cast(T, obj)