from dataclasses import dataclass

@dataclass
class GeometricConstraints:
    # global tolerances
    tolerance_horizontal_deviation: float = 0.05   # m
    tolerance_elevation_deviation: float = 0.03    # m
    smoothing_factor: float = 0.3                  # 0–1

    # classification/context
    road_class: str = "arterial"       # highway|arterial|collector|local
    context: str = "urban"             # urban|rural
    design_speed_kph: float = 60.0
    max_superelevation: float = 0.08   # 8%
    max_grade: float = 0.08

    # fallbacks if no table match
    min_horizontal_radius: float = 30.0

    def min_radius_for_design(self) -> float:
        """
        Very simple radius rule-of-thumb table by class & speed (m).
        These are intentionally conservative placeholders; replace with local standards as needed.
        """
        table = {
            "highway":   {50: 120, 60: 180, 80: 360, 100: 600, 120: 900},
            "arterial":  {40: 80,  50: 120, 60: 180, 80: 300},
            "collector": {30: 50,  40: 80,  50: 120, 60: 160},
            "local":     {20: 20,  30: 40,  40: 70}
        }
        speeds = table.get(self.road_class, {})
        if not speeds:
            return max(self.min_horizontal_radius, 30.0)
        # pick nearest speed key
        kv = sorted(speeds.items(), key=lambda kv: abs(kv[0] - self.design_speed_kph))
        return float(kv[0][1])