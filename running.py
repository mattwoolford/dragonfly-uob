import math
from demo import sample_markers_in_blue, find_best_phase, plot_scene, MARKER_STEP, PHASE_STEP, CELL_W, CELL_H

from zuobiaoxi import (
    point_1_exact,
    point_2_exact,
    geo_to_custom_xy,
    build_custom_frame,
)

from path_planner import (
    plan_full_route,
    print_route_summary,
    plot_route_result,
)

# ============================================================
# Geographic conversion helpers
# ============================================================

EARTH_RADIUS_M = 6378137.0


def geo_to_local(lat: float, lon: float, lat0: float, lon0: float):
    """
    Convert geographic coordinates (lat, lon) to local planar coordinates (x, y) in meters,
    using a local tangent-plane approximation around (lat0, lon0).
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lat0_rad = math.radians(lat0)
    lon0_rad = math.radians(lon0)

    x = (lon_rad - lon0_rad) * EARTH_RADIUS_M * math.cos(lat0_rad)
    y = (lat_rad - lat0_rad) * EARTH_RADIUS_M
    return x, y


def local_to_geo(x: float, y: float, lat0: float, lon0: float):
    """
    Convert local planar coordinates (x, y) in meters back to geographic coordinates (lat, lon),
    using the same local tangent-plane approximation around (lat0, lon0).
    """
    lat0_rad = math.radians(lat0)
    lon0_rad = math.radians(lon0)

    lat_rad = lat0_rad + y / EARTH_RADIUS_M
    lon_rad = lon0_rad + x / (EARTH_RADIUS_M * math.cos(lat0_rad))

    lat = math.degrees(lat_rad)
    lon = math.degrees(lon_rad)
    return lat, lon


def polygon_geo_to_local(polygon_geo, lat0, lon0):
    return [geo_to_local(lat, lon, lat0, lon0) for lat, lon in polygon_geo]


def points_local_to_geo(points_local, lat0, lon0):
    return [local_to_geo(x, y, lat0, lon0) for x, y in points_local]


# ============================================================
# New helpers for custom XY <-> geographic conversion
# ============================================================

def points_custom_to_geo(points_custom, point1_geo, point2_geo):
    """
    Convert points from the custom XY frame back to geographic coordinates.

    Custom frame definition:
    - origin at point1_geo
    - +X along point1_geo -> point2_geo
    - +Y perpendicular to +X, chosen as the "north-ish" side
    """
    _, ex, ey = build_custom_frame(point1_geo, point2_geo)

    lat0, lon0 = point1_geo
    points_geo = []

    for x_custom, y_custom in points_custom:
        # Convert custom XY back to East-North
        east = x_custom * ex[0] + y_custom * ey[0]
        north = x_custom * ex[1] + y_custom * ey[1]

        # Convert East-North back to geographic coordinates
        lat, lon = local_to_geo(east, north, lat0, lon0)
        points_geo.append((lat, lon))

    return points_geo


# ============================================================
# Main
# ============================================================

def running(plb_geo=None):
    # --------------------------------------------------------
    # Input polygons from the KML file
    # Format: (latitude, longitude)
    # --------------------------------------------------------

    green_geo = [
        (51.42342595349562, -2.671720766408759),
        (51.42124623420381, -2.670134027271237),
        (51.42244011936099, -2.665687818885850),
        (51.42469179370701, -2.667060227266051),
    ]

    orange_geo = [
        (51.42353586816967, -2.671451754138619),
        (51.42215640321154, -2.669768242108598),
        (51.42267105383615, -2.667705438815299),
        (51.42335592245168, -2.668164601092489),
        (51.42286082606338, -2.670043418345824),
        (51.42326667015552, -2.670965419051837),
        (51.42356862274763, -2.671324297543731),
    ]

    default_blue_geo = [
        (51.42326956502679, -2.670948345438704),
        (51.42287025017865, -2.670045428650557),
        (51.42336622593724, -2.668169295906676),
        (51.42421477437771, -2.668809768621569),
        (51.42354069739116, -2.671277780473196),
    ]

    # --------------------------------------------------------
    # Select blue search region
    # - None: use default initial blue region
    # - Otherwise: use incoming PLB polygon directly
    # --------------------------------------------------------

    if plb_geo is None:
        blue_geo = default_blue_geo
        print("\nUsing default initial blue search region.")
    else:
        if not isinstance(plb_geo, (list, tuple)):
            raise TypeError("plb_geo must be a list or tuple of geographic points.")

        if len(plb_geo) < 3:
            raise ValueError("plb_geo must contain at least 3 geographic points.")

        for p in plb_geo:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                raise ValueError("Each point in plb_geo must be a (lat, lon) pair.")

        blue_geo = list(plb_geo)
        print("\nUsing PLB-provided blue search region.")

    # --------------------------------------------------------
    # Convert all polygons into the custom XY frame first
    # --------------------------------------------------------

    green_rect = geo_to_custom_xy(green_geo, point_1_exact, point_2_exact)
    orange_poly = geo_to_custom_xy(orange_geo, point_1_exact, point_2_exact)
    blue_poly = geo_to_custom_xy(blue_geo, point_1_exact, point_2_exact)

    # --------------------------------------------------------
    # Run the existing planner in custom metric coordinates
    # --------------------------------------------------------

    markers = sample_markers_in_blue(blue_poly, step=MARKER_STEP)
    print(f"Markers (2m step) inside blue: {len(markers)}")

    best = find_best_phase(
        green_rect=green_rect,
        orange_poly=orange_poly,
        blue_poly=blue_poly,
        markers=markers,
        phase_step=PHASE_STEP
    )

    dx = best["dx"]
    dy = best["dy"]
    coverage = best["coverage"]
    selected = best["selected"]
    selected_good = best["selected_good"]
    selected_bad = best["selected_bad"]
    uncovered_idx = best["uncovered_idx"]

    print(f"Best phase: dx={dx:.1f} m, dy={dy:.1f} m")
    print(f"Coverage (marker-based): {coverage * 100:.2f}%")
    print(f"Selected rectangles: {len(selected)}")
    print(f"Selected GOOD cells: {len(selected_good)}")
    print(f"Selected BAD/repair cells: {len(selected_bad)}")
    print(f"Uncovered markers: {len(uncovered_idx)}")

    # --------------------------------------------------------
    # Original rectangle center output
    # --------------------------------------------------------

    center_points_local = [(cx, cy) for cx, cy, _, _ in selected]
    center_points_local = sorted(center_points_local, key=lambda p: (-p[1], p[0]))

    print("\nFinal rectangle center points in custom local meters:")
    for i, (x, y) in enumerate(center_points_local, start=1):
        print(f"{i}: ({x:.2f}, {y:.2f})")

    center_points_geo = points_custom_to_geo(
        center_points_local,
        point_1_exact,
        point_2_exact
    )

    print("\nFinal rectangle center points in geographic coordinates:")
    for i, (lat, lon) in enumerate(center_points_geo, start=1):
        print(f"{i}: ({lat:.7f}, {lon:.7f})")

    print("\nPython list of geographic waypoints (rectangle centers only):")
    print(center_points_geo)

    # --------------------------------------------------------
    # Path planning
    # Use selected_good / selected_bad directly from demo result
    # --------------------------------------------------------

    route_result = plan_full_route(
        good_cells=selected_good,
        repair_cells=selected_bad,
        protected_zone=orange_poly
    )

    print_route_summary(route_result)

    final_route_local = route_result["final_route_points"]
    final_route_geo = points_custom_to_geo(
        final_route_local,
        point_1_exact,
        point_2_exact
    )

    print("\nFinal route points in geographic coordinates:")
    for i, (lat, lon) in enumerate(final_route_geo, start=1):
        print(f"{i}: ({lat:.7f}, {lon:.7f})")

    print("\nPython list of final geographic route:")
    print(final_route_geo)

    # --------------------------------------------------------
    # Plot 1: original selected rectangles
    # --------------------------------------------------------

    plot_scene(
        green_rect,
        orange_poly,
        blue_poly,
        selected_cells=selected,
        markers=markers,
        uncovered_idx=uncovered_idx,
        title=f"Rect {CELL_W}x{CELL_H} | dx={dx:.1f}, dy={dy:.1f} | cov={coverage * 100:.2f}% | n={len(selected)}"
    )

    # --------------------------------------------------------
    # Plot 2: route result
    # --------------------------------------------------------

    plot_route_result(
        green_poly=green_rect,
        orange_poly=orange_poly,
        blue_poly=blue_poly,
        good_cells=selected_good,
        repair_cells=selected_bad,
        result=route_result,
    )

    return final_route_geo