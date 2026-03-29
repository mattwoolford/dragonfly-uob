"""
Aircraft-based simulation / SITL integration test.
基于 Aircraft 类的 SITL 仿真测试。

Runs the geographic waypoints produced by running.running() through the
Aircraft controller against Mission Planner SITL.

Usage / 用法:
    python aircraft_simulation_test.py

Requirements / 依赖:
    - Mission Planner SITL running on TCP 5762
    - pip install pymavlink shapely matplotlib
"""

import asyncio
import time

from Aircraft import Aircraft, DroneState
import running as route_planner   # running.running() returns final_route_geo

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAV_CONNECTION   = "tcp:127.0.0.1:5762"
FLIGHT_ALT_M     = 20.0   # relative altitude for every waypoint (m)
TAKEOFF_ALT_M    = 15.0   # arm-and-takeoff target altitude (m)
ARRIVE_THRESH_M  = 10.0   # distance (m) at which we declare "arrived"
WAYPOINT_TIMEOUT = 90     # max seconds to wait per waypoint
POLL_INTERVAL    = 5      # seconds between status polls


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _fmt_status(s: dict) -> str:
    return (
        f"state={s['state']} | "
        f"pos=({s['lat']:.6f}, {s['lon']:.6f}) | "
        f"alt={s['alt']:.1f} m | "
        f"progress={s['progress_pct']}% | "
        f"remaining={s['remaining_m']} m"
    )


# ---------------------------------------------------------------------------
# Individual test steps
# ---------------------------------------------------------------------------

async def test_connection(aircraft: Aircraft):
    """[T1] Verify telemetry arrives after connect."""
    print("\n[T1] Waiting for first telemetry packet...")
    for _ in range(20):
        if aircraft._telemetry["lat"] is not None:
            break
        await asyncio.sleep(0.5)
    assert aircraft._telemetry["lat"] is not None, \
        "No telemetry received within 10 s – is SITL running?"
    t = aircraft._telemetry
    print(f"    PASS: lat={t['lat']:.6f}, lon={t['lon']:.6f}, alt={t['alt']:.1f} m")


async def test_safety_check(aircraft: Aircraft, waypoints):
    """[T2] Pre-flight geofence check for every waypoint."""
    print("\n[T2] Pre-flight safety check for all waypoints...")
    blocked = []
    for i, (lat, lon) in enumerate(waypoints, 1):
        ok, reason = aircraft.check_safety(lat, lon, FLIGHT_ALT_M)
        mark = "OK  " if ok else "FAIL"
        print(f"    [{mark}] WP{i:02d}: ({lat:.6f}, {lon:.6f}) → {reason}")
        if not ok:
            blocked.append((i, reason))
    if blocked:
        print(f"    WARNING: {len(blocked)} waypoint(s) blocked – they will be skipped.")
    else:
        print(f"    PASS: all {len(waypoints)} waypoints are inside the safe zone.")
    return blocked


async def test_arm_takeoff(aircraft: Aircraft):
    """[T3] Arm and take off to TAKEOFF_ALT_M."""
    print(f"\n[T3] Arming and taking off to {TAKEOFF_ALT_M} m...")
    ok = await aircraft.arm_and_takeoff(TAKEOFF_ALT_M)
    if not ok:
        print("    FAIL: arm_and_takeoff() returned False.")
        return False

    print("    Waiting for climb...", end="", flush=True)
    for _ in range(40):
        await asyncio.sleep(1)
        alt = aircraft._telemetry.get("alt") or 0.0
        print(f"\r    Climbing: {alt:.1f} m   ", end="", flush=True)
        if alt >= TAKEOFF_ALT_M * 0.85:
            print()
            break
    else:
        print()

    alt = aircraft._telemetry.get("alt") or 0.0
    print(f"    PASS: current altitude = {alt:.1f} m")
    return True


async def fly_waypoints(aircraft: Aircraft, waypoints, blocked_indices):
    """[T4] Fly through every safe waypoint sequentially."""
    print(f"\n[T4] Flying {len(waypoints)} waypoints at {FLIGHT_ALT_M} m AGL...")
    blocked_set = {i for i, _ in blocked_indices}

    for i, (lat, lon) in enumerate(waypoints, 1):
        if i in blocked_set:
            print(f"\n  WP{i:02d}: SKIPPED (blocked by geofence)")
            continue

        print(f"\n  WP{i:02d}/{len(waypoints)}: goto ({lat:.6f}, {lon:.6f}, {FLIGHT_ALT_M} m)...")
        result = await aircraft.goto(lat, lon, FLIGHT_ALT_M)
        if not result:
            s = aircraft.get_status()
            print(f"    WARN: goto() blocked – error='{s['error']}'. Skipping.")
            # Reset state so subsequent waypoints can still be attempted
            aircraft._set_state(DroneState.CONNECTED)
            continue

        # Poll until arrived or timeout
        deadline = time.time() + WAYPOINT_TIMEOUT
        arrived  = False
        while time.time() < deadline:
            await asyncio.sleep(POLL_INTERVAL)
            s = aircraft.get_status()
            print(f"    {_fmt_status(s)}")

            if s["state"] == DroneState.ARRIVED.value:
                arrived = True
                break

            rem = s["remaining_m"]
            if rem is not None and rem < ARRIVE_THRESH_M:
                aircraft._set_state(DroneState.ARRIVED)
                aircraft._mission["progress_pct"] = 100.0
                arrived = True
                break

        if arrived:
            print(f"  WP{i:02d}: ARRIVED OK")
        else:
            dist = aircraft._mission['current_dist']
            dist_str = f"{dist:.0f} m away" if dist is not None else "unknown distance"
            print(f"  WP{i:02d}: TIMEOUT (still {dist_str})")

    print("\n  All waypoints processed.")


async def test_rth(aircraft: Aircraft):
    """[T5] Return to launch."""
    print("\n[T5] Returning to launch (RTL)...")
    await aircraft.rth()
    s = aircraft.get_status()
    assert s["state"] == DroneState.RTH.value, f"Expected RTH, got {s['state']}"
    print(f"    PASS: state={s['state']}")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

async def running():
    print("=" * 65)
    print("  Aircraft Simulation Test  –  SITL @ " + MAV_CONNECTION)
    print("=" * 65)

    # ---- Step 0: generate waypoints from path planner ----
    print("\n[Step 0] Running path planner (running.running()) ...")
    final_route_geo = route_planner.running()   # list of (lat, lon)
    print(f"  Planner produced {len(final_route_geo)} geographic waypoints.")
    print("  Waypoints:")
    for i, (lat, lon) in enumerate(final_route_geo, 1):
        print(f"    WP{i:02d}: ({lat:.7f}, {lon:.7f})")

    # ---- Step 1: connect ----
    print(f"\n[Step 1] Connecting to {MAV_CONNECTION} ...")
    aircraft = Aircraft.connect(MAV_CONNECTION)
    aircraft.start_refresh()

    # ---- Tests ----
    await test_connection(aircraft)
    blocked = await test_safety_check(aircraft, final_route_geo)

    armed = await test_arm_takeoff(aircraft)
    if not armed:
        print("\nFATAL: Could not arm. Aborting simulation.")
        aircraft.stop_refresh()
        return

    await fly_waypoints(aircraft, final_route_geo, blocked)
    await test_rth(aircraft)

    aircraft.stop_refresh()

    print("\n" + "=" * 65)
    print("  Simulation complete.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(running())
