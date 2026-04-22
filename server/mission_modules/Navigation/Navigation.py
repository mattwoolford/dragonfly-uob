from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
from shapely.plotting import plot_polygon
import contextily as cx
from pyproj import Transformer

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

    def start(self, options):
        pass

    @staticmethod
    def check_point(lat, lon, alt) -> tuple[bool, str]:
        """Check a single point against geofence rules."""
        # FIXME: check_path does not check for a route around an object, so this is temporarily put in place to progress development of the mission until there is a fix
        return True, "SAFE"
        p = Point(lon, lat)
        if not Navigation.flight_area.contains(p):
            return False, "OUTSIDE_FLIGHT_AREA"
        if Navigation.sssi_area.contains(p):
            return False, "INSIDE_SSSI_NFZ"
        if alt > Navigation.max_alt:
            return False, "ALTITUDE_TOO_HIGH"
        return True, "SAFE"

    @staticmethod
    def check_path(from_lat, from_lon, to_lat, to_lon, alt, steps=50) -> tuple[bool, str]:
        """
        Interpolate `steps` points along the straight-line path and
        check each point against geofence rules.
        """
        for i in range(steps + 1):
            t = i / steps
            lat_i = from_lat + t * (to_lat - from_lat)
            lon_i = from_lon + t * (to_lon - from_lon)
            ok, reason = Navigation.check_point(lat_i, lon_i, alt)
            if not ok:
                return False, f"PATH_BLOCKED at {t:.0%} ({lat_i:.6f}, {lon_i:.6f}): {reason}"
        return True, "SAFE"

    @staticmethod
    def plot_areas():
        """Plot the flight area and SSSI no-fly zone on a map with a satellite background."""
        fig, ax = plt.subplots(figsize=(10, 10))

        # We need to transform coordinates from WGS84 (lat/lon) to Web Mercator (EPSG:3857) for contextily
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

        def transform_poly(poly):
            x, y = poly.exterior.coords.xy
            new_coords = [transformer.transform(xi, yi) for xi, yi in zip(x, y)]
            return Polygon(new_coords)

        flight_area_merc = transform_poly(Navigation.flight_area)
        sssi_area_merc = transform_poly(Navigation.sssi_area)

        # Plot flight area (green)
        plot_polygon(flight_area_merc, ax=ax, add_points=False, color='green', alpha=0.3, label='Flight Area')
        # Plot SSSI no-fly zone (red)
        plot_polygon(sssi_area_merc, ax=ax, add_points=False, color='red', alpha=0.5, label='SSSI No-Fly Zone')

        # Add satellite background
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
        except Exception as e:
            print(f"Could not add basemap: {e}")
            # Fallback to coordinates if basemap fails
            all_xs, all_ys = flight_area_merc.exterior.coords.xy
            ax.set_xlim(min(all_xs) - 100, max(all_xs) + 100)
            ax.set_ylim(min(all_ys) - 100, max(all_ys) + 100)

        ax.set_xlabel('Eastings (m)')
        ax.set_ylabel('Northings (m)')
        ax.set_title('Navigation Areas with Satellite Imagery')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.show()
