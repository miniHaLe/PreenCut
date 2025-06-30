"""
Legacy configuration module for backwards compatibility.
This module re-exports the new configuration system for existing code.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from 'config' is deprecated. Use 'from config import get_config' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from the new configuration system
from config import *

# Add a note for developers
print("⚠️  Note: config.py is deprecated. Please migrate to 'from config import get_config'")
