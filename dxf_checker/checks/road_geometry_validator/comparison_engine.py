from typing import List, Tuple
import math
from .road_line import RoadLine
from .validation_report import ValidationReport, Deviation
from .geometric_constraints import GeometricConstraints

class ComparisonEngine:
    """
    Station-based comparison between original and ideal alignments.
    We sample both lines at uniform station intervals along XY.
    """

    def __init__(
        self,
        station_step: float = 5.0,
        constraints: GeometricConstraints = None,
        deadband_h: float = 0.012,     # 12 mm → treat <=12 mm as 0
        deadband_z: float = 0.015,     # 15 mm for elevation
        min_report_error: float = 0.015,  # don’t record row unless >15 mm horiz
        round_mm: int = 1              # round to nearest 1 mm in output values
    ):
        self.station_step = station_step
        self.constraints = constraints or GeometricConstraints()
        self.deadband_h = float(deadband_h)
        self.deadband_z = float(deadband_z)
        self.min_report_error = float(min_report_error)
        self.round_mm = int(round_mm)

    def compare(self, original: RoadLine, ideal: RoadLine) -> ValidationReport:
        deviations: List[Deviation] = []
        if len(ideal.vertices) < 2 or len(original.vertices) < 2:
            return ValidationReport(original=original, ideal=ideal, deviations=deviations)

        # Resample both lines  (math only)
        step = max(0.5, float(self.station_step))
        A = original.resample_by_station(step)
        B = ideal.resample_by_station(step)

        SA = A.stations()
        SB = B.stations()
        L = min(SA[-1], SB[-1])
        if L <= 0:
            return ValidationReport(original=original, ideal=ideal, deviations=deviations)

        station = 0.0
        idx = 0
        while station <= L + 1e-9:
            oa = A.sample_xy_at_station(station)
            ib = B.sample_xy_at_station(station)
            dx = oa[0] - ib[0]
            dy = oa[1] - ib[1]
            dz = oa[2] - ib[2]
            h_err = math.hypot(dx, dy)
            z_err = abs(dz)
            # apply deadbands (snap tiny values to 0)
            if h_err <= self.deadband_h:
                h_err = 0.0
            if z_err <= self.deadband_z:
                z_err = 0.0

            # engineering metrics at this station
            kA = self._curv_at_station(A, station)
            kB = self._curv_at_station(B, station)
            curv_dev = abs(kA - kB)
            brA = A.bearing_at_station(station)
            brB = B.bearing_at_station(station)
            # wrap to [0, pi]
            bearing_dev = abs((brA - brB + math.pi) % (2*math.pi) - math.pi)

            # design-speed compatibility (radius)
            # R ≈ 1/|k| (guard against zero)
            R_ideal = 1e9 if abs(kB) < 1e-9 else 1.0 / abs(kB)
            min_R = self.constraints.min_radius_for_design()
            design_ok = R_ideal >= min_R

            # skip trivial rows (keeps CSV small & readable)
            if h_err < self.min_report_error and z_err == 0.0:
                station += step
                idx += 1
                continue

            # rounding helper (to nearest mm)
            r = lambda v: round(v, 3) if self.round_mm <= 0 else round(v, 3)  # values are meters; 3 dp = 1 mm

            deviations.append(
                Deviation(
                    vertex_index=idx,                  
                    station=r(station),
                    original=(r(oa[0]), r(oa[1]), r(oa[2])),
                    ideal=(r(ib[0]), r(ib[1]), r(ib[2])),
                    horizontal_error=r(h_err),
                    elevation_error=r(z_err),
                    curvature_dev=r(curv_dev),
                    bearing_dev=bearing_dev,   # keep radians full precision
                    design_radius=r(R_ideal),
                    design_ok=design_ok,
                )
            )
            station += step
            idx += 1

        return ValidationReport(original=original, ideal=ideal, deviations=deviations)

    # helpers ------------------------------------------------------------
    def _curv_at_station(self, line: RoadLine, s: float) -> float:
        """Discrete curvature around station s using ±step."""
        eps = max(0.5, self.station_step)
        s1 = max(0.0, s - eps)
        s2 = min(line.stations()[-1], s + eps)
        p1 = line.sample_xy_at_station(s1)
        p  = line.sample_xy_at_station(s)
        p2 = line.sample_xy_at_station(s2)
        # same formula as RoadLine.curvature_at but using sampled triplet
        ax, ay = p[0] - p1[0], p[1] - p1[1]
        bx, by = p2[0] - p[0], p2[1] - p[1]
        cross = ax * by - ay * bx
        la = math.hypot(ax, ay)
        lb = math.hypot(bx, by)
        lc = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        denom = la * lb * lc
        if denom <= 1e-12:
            return 0.0
        return 2.0 * cross / denom