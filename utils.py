"""
Legacy utils module for backwards compatibility.
This module re-exports the new utils package for existing code.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from 'utils' module is deprecated. Use 'from utils import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from the new utils package
from utils import *

# Add a note for developers
print("⚠️  Note: utils.py is deprecated. Please migrate to 'from utils import ...'")
