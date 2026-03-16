import math
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt
from demo import CELL_W, CELL_H

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
# Good route
# ============================================================

def choose_center_cell(good_cells: List[Cell]) -> Cell:
    """
    Kept for compatibility with any external code that may still call it.
    """
    if not good_cells:
        raise ValueError("good_cells is empty.")

    mean_x = sum(c[0] for c in good_cells) / len(good_cells)
    mean_y = sum(c[1] for c in good_cells) / len(good_cells)

    return min(
        good_cells,
        key=lambda c: (c[0] - mean_x) ** 2 + (c[1] - mean_y) ** 2
    )


def choose_rightmost_bottom_cell(good_cells: List[Cell]) -> Cell:
    """
    Start cell rule:
    - choose the rightmost good cell
    - if tied, choose the bottommost one among them
    """
    if not good_cells:
        raise ValueError("good_cells is empty.")

    return max(good_cells, key=lambda c: (c[0], -c[1]))


def quantize_column(x: float) -> int:
    """
    Convert a cell center x into a logical column index.
    This keeps the logic synchronized with current CELL_W.
    """
    return int(round(x / CELL_W))


def build_vertical_snake_route(good_cells: List[Cell]) -> Tuple[List[Cell], Cell]:
    """
    Build the good main route using the new rule:

    - start from the rightmost-bottom good cell
    - group cells by column
    - visit columns from right to left
    - first column:  bottom -> top
    - second column: top -> bottom
    - third column:  bottom -> top
    - ...

    This guarantees all good cells are included.
    """
    if not good_cells:
        return [], None  # type: ignore

    # Group cells by logical column
    columns: Dict[int, List[Cell]] = {}
    for cell in good_cells:
        cx, cy, ix, iy = cell
        col_id = quantize_column(cx)
        if col_id not in columns:
            columns[col_id] = []
        columns[col_id].append(cell)

    # Columns: right -> left
    sorted_col_ids = sorted(columns.keys(), reverse=True)

    ordered: List[Cell] = []

    for i, col_id in enumerate(sorted_col_ids):
        col_cells = columns[col_id]

        # y small -> bottom, y large -> top
        col_cells_sorted = sorted(col_cells, key=lambda c: c[1])

        if i % 2 == 0:
            # 1st, 3rd, 5th... column: bottom -> top
            ordered.extend(col_cells_sorted)
        else:
            # 2nd, 4th, 6th... column: top -> bottom
            ordered.extend(reversed(col_cells_sorted))

    start_cell = ordered[0]
    return ordered, start_cell


def build_center_out_good_route(good_cells: List[Cell]) -> Tuple[List[Cell], Cell]:
    """
    Kept under the old function name for compatibility with plan_full_route().
    New rule:
    - start from the rightmost-bottom good cell
    - move in a vertical snake / zigzag pattern across all good cells
    """
    return build_vertical_snake_route(good_cells)


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
    - if moving left/right, standard unit = CELL_W
    - if moving up/down,   standard unit = CELL_H

    Candidate must:
    - have absolute projection within the A-B length
    - stay within the strip offset
    """
    proj, offset, main_len = projection_and_offset(current, target_main, candidate)
    if main_len < 1e-9:
        return False

    if is_horizontal_step(current, target_main):
        standard_unit = CELL_W
    else:
        standard_unit = CELL_H

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
                f"Current snake main route needs further adjustment."
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
            f"Chosen start cell: "
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
    plt.title("Vertical Snake Good Route + Repair Insertion")
    plt.legend()
    plt.grid(True)
    plt.show()