"""Polygon / box geometry. All coordinates are normalized to 0..1 (x right, y down)."""


def point_in_polygon(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def anchor_point(box, anchor):
    x1, y1, x2, y2 = box
    if anchor == "center":
        return (x1 + x2) / 2, (y1 + y2) / 2
    return (x1 + x2) / 2, y2  # "bottom": where the object touches the floor


def footprint(box, frac=0.15):
    """Bottom strip of the box: roughly where wheels or feet meet the ground."""
    x1, y1, x2, y2 = box
    return [x1, y2 - (y2 - y1) * frac, x2, y2]


def overlap_ratio(box, poly, grid=10):
    """Fraction of the box area inside the polygon, by sampling (handles concave zones)."""
    x1, y1, x2, y2 = box
    hits = 0
    for i in range(grid):
        for j in range(grid):
            px = x1 + (x2 - x1) * (i + 0.5) / grid
            py = y1 + (y2 - y1) * (j + 0.5) / grid
            hits += point_in_polygon(px, py, poly)
    return hits / (grid * grid)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def center_dist(a, b):
    return (((a[0] + a[2]) - (b[0] + b[2])) ** 2 + ((a[1] + a[3]) - (b[1] + b[3])) ** 2) ** 0.5 / 2
