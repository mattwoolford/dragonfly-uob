import math
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt

Point = Tuple[float, float]
Polygon = List[Point]
Cell = Tuple[float, float, int, int]   # (cx, cy, ix, iy)


# ============================================================
# Basic geometry
# ============================================================

def dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def point_on_segment(p: Point, a: Point, b: Point, eps: float = 1e-9) -> bool:
    ap = sub(p, a)
    ab = sub(b, a)
    if abs(cross(ap, ab)) > eps:
        return False

    min_x = min(a[0], b[0]) - eps
    max_x = max(a[0], b[0]) + eps
    min_y = min(a[1], b[1]) - eps
    max_y = max(a[1], b[1]) + eps
    return min_x <= p[0] <= max_x and min_y <= p[1] <= max_y


def orientation(a: Point, b: Point, c: Point, eps: float = 1e-9) -> int:
    v = cross(sub(b, a), sub(c, a))
    if v > eps:
        return 1
    if v < -eps:
        return -1
    return 0


def segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point, eps: float = 1e-9) -> bool:
    o1 = orientation(a1, a2, b1, eps)
    o2 = orientation(a1, a2, b2, eps)
    o3 = orientation(b1, b2, a1, eps)
    o4 = orientation(b1, b2, a2, eps)

    if o1 != o2 and o3 != o4:
        return True

    if o1 == 0 and point_on_segment(b1, a1, a2, eps):
        return True
    if o2 == 0 and point_on_segment(b2, a1, a2, eps):
        return True
    if o3 == 0 and point_on_segment(a1, b1, b2, eps):
        return True
    if o4 == 0 and point_on_segment(a2, b1, b2, eps):
        return True

    return False


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    x, y = point
    inside = False
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-12) + x1
        )
        if intersects:
            inside = not inside

    return inside


def segment_crosses_polygon(a: Point, b: Point, polygon: Polygon) -> bool:
    """
    Return True if segment AB touches or crosses polygon.
    """
    mid = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
    if point_in_polygon(mid, polygon):
        return True

    n = len(polygon)
    for i in range(n):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % n]
        if segments_intersect(a, b, p1, p2):
            return True

    return False


# ============================================================
# Good route: fixed 3x4 main-path pattern
# ============================================================

def choose_center_cell(good_cells: List[Cell]) -> Cell:
    """
    Keep this helper for compatibility.
    For the fixed 3x4 pattern, the start cell is used as the main reference cell.
    """
    if not good_cells:
        raise ValueError("good_cells is empty.")

    mean_x = sum(c[0] for c in good_cells) / len(good_cells)
    mean_y = sum(c[1] for c in good_cells) / len(good_cells)

    return min(
        good_cells,
        key=lambda c: (c[0] - mean_x) ** 2 + (c[1] - mean_y) ** 2
    )


def build_good_grid_map(good_cells: List[Cell], tol: float = 1e-6) -> Dict[Tuple[int, int], Cell]:
    """
    Build user-style grid coordinates:
    - bottom-left is (1,1)
    - x increases to the right
    - y increases upward

    This is based on actual cell center coordinates, not demo ix/iy.
    """
    if not good_cells:
        return {}

    xs = sorted({round(c[0], 6) for c in good_cells})
    ys = sorted({round(c[1], 6) for c in good_cells})

    x_to_col = {x: i + 1 for i, x in enumerate(xs)}
    y_to_row = {y: i + 1 for i, y in enumerate(ys)}

    grid_map: Dict[Tuple[int, int], Cell] = {}
    for cell in good_cells:
        cx, cy, ix, iy = cell
        col = x_to_col[round(cx, 6)]
        row = y_to_row[round(cy, 6)]
        grid_map[(col, row)] = cell

    return grid_map


def build_fixed_3x4_good_route(good_cells: List[Cell]) -> Tuple[List[Cell], Cell]:
    """
    Fixed main-path pattern required by user for the current 3x4 good-cell rectangle:

        start at (3,2)
        -> (3,3)
        -> (4,3)
        -> (4,2)
        -> (4,1)
        -> (3,1)
        -> (2,1)
        -> (1,1)
        -> (1,2)
        -> (1,3)
        -> (2,3)
        -> (2,2)

    Grid definition:
    - bottom-left is (1,1)
    """
    if not good_cells:
        return [], None  # type: ignore

    grid_map = build_good_grid_map(good_cells)

    cols = sorted({k[0] for k in grid_map.keys()})
    rows = sorted({k[1] for k in grid_map.keys()})

    if len(cols) != 4 or len(rows) != 3 or len(grid_map) != 12:
        raise ValueError(
            "Current fixed main-path logic requires exactly a 3x4 good-cell rectangle "
            "(4 columns x 3 rows = 12 good cells)."
        )

    required_order = [
        (3, 2),
        (3, 3),
        (4, 3),
        (4, 2),
        (4, 1),
        (3, 1),
        (2, 1),
        (1, 1),
        (1, 2),
        (1, 3),
        (2, 3),
        (2, 2),
    ]

    ordered: List[Cell] = []
    for key in required_order:
        if key not in grid_map:
            raise ValueError(f"Missing good cell at grid position {key}.")
        ordered.append(grid_map[key])

    center_cell = grid_map[(3, 2)]
    return ordered, center_cell


def build_center_out_good_route(good_cells: List[Cell]) -> Tuple[List[Cell], Cell]:
    """
    Keep the original function name so main.py and downstream code do not need changes.
    Internally, use the user's fixed 3x4 main-path pattern.
    """
    return build_fixed_3x4_good_route(good_cells)


# ============================================================
# Repair insertion
# ============================================================

def projection_and_offset(current: Point, target_main: Point, candidate: Point) -> Tuple[float, float, float]:
    """
    Projection / offset relative to current -> target_main.
    """
    d_main = sub(target_main, current)
    d_cand = sub(candidate, current)

    main_len = math.hypot(d_main[0], d_main[1])
    if main_len < 1e-9:
        return 0.0, float("inf"), 0.0

    ux = d_main[0] / main_len
    uy = d_main[1] / main_len
    perp = (-uy, ux)

    proj = d_cand[0] * ux + d_cand[1] * uy
    offset = abs(d_cand[0] * perp[0] + d_cand[1] * perp[1])

    return proj, offset, main_len


def is_horizontal_step(a: Point, b: Point) -> bool:
    return abs(b[0] - a[0]) >= abs(b[1] - a[1])


def candidate_in_direction_strip(current: Point, target_main: Point, candidate: Point) -> bool:
    """
    User rule:
    - if moving left/right, standard unit = 40 m
    - if moving up/down,   standard unit = 30 m

    Candidate must:
    - have absolute projection within the A-B length
    - stay within the strip offset
    """
    proj, offset, main_len = projection_and_offset(current, target_main, candidate)
    if main_len < 1e-9:
        return False

    if is_horizontal_step(current, target_main):
        standard_unit = 40.0
    else:
        standard_unit = 30.0

    if abs(proj) > main_len + 1e-9:
        return False

    if offset > standard_unit + 1e-9:
        return False

    return True


def choose_next_repair(
    current: Point,
    target_main: Point,
    unvisited_repairs: List[Point],
    protected_zone: Polygon,
) -> Optional[Point]:
    """
    Choose the cheapest legal next repair point.
    """
    legal: List[Point] = []

    for r in unvisited_repairs:
        if not candidate_in_direction_strip(current, target_main, r):
            continue

        if segment_crosses_polygon(current, r, protected_zone):
            continue

        if segment_crosses_polygon(r, target_main, protected_zone):
            continue

        legal.append(r)

    if not legal:
        return None

    legal.sort(key=lambda r: dist(current, r))
    return legal[0]


def expand_segment_with_repairs(
    a: Point,
    b: Point,
    unvisited_repairs: List[Point],
    protected_zone: Polygon,
) -> Tuple[List[Point], List[Point]]:
    """
    Expand one main segment A -> B into:
        A -> R1 -> R2 -> ... -> B

    Stop rule:
    - if next repair costs more than going directly to B, stop.
    """
    chain: List[Point] = []
    current = a

    while True:
        best_r = choose_next_repair(current, b, unvisited_repairs, protected_zone)
        if best_r is None:
            break

        if dist(current, best_r) > dist(current, b) + 1e-9:
            break

        chain.append(best_r)
        unvisited_repairs.remove(best_r)
        current = best_r

    return chain, unvisited_repairs


# ============================================================
# Full path planning
# ============================================================

def plan_full_route(
    good_cells: List[Cell],
    repair_cells: List[Cell],
    protected_zone: Polygon,
) -> Dict:
    """
    good_cells / repair_cells are taken directly from demo.find_best_phase outputs:
        selected_good / selected_bad

    Returns:
        center_cell
        main_route_cells
        main_route_points
        final_route_points
        leftover_repairs
    """
    if not good_cells:
        raise ValueError("good_cells is empty.")

    main_route_cells, center_cell = build_center_out_good_route(good_cells)
    main_route_points = [(cx, cy) for cx, cy, _, _ in main_route_cells]

    repair_points = [(cx, cy) for cx, cy, _, _ in repair_cells]
    unvisited_repairs = repair_points.copy()

    final_route: List[Point] = [main_route_points[0]]

    for b in main_route_points[1:]:
        current_start = final_route[-1]

        repair_chain, unvisited_repairs = expand_segment_with_repairs(
            current_start, b, unvisited_repairs, protected_zone
        )

        for r in repair_chain:
            if segment_crosses_polygon(final_route[-1], r, protected_zone):
                raise ValueError(f"Inserted repair segment crosses protected zone: {final_route[-1]} -> {r}")
            final_route.append(r)

        if segment_crosses_polygon(final_route[-1], b, protected_zone):
            raise ValueError(
                f"Main segment crosses protected zone: {final_route[-1]} -> {b}\n"
                f"Current center-out route needs further adjustment."
            )

        final_route.append(b)

    return {
        "center_cell": center_cell,
        "main_route_cells": main_route_cells,
        "main_route_points": main_route_points,
        "final_route_points": final_route,
        "leftover_repairs": unvisited_repairs,
    }


# ============================================================
# Output helpers
# ============================================================

def polyline_length(points: List[Point]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def print_route_summary(result: Dict) -> None:
    center_cell = result["center_cell"]
    main_route_points = result["main_route_points"]
    final_route_points = result["final_route_points"]
    leftover_repairs = result["leftover_repairs"]

    print("\n========== PATH PLANNING RESULT ==========")
    if center_cell is not None:
        print(
            f"Chosen center cell: "
            f"(x={center_cell[0]:.2f}, y={center_cell[1]:.2f}, ix={center_cell[2]}, iy={center_cell[3]})"
        )

    print(f"Main route point count : {len(main_route_points)}")
    print(f"Final route point count: {len(final_route_points)}")
    print(f"Leftover repair points : {len(leftover_repairs)}")
    print(f"Main route length      : {polyline_length(main_route_points):.2f} m")
    print(f"Final route length     : {polyline_length(final_route_points):.2f} m")

    print("\nFinal route points in local custom XY:")
    for i, (x, y) in enumerate(final_route_points, start=1):
        print(f"{i}: ({x:.2f}, {y:.2f})")


def plot_route_result(
    green_poly: Polygon,
    orange_poly: Polygon,
    blue_poly: Polygon,
    good_cells: List[Cell],
    repair_cells: List[Cell],
    result: Dict,
) -> None:
    main_route = result["main_route_points"]
    final_route = result["final_route_points"]
    leftover_repairs = result["leftover_repairs"]

    plt.figure(figsize=(10, 8))

    def draw_poly(poly: Polygon, color: str, label: str):
        xs = [p[0] for p in poly] + [poly[0][0]]
        ys = [p[1] for p in poly] + [poly[0][1]]
        plt.plot(xs, ys, color=color, label=label)

    draw_poly(green_poly, "green", "Flight Boundary")
    draw_poly(orange_poly, "orange", "Protected Zone")
    draw_poly(blue_poly, "blue", "Target Area")

    if good_cells:
        gx = [c[0] for c in good_cells]
        gy = [c[1] for c in good_cells]
        plt.scatter(gx, gy, s=35, label="Good Centers")

    if repair_cells:
        rx = [c[0] for c in repair_cells]
        ry = [c[1] for c in repair_cells]
        plt.scatter(rx, ry, s=35, marker="x", label="Repair Centers")

    if len(main_route) >= 2:
        plt.plot(
            [p[0] for p in main_route],
            [p[1] for p in main_route],
            "--",
            linewidth=1.5,
            label="Main Good Route"
        )

    if len(final_route) >= 2:
        plt.plot(
            [p[0] for p in final_route],
            [p[1] for p in final_route],
            "-",
            linewidth=2.5,
            label="Final Route"
        )

    if final_route:
        plt.scatter(
            [p[0] for p in final_route],
            [p[1] for p in final_route],
            s=18,
            label="Visited Route Points"
        )

    if leftover_repairs:
        plt.scatter(
            [p[0] for p in leftover_repairs],
            [p[1] for p in leftover_repairs],
            s=60,
            marker="s",
            label="Leftover Repairs"
        )

    plt.axis("equal")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title("Fixed 3x4 Good Route + Repair Insertion")
    plt.legend()
    plt.grid(True)
    plt.show()