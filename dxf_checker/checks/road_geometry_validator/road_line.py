from typing import List, Dict, Any, Tuple, Optional
import math
from ._utils import distance_3d

class RoadLine:
    """
    Immutable representation of a road alignment.
    """

    def __init__(self,
                 vertices: List[Tuple[float, float, float]],
                 meta: Optional[Dict[str, Any]] = None,
                 ):
        self.vertices = vertices
        self.meta = meta or {}

    # --- basic geometry -------------------------------------------------
    def length(self) -> float:
        return sum(
            distance_3d(self.vertices[i], self.vertices[i + 1])
            for i in range(len(self.vertices) - 1)
        )

    def segment_lengths(self) -> List[float]:
        return [
            distance_3d(self.vertices[i], self.vertices[i + 1])
            for i in range(len(self.vertices) - 1)
        ]

    def bearing_at(self, index: int) -> float:
        """Horizontal bearing (radians) of segment i→i+1"""
        dx = self.vertices[index + 1][0] - self.vertices[index][0]
        dy = self.vertices[index + 1][1] - self.vertices[index][1]
        return math.atan2(dy, dx)

    # --- segmentation helpers ------------------------------------------
    def split_by_max_length(self, max_len: float) -> "RoadLine":
        """Return new RoadLine with extra vertices if any segment > max_len"""
        new_pts = [self.vertices[0]]
        for p1, p2 in zip(self.vertices[:-1], self.vertices[1:]):
            d = distance_3d(p1, p2)
            if d > max_len:
                n = int(math.ceil(d / max_len))
                for k in range(1, n):
                    t = k / n
                    new_pts.append(tuple(p1[i] * (1 - t) + p2[i] * t for i in range(3)))
            new_pts.append(p2)
        return RoadLine(new_pts, self.meta)