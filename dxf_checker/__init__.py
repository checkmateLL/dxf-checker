"""
CheckMateLL DXF Checker - A tool for validating DXF segment integrity
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .main import main
from .config import ERROR_LAYERS, ERROR_COLORS, THRESHOLDS

__all__ = ["main", "ERROR_LAYERS", "ERROR_COLORS", "THRESHOLDS"]