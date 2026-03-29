from server.interfaces.MissionModule import MissionModule
from .running import running
from pathlib import Path
import json


# ============================================================
# Fixed transit waypoints
# ============================================================

TRANSIT_POINTS_GEO = [
    (51.4218011, -2.6699728),
    (51.4225102, -2.6669633),
    (51.4239386, -2.6678056),
]

# ============================================================
# Example PLB polygon
# ============================================================

EXAMPLE_PLB_GEO = [
    (51.4236844, -2.6698843),
    (51.4235388, -2.6689777),
    (51.4232478, -2.6698118),
    (51.4233465, -2.6700774),
]


# ============================================================
# File helpers
# Save previous route to Desktop/Path/last_route.json
# ============================================================

def _get_route_file():
    """
    Get the file path used to save the latest route.
    Folder: Desktop/Path
    File:   last_route.json
    """
    desktop = Path.home() / "Desktop"
    folder = desktop / "Path"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "last_route.json"


def _save_route(route_geo):
    """
    Save route to JSON file.
    """
    route_file = _get_route_file()

    data = {
        "route_geo": [[lat, lon] for lat, lon in route_geo]
    }

    with open(route_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_route():
    """
    Load route from JSON file.
    """
    route_file = _get_route_file()

    if not route_file.exists():
        raise FileNotFoundError(f"No previous route file found: {route_file}")

    with open(route_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "route_geo" not in data:
        raise ValueError("Route file is invalid: missing 'route_geo'.")

    route_geo = []
    for p in data["route_geo"]:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError("Route file contains invalid point format.")
        route_geo.append((float(p[0]), float(p[1])))

    return route_geo


# ============================================================
# Search Mission Module
# ============================================================

class Search(MissionModule):
    """
    This mission module implements path planning for field search,
    including optional PLB-based replanning.
    """

    def _validate_plb_geo(self, plb_geo):
        """
        Validate PLB polygon input.
        """
        if plb_geo is None:
            raise ValueError("mode='plb' requires 'plb_geo' in options.")

        if not isinstance(plb_geo, (list, tuple)) or len(plb_geo) < 3:
            raise ValueError("plb_geo must be a list/tuple of at least 3 (lat, lon) points.")

        validated = []
        for p in plb_geo:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                raise ValueError("Each PLB point must be a (lat, lon) pair.")

            lat, lon = p
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                raise ValueError("Each PLB point must contain numeric lat/lon values.")

            validated.append((float(lat), float(lon)))

        return validated

    def _finalise_route(self, planned_route_geo, add_transit):
        """
        Add optional transit points, save the route, and return it.
        """
        route_geo = TRANSIT_POINTS_GEO + planned_route_geo if add_transit else planned_route_geo
        _save_route(route_geo)
        return route_geo

    def start(self, options):
        """
        Start the mission module.

        Expected options format:
            {
                "mode": "full" | "reuse" | "plb" | "plb_demo",
                "plb_geo": [(lat, lon), ...],   # required only for mode="plb"
                "add_transit": True | False     # optional, default True
            }

        Returns:
            route_geo: list of (lat, lon)
        """
        if options is None:
            options = {}

        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary.")

        mode = options.get("mode", "full")
        plb_geo = options.get("plb_geo", None)
        add_transit = options.get("add_transit", True)

        if not isinstance(add_transit, bool):
            raise ValueError("add_transit must be True or False.")

        if mode == "reuse":
            return _load_route()

        elif mode == "full":
            planned_route_geo = running(plb_geo=None)
            return self._finalise_route(planned_route_geo, add_transit)

        elif mode == "plb":
            validated_plb_geo = self._validate_plb_geo(plb_geo)
            planned_route_geo = running(plb_geo=validated_plb_geo)
            return self._finalise_route(planned_route_geo, add_transit)

        elif mode == "plb_demo":
            planned_route_geo = running(plb_geo=EXAMPLE_PLB_GEO)
            return self._finalise_route(planned_route_geo, add_transit)

        else:
            raise ValueError(
                "Invalid mode. Use one of: 'reuse', 'full', 'plb', 'plb_demo'."
            )