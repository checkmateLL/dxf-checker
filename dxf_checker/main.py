import argparse
import os
import sys
import csv
from datetime import datetime
from pathlib import Path

import ezdxf
from ezdxf import new

from dxf_checker import config
from dxf_checker.logger import log, setup_logging, LOG_DIR
from dxf_checker.utils import load_checks, get_output_path
from dxf_checker.logger import log_verbose

from dxf_checker.checks.road_geometry_validator import (
    DXFReader,
    GeometryIdealizer,
    ComparisonEngine,
    GeometricConstraints,
    ValidationReport,
)


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
    return parser.parse_args()


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

    msp = input_doc.modelspace()
    entities = list(msp.query("LINE LWPOLYLINE POLYLINE SPLINE 3DPOLYLINE"))
    log(f"Found {len(entities)} linear entities")

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
    # 3. Load and run checks
    # ------------------------------------------------------------------
    check_params = {
        'verbose': args.verbose,
        'max_distance': args.max_dist,
        'min_distance': args.min_dist,
        'units_scale': args.scale
    }

    checks = load_checks(args.checks, check_params)
    error_count = 0

    for check in checks:
        log(f"Running {check.__class__.__name__}...")
        try:
            for entity in entities:
                points = []
                try:
                    if entity.dxftype() == 'LINE':
                        points = [entity.dxf.start.xyz, entity.dxf.end.xyz]
                    elif entity.dxftype() == 'LWPOLYLINE':
                        points = [vertex.xyz for vertex in entity.vertices()]
                    elif entity.dxftype() in ['POLYLINE', '3DPOLYLINE']:
                        points = [vertex.dxf.location.xyz for vertex in entity.vertices]
                    elif entity.dxftype() == 'SPLINE':
                        points = [point.xyz for point in entity.control_points]
                except Exception as e:
                    if args.verbose:
                        log(f"Skipping entity {entity.dxftype()}: {e}", level="WARNING")
                    continue

                if points:
                    check.run(entity, points, output_msp)

            # Handle any finalize() logic (e.g., UnconnectedCrossingCheck)
            if hasattr(check, 'finalize'):
                check.finalize(output_msp)

            error_count += check.get_error_count()

        except Exception as e:
            log(f"Check {check.__class__.__name__} failed: {e}", level="ERROR")
            if args.verbose:
                import traceback
                traceback.print_exc()

    # ------------------------------------------------------------------
    # 4. Save only the error markers
    # ------------------------------------------------------------------
    output_path = args.output or get_output_path(args.input_file)
    try:
        output_doc.saveas(output_path)
        log(f"Saved error markers only to: {output_path}")
    except Exception as e:
        log(f"Failed to save output file: {e}", level="ERROR")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 5. Optional Road Geometry Validation
    # ------------------------------------------------------------------
    if "road_geom" in args.checks:
        log("\n=== Road Geometry Validation ===")
        reader = DXFReader()
        lines = reader.load_dxf(args.input_file)

        constraints = GeometricConstraints()
        idealizer = GeometryIdealizer(constraints)
        engine = ComparisonEngine()

        total_issues = 0
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Generate timestamp
        csv_path = LOG_DIR / f"road_geom_validation_{timestamp}.csv"  # Unique CSV file per run
        error_dxf_path = LOG_DIR / f"road_geom_errors_{timestamp}.dxf"  # Separate DXF for errors

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["handle", "vertex_index", "orig_x", "orig_y", "orig_z",
                            "ideal_x", "ideal_y", "ideal_z",
                            "horizontal_error", "elevation_error"])

            error_doc = new(config.DXF_VERSION)  # Create new DXF document for errors
            error_msp = error_doc.modelspace()

            for line in lines:
                ideal = idealizer.idealize(line)
                report = engine.compare(line, ideal)
                summary = report.summary()

                max_h = summary["max_horizontal"]
                max_z = summary["max_elevation"]
                cnt = summary["count"]
                total_issues += cnt

                handle = line.meta.get("handle", "?")
                log(f"  {handle}  h-dev={max_h:.3f}m  z-dev={max_z:.3f}m  issues={cnt}")

                for deviation in report.deviations:
                    writer.writerow([
                        handle,
                        deviation.vertex_index,
                        *deviation.original,
                        *deviation.ideal,
                        deviation.horizontal_error,
                        deviation.elevation_error,
                    ])

                    # Add error markers to the error DXF
                    error_layer = "ERROR_ROAD_GEOM"
                    if error_layer not in error_doc.layers:
                        error_doc.layers.new(name=error_layer, dxfattribs={'color': 7})
                    error_msp.add_point(deviation.original, dxfattribs={'layer': error_layer})

                    # Add idealized geometry to the error DXF
                    ideal_layer = "IDEAL_ROAD_GEOM"
                    if ideal_layer not in error_doc.layers:
                        error_doc.layers.new(name=ideal_layer, dxfattribs={'color': 2})
                    error_msp.add_polyline3d([v for v in ideal.vertices], dxfattribs={'layer': ideal_layer})

        log(f"Road geometry validation complete. Total issues: {total_issues}")
        log(f"Validation results saved to: {csv_path}")

        # Save the error DXF file
        try:
            error_doc.saveas(error_dxf_path)
            log(f"Saved error markers and idealized geometry to: {error_dxf_path}")
        except Exception as e:
            log(f"Failed to save error DXF file: {e}", level="ERROR")
            sys.exit(1)
    
    # ------------------------------------------------------------------
    # 6. Summary
    # ------------------------------------------------------------------
    log("\n=== Check Summary ===")
    for check in checks:
        log(f"{check.__class__.__name__}: {check.get_error_count()} issue(s)")

    if "road_geom" in args.checks and total_issues == 0:
        log("No road geometry issues detected.")

    classic_total = sum(c.get_error_count() for c in checks)
    combined_total = classic_total + (total_issues if "road_geom" in args.checks else 0)

    if combined_total == 0:
        log("No issues detected at all.")
    else:
        log(f"Total issues (classic + road): {combined_total}")


if __name__ == "__main__":
    import sys
    sys.exit(main())