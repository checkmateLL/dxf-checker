import os
import argparse
import ezdxf #install via pip
from utils import get_3d_points_from_entity, collect_all_linear_entities
from config import ERROR_LAYERS, ERROR_COLORS, DXF_VERSION
from checks.too_long_segment import TooLongSegmentCheck
from checks.too_short_segment import TooShortSegmentCheck
from checks.duplicate_vertices import DuplicateVerticesCheck
from checks.z_anomalous_vertices import ZAnomalousVerticesCheck
from checks.unconnected_crossings import UnconnectedCrossingCheck

def get_enabled_checks(args):
    checks = []

    if 'too_long' in args.checks:
        checks.append(TooLongSegmentCheck(max_distance=args.max_dist, units_scale=args.scale, verbose=args.verbose))
    if 'too_short' in args.checks:
        checks.append(TooShortSegmentCheck(min_distance=args.min_dist, units_scale=args.scale, verbose=args.verbose))
    if 'duplicates' in args.checks:
        checks.append(DuplicateVerticesCheck(verbose=args.verbose))
    if 'z_anomaly' in args.checks:
        checks.append(ZAnomalousVerticesCheck(verbose=args.verbose))
    if 'crossing' in args.checks:
        checks.append(UnconnectedCrossingCheck(verbose=args.verbose))

    return checks

def setup_output_layers(doc):
    for layer in ERROR_LAYERS.values():
        if layer not in doc.layers:
            doc.layers.new(name=layer, dxfattribs={'color': 7})

def main():
    parser = argparse.ArgumentParser(description="DXF Segment Checker")
    parser.add_argument("input", help="Input DXF file path")
    parser.add_argument("-o", "--output", help="Output DXF path (default: <input>_errors.dxf)")
    parser.add_argument("-c", "--checks", nargs="+", default=["too_long", "too_short", "duplicates", "z_anomaly", "crossing"],
                        help="Checks to run: too_long, too_short, duplicates, z_anomaly, crossing")
    parser.add_argument("--max_dist", type=float, default=50.0)
    parser.add_argument("--min_dist", type=float, default=0.01)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"File not found: {args.input}")
        return

    output_path = args.output or f"{os.path.splitext(args.input)[0]}_errors.dxf"

    print(f"Input DXF: {args.input}")
    print(f"Output DXF: {output_path}")
    print(f"Checks enabled: {args.checks}")

    input_doc = ezdxf.readfile(args.input)
    output_doc = ezdxf.new(DXF_VERSION)
    output_msp = output_doc.modelspace()
    setup_output_layers(output_doc)

    entities = collect_all_linear_entities(input_doc)
    print(f"Found {len(entities)} linear entities")

    checks = get_enabled_checks(args)

    for entity in entities:
        points = get_3d_points_from_entity(entity)
        if len(points) < 2:
            continue
        for check in checks:
            check.run(entity, points, output_msp)

    # finalize() for those that need post-processing
    for check in checks:
        if hasattr(check, "finalize"):
            check.finalize(output_msp)

    output_doc.saveas(output_path)
    print(f"Saved output to: {output_path}")

    # Summary
    print("\n=== Check Summary ===")
    for check in checks:
        print(f"{check.name}: {check.error_count} issue(s)")

if __name__ == "__main__":
    main()
