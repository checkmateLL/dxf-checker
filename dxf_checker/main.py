import argparse
import os
import sys
from pathlib import Path

import ezdxf
from ezdxf import new

from dxf_checker import config
from dxf_checker.logger import log, setup_logging
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
    # 5. Summary
    # ------------------------------------------------------------------
    log("\n=== Check Summary ===")
    for check in checks:
        log(f"{check.__class__.__name__}: {check.get_error_count()} issue(s)")

    if error_count == 0:
        log("No issues detected.")
    else:
        log(f"Total issues: {error_count}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())