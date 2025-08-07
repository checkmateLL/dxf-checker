from dataclasses import dataclass

@dataclass
class GeometricConstraints:
    min_horizontal_radius: float = 30.0        # m
    max_grade: float = 0.08                    # 8 %
    tolerance_horizontal_deviation: float = 0.05  # m
    tolerance_elevation_deviation: float = 0.03   # m
    smoothing_factor: float = 0.3              # 0–1