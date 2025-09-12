import os
from pathlib import Path
from importlib import import_module

from dxf_checker import config
from dxf_checker.logger import log


def load_checks(check_names, check_params=None):
    """
    Dynamically load check classes based on names passed from CLI.
    """
    if check_params is None:
        check_params = {}
    
    checks = []
    check_mapping = {
        "too_long": ("too_long_check", "TooLongSegmentCheck"),    
        "too_short": ("too_short_check", "TooShortSegmentCheck"),   
        "duplicates": ("duplicate_vertices_check", "DuplicateVerticesCheck"),
        "z_anomaly": ("z_anomalous_vertices_check", "ZAnomalousVerticesCheck"),
        "crossing": ("crossing_check", "UnconnectedCrossingCheck"),        
        "zero_elevation": ("zero_elevation_check", "ZeroElevationCheck"),
    }
    
    for name in check_names:
        if name not in check_mapping:
            log(f"Unknown check '{name}'. Available: {list(check_mapping.keys())}", level="ERROR")
            continue
            
        module_name, class_name = check_mapping[name]
        try:
            module = import_module(f"dxf_checker.checks.{module_name}")
            check_class = getattr(module, class_name)
            
            # Initialize with appropriate parameters
            if name == "too_long":
                check = check_class(
                    max_distance=check_params.get('max_distance', 50.0),
                    units_scale=check_params.get('units_scale', 1.0),
                    verbose=check_params.get('verbose', False)
                )
            elif name == "too_short":
                check = check_class(
                    min_distance=check_params.get('min_distance', 0.05),
                    units_scale=check_params.get('units_scale', 1.0),
                    verbose=check_params.get('verbose', False)
                )
            elif name == "zero_elevation":
                check = check_class(
                    tolerance=check_params.get('zero_tolerance', 1e-6),
                    verbose=check_params.get('verbose', False)
                )
            else:
                # For other checks, just pass verbose flag for now
                check = check_class(verbose=check_params.get('verbose', False))
            
            checks.append(check)
            log(f"Loaded check: {class_name}")
            
        except (ModuleNotFoundError, AttributeError) as e:
            log(f"Could not load check '{name}': {e}", level="ERROR")
    
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