import matplotlib.pyplot as plt
from typing import List, Tuple, Optional, Set, Dict

Point = Tuple[float, float]
Polygon = List[Point]

# ============================================================
# Configuration
# ============================================================

# Rectangle (cell) size: 40m wide (x), 30m tall (y)
CELL_W = 40.0
CELL_H = 30.0
HALF_W = CELL_W / 2.0
HALF_H = CELL_H / 2.0

#REPAIR COVERAGE#
MIN_REPAIR_COVERAGE_RATIO = 0.005  # 0.5%

# Marker sampling: 2m x 2m points
MARKER_STEP = 2.0

# Phase search step (global translation dx, dy)
PHASE_STEP = 5.0  # try 0,5,10,... within one cell width/height

# Max local movement range for BAD cells
MAX_MOVE_CELLS = 2

# Fine repair step for BAD-cell movement
REPAIR_STEP = 5.0

# Direction rule:
# if iy < 3 -> move left or right
# else      -> move in full 2D (up/down/left/right, combined)
DIRECTION_SPLIT_ROWS = 3


# ============================================================
# Geometry helpers
# ============================================================

def point_on_segment(p: Point, a: Point, b: Point) -> bool:
    (px, py), (x1, y1), (x2, y2) = p, a, b
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > 1e-9:
        return False
    dot = (px - x1) * (px - x2) + (py - y1) * (py - y2)
    return dot <= 0


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """Ray casting. Boundary counts as inside."""
    x, y = point
    inside = False
    n = len(polygon)

    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        if point_on_segment(point, (x1, y1), (x2, y2)):
            return True

        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x_intersect >= x:
                inside = not inside

    return inside


def segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    """Boundary inclusive segment intersection."""
    def ccw(p1, p2, p3):
        return (p3[1] - p1[1]) * (p2[0] - p1[0]) > (p2[1] - p1[1]) * (p3[0] - p1[0])

    if point_on_segment(a1, b1, b2) or point_on_segment(a2, b1, b2):
        return True
    if point_on_segment(b1, a1, a2) or point_on_segment(b2, a1, a2):
        return True

    return (ccw(a1, b1, b2) != ccw(a2, b1, b2)) and \
           (ccw(a1, a2, b1) != ccw(a1, a2, b2))


def rect_corners(cx: float, cy: float) -> List[Point]:
    return [
        (cx - HALF_W, cy - HALF_H),
        (cx + HALF_W, cy - HALF_H),
        (cx + HALF_W, cy + HALF_H),
        (cx - HALF_W, cy + HALF_H),
    ]


def rect_intersects_polygon(cx: float, cy: float, polygon: Polygon) -> bool:
    """Axis-aligned rectangle intersects polygon (boundary inclusive)."""
    corners = rect_corners(cx, cy)

    # 1) Any rectangle corner inside polygon
    if any(point_in_polygon(c, polygon) for c in corners):
        return True

    # 2) Any polygon vertex inside rectangle
    xmin, xmax = cx - HALF_W, cx + HALF_W
    ymin, ymax = cy - HALF_H, cy + HALF_H
    for px, py in polygon:
        if xmin <= px <= xmax and ymin <= py <= ymax:
            return True

    # 3) Any edges intersect
    rect_edges = list(zip(corners, corners[1:] + [corners[0]]))
    poly_edges = list(zip(polygon, polygon[1:] + [polygon[0]]))
    for r1, r2 in rect_edges:
        for p1, p2 in poly_edges:
            if segments_intersect(r1, r2, p1, p2):
                return True

    return False


def point_in_rect(px: float, py: float, cx: float, cy: float) -> bool:
    return (cx - HALF_W <= px <= cx + HALF_W) and (cy - HALF_H <= py <= cy + HALF_H)


def frange(start: float, stop: float, step: float):
    x = start
    while x <= stop + 1e-9:
        yield x
        x += step


# ============================================================
# Marker sampling (2m x 2m points inside blue polygon)
# ============================================================

def sample_markers_in_blue(blue_poly: Polygon, step: float = MARKER_STEP) -> List[Point]:
    xs = [p[0] for p in blue_poly]
    ys = [p[1] for p in blue_poly]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    markers: List[Point] = []
    y = ymin
    while y <= ymax + 1e-9:
        x = xmin
        while x <= xmax + 1e-9:
            if point_in_polygon((x, y), blue_poly):
                markers.append((x, y))
            x += step
        y += step
    return markers


# ============================================================
# Grid generation with (ix, iy) indexing
# ============================================================

def generate_grid_with_indices(green_rect: Polygon, dx: float = 0.0, dy: float = 0.0):
    xmin = min(p[0] for p in green_rect)
    xmax = max(p[0] for p in green_rect)
    ymin = min(p[1] for p in green_rect)
    ymax = max(p[1] for p in green_rect)

    x0 = xmin + HALF_W + dx
    y0 = ymin + HALF_H + dy

    cells = []  # (cx, cy, ix, iy)
    iy = 0
    y = y0
    while y <= ymax - HALF_H + 1e-9:
        ix = 0
        x = x0
        while x <= xmax - HALF_W + 1e-9:
            cells.append((x, y, ix, iy))
            x += CELL_W
            ix += 1
        y += CELL_H
        iy += 1

    group_rows = iy
    group_cols = 0
    if cells:
        group_cols = max(c[2] for c in cells) + 1

    return cells, group_cols, group_rows


# ============================================================
# Coverage helpers
# ============================================================

def build_cover_set_for_cell_from_indices(
    cx: float,
    cy: float,
    markers: List[Point],
    candidate_indices: Set[int]
) -> Set[int]:
    """
    Only test marker indices in candidate_indices.
    This is much cheaper than scanning all markers every time.
    """
    covered: Set[int] = set()
    for i in candidate_indices:
        mx, my = markers[i]
        if point_in_rect(mx, my, cx, cy):
            covered.add(i)
    return covered


# ============================================================
# Cell classification
# ============================================================

def classify_cells(
    cells: List[Tuple[float, float, int, int]],
    orange_poly: Polygon,
    blue_poly: Polygon
):
    """
    GOOD:
        - center in blue
        - center not in orange

    BAD:
        - intersects blue
        - center not in blue
    """
    good: List[Tuple[float, float, int, int]] = []
    bad: List[Tuple[float, float, int, int]] = []

    for cx, cy, ix, iy in cells:
        if not rect_intersects_polygon(cx, cy, blue_poly):
            continue

        if point_in_polygon((cx, cy), blue_poly):
            if not point_in_polygon((cx, cy), orange_poly):
                good.append((cx, cy, ix, iy))
        else:
            bad.append((cx, cy, ix, iy))

    return good, bad


# ============================================================
# Greedy selection (GOOD cells only, with dynamic uncovered set)
# ============================================================

def greedy_select_cells(
    good_cells: List[Tuple[float, float, int, int]],
    markers: List[Point]
) -> Tuple[List[Tuple[float, float, int, int]], Set[int]]:
    """
    Greedy set cover using a dynamic uncovered marker set.
    Cover sets are always computed only against the current uncovered markers.
    """
    uncovered: Set[int] = set(range(len(markers)))
    selected: List[Tuple[float, float, int, int]] = []
    remaining = set(range(len(good_cells)))

    while uncovered:
        best_idx = None
        best_cover: Set[int] = set()
        best_gain = 0

        for idx in list(remaining):
            cx, cy, _, _ = good_cells[idx]
            covered = build_cover_set_for_cell_from_indices(cx, cy, markers, uncovered)
            gain = len(covered)

            if gain > best_gain:
                best_gain = gain
                best_idx = idx
                best_cover = covered

        if best_idx is None or best_gain == 0:
            break

        selected.append(good_cells[best_idx])
        uncovered -= best_cover
        remaining.remove(best_idx)

    return selected, uncovered


# ============================================================
# BAD-cell repair (dynamic uncovered set)
# ============================================================

def choose_candidate_by_average_move(candidates):
    """
    candidates: list of (move_value, nx, ny, covered_set)

    Rule:
    - among equal-best-gain candidates,
      compute target_move = (min_move + max_move) / 2
    - choose candidate whose move_value is closest to target_move
    - if still tied, choose the one with smaller move_value
    """
    if not candidates:
        return None

    move_values = [c[0] for c in candidates]
    min_move = min(move_values)
    max_move = max(move_values)
    target_move = (min_move + max_move) / 2.0

    best = None
    best_dist = float("inf")
    best_move = float("inf")

    for cand in candidates:
        move_value = cand[0]
        dist = abs(move_value - target_move)

        if dist < best_dist:
            best = cand
            best_dist = dist
            best_move = move_value
        elif abs(dist - best_dist) < 1e-12:
            if move_value < best_move:
                best = cand
                best_move = move_value

    return best


def repair_bad_cells(
    bad_cells: List[Tuple[float, float, int, int]],
    uncovered: Set[int],
    markers: List[Point],
    orange_poly: Polygon,
    green_rect: Polygon,
    blue_poly: Polygon
) -> Tuple[List[Tuple[float, float, int, int]], Set[int]]:
    repaired: List[Tuple[float, float, int, int]] = []
    uncovered_now = set(uncovered)

    max_shift = MAX_MOVE_CELLS * max(CELL_W, CELL_H)
    shift_values = list(frange(REPAIR_STEP, max_shift, REPAIR_STEP))

    for cx, cy, ix, iy in bad_cells:
        best_gain = 0
        best_candidates = []

        if iy < DIRECTION_SPLIT_ROWS:
            for shift in shift_values:
                for sign in (-1.0, 1.0):
                    nx = cx + sign * shift
                    ny = cy
                    move_value = abs(sign * shift)

                    if not point_in_polygon((nx, ny), blue_poly):
                        continue

                    covered = build_cover_set_for_cell_from_indices(
                        nx, ny, markers, uncovered_now
                    )
                    gain = len(covered)

                    if gain <= 0:
                        continue

                    if gain > best_gain:
                        best_gain = gain
                        best_candidates = [(move_value, nx, ny, covered)]
                    elif gain == best_gain:
                        best_candidates.append((move_value, nx, ny, covered))
        else:
            delta_values = [0.0]
            for s in shift_values:
                delta_values.append(s)
                delta_values.append(-s)

            for dy in delta_values:
                for dx in delta_values:
                    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                        continue

                    nx = cx + dx
                    ny = cy + dy
                    move_value = abs(dx) + abs(dy)

                    if not point_in_polygon((nx, ny), blue_poly):
                        continue

                    covered = build_cover_set_for_cell_from_indices(
                        nx, ny, markers, uncovered_now
                    )
                    gain = len(covered)

                    if gain <= 0:
                        continue

                    if gain > best_gain:
                        best_gain = gain
                        best_candidates = [(move_value, nx, ny, covered)]
                    elif gain == best_gain:
                        best_candidates.append((move_value, nx, ny, covered))

        if best_gain <= 0 or not best_candidates:
            continue

        if len(markers) == 0:
            continue

        repair_ratio = best_gain / len(markers)
        if repair_ratio < MIN_REPAIR_COVERAGE_RATIO:
            continue

        chosen = choose_candidate_by_average_move(best_candidates)
        if chosen is None:
            continue

        _, nx, ny, best_cover = chosen
        repaired.append((nx, ny, ix, iy))

        uncovered_now -= best_cover

        if not uncovered_now:
            break

    return repaired, uncovered_now


# ============================================================
# Phase evaluation
# ============================================================

def evaluate_phase(
    green_rect: Polygon,
    orange_poly: Polygon,
    blue_poly: Polygon,
    markers: List[Point],
    dx: float,
    dy: float
):
    cells, group_cols, group_rows = generate_grid_with_indices(green_rect, dx=dx, dy=dy)

    # --------------------------------------------------------
    # Classify cells into GOOD / BAD only
    # --------------------------------------------------------
    good, bad = classify_cells(
        cells=cells,
        orange_poly=orange_poly,
        blue_poly=blue_poly
    )

    # --------------------------------------------------------
    # 1) Greedy select GOOD cells
    # --------------------------------------------------------
    selected_good, uncovered = greedy_select_cells(good, markers)

    # --------------------------------------------------------
    # 2) Repair BAD cells
    # --------------------------------------------------------
    selected_bad, uncovered_final = repair_bad_cells(
        bad_cells=bad,
        uncovered=uncovered,
        markers=markers,
        orange_poly=orange_poly,
        green_rect=green_rect,
        blue_poly=blue_poly
    )

    selected_all = selected_good + selected_bad

    coverage = 1.0
    if markers:
        coverage = 1.0 - (len(uncovered_final) / len(markers))

    return {
        "dx": dx,
        "dy": dy,
        "coverage": coverage,
        "selected": selected_all,
        "selected_good": selected_good,
        "selected_bad": selected_bad,
        "uncovered_idx": uncovered_final,
        "group_rows": group_rows,
        "group_cols": group_cols
    }


def find_best_phase(
    green_rect: Polygon,
    orange_poly: Polygon,
    blue_poly: Polygon,
    markers: List[Point],
    phase_step: float = PHASE_STEP
):
    dx_list = [i for i in frange(0.0, CELL_W - 1e-9, phase_step)]
    dy_list = [i for i in frange(0.0, CELL_H - 1e-9, phase_step)]

    best: Optional[Dict] = None

    for dy in dy_list:
        for dx in dx_list:
            result = evaluate_phase(green_rect, orange_poly, blue_poly, markers, dx, dy)

            if best is None:
                best = result
                continue

            if result["coverage"] > best["coverage"]:
                best = result
            elif abs(result["coverage"] - best["coverage"]) < 1e-12:
                if len(result["selected"]) < len(best["selected"]):
                    best = result

    if best is None:
        raise RuntimeError("No valid phase was evaluated.")

    return best


# ============================================================
# Plotting
# ============================================================

def plot_scene(
    green: Polygon,
    orange: Polygon,
    blue: Polygon,
    selected_cells: List[Tuple[float, float, int, int]],
    markers: List[Point],
    uncovered_idx: Set[int],
    title: str = ""
):
    fig, ax = plt.subplots()

    def draw_poly(poly: Polygon, color: str, label: str):
        xs = [p[0] for p in poly] + [poly[0][0]]
        ys = [p[1] for p in poly] + [poly[0][1]]
        ax.plot(xs, ys, color=color, label=label)

    draw_poly(green, "green", "Flight Boundary")
    draw_poly(orange, "orange", "Protected Zone")
    draw_poly(blue, "blue", "Target Area")

    for cx, cy, _, _ in selected_cells:
        corners = rect_corners(cx, cy)
        xs = [p[0] for p in corners] + [corners[0][0]]
        ys = [p[1] for p in corners] + [corners[0][1]]
        ax.plot(xs, ys, color="black", linewidth=1.5)

    if uncovered_idx:
        ux = [markers[i][0] for i in uncovered_idx]
        uy = [markers[i][1] for i in uncovered_idx]
        ax.scatter(ux, uy, s=10, color="red", label="Uncovered markers")

    ax.set_aspect("equal")
    ax.legend()
    if title:
        ax.set_title(title)
    plt.show()