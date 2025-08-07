"""Shared tiny helpers"""

from typing import Tuple
import math

def distance_3d(p1: Tuple[float, float, float],
                p2: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

def midpoint(p1, p2):
    return tuple((a + b) / 2 for a, b in zip(p1, p2))