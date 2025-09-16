import argparse
import os
from pathlib import Path
import ezdxf
from ezdxf import new
from ezdxf.math import Matrix44

from dxf_checker import config
from dxf_checker.logger import DXFLogger
from dxf_checker.utils import load_checks, get_output_path

def parse_args():
    parser = argparse.ArgumentParser(
        description="DXF Checker: Detects geometric and topological issues in DXF files."
    )
    parser.add_argument(
        "input_file", help="Path to the input DXF file", type=Path
    )
    parser.add_argument(
        "-c", "--checks", nargs="+", required=True,
        help="List of checks to run. Example: -c too_short too_long"
    )
    parser.add_argument(
        "--cleanup-logs", action="store_true", 
        help="Manually clean up log files older than 1 week"
    )
    parser.add_argument(
        "-o", "--output", help="Optional path for output DXF file"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Save detailed report"
    )
    parser.add_argument(
        "--max_dist", type=float, default=config.THRESHOLDS["too_long_segment"], help="Max segment length for too_long check (meters)"
    )
    parser.add_argument(
        "--min_dist", type=float, default=config.THRESHOLDS["too_short_segment"], help="Min segment length for too_short check (meters)"
    )
    parser.add_argument(
        "--scale", type=float, default=1.0, help="Scale factor for measurements"
    )
    parser.add_argument(
        "--dup_tolerance", type=float, default=config.THRESHOLDS["vertex_duplicate_tol"], 
        help="Tolerance for duplicate vertex detection (meters)"
    )
    parser.add_argument(
        "--zero_tolerance", type=float, default=1e-6, 
        help="Tolerance for considering elevation as zero (meters)"
    )    
    return parser.parse_args()


def extract_entities_from_doc(doc, logger):
    """
    Extract all linear entities from the document, including those inside block definitions.
    Returns a list of (entity, transform_matrix) tuples.
    """
    entities_with_transforms = []
    msp = doc.modelspace()
    
    # First, get direct entities from modelspace
    # FIXED: Adding HATCH to catch polygon boundaries
    direct_entities = list(msp.query("LINE LWPOLYLINE POLYLINE SPLINE 3DPOLYLINE POINT HATCH"))
    
    # Debug logging
    entity_types = {}
    for entity in direct_entities:
        dxftype = entity.dxftype()
        if dxftype == 'HATCH':
            logger.log_verbose(f"Found HATCH in modelspace with {len(entity.paths)} boundary paths")
        entity_types[dxftype] = entity_types.get(dxftype, 0) + 1
    
    logger.log("Entity types found in modelspace:")
    for etype, count in entity_types.items():
        logger.log(f"  {etype}: {count}")
    
    for entity in direct_entities:
        entities_with_transforms.append((entity, Matrix44()))  # Identity matrix for direct entities
    
    # Then, handle INSERT entities (block references)
    insert_entities = list(msp.query("INSERT"))
    logger.log(f"Found {len(insert_entities)} INSERT entities (block references)")
    
    block_entity_types = {}
    total_block_entities = 0
    
    for insert in insert_entities:
        try:
            # Get the block definition
            block = doc.blocks[insert.dxf.name]
            
            # Create transformation matrix for this insert
            transform = Matrix44.chain(
                Matrix44.scale(insert.dxf.xscale, insert.dxf.yscale, insert.dxf.zscale),
                Matrix44.z_rotate(insert.dxf.rotation),
                Matrix44.translate(insert.dxf.insert.x, insert.dxf.insert.y, insert.dxf.insert.z)
            )
            
            # FIXED: Get entities from the block INCLUDING HATCH
            block_entities = list(block.query("LINE LWPOLYLINE POLYLINE SPLINE 3DPOLYLINE POINT HATCH"))
            total_block_entities += len(block_entities)
            
            # Debug: count block entity types
            for entity in block_entities:
                dxftype = entity.dxftype()
                if dxftype == 'HATCH':
                    logger.log_verbose(f"Found HATCH in block '{insert.dxf.name}' with {len(entity.paths)} boundary paths")
                block_entity_types[dxftype] = block_entity_types.get(dxftype, 0) + 1
            
            for entity in block_entities:
                entities_with_transforms.append((entity, transform))
                
        except KeyError:
            logger.log(f"Warning: Block '{insert.dxf.name}' not found", level="WARNING")
        except Exception as e:
            logger.log(f"Warning: Error processing INSERT entity: {e}", level="WARNING")
    
    if block_entity_types:
        logger.log("Entity types found in blocks:")
        for etype, count in block_entity_types.items():
            logger.log(f"  {etype}: {count}")
    
    logger.log(f"Total entities extracted: {len(entities_with_transforms)} (direct: {len(direct_entities)}, from blocks: {total_block_entities})")
    
    return entities_with_transforms


def transform_points(points, transform_matrix):
    """Transform a list of points using the given transformation matrix."""
    # Check if it's an identity matrix by comparing to identity
    if transform_matrix == Matrix44():
        return points
    
    transformed_points = []
    for point in points:
        if len(point) == 2:
            # 2D point, add Z=0
            point_3d = (point[0], point[1], 0.0)
        else:
            point_3d = point
        
        # Apply transformation
        transformed = transform_matrix.transform(point_3d)
        transformed_points.append((transformed.x, transformed.y, transformed.z))
    
    return transformed_points


def extract_points_from_entity(entity, logger, verbose=False):
    """
    Extract points from various entity types.
    
    Args:
        entity: The DXF entity to extract points from
        verbose: Enable verbose logging (default: False)
    """
    points = []
    try:
        dxftype = entity.dxftype()
        if dxftype == 'LINE':
            points = [entity.dxf.start.xyz, entity.dxf.end.xyz]
        elif dxftype == 'LWPOLYLINE':            
            vertices_2d = list(entity.get_points("xy"))           
            elevation = getattr(entity.dxf, 'elevation', 0.0)
            points = [(v[0], v[1], elevation) for v in vertices_2d]
        elif dxftype in ['POLYLINE', '3DPOLYLINE']:
            points = [vertex.dxf.location.xyz for vertex in entity.vertices]
        elif dxftype == 'SPLINE':
            points = [point.xyz for point in entity.control_points]
        elif dxftype == 'POINT':
            points = [entity.dxf.location.xyz]
        elif dxftype == 'HATCH':
            # Extract points from hatch boundaries with proper ezdxf API
            if verbose:
                logger.log_verbose(f"Processing HATCH with {len(entity.paths)} paths")
            
            for path_idx, path in enumerate(entity.paths):
                path_type = path.__class__.__name__
                if verbose:
                    logger.log_verbose(f"  Path {path_idx}: type={path_type}")
                
                if path_type == 'PolylinePath':
                    path_points = []
                    for vertex in path.vertices:
                        # Handle different vertex formats
                        if len(vertex) >= 3:
                            path_points.append((vertex[0], vertex[1], vertex[2]))
                        elif len(vertex) >= 2:
                            path_points.append((vertex[0], vertex[1], 0.0))  # Assume Z=0 for 2D
                        else:
                            if verbose:
                                logger.log_verbose(f"    Warning: vertex has insufficient coordinates: {vertex}")
                    
                    points.extend(path_points)
                    if verbose:
                        logger.log_verbose(f"    Added {len(path_points)} points from PolylinePath")
                
                elif path_type == 'EdgePath':
                    # Handle edge paths (lines, arcs, etc.)
                    for edge in path.edges:
                        edge_type = edge.__class__.__name__
                        if edge_type == 'LineEdge':
                            # Add start and end points of line edges
                            start = edge.start if len(edge.start) >= 3 else (edge.start[0], edge.start[1], 0.0)
                            end = edge.end if len(edge.end) >= 3 else (edge.end[0], edge.end[1], 0.0)
                            points.extend([start, end])
                            if verbose:
                                logger.log_verbose(f"    Added 2 points from LineEdge")
                        elif edge_type == 'ArcEdge':
                            # For arcs, add center and start/end points
                            center = edge.center if len(edge.center) >= 3 else (edge.center[0], edge.center[1], 0.0)
                            points.append(center)
                            if verbose:
                                logger.log_verbose(f"    Added 1 point from ArcEdge center")
        
        if points and verbose:
            logger.log_verbose(f"Extracted {len(points)} points from {dxftype}")
            # Show first few points for debugging
            for i, point in enumerate(points[:3]):
                logger.log_verbose(f"  Point {i}: {point}")
            if len(points) > 3:
                logger.log_verbose(f"  ... and {len(points) - 3} more points")
            
    except Exception as e:
        logger.log(f"Error extracting points from {entity.dxftype()}: {e}", level="WARNING")
        if verbose:
            import traceback
            traceback.print_exc()
    
    return points


def main(cli_args=None):
    args = parse_args() if cli_args is None else cli_args

    logger = DXFLogger(verbose=args.verbose)

    if not args.input_file.exists():
        logger.log(f"Input file does not exist: {args.input_file}", level="ERROR")
        raise SystemExit(1)    

    logger.log(f"Input DXF: {args.input_file}")
    logger.log(f"Checks enabled: {args.checks}")

    # ------------------------------------------------------------------
    # 1. Read input DXF
    # ------------------------------------------------------------------
    try:
        input_doc = ezdxf.readfile(args.input_file)
    except IOError as e:
        logger.log(f"Failed to read DXF file: {e}", level="ERROR")
        raise SystemExit(1)

    # Extract all entities (including from blocks)
    entities_with_transforms = extract_entities_from_doc(input_doc, logger)
    logger.log(f"Found {len(entities_with_transforms)} linear entities (including from blocks)")

    # ------------------------------------------------------------------
    # 2. Create clean output DXF for error markers only
    # ------------------------------------------------------------------
    output_doc = new(config.DXF_VERSION)
    output_msp = output_doc.modelspace()

    # Ensure all required error layers exist
    for layer in config.ERROR_LAYERS.values():
        if layer not in output_doc.layers:
            output_doc.layers.new(name=layer, dxfattribs={'color': 7})

    # ------------------------------------------------------------------
    # 3. Load and run standard checks
    # ------------------------------------------------------------------
    standard_checks = args.checks
    total_issues = 0
    
    if standard_checks:
        check_params = {
            'verbose': args.verbose,
            'max_distance': args.max_dist,
            'min_distance': args.min_dist,
            'units_scale': args.scale,
            'zero_tolerance': args.zero_tolerance,
            'vertex_duplicate_tolerance': args.dup_tolerance,
            'logger': logger
        }

        checks = load_checks(standard_checks, check_params, logger)
        error_count = 0

        for check in checks:
            logger.log(f"Running {check.__class__.__name__}...")
            try:
                for entity, transform in entities_with_transforms:
                    points = extract_points_from_entity(entity, logger, verbose=args.verbose)
                    
                    if points:
                        # Transform points if needed
                        transformed_points = transform_points(points, transform)
                        check.run(entity, transformed_points, output_msp)

                # Handle any finalize() logic (e.g., UnconnectedCrossingCheck)
                if hasattr(check, 'finalize'):
                    check.finalize(output_msp)

                error_count += check.get_error_count()

            except Exception as e:
                logger.log(f"Check {check.__class__.__name__} failed: {e}", level="ERROR")
                if args.verbose:
                    import traceback
                    traceback.print_exc()

        total_issues += error_count
    
    # ------------------------------------------------------------------
    # 5. Save standard error markers
    # ------------------------------------------------------------------
    if standard_checks:
        output_path = args.output or get_output_path(args.input_file)
        try:
            output_doc.saveas(output_path)
            logger.log(f"Saved standard error markers to: {output_path}")
        except Exception as e:
            logger.log(f"Failed to save output file: {e}", level="ERROR")
            raise SystemExit(1)

    # ------------------------------------------------------------------
    # 6. Summary
    # ------------------------------------------------------------------
    logger.log("\n=== Check Summary ===")
    if standard_checks:
        for check in checks:
            logger.log(f"{check.__class__.__name__}: {check.get_error_count()} issue(s)")
    
    if total_issues == 0:
        logger.log("No issues detected.")
    else:
        logger.log(f"Total issues found: {total_issues}")

    logger.cleanup()

if __name__ == "__main__":
    main()