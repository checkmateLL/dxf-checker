from dataclasses import dataclass
from typing import List, Tuple
import csv
from pathlib import Path
import math

from .road_line import RoadLine
from .geometric_constraints import GeometricConstraints


@dataclass
class Deviation:
    vertex_index: int
    station: float
    original: Tuple[float, float, float]
    ideal: Tuple[float, float, float]
    horizontal_error: float
    elevation_error: float
    curvature_dev: float          # |k_orig - k_ideal|
    bearing_dev: float            # radians in [0, pi]
    design_radius: float          # 1/|k_ideal| (approx)
    design_ok: bool               # compatible with class/speed

class ValidationReport:
    def __init__(self, original: RoadLine, ideal: RoadLine, deviations: List[Deviation],
                 constraints: GeometricConstraints = None):
        self.original = original
        self.ideal = ideal
        self.deviations = deviations
        self.constraints = constraints or GeometricConstraints()

    def summary(self) -> dict:
        if not self.deviations:
            return {"max_horizontal": 0.0, "max_elevation": 0.0, "count": 0}
        hs = [d.horizontal_error for d in self.deviations]
        zs = [d.elevation_error for d in self.deviations]
        curvs = [d.curvature_dev for d in self.deviations]
        bears = [d.bearing_dev for d in self.deviations]
        def _std(a):
            if len(a) < 2: return 0.0
            m = sum(a)/len(a)
            return math.sqrt(sum((x-m)**2 for x in a)/(len(a)-1))
        severities = [self.severity(d) for d in self.deviations]
        return {
            "count": len(self.deviations),
            "max_horizontal": max(hs),
            "mean_horizontal": sum(hs)/len(hs),
            "std_horizontal": _std(hs),
            "max_elevation": max(zs),
            "mean_elevation": sum(zs)/len(zs),
            "std_elevation": _std(zs),
            "max_curvature_dev": max(curvs),
            "mean_curvature_dev": sum(curvs)/len(curvs),
            "max_bearing_dev_rad": max(bears),
            "mean_bearing_dev_rad": sum(bears)/len(bears),
            "severity_counts": {
                "high": sum(1 for s in severities if s == "high"),
                "medium": sum(1 for s in severities if s == "medium"),
                "low": sum(1 for s in severities if s == "low"),
            },
        }

    def severity(self, d: Deviation) -> str:
        h_tol = self.constraints.tolerance_horizontal_deviation  # e.g., 0.05 m
        if d.horizontal_error <= 0.0:
            return "low"
        # z not primary here; horizontal governs
        if d.horizontal_error > 2.0 * h_tol or not d.design_ok:
            return "high"
        if d.horizontal_error > h_tol:
            return "medium"
        return "low"

    def save_csv(self, path: Path):
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "index", "station_m",
                "orig_x", "orig_y", "orig_z",
                "ideal_x", "ideal_y", "ideal_z",
                "horizontal_error_m", "elevation_error_m",
                "curvature_dev_1m", "bearing_dev_rad",
                "ideal_design_radius_m", "design_ok"
            ])
            for d in self.deviations:
                writer.writerow([
                    d.vertex_index,
                    d.station,
                    *d.original,
                    *d.ideal,
                    d.horizontal_error,
                    d.elevation_error,
                    d.curvature_dev,
                    d.bearing_dev,
                    d.design_radius,
                    int(bool(d.design_ok)),
                ])