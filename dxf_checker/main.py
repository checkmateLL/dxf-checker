import argparse
import os
import sys
import csv
from datetime import datetime
from pathlib import Path

import ezdxf
from ezdxf import new
from ezdxf.math import Matrix44

from dxf_checker import config
from dxf_checker.logger import log, setup_logging, LOG_DIR
from dxf_checker.utils import load_checks, get_output_path
from dxf_checker.logger import log_verbose


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
        "-o", "--output", help="Optional path for output DXF file"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Save detailed report"
    )
    parser.add_argument(
        "--max_dist", type=float, default=50.0, help="Max segment length for too_long check (meters)"
    )
    parser.add_argument(
        "--min_dist", type=float, default=0.05, help="Min segment length for too_short check (meters)"
    )
    parser.add_argument(
        "--scale", type=float, default=1.0, help="Scale factor for measurements"
    )
    parser.add_argument(
        "--zero_tolerance", type=float, default=1e-6, 
        help="Tolerance for considering elevation as zero (meters)"
    )    
    return parser.parse_args()


def extract_entities_from_doc(doc):
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
            log_verbose(f"Found HATCH in modelspace with {len(entity.paths)} boundary paths")
        entity_types[dxftype] = entity_types.get(dxftype, 0) + 1
    
    log("Entity types found in modelspace:")
    for etype, count in entity_types.items():
        log(f"  {etype}: {count}")
    
    for entity in direct_entities:
        entities_with_transforms.append((entity, Matrix44()))  # Identity matrix for direct entities
    
    # Then, handle INSERT entities (block references)
    insert_entities = list(msp.query("INSERT"))
    log(f"Found {len(insert_entities)} INSERT entities (block references)")
    
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
                    log_verbose(f"Found HATCH in block '{insert.dxf.name}' with {len(entity.paths)} boundary paths")
                block_entity_types[dxftype] = block_entity_types.get(dxftype, 0) + 1
            
            for entity in block_entities:
                entities_with_transforms.append((entity, transform))
                
        except KeyError:
            log(f"Warning: Block '{insert.dxf.name}' not found", level="WARNING")
        except Exception as e:
            log(f"Warning: Error processing INSERT entity: {e}", level="WARNING")
    
    if block_entity_types:
        log("Entity types found in blocks:")
        for etype, count in block_entity_types.items():
            log(f"  {etype}: {count}")
    
    log(f"Total entities extracted: {len(entities_with_transforms)} (direct: {len(direct_entities)}, from blocks: {total_block_entities})")
    
    return entities_with_transforms


def transform_points(points, transform_matrix):
    """Transform a list of points using the given transformation matrix."""
    # Check if it's an identity matrix by comparing to identity
    identity = Matrix44()
    is_identity = transform_matrix == identity
    
    if is_identity:
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


def extract_points_from_entity(entity, verbose=False):
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
            points = [vertex.xyz for vertex in entity.vertices()]
        elif dxftype in ['POLYLINE', '3DPOLYLINE']:
            points = [vertex.dxf.location.xyz for vertex in entity.vertices]
        elif dxftype == 'SPLINE':
            points = [point.xyz for point in entity.control_points]
        elif dxftype == 'POINT':
            points = [entity.dxf.location.xyz]
        elif dxftype == 'HATCH':
            # Extract points from hatch boundaries with proper ezdxf API
            if verbose:
                log_verbose(f"Processing HATCH with {len(entity.paths)} paths")
            
            for path_idx, path in enumerate(entity.paths):
                path_type = path.__class__.__name__
                if verbose:
                    log_verbose(f"  Path {path_idx}: type={path_type}")
                
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
                                log_verbose(f"    Warning: vertex has insufficient coordinates: {vertex}")
                    
                    points.extend(path_points)
                    if verbose:
                        log_verbose(f"    Added {len(path_points)} points from PolylinePath")
                
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
                                log_verbose(f"    Added 2 points from LineEdge")
                        elif edge_type == 'ArcEdge':
                            # For arcs, add center and start/end points
                            center = edge.center if len(edge.center) >= 3 else (edge.center[0], edge.center[1], 0.0)
                            points.append(center)
                            if verbose:
                                log_verbose(f"    Added 1 point from ArcEdge center")
        
        if points and verbose:
            log_verbose(f"Extracted {len(points)} points from {dxftype}")
            # Show first few points for debugging
            for i, point in enumerate(points[:3]):
                log_verbose(f"  Point {i}: {point}")
            if len(points) > 3:
                log_verbose(f"  ... and {len(points) - 3} more points")
            
    except Exception as e:
        log(f"Error extracting points from {entity.dxftype()}: {e}", level="WARNING")
        if verbose:
            import traceback
            traceback.print_exc()
    
    return points


def main(cli_args=None):
    args = parse_args() if cli_args is None else cli_args

    if not args.input_file.exists():
        log(f"Input file does not exist: {args.input_file}", level="ERROR")
        sys.exit(1)

    setup_logging(verbose=args.verbose)

    log(f"Input DXF: {args.input_file}")
    log(f"Checks enabled: {args.checks}")

    # ------------------------------------------------------------------
    # 1. Read input DXF
    # ------------------------------------------------------------------
    try:
        input_doc = ezdxf.readfile(args.input_file)
    except IOError as e:
        log(f"Failed to read DXF file: {e}", level="ERROR")
        sys.exit(1)

    # Extract all entities (including from blocks)
    entities_with_transforms = extract_entities_from_doc(input_doc)
    log(f"Found {len(entities_with_transforms)} linear entities (including from blocks)")

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
    # 3. Load and run standard checks (excluding road_geom)
    # ------------------------------------------------------------------
    standard_checks = [check for check in args.checks if check != "road_geom"]
    total_issues = 0
    
    if standard_checks:
        check_params = {
            'verbose': args.verbose,
            'max_distance': args.max_dist,
            'min_distance': args.min_dist,
            'units_scale': args.scale,
            'zero_tolerance': args.zero_tolerance
        }

        checks = load_checks(standard_checks, check_params)
        error_count = 0

        for check in checks:
            log(f"Running {check.__class__.__name__}...")
            try:
                for entity, transform in entities_with_transforms:
                    points = extract_points_from_entity(entity, verbose=args.verbose)
                    
                    if points:
                        # Transform points if needed
                        transformed_points = transform_points(points, transform)
                        check.run(entity, transformed_points, output_msp)

                # Handle any finalize() logic (e.g., UnconnectedCrossingCheck)
                if hasattr(check, 'finalize'):
                    check.finalize(output_msp)

                error_count += check.get_error_count()

            except Exception as e:
                log(f"Check {check.__class__.__name__} failed: {e}", level="ERROR")
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
            log(f"Saved standard error markers to: {output_path}")
        except Exception as e:
            log(f"Failed to save output file: {e}", level="ERROR")
            sys.exit(1)

    # ------------------------------------------------------------------
    # 6. Summary
    # ------------------------------------------------------------------
    log("\n=== Check Summary ===")
    if standard_checks:
        for check in checks:
            log(f"{check.__class__.__name__}: {check.get_error_count()} issue(s)")
    
    if total_issues == 0:
        log("No issues detected.")
    else:
        log(f"Total issues found: {total_issues}")


if __name__ == "__main__":
    import sys
    sys.exit(main())