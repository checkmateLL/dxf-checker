DXF Segment Checker
===================

Checks available:
-----------------
- Too Long Segment       : segments > 50 m
- Too Short Segment      : segments < 5 cm
- Duplicate Vertices     : repeated or near-repeated vertices on same line
- Unconnected Crossings  : lines that cross in 2D but don't share a vertex
- Z Anomalous Vertices   : vertex elevation deviates from local trend

Too Long Segment	-c too_long
Too Short Segment	-c too_short
Duplicate Vertices	-c duplicates
Z-Anomalous Vertices	-c z_anomaly
Unconnected Crossing	-c crossing


Usage:
------
Run from the command line like this:

    python main.py <input_file.dxf> [options]

Examples:
---------
Run all checks with verbose output (detailed console output):

    python main.py script_check.dxf -c too_long too_short duplicates crossing z_anomaly --verbose

Run specific checks and output to a custom file:

    python main.py input.dxf -c too_short crossing -o flagged_output.dxf

Options:
--------
    -c, --checks      List of checks to run (see list above)
    -o, --output      Output file path (default: inputname_errors.dxf)
    -v, --verbose     Enable detailed logging
    --max_dist        Max segment length (for too_long)
    --min_dist        Min segment length (for too_short)
    --scale           Scale factor (default: 1.0)

Requirements:
-------------
- Python 3.8+
- ezdxf

Install dependencies:

    pip install -r requirements.txt

Output:
-------
- The output DXF file will contain error markers on separate layers:
  ERROR_TOO_LONG, ERROR_SHORT_SEGMENTS, ERROR_DUPLICATE_VERTS, etc.

