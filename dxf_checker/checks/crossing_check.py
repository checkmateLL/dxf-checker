from dxf_checker.checks.base import SegmentCheck
from dxf_checker.config import ERROR_LAYERS, ERROR_COLORS
from dxf_checker.logger import log_verbose
import math
from itertools import combinations

class UnconnectedCrossingCheck(SegmentCheck):
    def __init__(self, proximity_tolerance: float = 0.01, verbose: bool = False, logger=None):
        super().__init__("UnconnectedCrossing", "Intersecting lines without shared vertex")
        self.tolerance = proximity_tolerance
        self.verbose = verbose
        self.line_segments = []  # [(entity, (p1, p2))]

    def run(self, entity, points, output_msp):
        # Extract segments from this entity
        for i in range(len(points) - 1):
            self.line_segments.append((entity, (points[i], points[i + 1])))
        

    def finalize(self, output_msp):
        for (e1, seg1), (e2, seg2) in combinations(self.line_segments, 2):
            if e1 is e2:
                continue# skip comparing with self

            if self._segments_intersect_2d(seg1, seg2):
                intersection = self._intersection_point_2d(seg1, seg2)

                if not self._near_any_vertex(intersection, seg1, seg2):
                    self.error_count += 1
                    if self.verbose and self.logger:
                        self.logger.log_verbose(f"  *** ERROR: Unconnected crossing at {intersection} ***")
                    self._mark_error(output_msp, intersection)

    def _segments_intersect_2d(self, seg1, seg2):
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        A, B = seg1[0][:2], seg1[1][:2]
        C, D = seg2[0][:2], seg2[1][:2]
        return (ccw(A,C,D) != ccw(B,C,D)) and (ccw(A,B,C) != ccw(A,B,D))


    def _intersection_point_2d(self, seg1, seg2):
        # Returns intersection point in 3D with z = average of the four
        (x1, y1, z1), (x2, y2, z2) = seg1
        (x3, y3, z3), (x4, y4, z4) = seg2

        denom = (x1 - x2)*(y3 - y4) - (y1 - y2)*(x3 - x4)
        if denom == 0:
            return ((x1 + x2 + x3 + x4)/4, (y1 + y2 + y3 + y4)/4, (z1 + z2 + z3 + z4)/4)  # fallback

        px = ((x1*y2 - y1*x2)*(x3 - x4) - (x1 - x2)*(x3*y4 - y3*x4)) / denom
        py = ((x1*y2 - y1*x2)*(y3 - y4) - (y1 - y2)*(x3*y4 - y3*x4)) / denom
        pz = (z1 + z2 + z3 + z4) / 4  # Just for consistency in 3D
        return (px, py, pz)

    def _near_any_vertex(self, point, seg1, seg2):
        """
        Returns True if 'point' is near any endpoint in either segment.
        """
        for pt in seg1 + seg2:
            if self.distance_2d(pt, point) < self.tolerance:
                return True
        return False

    def distance_2d(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _mark_error(self, msp, pt):
        msp.add_point(
            pt,
            dxfattribs={'layer': 'ERROR_UNCONNECTED_CROSSINGS', 'color': 5}
        )
