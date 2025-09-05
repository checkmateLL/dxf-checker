from typing import List, Dict, Any, Tuple, Optional
import math
from ._utils import distance_3d

class RoadLine:
    """
    Immutable representation of a road alignment.
    """

    def __init__(self,
                 vertices: List[Tuple[float, float, float]],
                 meta: Optional[Dict[str, Any]] = None,
                 ):
        self.vertices = vertices
        self.meta = meta or {}

    # --- basic geometry -------------------------------------------------
    def length(self) -> float:
        return sum(
            distance_3d(self.vertices[i], self.vertices[i + 1])
            for i in range(len(self.vertices) - 1)
        )

    def segment_lengths(self) -> List[float]:
        return [
            distance_3d(self.vertices[i], self.vertices[i + 1])
            for i in range(len(self.vertices) - 1)
        ]

    def bearing_at(self, index: int) -> float:
        """Horizontal bearing (radians) of segment i→i+1"""
        dx = self.vertices[index + 1][0] - self.vertices[index][0]
        dy = self.vertices[index + 1][1] - self.vertices[index][1]
        return math.atan2(dy, dx)

    # --- segmentation helpers ------------------------------------------
    def split_by_max_length(self, max_len: float) -> "RoadLine":
        """Return new RoadLine with extra vertices if any segment > max_len"""
        new_pts = [self.vertices[0]]
        for p1, p2 in zip(self.vertices[:-1], self.vertices[1:]):
            d = distance_3d(p1, p2)
            if d > max_len:
                n = int(math.ceil(d / max_len))
                for k in range(1, n):
                    t = k / n
                    new_pts.append(tuple(p1[i] * (1 - t) + p2[i] * t for i in range(3)))
            new_pts.append(p2)
        return RoadLine(new_pts, self.meta)
    
    # --- stationing -----------------------------------------------------
    def stations(self) -> List[float]:
        """Cumulative 2D stationing along XY (meters)."""
        s = [0.0]
        for a, b in zip(self.vertices[:-1], self.vertices[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            s.append(s[-1] + math.hypot(dx, dy))
        return s

    def _interp_xy(self, a, b, t: float) -> Tuple[float, float]:
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def _interp_xyz(self, a, b, t: float) -> Tuple[float, float, float]:
        return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

    def sample_xy_at_station(self, station: float) -> Tuple[float, float, float]:
        """
        Return (x, y, z) where x,y are interpolated by stationing (XY length).
        z is linearly interpolated by segment param t (no vertical stationing).
        """
        S = self.stations()
        if station <= 0:
            return self.vertices[0]
        if station >= S[-1]:
            return self.vertices[-1]
        # find segment
        lo = 0
        hi = len(S) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if S[mid] <= station:
                lo = mid
            else:
                hi = mid
        seg_len = S[lo + 1] - S[lo]
        t = 0.0 if seg_len <= 1e-12 else (station - S[lo]) / seg_len
        return self._interp_xyz(self.vertices[lo], self.vertices[lo + 1], t)

    def resample_by_station(self, step: float) -> "RoadLine":
        """Uniform stationing resample along XY."""
        L = self.stations()[-1]
        if L <= 0:
            return self
        n = max(1, int(math.floor(L / step)))
        pts = [self.sample_xy_at_station(i * step) for i in range(n + 1)]
        if pts[-1] != self.vertices[-1]:
            pts[-1] = self.vertices[-1]
        return RoadLine(pts, {**self.meta, "resampled_step": step})

    # --- curvature & bearings ------------------------------------------
    def curvature_at(self, i: int) -> float:
        """
        Discrete curvature k ≈ 1/R using 3 consecutive points in XY.
        Sign indicates turning direction (left + / right -).
        """
        if i <= 0 or i >= len(self.vertices) - 1:
            return 0.0
        x1, y1 = self.vertices[i - 1][0], self.vertices[i - 1][1]
        x2, y2 = self.vertices[i][0], self.vertices[i][1]
        x3, y3 = self.vertices[i + 1][0], self.vertices[i + 1][1]
        # triangle area * 2 = cross of (p2-p1, p3-p2)
        ax, ay = x2 - x1, y2 - y1
        bx, by = x3 - x2, y3 - y2
        cross = ax * by - ay * bx
        la = math.hypot(ax, ay)
        lb = math.hypot(bx, by)
        lc = math.hypot(x3 - x1, y3 - y1)
        denom = la * lb * lc
        if denom <= 1e-12:
            return 0.0
        # curvature sign preserved by cross sign
        return 2.0 * cross / denom

    def bearing_at_station(self, station: float) -> float:
        """Bearing from tangent at station (XY only)."""
        S = self.stations()
        if station <= 0:
            return self.bearing_at(0)
        if station >= S[-1]:
            return self.bearing_at(len(self.vertices) - 2)
        # sample slightly before/after
        eps = 0.1
        p1 = self.sample_xy_at_station(max(0.0, station - eps))
        p2 = self.sample_xy_at_station(min(S[-1], station + eps))
        return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

    # --- validation utilities ------------------------------------------
    def is_closed(self, tol: float = 1e-6) -> bool:
        a, b = self.vertices[0], self.vertices[-1]
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    def has_self_intersection(self, tol: float = 0.0) -> bool:
        """Simple O(n^2) segment intersection in XY."""
        segs = list(zip(self.vertices[:-1], self.vertices[1:]))
        def ccw(A,B,C):
            return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])
        for i in range(len(segs)):
            A,B = segs[i]
            for j in range(i+2, len(segs)):
                # skip consecutive neighbor sharing a point
                if j == i+1:
                    continue
                C,D = segs[j]
                A2, B2, C2, D2 = A[:2], B[:2], C[:2], D[:2]
                if (ccw(A2,C2,D2) != ccw(B2,C2,D2)) and (ccw(A2,B2,C2) != ccw(A2,B2,D2)):
                    return True
        return False

    def has_loop(self, min_loop_len: float = 1.0) -> bool:
        """Detect if the line doubles back significantly (coarse)."""
        S = self.stations()
        L = S[-1]
        if L < 2 * min_loop_len:
            return False
        # compare headings early vs late
        h1 = self.bearing_at(0)
        h2 = self.bearing_at(len(self.vertices) - 2)
        d = abs((h2 - h1 + math.pi) % (2*math.pi) - math.pi)
        return d > (2.5)  # ~> 143deg

    def segment_by_curvature(self, k_threshold: float = 1e-4) -> List[Tuple[int,int,str]]:
        """
        Return list of (start_idx, end_idx, kind) where kind ∈ {"tangent","curve"}.
        """
        if len(self.vertices) < 3:
            return [(0, len(self.vertices)-1, "tangent")]
        kinds = []
        mode = "tangent"
        start = 0
        for i in range(1, len(self.vertices)-1):
            k = abs(self.curvature_at(i))
            m = "curve" if k >= k_threshold else "tangent"
            if m != mode:
                kinds.append((start, i, mode))
                start = i
                mode = m
        kinds.append((start, len(self.vertices)-1, mode))
        return kinds