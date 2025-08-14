from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import ezdxf

from .road_line import RoadLine

class DXFReader:
    """
    Thin wrapper around ezdxf to extract polylines/lines and convert to RoadLine objects.
    """

    def __init__(self,
                 allowed_layers: Optional[List[str]] = None,
                 allowed_types: List[str] | None = None):
        self.allowed_layers = set(allowed_layers or [])
        self.allowed_types = set(allowed_types or ["LWPOLYLINE", "POLYLINE", "LINE"])

    def load_dxf(self, path: Path) -> List[RoadLine]:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        road_lines: List[RoadLine] = []

        for entity in msp.query(" ".join(self.allowed_types)):
            if self.allowed_layers and entity.dxf.layer not in self.allowed_layers:
                continue

            points = self._extract_points(entity)
            if len(points) < 2:
                continue  # skip degenerate

            road_lines.append(
                RoadLine(
                    vertices=points,
                    meta={
                        "handle": entity.dxf.handle,
                        "layer": entity.dxf.layer,
                        "type": entity.dxftype(),
                    },
                )
            )
        return road_lines

    def _extract_points(self, entity) -> List[Tuple[float, float, float]]:
        if entity.dxftype() == "LINE":
            return [entity.dxf.start.xyz, entity.dxf.end.xyz]
        if entity.dxftype() == "LWPOLYLINE":
            return [v.xyz for v in entity.vertices()]
        if entity.dxftype() in ("POLYLINE", "3DPOLYLINE"):
            return [v.dxf.location.xyz for v in entity.vertices]
        return []