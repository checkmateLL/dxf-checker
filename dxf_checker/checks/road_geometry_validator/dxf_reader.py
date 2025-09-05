from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Iterable
import ezdxf
from ezdxf.math import Matrix44

from .road_line import RoadLine

class DXFReader:
    """
    Extract polylines/lines (and HATCH boundaries) from modelspace AND blocks,
    applying block transforms. Produces RoadLine objects.
    """

    def __init__(
        self,
        allowed_layers: Optional[List[str]] = None,
        allowed_types: Optional[List[str]] = None,
        excluded_layers: Optional[List[str]] = None,
        include_blocks: bool = True,
        include_hatch: bool = True,
        min_length: Optional[float] = None,
        verbose: bool = False,
        arc_max_chord: float = 1.0,   # m, for HATCH arc approximation
    ):
        # Layer/type filtering (optional & configurable)
        self.allowed_layers = set(allowed_layers or [])
        self.excluded_layers = set(excluded_layers or [])
        base_types = ["LWPOLYLINE", "POLYLINE", "3DPOLYLINE", "LINE", "SPLINE", "POINT"]
        if include_hatch:
            base_types.append("HATCH")
        self.allowed_types = set(allowed_types or base_types)

        self.include_blocks = include_blocks
        self.include_hatch = include_hatch
        self.min_length = min_length
        self.verbose = verbose
        self.arc_max_chord = max(0.01, float(arc_max_chord))

    def load_dxf(self, path: Path) -> List[RoadLine]:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        lines: List[RoadLine] = []

        # 1) Pull from modelspace directly
        for entity in msp.query(" ".join(self.allowed_types)):
            if not self._layer_ok(entity):
                continue
            pts = self._extract_points(entity)
            self._append_if_viable(lines, pts, entity)

            # 2) Pull from blocks (INSERT), applying transforms
        if self.include_blocks:
            inserts = list(msp.query("INSERT"))
            if self.verbose:
                print(f"[DXFReader] Found {len(inserts)} block references (INSERT).")
            for ins in inserts:
                try:
                    block = doc.blocks[ins.dxf.name]
                except KeyError:
                    if self.verbose:
                        print(f"[DXFReader] Missing block '{ins.dxf.name}'")
                    continue

                transform = Matrix44.chain(
                    Matrix44.scale(ins.dxf.xscale, ins.dxf.yscale, ins.dxf.zscale),
                    Matrix44.z_rotate(ins.dxf.rotation),
                    Matrix44.translate(ins.dxf.insert.x, ins.dxf.insert.y, ins.dxf.insert.z),
                )
                # collect in-block entities
                q = " ".join(self.allowed_types)
                block_entities = list(block.query(q))
                if self.verbose:
                    counts = {}
                    for e in block_entities:
                        t = e.dxftype()
                        counts[t] = counts.get(t, 0) + 1
                    print(f"[DXFReader] Block '{ins.dxf.name}': {counts}")

                for be in block_entities:
                    # NOTE: we decide layer filter against the referenced entity's layer,
                    # which is typical in CAD practice
                    if not self._layer_ok(be):
                        continue
                    pts = self._extract_points(be)
                    if not pts:
                        continue
                    # apply transform
                    tr_pts = self._apply_transform(pts, transform)
                    self._append_if_viable(lines, tr_pts, be)

        if self.verbose:
            print(f"[DXFReader] Produced {len(lines)} RoadLine(s).")
        return lines

    def _extract_points(self, entity) -> List[Tuple[float, float, float]]:
        if entity.dxftype() == "LINE":
            return [entity.dxf.start.xyz, entity.dxf.end.xyz]
        if entity.dxftype() == "LWPOLYLINE":
            return [v.xyz for v in entity.vertices()]
        if entity.dxftype() in ("POLYLINE", "3DPOLYLINE"):
            return [v.dxf.location.xyz for v in entity.vertices]
        if entity.dxftype() == "SPLINE":            
            return [p.xyz for p in entity.control_points]
        if entity.dxftype() == "POINT":
            return [entity.dxf.location.xyz]
        if entity.dxftype() == "HATCH" and self.include_hatch:
            return self._extract_hatch_boundary_points(entity)
        return []
    
    # --- helpers ---------------------------------------------------------
    def _apply_transform(
        self, points: Iterable[Tuple[float, float, float]], m: Matrix44
    ) -> List[Tuple[float, float, float]]:
        out = []
        for p in points:
            # ezdxf Matrix44 produces Vec3 with .x,.y,.z
            v = m.transform(p)
            out.append((float(v.x), float(v.y), float(v.z)))
        return out

    def _layer_ok(self, e) -> bool:
        layer = getattr(e.dxf, "layer", None)
        if layer is None:
            return True
        if self.excluded_layers and layer in self.excluded_layers:
            return False
        if self.allowed_layers and layer not in self.allowed_layers:
            return False
        return True

    def _length(self, pts: List[Tuple[float, float, float]]) -> float:
        if len(pts) < 2:
            return 0.0
        d = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            dx, dy, dz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            d += (dx*dx + dy*dy + dz*dz) ** 0.5
        return d

    def _append_if_viable(self, dest: List[RoadLine], pts: List[Tuple[float, float, float]], e) -> None:
        if len(pts) < 2:
            return
        if self.min_length is not None and self._length(pts) < self.min_length:
            return
        dest.append(
            RoadLine(
                vertices=pts,
                meta={
                    "handle": getattr(e.dxf, "handle", None),
                    "layer": getattr(e.dxf, "layer", None),
                    "type": e.dxftype(),
                },
            )
        )

    def _extract_hatch_boundary_points(self, hatch) -> List[Tuple[float, float, float]]:
        """
        Convert HATCH boundary paths into a polyline-like list of 3D points.
        EdgePath arcs are approximated by chords with max length `arc_max_chord`.
        """
        pts: List[Tuple[float, float, float]] = []
        for path in hatch.paths:
            name = path.__class__.__name__
            if name == "PolylinePath":
                for v in path.vertices:
                    if len(v) >= 3:
                        pts.append((float(v[0]), float(v[1]), float(v[2])))
                    elif len(v) == 2:
                        pts.append((float(v[0]), float(v[1]), 0.0))
            elif name == "EdgePath":
                for edge in path.edges:
                    et = edge.__class__.__name__
                    if et == "LineEdge":
                        s = edge.start if len(edge.start) >= 3 else (edge.start[0], edge.start[1], 0.0)
                        e = edge.end   if len(edge.end)   >= 3 else (edge.end[0],   edge.end[1],   0.0)
                        pts.extend([tuple(map(float, s)), tuple(map(float, e))])
                    elif et == "ArcEdge":
                        # Try to approximate arc → polyline
                        try:
                            c = edge.center
                            r = float(edge.radius)
                            ang1 = float(edge.start_angle)
                            ang2 = float(edge.end_angle)
                            arc_pts = self._approx_arc_2d(c, r, ang1, ang2)
                            for ap in arc_pts:
                                pts.append((ap[0], ap[1], 0.0))
                        except Exception:
                            # Fallback: take center only if arc attributes not fully available
                            c = edge.center if len(edge.center) >= 3 else (edge.center[0], edge.center[1], 0.0)
                            pts.append(tuple(map(float, c)))
            # Ignore Ellipse/Spline edges in HATCH for now (rare for centerlines)
        return pts

    def _approx_arc_2d(self, center, radius, start_deg, end_deg) -> List[Tuple[float, float]]:
        """
        Approximate a circular arc by chord-limited straight segments.
        Angles are in degrees. Returns XY points including start & end.
        """
        import math
        cx, cy = float(center[0]), float(center[1])
        r = float(radius)
        if r <= 0:
            return [(cx, cy)]
        # normalize direction
        a1 = math.radians(start_deg)
        a2 = math.radians(end_deg)
        # ensure forward direction
        if a2 < a1:
            a2 += 2 * math.pi
        arc_len = r * (a2 - a1)
        n = max(1, int(math.ceil(arc_len / self.arc_max_chord)))
        pts = []
        for k in range(n + 1):
            t = a1 + (a2 - a1) * (k / n)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        return pts    