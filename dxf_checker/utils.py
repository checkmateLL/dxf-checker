import os
from pathlib import Path
from importlib import import_module

from dxf_checker import config
from dxf_checker.logger import log


def load_checks(check_names):
    """
    Dynamically load check classes based on names passed from CLI.
    """
    checks = []
    for name in check_names:
        try:
            module = import_module(f"dxf_checker.checks.{name}_check")
            class_name = "".join([part.capitalize() for part in name.split("_")]) + "Check"
            check_class = getattr(module, class_name)
            checks.append(check_class())
        except (ModuleNotFoundError, AttributeError) as e:
            log(f"❌ Could not load check '{name}': {e}", level="ERROR")
    return checks


def get_output_path(input_file: Path):
    """
    Create a default error DXF output path like 'yourfile_errors.dxf'.
    """
    folder = input_file.parent
    name = input_file.stem
    return folder / f"{name}_errors.dxf"


def distance_3d(p1, p2):
    """
    3D Euclidean distance.
    """
    return ((p1[0] - p2[0]) ** 2 +
            (p1[1] - p2[1]) ** 2 +
            (p1[2] - p2[2]) ** 2) ** 0.5


def midpoint(p1, p2):
    """
    Midpoint between two 3D points.
    """
    return (
        (p1[0] + p2[0]) / 2,
        (p1[1] + p2[1]) / 2,
        (p1[2] + p2[2]) / 2
    )
