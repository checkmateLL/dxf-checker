# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Proper logging system with configurable levels
- Enhanced error reporting with timestamps

### Changed
- Improved documentation formatting
- Better error messages in verbose mode

### Fixed
- Minor bug fixes in segment distance calculations

## [1.0.6] - 2025-08-03
### Added
- Five core check types:
  - Too Long Segment detection (>50m)
  - Too Short Segment detection (<5cm) 
  - Duplicate Vertices detection
  - Unconnected Crossings detection
  - Z-Anomalous Vertices detection
- Command-line interface with configurable parameters
- DXF output with error markers on separate layers
- Verbose logging option
- Support for multiple DXF entity types (LINE, LWPOLYLINE, POLYLINE, etc.)
- Extended data attachment to error markers
- Configurable thresholds and tolerances

## [1.1.2] - 2025-08-06
### Added
- Proper logging

## [1.1.3] - 2025-08-07
### Fixed
- Minor bug with saving DXF file
- 'float' error when storing coordinates

## [1.1.5] - 2025-08-07
### Fixed
- Fixed issue with auto tags in bumpver

## [1.2.0] - 2025-08-07
### Added
- Added engine for comparing ideal road geometry with existing

## [2.0.0] - 2025-08-14
### Changed
- **Breaking change:** `ZeroElevationCheck` now counts **one error per entity** (instead of per vertex) when zero/missing elevations are found.
- **Breaking change:** Zero/missing elevation markers are now placed **at the centroid** of all offending points for the entity, instead of one marker per offending vertex. Removed automatic circle drawing around each point.
- Expanded HATCH entity handling:
  - In **entity extraction**, now includes HATCH entities inside both modelspace and block definitions.
  - In **point extraction**, supports both `PolylinePath` and `EdgePath` (line edges and arc edges), with proper 3D normalization.
  - In **zero elevation check**, inspects each HATCH point individually, respecting tolerance, and logs detailed diagnostics.
- Enhanced verbose logging throughout entity extraction and zero elevation checks:
  - Entity-type counts for both modelspace and block contents.
  - Detailed HATCH path types and sample points.
  - Closed-polygon detection for polylines.
  - Sample point previews and explicit tolerance reporting.

### Added
- Centroid calculation helper for consolidating zero-elevation point locations into a single marker.
- Summary log of total entities extracted (direct vs from blocks).

### Impact
- **Scripts/tests depending on previous per-vertex error counts or markers will need updating** to handle the new per-entity counting and centroid-based marking.
- HATCH entities within blocks are now processed and may surface additional issues that were previously undetected.

### Type
- **Major** — due to changes in error counting and marker placement behavior that can affect downstream processing.
