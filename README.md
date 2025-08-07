# DXF Checker

A Python tool for validating DXF segment integrity and detecting geometry issues in CAD files.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)
[![Version](https://img.shields.io/badge/version-1.1.5-green.svg)](https://github.com/checkmatell/dxf-checker)

## Overview

DXF Checker is a command-line tool designed for engineers, architects, and CAD/GIS professionals who need to validate the geometric integrity of DXF (Drawing Exchange Format) files. It automatically detects common issues that can cause problems in manufacturing, construction, or further CAD processing.

## Features

### **Five Core Validation Checks**

| Check Type | Description | Default Threshold |
|------------|-------------|-------------------|
| **Too Long Segments** | Detects segments longer than specified length | > 50m |
| **Too Short Segments** | Finds segments shorter than minimum length | < 5cm |
| **Duplicate Vertices** | Identifies repeated or nearly identical points | < 0.05m apart |
| **Unconnected Crossings** | Finds lines that cross but don't share vertices | 2D intersection analysis |
| **Z-Anomalous Vertices** | Detects elevation outliers in 3D data | > 4cm deviation |

###  **Output Capabilities**
- **Error Visualization**: Outputs DXF file with error markers on separate layers
- **Detailed Logging**: Optional verbose reports with coordinates and measurements
- **Extended Data**: Error markers include metadata for further analysis
- **Configurable Thresholds**: Customize validation parameters for specific needs

## Installation

### Requirements
- Python 3.8 or higher
- `ezdxf` library (automatically installed)

### Install from PyPI (Coming Soon)
```bash
pip install dxf-checker
```

### Install from Source
```bash
git clone https://github.com/checkmatell/dxf-checker.git
cd dxf-checker
pip install -r requirements.txt
pip install -e .
```

## Quick Start

### Basic Usage
```bash
# Run all checks on a DXF file
python -m dxf_checker input.dxf -c too_long too_short duplicates crossing z_anomaly

# Run specific checks with verbose output
python -m dxf_checker drawing.dxf -c too_short crossing --verbose

# Custom output file
python -m dxf_checker input.dxf -c too_long -o custom_errors.dxf
```

### Using as Installed Package
```bash
# After installation via pip
dxf-checker input.dxf -c too_long too_short duplicates crossing z_anomaly
```

## Command Line Reference

### Required Arguments
- `input_file` - Path to the input DXF file to validate

### Check Types (`-c, --checks`)
| Flag | Check | Description |
|------|-------|-------------|
| `too_long` | Too Long Segments | Segments exceeding maximum length |
| `too_short` | Too Short Segments | Segments below minimum length |
| `duplicates` | Duplicate Vertices | Repeated points on same entity |
| `crossing` | Unconnected Crossings | Lines crossing without shared vertices |
| `z_anomaly` | Z-Anomalous Vertices | Elevation deviations from local trend |

### Optional Parameters

#### Output Control
```bash
-o, --output FILE          # Custom output file path (default: inputname_errors.dxf)
-v, --verbose             # Enable detailed console output and reporting
```

#### Threshold Customization
```bash
--max_dist METERS         # Maximum segment length (default: 50.0)
--min_dist METERS         # Minimum segment length (default: 0.05)
--scale FACTOR           # Scale factor for measurements (default: 1.0)
```

## Examples

### 1. Quality Control for Manufacturing
```bash
# Check for segments that might cause machining issues
dxf-checker part_drawing.dxf -c too_short too_long --min_dist 0.01 --max_dist 1000
```

### 2. Architectural Drawing Validation
```bash
# Check with detailed reporting
dxf-checker floor_plan.dxf -c too_short duplicates crossing z_anomaly --verbose
```

### 3. Survey Data Validation
```bash
# Focus on elevation issues and crossing problems
dxf-checker survey.dxf -c z_anomaly crossing --verbose -o survey_issues.dxf
```

### 4. Batch Processing Script
```bash
#!/bin/bash
for file in *.dxf; do
    echo "Processing $file..."
    dxf-checker "$file" -c too_long too_short duplicates crossing z_anomaly
done
```

## Understanding Output

### Error Layers
The output DXF file contains error markers organized on separate layers:

| Layer Name | Check Type | Color | Marker Type |
|------------|------------|-------|-------------|
| `ERROR_TOO_LONG` | Too Long Segments | Red (1) | Point at segment midpoint |
| `ERROR_SHORT_SEGMENTS` | Too Short Segments | Yellow (2) | Point at segment midpoint |
| `ERROR_DUPLICATE_VERTS` | Duplicate Vertices | Green (3) | Point at duplicate location |
| `ERROR_Z_ANOMALY` | Z-Anomalous Vertices | Magenta (6) | Point at anomalous vertex |
| `ERROR_UNCONNECTED_CROSSINGS` | Unconnected Crossings | Blue (5) | Point at intersection |

### Extended Data
Error markers include extended data with:
- Unique error ID
- Description of the issue
- Relevant measurements (distances, deviations)
- Coordinate information

### Console Output
```
[INFO] Input DXF: example.dxf
[INFO] Checks enabled: ['too_short', 'crossing']
[INFO] Found 1247 linear entities
[INFO] Running TooShortSegmentCheck...
[INFO] Running UnconnectedCrossingCheck...
[INFO] Saved error markers only to: example_errors.dxf

=== Check Summary ===
TooShortSegmentCheck: 3 issue(s)
UnconnectedCrossingCheck: 1 issue(s)
Total issues: 4
```

## Supported DXF Entities

The tool analyzes these DXF entity types:
- **LINE** - Simple line segments
- **LWPOLYLINE** - Lightweight polylines
- **POLYLINE** - Standard polylines
- **3DPOLYLINE** - 3D polylines
- **SPLINE** - Spline curves (analyzed via control points)

## Configuration and Customization

### Default Thresholds
- **Too Long Segment**: 50.0 meters
- **Too Short Segment**: 0.05 meters (5cm)
- **Z Anomaly Deviation**: 0.04 meters (4cm)
- **Vertex Duplicate Tolerance**: 0.0001 meters
- **Crossing Proximity Tolerance**: 0.01 meters

## Troubleshooting

### Common Issues

#### "Failed to read DXF file"
- Ensure the file exists and is a valid DXF format
- Check file permissions
- Try opening the file in a CAD application first

#### "No issues detected" when you expect problems
- Verify you're using the correct check types
- Adjust thresholds using `--max_dist`, `--min_dist` parameters
- Use `--verbose` to see detailed processing information

#### High memory usage on large files
- Process files in smaller sections if possible
- Close other applications to free memory
- Consider the file size and available system RAM

#### Unexpected results in coordinate systems
- Use the `--scale` parameter if your DXF uses non-standard units
- Check if your DXF file uses consistent coordinate systems

### Getting Help
```bash
# Show all available options
dxf-checker --help

# Show version information
python -c "from dxf_checker import __version__; print(__version__)"
```

## Development and Contributing

### Development Setup
```bash
git clone https://github.com/checkmatell/dxf-checker.git
cd dxf-checker
pip install -e .[dev]
pre-commit install
```


### Code Quality
```bash
# Formatting
black dxf_checker/
isort dxf_checker/

# Linting
flake8 dxf_checker/
mypy dxf_checker/
```

## License

Use or redistribution **requires explicit written permission**.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## Support and Issues

- **Bug Reports**: [GitHub Issues](https://github.com/checkmatell/dxf-checker/issues)
- **Feature Requests**: [GitHub Issues](https://github.com/checkmatell/dxf-checker/issues)
- **Documentation**: [GitHub Repository](https://github.com/checkmatell/dxf-checker)

## Acknowledgments

- Built with [ezdxf](https://github.com/mozman/ezdxf) - Excellent DXF library for Python
- Inspired by the need for automated CAD file validation in engineering workflows

---