# Layer names for each error type
ERROR_LAYERS = {
    "TooLongSegment": "ERROR_TOO_LONG",
    "TooShortSegment": "ERROR_SHORT_SEGMENTS",
    "DuplicateVertices": "ERROR_DUPLICATE_VERTS",
    "ZAnomalousVertices": "ERROR_Z_ANOMALY",
    "UnconnectedCrossing": "ERROR_UNCONNECTED_CROSSINGS",
    "ZeroElevation": "ERROR_ZERO_ELEVATION"
}


# DXF colors for each error type
ERROR_COLORS = {
    "TooLongSegment": 1,          # Red
    "TooShortSegment": 2,         # Yellow
    "DuplicateVertices": 3,       # Green
    "ZAnomalousVertices": 6,      # Magenta
    "UnconnectedCrossing": 5,      # Blue
    "ZeroElevation": 30
    
}

# Default thresholds
THRESHOLDS = {
    "too_long_segment": 50.0,     # in meters
    "too_short_segment": 0.01,    # in meters
    "z_anomaly_deviation": 0.04,  # in meters
    "vertex_duplicate_tol": 1e-4, # in meters
    "crossing_proximity_tol": 0.01  # in meters
}

# Default DXF version for output files
DXF_VERSION = 'R2010'

# Default layer for fallback/general errors
DEFAULT_ERROR_LAYER = "SEGMENT_ERRORS_3D"