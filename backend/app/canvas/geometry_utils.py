"""
InkLoop Canvas Geometry Utilities.
Provides deterministic geometric algorithms for polygons, non-rectangular panels,
bounding calculations, grid snapping, and boundary validation.
Authoritative coordinate reference: Top-Left (0, 0), +X right, +Y down.
"""
import math
from typing import List, Tuple, Optional
from app.contracts.geometry import Point, Rect, snap_to_pixel_grid

def shoelace_area(points: List[Point]) -> float:
    """
    Computes the 2D polygon area using the shoelace formula (Gauss's area formula).
    Returns strictly positive float for valid non-degenerate polygons.
    """
    n = len(points)
    if n < 3:
        return 0.0

    area2 = 0.0
    for i in range(n):
        j = (i + 1) % n
        area2 += points[i].x * points[j].y - points[j].x * points[i].y

    return abs(area2) / 2.0

def polygon_bounding_box(points: List[Point]) -> Rect:
    """Computes the minimal axis-aligned bounding box enclosing all polygon vertices."""
    if not points:
        return Rect(x=0.0, y=0.0, width=1.0, height=1.0)

    min_x = min(p.x for p in points)
    max_x = max(p.x for p in points)
    min_y = min(p.y for p in points)
    max_y = max(p.y for p in points)

    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    return Rect(x=min_x, y=min_y, width=width, height=height)

def snap_polygon_to_grid(points: List[Point]) -> List[Point]:
    """Snaps every vertex of a polygon to integer pixel coordinates."""
    return [
        Point(
            x=float(math.floor(p.x + 0.5)),
            y=float(math.floor(p.y + 0.5))
        )
        for p in points
    ]

def segments_intersect(p1: Point, p2: Point, q1: Point, q2: Point, epsilon: float = 1e-7) -> bool:
    """
    Returns True if line segment (p1, p2) and segment (q1, q2) intersect at an interior point.
    Endpoints touching (or collinear shared endpoints) are treated as non-intersecting.
    """
    def ccw(a: Point, b: Point, c: Point) -> float:
        return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)

    d1 = ccw(p1, p2, q1)
    d2 = ccw(p1, p2, q2)
    d3 = ccw(q1, q2, p1)
    d4 = ccw(q1, q2, p2)

    # General intersection: segments straddle each other's lines
    if ((d1 > epsilon and d2 < -epsilon) or (d1 < -epsilon and d2 > epsilon)) and \
       ((d3 > epsilon and d4 < -epsilon) or (d3 < -epsilon and d4 > epsilon)):
        return True

    return False

def polygon_is_self_intersecting(points: List[Point]) -> bool:
    """
    Checks if a polygon has self-intersecting boundary edges.
    Consecutive edges sharing a vertex are allowed; non-consecutive edge intersections indicate self-intersection.
    """
    n = len(points)
    if n < 4:
        return False

    for i in range(n):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        for j in range(i + 2, n):
            # Skip the edge connecting last to first vertex when checking the first edge
            if i == 0 and j == n - 1:
                continue
            q1 = points[j]
            q2 = points[(j + 1) % n]
            if segments_intersect(p1, p2, q1, q2):
                return True

    return False

def point_in_polygon(point: Point, polygon: List[Point], epsilon: float = 1e-7) -> bool:
    """
    Determines if a 2D point lies strictly inside a simple polygon using the ray-casting algorithm.
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    x, y = point.x, point.y

    for i in range(n):
        j = (i + 1) % n
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y

        # Ray-casting crossing condition: (yj - yi) is guaranteed non-zero when (yi > y) != (yj > y)
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside

    return inside

def polygons_intersect(poly_a: List[Point], poly_b: List[Point]) -> bool:
    """
    Checks if two simple polygons overlap with non-zero area.
    Tests boundary edge intersections and interior point containment.
    """
    # 1. Check if any edge of poly_a intersects any edge of poly_b
    n_a = len(poly_a)
    n_b = len(poly_b)

    for i in range(n_a):
        p1 = poly_a[i]
        p2 = poly_a[(i + 1) % n_a]
        for j in range(n_b):
            q1 = poly_b[j]
            q2 = poly_b[(j + 1) % n_b]
            if segments_intersect(p1, p2, q1, q2):
                return True

    # 2. Check if poly_a is contained inside poly_b (any vertex or center)
    if any(point_in_polygon(p, poly_b) for p in poly_a):
        return True
    center_a = Point(
        x=sum(p.x for p in poly_a) / n_a,
        y=sum(p.y for p in poly_a) / n_a
    )
    if point_in_polygon(center_a, poly_b):
        return True

    # 3. Check if poly_b is contained inside poly_a (any vertex or center)
    if any(point_in_polygon(p, poly_a) for p in poly_b):
        return True
    center_b = Point(
        x=sum(p.x for p in poly_b) / n_b,
        y=sum(p.y for p in poly_b) / n_b
    )
    if point_in_polygon(center_b, poly_a):
        return True

    return False

def polygon_is_within_rect(points: List[Point], boundary: Rect, epsilon: float = 1e-6) -> bool:
    """Verifies that all vertices of a polygon lie within the specified boundary rectangle."""
    for p in points:
        if (p.x < boundary.left - epsilon or
            p.x > boundary.right + epsilon or
            p.y < boundary.top - epsilon or
            p.y > boundary.bottom + epsilon):
            return False
    return True
