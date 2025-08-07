from typing import List
from .road_line import RoadLine
from .geometric_constraints import GeometricConstraints

class GeometryIdealizer:
    """
    Create an 'ideal' road line that satisfies geometric constraints.
    Very light implementation – replace with sophisticated fitters if needed.
    """

    def __init__(self, constraints: GeometricConstraints):
        self.constraints = constraints

    def idealize(self, road_line: RoadLine) -> RoadLine:
        # 1. Split long segments
        split = road_line.split_by_max_length(self.constraints.min_horizontal_radius)

        # 2. Simple moving-average smoothing
        vertices = split.vertices
        if len(vertices) < 3:
            return split

        alpha = self.constraints.smoothing_factor
        smoothed = [vertices[0]]
        for prev, curr, nxt in zip(vertices, vertices[1:], vertices[2:]):
            x = tuple(
                (1 - alpha) * curr[i] + alpha * (prev[i] + nxt[i]) / 2
                for i in range(3)
            )
            smoothed.append(x)
        smoothed.append(vertices[-1])

        return RoadLine(smoothed, {**road_line.meta, "idealized": True})