from running import running
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
# Built-in example PLB polygon
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
# Unified entry point
# mode options:
# - "reuse"    : return previous saved route
# - "full"     : plan route for default full search area
# - "plb"      : plan route for provided PLB area
# - "plb_demo" : plan route for built-in example PLB area
# ============================================================

def start(mode="full", plb_geo=None, add_transit=True):
    """
    Unified route entry.

    Args:
        mode:
            "reuse"    -> load and return previous saved route
            "full"     -> plan route for default full search area
            "plb"      -> plan route for the provided PLB polygon
            "plb_demo" -> plan route for the built-in example PLB polygon

        plb_geo:
            Required only when mode == "plb".
            Format: list of (lat, lon)

        add_transit:
            If True, prepend fixed transit waypoints.
            Usually useful for "full".

    Returns:
        route_geo: list of (lat, lon)
    """

    if mode == "reuse":
        return _load_route()

    elif mode == "full":
        planned_route_geo = running(plb_geo=None)
        route_geo = TRANSIT_POINTS_GEO + planned_route_geo if add_transit else planned_route_geo
        _save_route(route_geo)
        return route_geo

    elif mode == "plb":
        if plb_geo is None:
            raise ValueError("mode='plb' requires plb_geo input.")

        if not isinstance(plb_geo, (list, tuple)) or len(plb_geo) < 3:
            raise ValueError("plb_geo must be a list/tuple of at least 3 (lat, lon) points.")

        for p in plb_geo:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                raise ValueError("Each PLB point must be a (lat, lon) pair.")

            lat, lon = p
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                raise ValueError("Each PLB point must contain numeric lat/lon values.")

        planned_route_geo = running(plb_geo=plb_geo)
        route_geo = TRANSIT_POINTS_GEO + planned_route_geo if add_transit else planned_route_geo
        _save_route(route_geo)
        return route_geo

    elif mode == "plb_demo":
        planned_route_geo = running(plb_geo=EXAMPLE_PLB_GEO)
        route_geo = TRANSIT_POINTS_GEO + planned_route_geo if add_transit else planned_route_geo
        _save_route(route_geo)
        return route_geo

    else:
        raise ValueError(
            "Invalid mode. Use one of: 'reuse', 'full', 'plb', 'plb_demo'."
        )


def main():
    # --------------------------------------------------------
    # Choose one of the following modes:
    #
    # 1) Reuse previous saved route:
    # route_geo = start(mode="reuse")
    #
    # 2) Full search planning:
    # route_geo = start(mode="full", add_transit=True)
    #
    # 3) Real PLB planning:
    # real_plb_geo = [
    #     (51.4236844, -2.6698843),
    #     (51.4235388, -2.6689777),
    #     (51.4232478, -2.6698118),
    #     (51.4233465, -2.6700774),
    # ]
    # route_geo = start(mode="plb", plb_geo=real_plb_geo, add_transit=False)
    #
    # 4) Demo PLB planning:
    # route_geo = start(mode="plb_demo", add_transit=False)
    # --------------------------------------------------------

    route_geo = start(mode="full", add_transit=True)

    print("\nRoute (geo):")
    for i, (lat, lon) in enumerate(route_geo, start=1):
        print(f"{i}: ({lat:.7f}, {lon:.7f})")

    print(f"\nRoute saved to: {_get_route_file()}")


if __name__ == "__main__":
    main()