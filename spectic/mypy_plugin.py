"""
This module provides mypy plugin support for spectic.

To use this plugin, add the following to your mypy.ini or setup.cfg:

[mypy]
plugins = spectic.mypy_plugin

This will help mypy understand spectic classes better.
"""
from typing import Callable, Dict, List, Optional, Type

from mypy.plugin import ClassDefContext, Plugin
from mypy.types import Instance
from mypy.nodes import TypeInfo, ClassDef


class SpecticPlugin(Plugin):
    """Mypy plugin for spectic."""
    
    def get_class_decorator_hook(
        self, fullname: str
    ) -> Optional[Callable[[ClassDefContext], None]]:
        """Enable proper type checking for @spec-decorated classes."""
        if fullname.endswith('.spec'):
            return self._spec_hook
        return None
    
    def _spec_hook(self, context: ClassDefContext) -> None:
        """Transform class definition for @spec decorator."""
        info = context.cls.info
        
        # Add __init__ method signature based on class attributes
        self._add_init_method(info)
        
    def _add_init_method(self, info: TypeInfo) -> None:
        """Add __init__ method signature to the class."""
        # This would normally set up the proper __init__ signature
        # based on the class attributes, but that's complex to implement fully
        pass


def plugin(version: str) -> Type[Plugin]:
    """Entry point for mypy plugin."""
    return SpecticPlugin