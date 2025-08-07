from dxf_checker.checks.base import SegmentCheck
from dxf_checker.config import ERROR_LAYERS, ERROR_COLORS
from dxf_checker.logger import log_verbose
import math

class DuplicateVerticesCheck(SegmentCheck):
    def __init__(self, tolerance: float = 0.05, verbose: bool = False):
        super().__init__("DuplicateVertices", f"Vertices closer than {tolerance}m on same entity")
        self.tolerance = tolerance
        self.verbose = verbose

    def run(self, entity, points, output_msp):
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                if i == j:
                    continue
                dist = self._distance(points[i], points[j])
                if dist < self.tolerance:
                    self.error_count += 1
                    if self.verbose:
                        note = "EXACT duplicate" if dist == 0.0 else f"dist = {dist:.6f}"
                        log_verbose(f"  *** ERROR: Duplicate-like vertices at {points[i]} & {points[j]} ({note}) ***")
                    self._mark_error(output_msp, points[i])

    def _distance(self, a, b):
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    def _mark_error(self, msp, pt):
        layer = ERROR_LAYERS.get(self.name, 'SEGMENT_ERRORS_3D')
        color = ERROR_COLORS.get(self.name, 3)
        try:
            marker = msp.add_point(pt, dxfattribs={'layer': layer, 'color': color})
            marker.set_xdata(
                'SEGMENT_CHECKER_3D',
                [
                    (1000, f"ERR_DUP_VERT_{self.error_count:04d}"),
                    (1000, f"Two non-consecutive vertices < {self.tolerance}m apart"),
                    (1010, (pt[0], pt[1], pt[2])),
                ]
            )
        except Exception as e:
            if self.verbose:
                log_verbose(f"    Warning: Could not set extended data: {e}")
