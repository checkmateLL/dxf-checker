import math
from typing import List, Tuple
import ezdxf

def get_3d_points_from_entity(entity) -> List[Tuple[float, float, float]]:
    """Extracts 3D points from a DXF entity."""
    points = []
    entity_type = entity.dxftype()

    try:
        if entity_type == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            points = [
                (float(start.x), float(start.y), float(getattr(start, 'z', 0.0))),
                (float(end.x), float(end.y), float(getattr(end, 'z', 0.0)))
            ]

        elif entity_type == 'LWPOLYLINE':
            elevation = float(getattr(entity.dxf, 'elevation', 0.0))
            for point in entity:
                x, y = float(point[0]), float(point[1])
                points.append((x, y, elevation))
            if entity.closed and len(points) > 2:
                points.append(points[0])

        elif entity_type == 'POLYLINE':
            if hasattr(entity, 'vertices') and entity.vertices:
                for vertex in entity.vertices:
                    try:
                        x, y, z = map(float, vertex.dxf.location.xyz)
                        points.append((x, y, z))
                    except Exception as e:
                        print(f"    Failed to extract POLYLINE vertex: {e}")
            if entity.is_closed and len(points) > 2:
                points.append(points[0])

        elif entity_type == '3DPOLYLINE':
            for vertex in entity.vertices:
                x, y, z = map(float, vertex.dxf.location.xyz)
                points.append((x, y, z))

        elif entity_type in ['SPLINE', 'ARC', 'CIRCLE', 'ELLIPSE']:
            segments = 36 if entity_type in ['CIRCLE', 'ELLIPSE'] else 20
            approx_points = list(entity.approximate(segments=segments))
            points = [(float(p.x), float(p.y), float(getattr(p, 'z', 0.0))) for p in approx_points]
            if entity_type in ['CIRCLE', 'ELLIPSE']:
                points.append(points[0])  # close loop

    except Exception as e:
        print(f"Error extracting points from {entity_type}: {e}")

    return points

def collect_all_linear_entities(doc) -> List:
    """Collects LINE and polyline-like entities from modelspace, layouts, and blocks."""
    linear_types = ['LINE', 'LWPOLYLINE', 'POLYLINE', '3DPOLYLINE', 'SPLINE', 'ARC', 'CIRCLE', 'ELLIPSE']
    entities = []

    for entity in doc.modelspace():
        if entity.dxftype() in linear_types:
            entities.append(entity)

    for layout_name in doc.layout_names():
        if layout_name != 'Model':
            layout = doc.layouts.get(layout_name)
            for entity in layout:
                if entity.dxftype() in linear_types:
                    entities.append(entity)

    for block in doc.blocks:
        if not block.name.startswith('*'):
            for entity in block:
                if entity.dxftype() in linear_types:
                    entities.append(entity)

    return entities

def calculate_3d_distance(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((p2[i] - p1[i]) ** 2 for i in range(3)))
