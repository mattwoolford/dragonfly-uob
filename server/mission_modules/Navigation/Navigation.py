import math
import time
from itertools import permutations

from shapely.geometry import LineString, Point, Polygon

from server.interfaces.MissionModule import MissionModule


class Navigation(MissionModule):

    """
    Mission module that guides the aircraft to specified coordinates,
    enforcing geofence boundaries before any movement command.
    """

    # R01: Flight area boundary (lon, lat order for Shapely)
    flight_area = Polygon([
        (-2.671720766408759, 51.42342595349562),
        (-2.670134027271237, 51.42124623420381),
        (-2.66568781888585,  51.42244011936099),
        (-2.667060227266051, 51.42469179370701)
    ])

    # R02: SSSI no-fly zone
    sssi_area = Polygon([
        (-2.671451754138619, 51.42353586816967),
        (-2.669768242108598, 51.42215640321154),
        (-2.667705438815299, 51.42267105383615),
        (-2.668164601092489, 51.42335592245168),
        (-2.670043418345824, 51.42286082606338),
        (-2.670965419051837, 51.42326667015552),
        (-2.671324297543731, 51.42356862274763)
    ])

    # R04: Maximum altitude (metres, relative)
    max_alt = 50.0

    # Safety buffer around the SSSI polygon (~11 m)
    _OBSTACLE_BUFFER_DEG = 0.0001

    def start(self, options):
        """
        Route the aircraft to the supplied waypoint, detouring around the SSSI
        no-fly zone if the direct path is blocked.

        options:
            'aircraft' – Aircraft controller instance
            'waypoint' – (lat, lon, alt) destination tuple

        Returns True once the final goto command is sent, False on any safety failure.
        """
        aircraft = options['aircraft']
        lat, lon, alt = options['waypoint']

        ok, reason = Navigation.check_point(lat, lon, alt)
        if not ok:
            print(f"Navigation: destination unsafe: {reason}")
            return False

        pos = None
        for _ in range(20):
            pos = aircraft.get_position()
            if pos:
                break
            time.sleep(0.1)

        if pos is None:
            print("Navigation: cannot get current position, aborting")
            return False

        if pos:
            ok, reason = Navigation.check_path(pos[0], pos[1], lat, lon)
            if not ok:
                print(f"Navigation: direct path blocked ({reason}), planning detour...")
                ok, reason, waypoints = Navigation.find_waypoints(pos[0], pos[1], lat, lon, alt)
                if not ok:
                    print(f"Navigation: no safe route found: {reason}")
                    return False
                for wp_lat, wp_lon in waypoints:
                    print(f"Navigation: via ({wp_lat:.6f}, {wp_lon:.6f})")
                    if not aircraft.goto(wp_lat, wp_lon, alt):
                        return False
                    if not aircraft.wait_for_arrival(wp_lat, wp_lon, alt):
                        print("Navigation: timeout at intermediate waypoint")
                        return False

        return aircraft.goto(lat, lon, alt)

    @staticmethod
    def check_point(lat, lon, alt) -> tuple[bool, str]:
        """Check a single point against geofence rules."""
        p = Point(lon, lat)
        if not Navigation.flight_area.contains(p):
            return False, "OUTSIDE_FLIGHT_AREA"
        if Navigation.sssi_area.contains(p):
            return False, "INSIDE_SSSI_NFZ"
        if alt > Navigation.max_alt:
            return False, "ALTITUDE_TOO_HIGH"
        return True, "SAFE"

    @staticmethod
    def check_path(from_lat, from_lon, to_lat, to_lon, steps=50) -> tuple[bool, str]:
        """
        Interpolate `steps` points along the straight-line path and
        check each point against 2D geofence rules (flight area and SSSI only).
        Altitude is not checked here — use check_point() for that.
        """
        for i in range(steps + 1):
            t = i / steps
            lat_i = from_lat + t * (to_lat - from_lat)
            lon_i = from_lon + t * (to_lon - from_lon)
            p = Point(lon_i, lat_i)
            if not Navigation.flight_area.contains(p):
                return False, f"PATH_BLOCKED at {t:.0%} ({lat_i:.6f}, {lon_i:.6f}): OUTSIDE_FLIGHT_AREA"
            if Navigation.sssi_area.contains(p):
                return False, f"PATH_BLOCKED at {t:.0%} ({lat_i:.6f}, {lon_i:.6f}): INSIDE_SSSI_NFZ"
        return True, "SAFE"

    @staticmethod
    def find_waypoints(
            from_lat, from_lon,
            to_lat, to_lon,
            alt,
    ) -> tuple[bool, str, list[tuple[float, float]]]:
        """
        Compute a detour around the SSSI no-fly zone when the straight-line
        path is blocked.  The destination must itself be a safe point —
        call check_point() before this.

        Strategy
        --------
        1. Expand the SSSI polygon by a small safety buffer.
        2. Build the list of buffered-polygon vertices that are inside the
           flight area and within the 'corridor' between origin and destination
           (i.e. on the same side that shortens the detour).
        3. From those candidates pick the two that produce the shortest
           total path:  origin → entry_corner → exit_corner → destination.
           Both left-side and right-side detours are evaluated; the shorter
           one is returned.
        4. Each waypoint is re-validated with check_point(); if a corner
           happens to fall outside the flight area the method falls back to
           returning an empty waypoint list with ok=False.

        Returns
        -------
        (ok, reason, waypoints)
            ok        – True if a safe detour was found
            reason    – human-readable status string
            waypoints – ordered list of (lat, lon) intermediate waypoints
                        (does NOT include origin or destination)
        """
        buffered_obstacle = Navigation.sssi_area.buffer(Navigation._OBSTACLE_BUFFER_DEG)
        direct_line = LineString([(from_lon, from_lat), (to_lon, to_lat)])

        # If the direct path doesn't actually cross the obstacle, no detour needed.
        if not direct_line.intersects(buffered_obstacle):
            return True, "SAFE", []

        # Collect exterior vertices of the buffered obstacle.
        obstacle_coords = list(buffered_obstacle.exterior.coords)

        # Helper: total path length through a sequence of (lon, lat) points.
        def _path_len(points):
            total = 0.0
            for a, b in zip(points, points[1:]):
                dlat = math.radians(b[1] - a[1])
                dlon = math.radians(b[0] - a[0])
                ha = (math.sin(dlat / 2) ** 2
                      + math.cos(math.radians(a[1])) * math.cos(math.radians(b[1]))
                      * math.sin(dlon / 2) ** 2)
                total += 6378137.0 * 2 * math.atan2(math.sqrt(ha), math.sqrt(1 - ha))
            return total

        origin = (from_lon, from_lat)
        dest = (to_lon, to_lat)

        # Collect buffered-obstacle vertices that are inside the flight area
        # and outside the original SSSI — these are safe detour corners.
        valid_vertices = []
        for lon_v, lat_v in obstacle_coords:
            p = Point(lon_v, lat_v)
            if Navigation.flight_area.contains(p) and not Navigation.sssi_area.contains(p):
                valid_vertices.append((lon_v, lat_v))

        # Try ordered sequences of 1, 2, then 3 intermediate waypoints.
        # Segment intersection is checked against the original SSSI (not the buffer)
        # because the waypoints sit on the buffer boundary and would always trigger
        # intersects() against the buffered polygon.
        best_path = None
        best_len = float("inf")

        for n_wps in range(1, 4):
            for combo in permutations(valid_vertices, n_wps):
                pts = [origin] + list(combo) + [dest]
                segs = [LineString([pts[i], pts[i + 1]]) for i in range(len(pts) - 1)]
                if any(seg.intersects(Navigation.sssi_area) for seg in segs):
                    continue
                length = _path_len(pts)
                if length < best_len:
                    best_len = length
                    best_path = list(combo)

        if best_path is None:
            return False, "NO_DETOUR_FOUND", []

        # Validate each waypoint with the full safety checker.
        waypoints = []
        for lon_w, lat_w in best_path:
            ok, reason = Navigation.check_point(lat_w, lon_w, alt)
            if not ok:
                return False, f"DETOUR_WAYPOINT_UNSAFE: {reason}", []
            waypoints.append((lat_w, lon_w))

        return True, "DETOUR_PLANNED", waypoints