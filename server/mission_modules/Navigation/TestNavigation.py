"""
Integration test for Navigation.start() with detour logic.
Requires MissionPlanner SITL running on tcp:127.0.0.1:5762.

Run:
    python -m server.mission_modules.Navigation.TestNavigation
"""
import time

from server.controllers.Aircraft import Aircraft
from server.mission_modules.Navigation.Navigation import Navigation

TAKEOFF_ALT = 10.0
TOLERANCE_M = 2.0
ARRIVAL_TIMEOUT_S = 120
CONNECTION = "tcp:127.0.0.1:5762"

WAYPOINT_DIRECT = {"lat": 51.4234770, "lon": -2.6692110, "alt": 10.0}
WAYPOINT_DETOUR = {"lat": 51.4232,    "lon": -2.6713,    "alt": 10.0}


def wait_for_arrival(aircraft: Aircraft, target: dict, timeout_s=ARRIVAL_TIMEOUT_S):
    start = time.time()
    while time.time() - start < timeout_s:
        pos = aircraft.get_position()
        if pos:
            dist = Aircraft.get_distance_metres(pos[0], pos[1], target["lat"], target["lon"])
            alt_diff = abs(pos[2] - target["alt"])
            print(f"  pos=({pos[0]:.6f}, {pos[1]:.6f}, {pos[2]:.1f}m)  dist={dist:.1f}m")
            if dist <= TOLERANCE_M and alt_diff <= TOLERANCE_M:
                return True
        time.sleep(0.5)
    return False


def run():
    aircraft = Aircraft()
    nav = Navigation()

    # [1] Connect
    print(f"\n[1] Connecting to {CONNECTION}...")
    aircraft.connect(CONNECTION)
    print("    Connected.")

    # [2] Arm
    print("\n[2] Arming...")
    aircraft.set_mode("GUIDED")
    aircraft.wait_for_mode("GUIDED")
    assert aircraft.arm(), "Arm failed"

    # [3] Takeoff
    print(f"\n[3] Taking off to {TAKEOFF_ALT}m...")
    assert aircraft.takeoff(TAKEOFF_ALT), "Takeoff failed"
    print("    Airborne.")

    # [4] Navigate to WAYPOINT_DIRECT (may detour if takeoff crosses SSSI)
    print(f"\n[4] Navigation.start() -> WAYPOINT_DIRECT {WAYPOINT_DIRECT}")
    result = nav.start({"aircraft": aircraft, "waypoint": (WAYPOINT_DIRECT["lat"], WAYPOINT_DIRECT["lon"], WAYPOINT_DIRECT["alt"])})
    assert result, "FAILED: Navigation.start() could not reach WAYPOINT_DIRECT"
    assert wait_for_arrival(aircraft, WAYPOINT_DIRECT), "FAILED: did not arrive at WAYPOINT_DIRECT"
    print("    PASSED: arrived at WAYPOINT_DIRECT.")

    # [5] Navigate to WAYPOINT_DETOUR (direct path crosses SSSI, should detour)
    print(f"\n[5] Navigation.start() -> WAYPOINT_DETOUR {WAYPOINT_DETOUR}")
    result = nav.start({"aircraft": aircraft, "waypoint": (WAYPOINT_DETOUR["lat"], WAYPOINT_DETOUR["lon"], WAYPOINT_DETOUR["alt"])})
    assert result, "FAILED: Navigation.start() could not find safe route to WAYPOINT_DETOUR"
    assert wait_for_arrival(aircraft, WAYPOINT_DETOUR), "FAILED: did not arrive at WAYPOINT_DETOUR"
    print("    PASSED: arrived at WAYPOINT_DETOUR via detour.")

    print("\nAll tests done.")


if __name__ == "__main__":
    run()
