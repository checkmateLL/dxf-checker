from dxf_checker.checks.base import SegmentCheck
from dxf_checker.config import ERROR_LAYERS, ERROR_COLORS


class ZeroElevationCheck(SegmentCheck):
    def __init__(self, tolerance: float = 1e-6, verbose: bool = False, logger=None):
        """
        Check for vertices with zero or missing elevation.
        """
        super().__init__(
            "ZeroElevation",
            f"Zero or missing elevation (tolerance: {tolerance})",
            logger
        )
        self.tolerance = tolerance
        self.verbose = verbose
        self.logger = logger

    def run(self, entity, points, output_msp):
        """Check each vertex for zero or missing elevation values."""
        if not points:
            if self.verbose and self.logger:
                self.logger.log_verbose(f"No points provided for {entity.dxftype()}")
            return

        if self.verbose and self.logger:
            self.logger.log_verbose(f"\n=== Checking {entity.dxftype()} ===")
            self.logger.log_verbose(f"Entity has {len(points)} points")
            self.logger.log_verbose(f"Tolerance for zero elevation: {self.tolerance}")

        zero_points = []

        for i, point in enumerate(points):
            is_zero, full_point, z_val = self._check_point_has_zero_z(point, index=i)
            if is_zero:
                zero_points.append((i, full_point, z_val))

        if zero_points:
            self.error_count += 1
            if self.verbose and self.logger:
                self.logger.log_verbose(f"*** FOUND {len(zero_points)} ZERO ELEVATION POINTS in {entity.dxftype()} ***")
                for i, pt, z in zero_points:
                    self.logger.log_verbose(f"  ERROR: Zero/missing elevation at vertex {i}: {pt}, Z={z}")

            centroid = self._calculate_centroid([pt for _, pt, _ in zero_points])
            self._mark_error(output_msp, centroid)

        elif self.verbose and self.logger:
            self.logger.log_verbose(f"No zero elevation issues found in {entity.dxftype()}")

    def _check_point_has_zero_z(self, point, index=None):
        """
        Determine if a point has zero or missing Z elevation.

        Returns:
            is_zero_elev: bool
            full_point: (x, y, z)
            z_value: float
        """
        if len(point) < 3:
            full_point = list(point) + [0.0]
            z_value = 0.0
            is_zero = True
            reason = "2D point"
        else:
            z_value = point[2] if point[2] is not None else 0.0
            is_zero = abs(float(z_value)) <= self.tolerance
            full_point = list(point)
            reason = "within tolerance" if is_zero else "OK"

        if self.verbose and self.logger:
            msg = f"  Point {index}: {point} -> Z={z_value} ({reason})"
            self.logger.log_verbose(msg)

        return is_zero, full_point, z_value

    def _calculate_centroid(self, points):
        """Calculate centroid of a list of points."""
        if not points:
            return (0.0, 0.0, 0.0)

        sum_x = sum(pt[0] for pt in points)
        sum_y = sum(pt[1] for pt in points)
        sum_z = sum(pt[2] if len(pt) > 2 and pt[2] is not None else 0.0 for pt in points)

        count = len(points)
        return (sum_x / count, sum_y / count, sum_z / count)

    def _mark_error(self, msp, point):
        """Add a point marker to output DXF."""
        if len(point) < 3:
            point = (point[0], point[1], 0.0)
        else:
            point = (point[0], point[1], point[2] if point[2] is not None else 0.0)

        if self.verbose and self.logger:
            self.logger.log_verbose(f"    Marking error at: {point}")

        msp.add_point(
            point,
            dxfattribs={
                'layer': ERROR_LAYERS.get('ZeroElevation', 'ERROR_ZERO_ELEVATION'),
                'color': ERROR_COLORS.get('ZeroElevation', 30)
            }
        )
