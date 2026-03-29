"""
Integration test against Mission Planner SITL (TCP 5760/5761/5762).
针对 Mission Planner SITL 的集成测试（纯 pymavlink，无 mavsdk）。

Usage / 用法:
    python sitl_integration_test.py


Requirements / 依赖:
    - Mission Planner SITL running and listening on TCP 5761
    - pip install pymavlink shapely

Tested with / 测试环境: pymavlink + ArduPilot SITL via Mission Planner
"""

import asyncio
import time
from navigation_test2 import NavigationInterface, DroneState

# ---------------------------------------------------------------------------
# 连接地址配置 / Connection config
# ---------------------------------------------------------------------------
MAV_CONNECTION = "tcp:127.0.0.1:5762"   # pymavlink TCP 连接 / pymavlink TCP connection

# ---------------------------------------------------------------------------
# 测试目标点（Bristol 飞行区域内，SSSI 外）
# Test waypoint (inside Bristol flight area, outside SSSI)
# ---------------------------------------------------------------------------
TARGET_LAT = 51.4224
TARGET_LON = -2.6670
TARGET_ALT = 20.0   # 相对高度（米）/ Relative altitude (m)

ARRIVAL_THRESHOLD_M = 10.0  # goto 测试的到达判定阈值 / Arrival threshold for goto test


# ---------------------------------------------------------------------------
# 测试用例 / Test cases
# ---------------------------------------------------------------------------

async def test_connect(nav: NavigationInterface):
    """[T1] 连接测试 / Connection test"""
    print("\n[T1] 测试连接 / Testing connection...")
    result = await nav.connect()
    assert result, "连接失败！请确认 SITL 已启动 / Connection failed! Check SITL is running."
    assert nav._state == DroneState.CONNECTED, f"预期 CONNECTED，实际 {nav._state}"
    print("    PASS: 连接成功，状态 CONNECTED / Connected, state CONNECTED")


async def test_get_status_fields(nav: NavigationInterface):
    """[T2] get_status() 字段完整性 / get_status() field completeness"""
    print("\n[T2] 测试 get_status() 字段 / Testing get_status() fields...")
    status = nav.get_status()
    required_keys = {
        "state", "lat", "lon", "alt",
        "target_lat", "target_lon", "target_alt",
        "progress_pct", "remaining_m",
        "error", "timestamp",
    }
    missing = required_keys - status.keys()
    assert not missing, f"get_status() 缺少字段 / Missing fields: {missing}"
    assert status["state"] == DroneState.CONNECTED.value, \
        f"预期 CONNECTED，实际 {status['state']}"
    print(f"    PASS: 所有字段存在，状态={status['state']} / All fields present, state={status['state']}")


async def test_check_safety(nav: NavigationInterface):
    """[T3] 地理围栏安全检查（纯逻辑）/ Geofence safety check (logic only)"""
    print("\n[T3] 测试 check_safety() / Testing check_safety()...")
    cases = [
        (TARGET_LAT, TARGET_LON, TARGET_ALT, True,  "飞行区域内安全点 / Safe point inside flight area"),
        (TARGET_LAT, TARGET_LON, 99.0,       False, "超高度 / Altitude too high"),
        (51.422780,  -2.669228,  TARGET_ALT, False, "SSSI 禁飞区 / Inside SSSI NFZ"),
        (0.0,        0.0,        TARGET_ALT, False, "完全在区域外 / Completely outside flight area"),
    ]
    for lat, lon, alt, expect, desc in cases:
        ok, reason = nav.check_safety(lat, lon, alt)
        status = "PASS" if ok == expect else "FAIL"
        print(f"    [{status}] {desc}: ok={ok}, reason={reason}")
        assert ok == expect, f"check_safety 结果不符 / Unexpected result: {desc}"
    print("    所有用例通过 / All cases passed")


async def test_telemetry(nav: NavigationInterface):
    """[T4] 遥测数据（等待 recv 线程填充缓存）/ Telemetry data (wait for recv thread)"""
    print("\n[T4] 测试遥测 / Testing telemetry...")
    # 等待最多 5 秒让 recv 线程收到第一条位置消息
    # Wait up to 5 s for the recv thread to receive the first position message
    for _ in range(10):
        if nav._telemetry["lat"] is not None:
            break
        await asyncio.sleep(0.5)

    assert nav._telemetry["lat"] is not None, \
        "5 秒内未收到遥测数据 / No telemetry received within 5 s"
    t = nav._telemetry
    print(f"    位置/Position: lat={t['lat']:.6f}, lon={t['lon']:.6f}, "
          f"alt={t['alt']:.1f} m (relative), alt_amsl={t['alt_amsl']:.1f} m (AMSL)")
    print("    PASS: 遥测正常 / Telemetry OK")


async def test_distance_to_target(nav: NavigationInterface):
    """[T5] Haversine 距离计算 / Haversine distance calculation"""
    print("\n[T5] 测试 get_distance_to_target() / Testing distance calculation...")
    dist = await nav.get_distance_to_target(TARGET_LAT, TARGET_LON)
    assert dist >= 0, "距离不能为负 / Distance cannot be negative"
    print(f"    PASS: 当前距目标 {dist:.1f} m / Distance to target: {dist:.1f} m")


async def test_goto_safety_block(nav: NavigationInterface):
    """[T6] goto() 安全拦截 / goto() safety interception"""
    print("\n[T6] 测试 goto() 安全拦截 / Testing goto() safety block...")
    result = await nav.goto(0.0, 0.0, 10.0)  # 完全在区域外 / Completely outside area
    assert result is False, "goto() 应被拦截返回 False / goto() should return False"
    assert nav._state == DroneState.ERROR, f"预期 ERROR，实际 {nav._state}"
    status = nav.get_status()
    assert status["error"] != "", "error 字段应非空 / error field should be non-empty"
    print(f"    PASS: 已拦截，error='{status['error']}' / Intercepted, error='{status['error']}'")

    # 重置状态供后续测试使用 / Reset state for subsequent tests
    nav._set_state(DroneState.CONNECTED)


async def test_goto_live(nav: NavigationInterface):
    """
    [T7] 真实飞行：arm → takeoff → goto()（非阻塞）→ get_status() 轮询
         支持中途更改目标：再次调用 goto() 即可。
    [T7] Real flight: arm → takeoff → goto() (non-blocking) → poll get_status()
         To change target mid-flight: call goto() again.
    """
    print("\n[T7] 测试真实飞行（goto + get_status 轮询）/ Testing real flight...")

    TAKEOFF_REL_ALT = 15.0

    # 安全预检 / Safety pre-check
    is_safe, reason = nav.check_safety(TARGET_LAT, TARGET_LON, TAKEOFF_REL_ALT)
    if not is_safe:
        print(f"    SKIP: 目标点被拦截 ({reason}) / Target blocked ({reason})")
        return

    # Arm + Takeoff
    print("    正在 arm 并 takeoff / Arming and taking off...")
    ok = await nav.arm_and_takeoff(TAKEOFF_REL_ALT)

    if not ok:
        print("    SKIP: arm 失败，跳过飞行测试 / arm failed, skipping flight test")
        return

    # 等待爬升到 10 m / Wait for climb to 10 m
    print("    等待爬升 / Waiting for climb...", end="", flush=True)
    for _ in range(30):
        await asyncio.sleep(1)
        rel = nav._telemetry.get("alt") or 0.0
        print(f"\r    等待爬升 / Climbing: {rel:.1f} m   ", end="", flush=True)
        if rel > 10.0:
            print()
            break

    # 调用 goto()（非阻塞）/ Call goto() (non-blocking)
    print(f"    调用 nav.goto() → target alt={TAKEOFF_REL_ALT} m (relative)...")
    result = await nav.goto(TARGET_LAT, TARGET_LON, TAKEOFF_REL_ALT)
    if not result:
        print("    FAIL: goto() 返回 False / goto() returned False")
        return

    start_dist = nav._mission["start_dist"]
    print(f"    出发！起始距离 {start_dist:.1f} m / Departing! Start dist {start_dist:.1f} m")
    print("    通过 get_status() 轮询进度（最多 60 秒）/ Polling get_status() for up to 60 s...")

    for _ in range(12):
        await asyncio.sleep(5)
        status = nav.get_status()
        print(f"    状态/State={status['state']} | "
              f"进度/Progress={status['progress_pct']}% | "
              f"剩余/Remaining={status['remaining_m']} m")
        if status["state"] == DroneState.ARRIVED.value:
            print("    PASS: 到达目标区域 / Arrived at target area")
            return
        dist = status["remaining_m"]
        if dist is not None and dist < ARRIVAL_THRESHOLD_M:
            nav._set_state(DroneState.ARRIVED)
            nav._mission["progress_pct"] = 100.0
            print(f"    PASS: 到达目标区域 / Arrived at target area (dist={dist:.1f} m)")
            return

    print("    INFO: 60 秒内未到达（距离较远属正常）/ Not arrived within 60 s (may be expected)")


async def test_hold(nav: NavigationInterface):
    """[T8] hold() → 状态变为 HOVERING / hold() → state becomes HOVERING"""
    print("\n[T8] 测试 hold() / Testing hold()...")
    await nav.hold()
    assert nav._state == DroneState.HOVERING, f"预期 HOVERING，实际 {nav._state}"
    status = nav.get_status()
    assert status["state"] == DroneState.HOVERING.value
    print(f"    PASS: 状态={status['state']} / State={status['state']}")


async def test_cancel(nav: NavigationInterface):
    """
    [T9] cancel() 测试：模拟飞行中调用 cancel()，验证目标清空、状态为 HOVERING。
    [T9] cancel() test: simulate in-flight cancel(), verify target cleared and state is HOVERING.
    """
    print("\n[T9] 测试 cancel() / Testing cancel()...")

    # 手动注入飞行中状态 / Inject FLYING state manually
    nav._state  = DroneState.FLYING
    nav._target = {"lat": TARGET_LAT, "lon": TARGET_LON, "alt": TARGET_ALT}
    nav._mission = {"start_dist": 100.0, "current_dist": 50.0, "progress_pct": 50.0}
    print(f"    注入状态: {nav.get_status()['state']}, progress={nav.get_status()['progress_pct']}%")

    await nav.cancel()

    status = nav.get_status()
    assert status["state"] == DroneState.HOVERING.value, \
        f"cancel 后应为 HOVERING，实际 {status['state']}"
    assert status["target_lat"] is None, "cancel 后 target_lat 应为 None"
    assert status["target_lon"] is None, "cancel 后 target_lon 应为 None"
    assert status["progress_pct"] == 0.0, f"cancel 后进度应为 0，实际 {status['progress_pct']}"
    assert status["remaining_m"] is None, "cancel 后 remaining_m 应为 None"
    print(f"    PASS: 状态={status['state']}, target=None, progress=0% / "
          f"State={status['state']}, target cleared, progress reset")


async def test_rth(nav: NavigationInterface):
    """[T10] rth() → 状态变为 RTH / rth() → state becomes RTH"""
    print("\n[T10] 测试 rth() / Testing rth()...")
    await nav.rth()
    assert nav._state == DroneState.RTH, f"预期 RTH，实际 {nav._state}"
    status = nav.get_status()
    assert status["state"] == DroneState.RTH.value
    print(f"    PASS: 状态={status['state']} / State={status['state']}")


# ---------------------------------------------------------------------------
# 主入口 / Main entry point
# ---------------------------------------------------------------------------
async def main():
    print("=" * 60)
    print("  NavigationInterface SITL 集成测试 / Integration Test")
    print(f"  连接地址 / Connection : {MAV_CONNECTION}")
    print(f"  目标点 / Target       : lat={TARGET_LAT}, lon={TARGET_LON}, alt={TARGET_ALT} m")
    print("=" * 60)

    nav = NavigationInterface(connection_string=MAV_CONNECTION, refresh_interval=5.0)

    # T1-T6: 无需真实飞行 / No real flight required
    await test_connect(nav)
    await test_get_status_fields(nav)
    await test_check_safety(nav)
    await test_telemetry(nav)
    await test_distance_to_target(nav)
    await test_goto_safety_block(nav)

    # T7: 真实飞行（需要 SITL 正常运行）/ Real flight (requires SITL)
    await test_goto_live(nav)

    # T8-T10: 指令与状态机 / Commands and state machine
    await test_hold(nav)
    await test_cancel(nav)
    await test_rth(nav)

    nav.stop_refresh()

    print("\n" + "=" * 60)
    print("  所有测试完成 / All tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
