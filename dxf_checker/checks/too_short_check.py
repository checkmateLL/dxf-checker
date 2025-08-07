from dxf_checker.checks.base import SegmentCheck
from dxf_checker.config import ERROR_LAYERS, ERROR_COLORS
import math
from dxf_checker.logger import log_verbose

class TooShortSegmentCheck(SegmentCheck):
    def __init__(self, min_distance: float = 0.05, units_scale: float = 1.0, verbose: bool = False):
        super().__init__("TooShortSegment", f"Segment shorter than {min_distance}m")
        self.min_distance = min_distance  # Default to 5cm
        self.units_scale = units_scale
        self.verbose = verbose

    def run(self, entity, points, output_msp):
        if self.verbose:
            log_verbose(f"\n=== Checking {type(entity).__name__} with {len(points)} points ===")
            log_verbose(f"Looking for segments shorter than {self.min_distance}m")
        
        short_segments_found = 0
        
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            distance = self._calculate_distance(p1, p2) * self.units_scale

            # Check if segment is too short
            if 0.0 < distance < self.min_distance:
                short_segments_found += 1
                self.error_count += 1
                
                if self.verbose:
                    log_verbose(f"  *** ERROR: Segment {i+1} is too short: {distance:.6f}m ***")
                    log_verbose(f"      From: ({p1[0]:.3f}, {p1[1]:.3f}, {p1[2]:.3f})")
                    log_verbose(f"      To:   ({p2[0]:.3f}, {p2[1]:.3f}, {p2[2]:.3f})")

                midpoint = tuple((p1[j] + p2[j]) / 2 for j in range(3))
                self._mark_error(output_msp, midpoint, f"Short segment: {distance:.6f}m")
            
            # stats for debugging
            elif self.verbose and i < 5:
                log_verbose(f"  Segment {i+1}: {distance:.6f}m (OK)")
        
        if self.verbose:
            log_verbose(f"Total short segments found: {short_segments_found}")
            if short_segments_found == 0:
                log_verbose("No segments shorter than threshold found.")
                # shortest segments for reference
                all_distances = []
                for i in range(len(points) - 1):
                    p1, p2 = points[i], points[i + 1]
                    dist = self._calculate_distance(p1, p2) * self.units_scale
                    all_distances.append((i+1, dist))
                
                all_distances.sort(key=lambda x: x[1])
                log_verbose("Shortest 10 segments:")
                for seg_num, dist in all_distances[:10]:
                    log_verbose(f"  Segment {seg_num}: {dist:.6f}m")

    def _calculate_distance(self, p1, p2):
        return math.sqrt(sum((p2[i] - p1[i]) ** 2 for i in range(3)))

    def _mark_error(self, msp, pt, description=""):
        layer = ERROR_LAYERS.get(self.name, 'SEGMENT_ERRORS_3D')
        color = ERROR_COLORS.get(self.name, 2)
        try:
            # pt is a proper tuple/list of 3 coordinates (because errors)
            if len(pt) != 3:
                if self.verbose:
                    log_verbose(f"    Warning: Invalid point format: {pt}")
                return
                
            marker = msp.add_point(pt, dxfattribs={'layer': layer, 'color': color})
            marker.set_xdata(
                'SEGMENT_CHECKER_3D',
                [
                    (1000, f"ERR_3D_SHORT_{self.error_count:04d}"),
                    (1000, description or f"Segment < {self.min_distance}m"),
                    (1010, pt[0]),
                    (1020, pt[1]),
                    (1030, pt[2]),
                ]
            )
        except Exception as e:
            if self.verbose:
                log_verbose(f"    Warning: Could not set extended data: {e}")
                log_verbose(f"    Point was: {pt}")