from dxf_checker.checks.base import SegmentCheck
from dxf_checker.config import ERROR_LAYERS, ERROR_COLORS
from dxf_checker.logger import log_verbose
import math

class TooLongSegmentCheck(SegmentCheck):
    def __init__(self, max_distance: float = 50.0, units_scale: float = 1.0, verbose: bool = False):
        super().__init__("TooLongSegment", f"Segment longer than {max_distance}m")
        self.max_distance = max_distance
        self.units_scale = units_scale
        self.verbose = verbose

    def run(self, entity, points, output_msp):
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]

            distance = self._calculate_distance(p1, p2) * self.units_scale

            if self.verbose:
                log_verbose(f"  Segment {i + 1}: {distance:.3f}m")

            if distance > self.max_distance:
                self.error_count += 1
                if self.verbose:
                    log_verbose(f"  *** ERROR: Segment exceeds {self.max_distance}m! ***")

                midpoint = tuple((p1[j] + p2[j]) / 2 for j in range(3))

                layer_name = ERROR_LAYERS.get(self.name, 'SEGMENT_ERRORS_3D')
                color = ERROR_COLORS.get(self.name, 1)

                # Create marker
                point = output_msp.add_point(
                    midpoint,
                    dxfattribs={'layer': layer_name, 'color': color}
                )

                # Add extended data
                try:
                    point.set_xdata(
                        'SEGMENT_CHECKER_3D',
                        [
                            (1000, f"ERR_3D_LONG_{self.error_count:04d}"),
                            (1000, f"Segment > {self.max_distance}m"),
                            (1040, float(distance)),
                            # Start point
                            (1010, float(p1[0])),
                            (1020, float(p1[1])),
                            (1030, float(p1[2])),
                            # End point
                            (1011, float(p2[0])),
                            (1021, float(p2[1])),
                            (1031, float(p2[2])),
                        ]
                    )

                except Exception as e:
                    if self.verbose:
                        log_verbose(f"    Warning: Could not set extended data: {e}")

    def _calculate_distance(self, p1, p2):
        return math.sqrt(sum((p2[i] - p1[i]) ** 2 for i in range(3)))
