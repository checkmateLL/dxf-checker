from typing import List, Tuple
from .road_line import RoadLine
from .validation_report import ValidationReport, Deviation

class ComparisonEngine:
    """
    Compare original vs ideal line and compute deviations.
    """

    def compare(self, original: RoadLine, ideal: RoadLine) -> ValidationReport:
        deviations: List[Deviation] = []
        for idx, (orig_pt, ideal_pt) in enumerate(zip(original.vertices, ideal.vertices)):
            dx = orig_pt[0] - ideal_pt[0]
            dy = orig_pt[1] - ideal_pt[1]
            dz = orig_pt[2] - ideal_pt[2]
            deviations.append(
                Deviation(
                    vertex_index=idx,
                    original=orig_pt,
                    ideal=ideal_pt,
                    horizontal_error=(dx ** 2 + dy ** 2) ** 0.5,
                    elevation_error=abs(dz),
                )
            )
        return ValidationReport(original=original, ideal=ideal, deviations=deviations)