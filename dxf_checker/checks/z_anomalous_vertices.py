from checks.base import SegmentCheck

class ZAnomalousVerticesCheck(SegmentCheck):
    def __init__(self, threshold: float = 0.04, verbose: bool = False):
        super().__init__("ZAnomalousVertices", f"Z deviation > {threshold}m from local line")
        self.threshold = threshold
        self.verbose = verbose

    def run(self, entity, points, output_msp):
        if len(points) < 3:
            return  # Need at least 3 points to check

        for i in range(1, len(points) - 1):
            p_prev = points[i - 1]
            p_curr = points[i]
            p_next = points[i + 1]

            # Interpolated Z at p_curr based on p_prev → p_next
            expected_z = self._interpolate_z(p_prev, p_next, p_curr)

            actual_z = p_curr[2]
            deviation = abs(actual_z - expected_z)

            if deviation > self.threshold:
                self.error_count += 1
                if self.verbose:
                    print(f"  *** ERROR: Z-anomaly at {p_curr}, deviation = {deviation:.4f}m")

                self._mark_error(output_msp, p_curr, deviation)

    def _interpolate_z(self, p1, p2, p):
        """Linearly interpolate expected Z for point p on XY plane between p1 and p2"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        d2 = dx**2 + dy**2
        if d2 == 0:
            return (p1[2] + p2[2]) / 2  # Fallback

        t = ((p[0] - p1[0]) * dx + (p[1] - p1[1]) * dy) / d2
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
        return p1[2] + t * (p2[2] - p1[2])

    def _mark_error(self, msp, pt, deviation):
        msp.add_point(
            pt,
            dxfattribs={'layer': 'ERROR_Z_ANOMALY', 'color': 6}
        )
