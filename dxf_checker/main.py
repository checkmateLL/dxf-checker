import argparse
import os
import sys
import time
from pathlib import Path

import ezdxf

from dxf_checker import config
from dxf_checker.logger import log, log_verbose, setup_logging
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
        print(f"❌ Input file does not exist: {args.input_file}")
        sys.exit(1)

    setup_logging(verbose=args.verbose)

    log(f"Input DXF: {args.input_file}")
    log(f"Checks enabled: {args.checks}")

    try:
        doc = ezdxf.readfile(args.input_file)
    except IOError as e:
        log(f"❌ Failed to read DXF file: {e}", level="ERROR")
        sys.exit(1)

    msp = doc.modelspace()
    entities = list(msp.query("LINE LWPOLYLINE POLYLINE SPLINE 3DPOLYLINE"))
    log(f"Found {len(entities)} linear entities")

    # Load and run selected checks
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
        check.run(entities, doc)
        error_count += check.get_error_count()

    # Output file
    output_path = args.output or get_output_path(args.input_file)
    doc.saveas(output_path)
    log(f"✅ Saved output to: {output_path}")

    # Summary
    log("\n=== Check Summary ===")
    for check in checks:
        log(f"{check.__class__.__name__}: {check.get_error_count()} issue(s)")

    if error_count == 0:
        log("🎉 No issues detected.")
    else:
        log(f"⚠️ Total issues: {error_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())