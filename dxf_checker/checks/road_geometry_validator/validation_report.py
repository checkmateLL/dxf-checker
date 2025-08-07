from dataclasses import dataclass
from typing import List, Tuple
import csv
from pathlib import Path

from .road_line import RoadLine

@dataclass
class Deviation:
    vertex_index: int
    original: Tuple[float, float, float]
    ideal: Tuple[float, float, float]
    horizontal_error: float
    elevation_error: float

class ValidationReport:
    def __init__(self, original: RoadLine, ideal: RoadLine, deviations: List[Deviation]):
        self.original = original
        self.ideal = ideal
        self.deviations = deviations

    def summary(self) -> dict:
        if not self.deviations:
            return {"max_horizontal": 0.0, "max_elevation": 0.0, "count": 0}
        return {
            "max_horizontal": max(d.horizontal_error for d in self.deviations),
            "max_elevation": max(d.elevation_error for d in self.deviations),
            "count": len(self.deviations),
        }

    def save_csv(self, path: Path):
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "orig_x", "orig_y", "orig_z",
                             "ideal_x", "ideal_y", "ideal_z",
                             "horizontal_error", "elevation_error"])
            for d in self.deviations:
                writer.writerow([
                    d.vertex_index,
                    *d.original,
                    *d.ideal,
                    d.horizontal_error,
                    d.elevation_error,
                ])