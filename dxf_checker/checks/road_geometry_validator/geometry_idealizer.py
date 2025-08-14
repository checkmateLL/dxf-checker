from typing import List
import math
from .road_line import RoadLine
from .geometric_constraints import GeometricConstraints

class GeometryIdealizer:
    """
    Create an 'ideal' road line that fixes obvious errors while preserving
    legitimate geometric features like sharp turns, intersections, etc.
    """

    def __init__(self, constraints: GeometricConstraints):
        self.constraints = constraints

    def idealize(self, road_line: RoadLine) -> RoadLine:
        """
        Create idealized road geometry using conservative approach that preserves
        legitimate sharp direction changes
        """
        vertices = road_line.vertices
        if len(vertices) < 3:
            return road_line  # Can't improve lines with < 3 points
            
        # Step 1: Remove obvious duplicate/near-duplicate points only
        cleaned = self._remove_near_duplicates(vertices)
        if len(cleaned) < 3:
            return RoadLine(cleaned, {**road_line.meta, "idealized": True})
            
        # Step 2: Fix only obvious surveying/digitizing errors, preserve intentional geometry
        error_corrected = self._fix_obvious_errors(cleaned)
        
        # Step 3: Light elevation smoothing only (preserve horizontal alignment)
        final = self._smooth_elevations_only(error_corrected)
        
        return RoadLine(final, {**road_line.meta, "idealized": True})

    def _remove_near_duplicates(self, vertices: List[tuple]) -> List[tuple]:
        """Remove points that are very close to each other (surveying errors)"""
        if len(vertices) <= 2:
            return vertices
            
        cleaned = [vertices[0]]
        min_distance = 0.005  # 5mm minimum distance - very conservative
        
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

    def _fix_obvious_errors(self, vertices: List[tuple]) -> List[tuple]:
        """
        Fix only obvious digitizing errors while preserving intentional geometry.
        Uses angle analysis to distinguish between errors and legitimate features.
        """
        if len(vertices) < 5:  # Need enough points for context
            return vertices
            
        corrected = [vertices[0]]  # Always keep first point
        
        for i in range(1, len(vertices) - 1):
            curr_pt = vertices[i]
            
            # Analyze if this point looks like a digitizing error
            if self._is_likely_digitizing_error(vertices, i):
                # Apply minimal correction
                corrected_pt = self._apply_minimal_correction(vertices, i)
                corrected.append(corrected_pt)
            else:
                # Keep original point (it's likely intentional geometry)
                corrected.append(curr_pt)
        
        corrected.append(vertices[-1])  # Always keep last point
        return corrected

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
                smoothing_factor = 0.3  # Light smoothing
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