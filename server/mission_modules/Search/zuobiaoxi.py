import math

# ============================================================
# Exact reference points from the KML file
# New X-axis: point_1_exact -> point_2_exact
# ============================================================

point_1_exact = (51.42124623420381, -2.670134027271237)  # (lat, lon)
point_2_exact = (51.42244011936099, -2.66568781888585)   # (lat, lon)

EARTH_RADIUS_M = 6378137.0


# ============================================================
# Geographic -> local East-North
# ============================================================

def geo_to_local_en(points_geo, origin_geo):
    """
    Convert a list of geographic points (lat, lon) to local East-North coordinates (meters),
    using a local tangent-plane approximation around origin_geo.

    Args:
        points_geo: list of (lat, lon)
        origin_geo: (lat0, lon0)

    Returns:
        list of (east, north)
    """
    lat0_deg, lon0_deg = origin_geo
    lat0_rad = math.radians(lat0_deg)
    lon0_rad = math.radians(lon0_deg)

    local_points = []

    for lat_deg, lon_deg in points_geo:
        lat_rad = math.radians(lat_deg)
        lon_rad = math.radians(lon_deg)

        east = (lon_rad - lon0_rad) * EARTH_RADIUS_M * math.cos(lat0_rad)
        north = (lat_rad - lat0_rad) * EARTH_RADIUS_M

        local_points.append((east, north))

    return local_points


# ============================================================
# Build custom coordinate frame
# X-axis = point1 -> point2
# Y-axis = perpendicular to X-axis, chosen to point north-ish
# ============================================================

def build_custom_frame(point1_geo, point2_geo):
    """
    Build a custom 2D coordinate frame.

    Frame definition:
    - origin at point1_geo
    - +X along point1_geo -> point2_geo
    - +Y perpendicular to +X, choosing the side with positive north component

    Args:
        point1_geo: (lat, lon)
        point2_geo: (lat, lon)

    Returns:
        origin_en: (0.0, 0.0)
        ex: unit vector of custom X-axis in East-North coordinates
        ey: unit vector of custom Y-axis in East-North coordinates
    """
    p2_en = geo_to_local_en([point2_geo], point1_geo)[0]
    vx, vy = p2_en

    norm = math.hypot(vx, vy)
    if norm == 0:
        raise ValueError("point1_geo and point2_geo are identical or too close.")

    # Unit vector of new X-axis
    ex = (vx / norm, vy / norm)

    # Two possible perpendicular directions
    ey_candidate_1 = (-ex[1], ex[0])
    ey_candidate_2 = (ex[1], -ex[0])

    # Choose the one that points more toward geographic north
    ey = ey_candidate_1 if ey_candidate_1[1] >= ey_candidate_2[1] else ey_candidate_2

    origin_en = (0.0, 0.0)
    return origin_en, ex, ey


# ============================================================
# East-North -> custom XY
# ============================================================

def en_to_custom_xy(points_en, ex, ey):
    """
    Project East-North coordinates into the custom XY frame.

    Args:
        points_en: list of (east, north)
        ex: custom X-axis unit vector in EN frame
        ey: custom Y-axis unit vector in EN frame

    Returns:
        list of (x_custom, y_custom)
    """
    transformed = []

    for east, north in points_en:
        x_custom = east * ex[0] + north * ex[1]
        y_custom = east * ey[0] + north * ey[1]
        transformed.append((x_custom, y_custom))

    return transformed


# ============================================================
# Geographic -> custom XY
# ============================================================

def geo_to_custom_xy(points_geo, point1_geo, point2_geo):
    """
    Convert geographic coordinates directly into the custom XY frame.

    Args:
        points_geo: list of (lat, lon)
        point1_geo: start of custom X-axis, also the frame origin
        point2_geo: end of custom X-axis direction

    Returns:
        list of (x_custom, y_custom)
    """
    points_en = geo_to_local_en(points_geo, point1_geo)
    _, ex, ey = build_custom_frame(point1_geo, point2_geo)
    return en_to_custom_xy(points_en, ex, ey)