from typing import List, Tuple
import math
from .road_line import RoadLine
from .validation_report import ValidationReport, Deviation

class ComparisonEngine:
    """
    Compare original vs ideal line using proper geometric comparison.
    Instead of vertex-to-vertex comparison, find the closest point on the ideal line
    for each original vertex.
    """

    def compare(self, original: RoadLine, ideal: RoadLine) -> ValidationReport:
        deviations: List[Deviation] = []
        
        if len(ideal.vertices) < 2:
            # Can't do geometric comparison with less than 2 points
            return ValidationReport(original=original, ideal=ideal, deviations=deviations)
        
        # For each vertex in the original line, find closest point on ideal line
        for idx, orig_pt in enumerate(original.vertices):
            closest_point, segment_idx = self._find_closest_point_on_line(orig_pt, ideal.vertices)
            
            # Calculate deviations
            dx = orig_pt[0] - closest_point[0]
            dy = orig_pt[1] - closest_point[1] 
            dz = orig_pt[2] - closest_point[2]
            
            horizontal_error = math.sqrt(dx*dx + dy*dy)
            elevation_error = abs(dz)
            
            deviations.append(
                Deviation(
                    vertex_index=idx,
                    original=orig_pt,
                    ideal=closest_point,
                    horizontal_error=horizontal_error,
                    elevation_error=elevation_error,
                )
            )
            
        return ValidationReport(original=original, ideal=ideal, deviations=deviations)

    def _find_closest_point_on_line(self, point: Tuple[float, float, float], 
                                   line_vertices: List[Tuple[float, float, float]]) -> Tuple[Tuple[float, float, float], int]:
        """
        Find the closest point on a polyline to a given point.
        Returns (closest_point, segment_index)
        """
        min_distance = float('inf')
        closest_point = line_vertices[0]
        closest_segment = 0
        
        # Check each segment of the ideal line
        for i in range(len(line_vertices) - 1):
            seg_start = line_vertices[i]
            seg_end = line_vertices[i + 1]
            
            # Find closest point on this segment
            closest_on_segment = self._closest_point_on_segment(point, seg_start, seg_end)
            distance = self._distance_3d(point, closest_on_segment)
            
            if distance < min_distance:
                min_distance = distance
                closest_point = closest_on_segment
                closest_segment = i
                
        return closest_point, closest_segment

    def _closest_point_on_segment(self, point: Tuple[float, float, float], 
                                 seg_start: Tuple[float, float, float], 
                                 seg_end: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Find the closest point on a line segment to a given point.
        Uses 3D projection math.
        """
        # Vector from seg_start to seg_end
        seg_vec = (seg_end[0] - seg_start[0], 
                  seg_end[1] - seg_start[1], 
                  seg_end[2] - seg_start[2])
        
        # Vector from seg_start to point
        point_vec = (point[0] - seg_start[0],
                    point[1] - seg_start[1], 
                    point[2] - seg_start[2])
        
        # Length squared of segment
        seg_length_sq = (seg_vec[0]*seg_vec[0] + 
                        seg_vec[1]*seg_vec[1] + 
                        seg_vec[2]*seg_vec[2])
        
        if seg_length_sq < 1e-10:  # Segment is essentially a point
            return seg_start
            
        # Project point onto segment line
        # t = dot(point_vec, seg_vec) / seg_length_sq
        dot_product = (point_vec[0]*seg_vec[0] + 
                      point_vec[1]*seg_vec[1] + 
                      point_vec[2]*seg_vec[2])
        
        t = dot_product / seg_length_sq
        
        # Clamp t to [0,1] to stay within segment bounds
        t = max(0.0, min(1.0, t))
        
        # Calculate closest point
        closest = (seg_start[0] + t * seg_vec[0],
                  seg_start[1] + t * seg_vec[1], 
                  seg_start[2] + t * seg_vec[2])
        
        return closest

    def _distance_3d(self, p1: Tuple[float, float, float], 
                    p2: Tuple[float, float, float]) -> float:
        """Calculate 3D Euclidean distance between two points"""
        return math.sqrt((p1[0] - p2[0])**2 + 
                        (p1[1] - p2[1])**2 + 
                        (p1[2] - p2[2])**2)