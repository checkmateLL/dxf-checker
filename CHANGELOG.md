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
- Initial stable release
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