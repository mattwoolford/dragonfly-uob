from running import running


def start():
    """
    Stage 1:
    Run the initial search using the default search area inside running().
    Add 3 fixed transit waypoints in front of the planned search route.

    Returns:
        route_geo: list of (lat, lon)
    """
    planned_route_geo = running()

    transit_points_geo = [
        (51.4218011, -2.6699728),
        (51.4225102, -2.6669633),
        (51.4239386, -2.6678056),
    ]

    route_geo = transit_points_geo + planned_route_geo
    return route_geo


def plb(plb_geo):
    """
    Stage 2:
    Re-plan the route using the incoming PLB polygon
    as the new blue search region.

    Args:
        plb_geo: list of (lat, lon)

    Returns:
        route_geo: list of (lat, lon)
    """
    route_geo = running(plb_geo=plb_geo)
    return route_geo


def main():
    # --------------------------------------------------------
    # Stage 1: initial search route
    # Includes 3 fixed transit points before search waypoints
    # --------------------------------------------------------
    initial_route_geo = start()

    print("\nInitial search route (geo):")
    for i, (lat, lon) in enumerate(initial_route_geo, start=1):
        print(f"{i}: ({lat:.7f}, {lon:.7f})")

    # --------------------------------------------------------
    # Stage 2: PLB route re-planning
    # Replace this example with the real incoming PLB polygon later
    # --------------------------------------------------------
    example_plb_geo = [
        (51.4236844, -2.6698843),
        (51.4235388, -2.6689777),
        (51.4232478, -2.6698118),
        (51.4233465, -2.6700774),
    ]
    plb_route_geo = plb(example_plb_geo)

    print("\nPLB re-planned route (geo):")
    for i, (lat, lon) in enumerate(plb_route_geo, start=1):
        print(f"{i}: ({lat:.7f}, {lon:.7f})")


if __name__ == "__main__":
    main()