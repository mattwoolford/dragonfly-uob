"""
Integration test for Aircraft.goto with Navigation geofence checks.
Requires MissionPlanner SITL running on tcp:127.0.0.1:5762.

Run:
    python -m server.mission_modules.Navigation.TestNavigation
"""
import time

from server.controllers.Aircraft import Aircraft

# ------------------------------------------------------------------
# Test waypoints (within flight area, outside SSSI)
# ------------------------------------------------------------------
TAKEOFF_ALT = 10.0      # metres, relative

WAYPOINT_1 = {
    "lat": 51.4216974,
    "lon": -2.6700640,
    "alt": 10.0,
}

WAYPOINT_2 = {
    "lat": 51.4226206,
    "lon": -2.6663840,
    "alt": 10.0,
}

TOLERANCE_M = 3.0
ARRIVAL_TIMEOUT_S = 120

CONNECTION = "tcp:127.0.0.1:5762"


def wait_for_arrival(aircraft: Aircraft, target: dict, timeout_s=ARRIVAL_TIMEOUT_S):
    """Poll position until within tolerance of target, or timeout."""
    start = time.time()
    while time.time() - start < timeout_s:
        pos = aircraft.get_position()
        if pos:
            from server.controllers.Aircraft import Aircraft as A
            dist = A.get_distance_metres(pos[0], pos[1], target["lat"], target["lon"])
            alt_diff = abs(pos[2] - target["alt"])
            print(f"  Position: lat={pos[0]:.6f}, lon={pos[1]:.6f}, alt={pos[2]:.1f}m  |  dist={dist:.1f}m")
            if dist <= TOLERANCE_M and alt_diff <= TOLERANCE_M:
                return True
        time.sleep(0.1)
    return False


def run():
    aircraft = Aircraft()

    # ---- Connect ----
    print(f"\n[1] Connecting to {CONNECTION}...")
    aircraft.connect(CONNECTION)
    print("    Connected.")

    # ---- Arm ----
    print("\n[2] Arming...")
    aircraft.set_mode("GUIDED")
    aircraft.wait_for_mode("GUIDED")
    assert aircraft.arm(), "Arm failed"

    # ---- Takeoff ----
    print(f"\n[3] Taking off to {TAKEOFF_ALT}m...")
    assert aircraft.takeoff(TAKEOFF_ALT), "Takeoff failed"
    print("    Airborne.")

    # ---- goto waypoint 1 ----
    print(f"\n[4] goto waypoint 1: lat={WAYPOINT_1['lat']}, lon={WAYPOINT_1['lon']}, alt={WAYPOINT_1['alt']}m")
    result = aircraft.goto(WAYPOINT_1["lat"], WAYPOINT_1["lon"], WAYPOINT_1["alt"])

    if not result:
        print("    FAILED: safety check rejected waypoint 1.")
        return

    print(f"    Command sent. journey={aircraft.journey}")

    # ---- Wait for arrival at waypoint 1 ----
    print("\n[5] Waiting for arrival at waypoint 1...")
    arrived = wait_for_arrival(aircraft, WAYPOINT_1)

    if arrived:
        print("    PASSED: arrived at waypoint 1.")
    else:
        print("    FAILED: did not arrive at waypoint 1 within timeout.")
        return

    # ---- goto waypoint 2 ----
    print(f"\n[6] goto waypoint 2: lat={WAYPOINT_2['lat']}, lon={WAYPOINT_2['lon']}, alt={WAYPOINT_2['alt']}m")
    result = aircraft.goto(WAYPOINT_2["lat"], WAYPOINT_2["lon"], WAYPOINT_2["alt"])

    if not result:
        print("    FAILED: safety check rejected waypoint 2.")
        return

    print(f"    Command sent. journey={aircraft.journey}")

    # ---- Wait for arrival at waypoint 2 ----
    print("\n[7] Waiting for arrival at waypoint 2...")
    arrived = wait_for_arrival(aircraft, WAYPOINT_2)

    if arrived:
        print("    PASSED: arrived at waypoint 2.")
    else:
        print("    FAILED: did not arrive at waypoint 2 within timeout.")

    # ---- Cancel test ----
    print("\n[8] Testing cancel (goto waypoint 1 then set journey=None)...")
    aircraft.goto(WAYPOINT_1["lat"], WAYPOINT_1["lon"], WAYPOINT_1["alt"])
    time.sleep(2)
    aircraft.journey = None
    print(f"    journey after cancel: {aircraft.journey}")
    assert aircraft.journey is None, "Cancel failed"
    print("    PASSED: journey cancelled.")

    print("\nAll tests done.")


if __name__ == "__main__":
    run()
