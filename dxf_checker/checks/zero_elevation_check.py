from dxf_checker.checks.base import SegmentCheck
from dxf_checker.config import ERROR_LAYERS, ERROR_COLORS
from dxf_checker.logger import log_verbose, log


class ZeroElevationCheck(SegmentCheck):
    def __init__(self, tolerance: float = 1e-6, verbose: bool = False):
        """
        Check for vertices with zero or missing elevation.
        
        Args:
            tolerance: Small tolerance for considering a value as zero (default: 1e-6)
            verbose: Enable detailed logging
        """
        super().__init__("ZeroElevation", f"Zero or missing elevation (tolerance: {tolerance})")
        self.tolerance = tolerance
        self.verbose = verbose    
    
    def run(self, entity, points, output_msp):
        """Check each vertex for zero or missing elevation values."""
        if not points:
            if self.verbose:
                log_verbose(f"No points provided for {entity.dxftype()}")
            return

        entity_has_zero_elevation = False
        zero_points = []
        
        # Debug info
        if self.verbose:
            log_verbose(f"\n=== Checking {entity.dxftype()} ===")
            log_verbose(f"Entity has {len(points)} points")
            log_verbose(f"Tolerance for zero elevation: {self.tolerance}")
            
            # Show some sample points
            sample_count = min(5, len(points))
            for i in range(sample_count):
                log_verbose(f"  Sample point {i}: {points[i]}")
            if len(points) > sample_count:
                log_verbose(f"  ... and {len(points) - sample_count} more points")

        # Special handling for HATCH (which contains polygon boundaries)
        if entity.dxftype() == 'HATCH':
            if self.verbose:
                log_verbose(f"Processing HATCH with {len(entity.paths)} boundary paths")
                log_verbose(f"Points extracted: {len(points)}")
            
            # For HATCH, check each point individually
            for i, point in enumerate(points):
                point_has_zero_z = False
                z_value = 0.0
                
                if len(point) < 3:
                    # 2D point - definitely zero elevation
                    point_has_zero_z = True
                    z_value = 0.0
                    if self.verbose:
                        log_verbose(f"  Point {i}: 2D point {point} -> Z=0")
                else:
                    # 3D point - check Z value
                    z_value = point[2] if point[2] is not None else 0.0
                    if abs(float(z_value)) <= self.tolerance:
                        point_has_zero_z = True
                        if self.verbose:
                            log_verbose(f"  Point {i}: 3D point {point} -> Z={z_value} (within tolerance)")
                    elif self.verbose:
                        log_verbose(f"  Point {i}: 3D point {point} -> Z={z_value} (OK)")
                
                if point_has_zero_z:
                    entity_has_zero_elevation = True
                    # Ensure we have a 3D point for error marking
                    error_point = list(point) + [z_value] if len(point) < 3 else list(point)
                    zero_points.append((i, error_point, z_value))

        # Handle POLYLINE entities (including closed polygons)
        elif entity.dxftype() in ('POLYLINE', 'LWPOLYLINE'):
            if self.verbose:
                log_verbose(f"Processing {entity.dxftype()}")
                # Check if it's a closed polygon
                is_closed = hasattr(entity.dxf, 'flags') and (entity.dxf.flags & 1)
                log_verbose(f"  Closed polygon: {is_closed}")
            
            # For 2D entities
            if hasattr(entity, 'has_z') and not entity.has_z:
                if self.verbose:
                    log_verbose(f"  2D {entity.dxftype()} - all points have zero elevation")
                entity_has_zero_elevation = True
                for i, point in enumerate(points):
                    error_point = list(point) + [0.0] if len(point) < 3 else list(point)
                    zero_points.append((i, error_point, 0.0))
            else:
                # Check vertices of 3D polyline
                for i, point in enumerate(points):
                    point_has_zero_z = False
                    z_value = 0.0
                    
                    if len(point) < 3:
                        point_has_zero_z = True
                        z_value = 0.0
                        if self.verbose:
                            log_verbose(f"  Point {i}: 2D point {point} -> Z=0")
                    else:
                        z_value = point[2] if point[2] is not None else 0.0
                        if abs(float(z_value)) <= self.tolerance:
                            point_has_zero_z = True
                            if self.verbose:
                                log_verbose(f"  Point {i}: 3D point {point} -> Z={z_value} (within tolerance)")
                        elif self.verbose:
                            log_verbose(f"  Point {i}: 3D point {point} -> Z={z_value} (OK)")
                    
                    if point_has_zero_z:
                        entity_has_zero_elevation = True
                        error_point = list(point) if len(point) >= 3 else list(point) + [z_value]
                        zero_points.append((i, error_point, z_value))

        # Handle other entities (LINE, POINT, etc.)
        else:
            if self.verbose:
                log_verbose(f"Processing {entity.dxftype()}")
            
            for i, point in enumerate(points):
                point = list(point) if isinstance(point, tuple) else point
                point_has_zero_z = False
                z_value = 0.0
                
                if len(point) < 3:
                    point_has_zero_z = True
                    z_value = 0.0
                    if self.verbose:
                        log_verbose(f"  Point {i}: 2D point {point} -> Z=0")
                else:
                    z_value = point[2] if point[2] is not None else 0.0
                    if abs(float(z_value)) <= self.tolerance:
                        point_has_zero_z = True
                        if self.verbose:
                            log_verbose(f"  Point {i}: 3D point {point} -> Z={z_value} (within tolerance)")
                    elif self.verbose:
                        log_verbose(f"  Point {i}: 3D point {point} -> Z={z_value} (OK)")
                
                if point_has_zero_z:
                    entity_has_zero_elevation = True
                    error_point = point + [z_value] if len(point) < 3 else point
                    zero_points.append((i, error_point, z_value))

        # Mark errors and log
        if entity_has_zero_elevation:
            self.error_count += 1  # Count 1 error per entity, not per point
            
            if self.verbose:
                log_verbose(f"*** FOUND {len(zero_points)} ZERO ELEVATION POINTS in {entity.dxftype()} ***")
                for i, point, z in zero_points:
                    log_verbose(f"  ERROR: Zero/missing elevation at vertex {i}: {point}, Z={z}")
            
            # Calculate centroid of all zero elevation points
            centroid = self._calculate_centroid([point for _, point, _ in zero_points])
            self._mark_error(output_msp, centroid)
        elif self.verbose:
            log_verbose(f"No zero elevation issues found in {entity.dxftype()}")
    def _calculate_centroid(self, points):
        """Calculate centroid of a list of points."""
        if not points:
            return (0.0, 0.0, 0.0)
        
        sum_x = sum(point[0] for point in points)
        sum_y = sum(point[1] for point in points)
        sum_z = sum(point[2] if len(point) > 2 and point[2] is not None else 0.0 for point in points)
        
        count = len(points)
        return (sum_x / count, sum_y / count, sum_z / count)
    
    def _mark_error(self, msp, point):
        """
        Mark the error location with a point marker.
        """
        # Ensure we have a 3D point for marking
        if len(point) < 3:
            mark_point = (point[0], point[1], 0.0)
        else:
            mark_point = (point[0], point[1], point[2] if point[2] is not None else 0.0)
        
        if self.verbose:
            log_verbose(f"    Marking error at: {mark_point}")
        
        # Add error marker point
        msp.add_point(
            mark_point,
            dxfattribs={
                'layer': ERROR_LAYERS.get('ZeroElevation', 'ERROR_ZERO_ELEVATION'), 
                'color': ERROR_COLORS.get('ZeroElevation', 30)
            }
        )