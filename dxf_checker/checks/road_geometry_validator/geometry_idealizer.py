from typing import List
import math
from .road_line import RoadLine
from .geometric_constraints import GeometricConstraints

class GeometryIdealizer:
    """
    Create an 'ideal' road line using XY-only analysis.
    Curvature-based segmentation recognizes tangents, curves, and spiral-like transitions.
    """

    def __init__(
        self,
        constraints: GeometricConstraints,
        mode: str = "conservative",
        k_threshold: float = 8e-4,          # ↑ fewer false "tangents"
        max_xy_shift: float = 0.08,         # cap how far any point may move (m)
        tangent_rmse_tol: float = 0.025,    # only straighten if fit is good (m)
        curve_rmse_tol: float = 0.03,       # circle fit must be this tight (m)
    ):
        """mode: 'conservative' or 'aggressive'"""
        self.constraints = constraints
        self.mode = mode
        self.k_threshold = k_threshold
        self.max_xy_shift = max_xy_shift
        self.tangent_rmse_tol = tangent_rmse_tol
        self.curve_rmse_tol = curve_rmse_tol

    def idealize(self, road_line: RoadLine) -> RoadLine:
        """
        Idealize horizontal geometry; leave XY mostly intact; smooth Z lightly.
        """
        vertices = road_line.vertices
        if len(vertices) < 3:
            return road_line  # Can't improve lines with < 3 points
            
        cleaned = self._remove_near_duplicates(vertices)
        if len(cleaned) < 3:
            return RoadLine(cleaned, {**road_line.meta, "idealized": True})

        # Curvature-driven segmentation (XY)
        temp_line = RoadLine(cleaned, road_line.meta)
        segments = temp_line.segment_by_curvature(k_threshold=self.k_threshold)

        xy_fixed: List[tuple] = [cleaned[0]]
        for a, b, kind in segments:
            chunk = cleaned[a:b+1]
            if len(chunk) < 3:
                xy_fixed.extend(chunk[1:])
                continue
            if kind == "tangent":
                xy_fixed.extend(self._straighten_tangent(chunk)[1:])
            else:  # curve
                xy_fixed.extend(self._regularize_curve(chunk)[1:])

        # Elevation smoothing only (preserve XY)
        final = self._smooth_elevations_only(xy_fixed)
        return RoadLine(final, {**road_line.meta, "idealized": True})

    def _remove_near_duplicates(self, vertices: List[tuple]) -> List[tuple]:
        """Remove points that are very close to each other (surveying errors)"""
        if len(vertices) <= 2:
            return vertices
            
        cleaned = [vertices[0]]
        min_distance = 0.01 if self.mode == "aggressive" else 0.005
        
        for i in range(1, len(vertices)):
            prev_pt = cleaned[-1]
            curr_pt = vertices[i]
            
            # Calculate 3D distance
            dist_3d = math.sqrt((curr_pt[0] - prev_pt[0])**2 + 
                               (curr_pt[1] - prev_pt[1])**2 + 
                               (curr_pt[2] - prev_pt[2])**2)
            
            if dist_3d >= min_distance:
                cleaned.append(curr_pt)
                
        # Always keep the last point
        if len(cleaned) > 1 and cleaned[-1] != vertices[-1]:
            cleaned.append(vertices[-1])
                
        return cleaned

    # --- tangent/curve fixes -------------------------------------------
    def _straighten_tangent(self, pts: List[tuple]) -> List[tuple]:
        """
        Locally straighten using a least-squares line fit in XY.
        Only apply if RMSE is small; cap per-vertex movement.
        """
        import math
        if len(pts) < 3:
            return pts
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        # PCA for direction (2x2 covariance)
        sxx = sum((x - cx) ** 2 for x in xs)
        syy = sum((y - cy) ** 2 for y in ys)
        sxy = sum((x - cx) * (y - cy) for x, y in zip(xs, ys))
        # principal direction (largest eigenvector)
        # avoid atan2 for stability when sxy~0
        theta = 0.5 * math.atan2(2 * sxy, (sxx - syy)) if (sxx != syy or sxy != 0) else 0.0
        ux, uy = math.cos(theta), math.sin(theta)
        # projection + RMSE
        proj = []
        errs = []
        for p in pts:
            vx, vy = p[0] - cx, p[1] - cy
            t = vx * ux + vy * uy
            px, py = cx + t * ux, cy + t * uy
            proj.append((px, py))
            errs.append(math.hypot(px - p[0], py - p[1]))
        rmse = math.sqrt(sum(e * e for e in errs) / max(1, len(errs)))
        if rmse > self.tangent_rmse_tol:
            # too wiggly to treat as a clean tangent; keep original
            return pts
        # cap movement
        gain = 0.6 if self.mode == "aggressive" else 0.35
        out = [pts[0]]
        for (p, q) in zip(pts[1:-1], proj[1:-1]):
            dx, dy = (q[0] - p[0]) * gain, (q[1] - p[1]) * gain
            d = math.hypot(dx, dy)
            if d > self.max_xy_shift:
                scale = self.max_xy_shift / d
                dx *= scale
                dy *= scale
            out.append((p[0] + dx, p[1] + dy, p[2]))
        out.append(pts[-1])
        return out

    def _regularize_curve(self, pts: List[tuple]) -> List[tuple]:
        """
        Try circle fit; if good, nudge toward that arc with a displacement cap.
        Otherwise, leave the curve unchanged.
        """
        if len(pts) < 3:
             return pts
        
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        n = len(pts)
        # algebraic circle fit (Kåsa) with simple centering
        mx, my = sum(xs)/n, sum(ys)/n
        u = [x - mx for x in xs]
        v = [y - my for y in ys]
        Suu = sum(ui*ui for ui in u)
        Svv = sum(vi*vi for vi in v)
        Suv = sum(ui*vi for ui,vi in zip(u,v))
        Suuu = sum(ui*ui*ui for ui in u)
        Svvv = sum(vi*vi*vi for vi in v)
        Suvv = sum(ui*vi*vi for ui,vi in zip(u,v))
        Svuu = sum(vi*ui*ui for ui,vi in zip(u,v))
        det = 2*(Suu*Svv - Suv*Suv)
        if abs(det) < 1e-12:
            return pts  # nearly collinear; don't touch
        uc = (Svv*(Suuu+Suvv) - Suv*(Svvv+Svuu)) / det
        vc = (Suu*(Svvv+Svuu) - Suv*(Suuu+Suvv)) / det
        cx, cy = mx + uc, my + vc
        r = sum(math.hypot(x-cx, y-cy) for x,y in zip(xs,ys)) / n
        # residuals
        resid = [abs(math.hypot(x-cx,y-cy) - r) for x,y in zip(xs,ys)]
        rmse = math.sqrt(sum(e*e for e in resid)/n)
        # design/quality gates
        if rmse > self.curve_rmse_tol:
            return pts
        min_R = self.constraints.min_radius_for_design()
        if r < min_R * 0.8:  # too tight vs design intent → leave as-is
            return pts
        # preserve curvature sign
        def cross(a,b,c):
            ax, ay = b[0]-a[0], b[1]-a[1]
            bx, by = c[0]-b[0], c[1]-b[1]
            return ax*by - ay*bx
        sgn_data = 0.0
        for i in range(1, n-1):
            sgn_data += cross(pts[i-1], pts[i], pts[i+1])
        # build nudged points toward circle along radial direction with cap
        base_strength = 0.6 if self.mode == "aggressive" else 0.35
        out = [pts[0]]
        for P in pts[1:-1]:
            rx, ry = P[0]-cx, P[1]-cy
            d = math.hypot(rx, ry)
            if d < 1e-9:
                out.append(P); continue
            # target point on circle (same angle)
            tx, ty = cx + r*rx/d, cy + r*ry/d
            dx, dy = (tx - P[0])*base_strength, (ty - P[1])*base_strength
            # cap displacement
            m = math.hypot(dx, dy)
            if m > self.max_xy_shift:
                s = self.max_xy_shift / m
                dx *= s; dy *= s
            out.append((P[0]+dx, P[1]+dy, P[2]))
        out.append(pts[-1])
        # quick sign check—if fit flips turning direction noticeably, bail out
        sgn_fit = 0.0
        for i in range(1, n-1):
            sgn_fit += cross(out[i-1], out[i], out[i+1])
        if sgn_data*sgn_fit < 0:
            return pts
        return out

    # --- legacy helpers (kept; used indirectly in conservative pass) ---
    def _is_likely_digitizing_error(self, vertices: List[tuple], index: int) -> bool:
        """
        Determine if a point is likely a digitizing error vs intentional geometry.
        Look for patterns that indicate errors rather than design features.
        """
        if index <= 1 or index >= len(vertices) - 2:
            return False
            
        curr_pt = vertices[index]
        prev_pt = vertices[index - 1]
        next_pt = vertices[index + 1]
        
        # Get more context points if available
        prev2_pt = vertices[index - 2] if index >= 2 else None
        next2_pt = vertices[index + 2] if index < len(vertices) - 2 else None
        
        # Calculate distances
        dist_to_prev = self._distance_3d(curr_pt, prev_pt)
        dist_to_next = self._distance_3d(curr_pt, next_pt)
        
        # Very short segments might indicate digitizing errors
        if dist_to_prev < 0.02 or dist_to_next < 0.02:  # 2cm
            return True
            
        # Calculate deviation from straight line between prev and next
        deviation = self._point_to_line_distance(curr_pt, prev_pt, next_pt)
        
        # Small deviations (< 2cm) might be digitizing noise
        if deviation < 0.02:
            return True
            
        # Check if point creates an unrealistic zigzag pattern
        if prev2_pt and next2_pt:
            angle1 = self._calculate_angle(prev2_pt, prev_pt, curr_pt)
            angle2 = self._calculate_angle(prev_pt, curr_pt, next_pt)
            angle3 = self._calculate_angle(curr_pt, next_pt, next2_pt)
            
            # If we have alternating sharp angles, it might be digitizing errors
            # But be very conservative - only flag extreme cases
            if (abs(angle1 - angle3) < 0.2 and  # Similar angles
                abs(angle2) > 2.8 and  # Very sharp middle angle
                deviation < 0.05):  # Small deviation
                return True
                
        return False

    def _apply_minimal_correction(self, vertices: List[tuple], index: int) -> tuple:
        """
        Apply minimal correction to a point identified as likely error.
        Move only slightly toward the expected position.
        """
        curr_pt = vertices[index]
        prev_pt = vertices[index - 1]
        next_pt = vertices[index + 1]
        
        # Calculate expected position (simple interpolation)
        expected_x = (prev_pt[0] + next_pt[0]) / 2
        expected_y = (prev_pt[1] + next_pt[1]) / 2
        expected_z = (prev_pt[2] + next_pt[2]) / 2
        
        # Move only 50% toward expected position (very conservative)
        correction_factor = 0.5
        corrected_x = curr_pt[0] + correction_factor * (expected_x - curr_pt[0])
        corrected_y = curr_pt[1] + correction_factor * (expected_y - curr_pt[1])
        corrected_z = curr_pt[2] + correction_factor * (expected_z - curr_pt[2])
        
        return (corrected_x, corrected_y, corrected_z)

    def _smooth_elevations_only(self, vertices: List[tuple]) -> List[tuple]:
        """
        Apply light smoothing to elevations only, preserve XY coordinates.
        This fixes elevation surveying errors while keeping horizontal alignment intact.
        """
        if len(vertices) < 3:
            return vertices
            
        smoothed = [vertices[0]]  # Keep first point unchanged
        
        for i in range(1, len(vertices) - 1):
            curr_pt = vertices[i]
            prev_z = vertices[i - 1][2]
            next_z = vertices[i + 1][2]
            curr_z = curr_pt[2]
            
            # Calculate expected elevation based on neighbors
            expected_z = (prev_z + next_z) / 2
            z_deviation = abs(curr_z - expected_z)
            
            # Only smooth elevation if deviation is small (likely surveying noise)
            if z_deviation < 0.01:  # 1cm elevation noise
                smoothing_factor = max(0.3, self.constraints.smoothing_factor)
                new_z = curr_z + smoothing_factor * (expected_z - curr_z)
                smoothed_pt = (curr_pt[0], curr_pt[1], new_z)
            else:
                # Keep original elevation (likely intentional grade change)
                smoothed_pt = curr_pt
                
            smoothed.append(smoothed_pt)
        
        smoothed.append(vertices[-1])  # Keep last point unchanged
        return smoothed

    def _distance_3d(self, p1: tuple, p2: tuple) -> float:
        """Calculate 3D Euclidean distance"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)

    def _point_to_line_distance(self, point: tuple, line_start: tuple, line_end: tuple) -> float:
        """Calculate perpendicular distance from point to line (2D)"""
        # Using 2D distance to avoid elevation affecting the calculation
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]
        
        # Calculate distance using cross product formula
        numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denominator = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
        
        if denominator < 1e-10:
            return self._distance_3d(point, line_start)
            
        return numerator / denominator

    def _calculate_angle(self, p1: tuple, p2: tuple, p3: tuple) -> float:
        """Calculate angle at p2 formed by p1-p2-p3 (in radians)"""
        # Vectors p2->p1 and p2->p3
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # Calculate lengths
        len1 = math.sqrt(v1[0]**2 + v1[1]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if len1 < 1e-10 or len2 < 1e-10:
            return 0.0
            
        # Calculate dot product
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        
        # Calculate angle
        cos_angle = dot / (len1 * len2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to valid range
        
        return math.acos(cos_angle)