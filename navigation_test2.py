import asyncio
import math
import time
from enum import Enum
from mavsdk import System
from shapely.geometry import Point, Polygon


# ---------------------------------------------------------------------------
# 状态枚举 / State Enumeration
# ---------------------------------------------------------------------------
class DroneState(Enum):
    IDLE        = "IDLE"        # 未连接 / Not connected
    CONNECTING  = "CONNECTING"  # 正在连接 / Connecting
    CONNECTED   = "CONNECTED"   # 已连接，待命 / Connected, standby
    FLYING      = "FLYING"      # 正在飞往目标 / Flying to target
    HOVERING    = "HOVERING"    # 悬停中 / Hovering
    ARRIVED     = "ARRIVED"     # 已到达目标 / Arrived at target
    RTH         = "RTH"         # 返航中 / Returning to launch
    ERROR       = "ERROR"       # 错误 / Error


# ---------------------------------------------------------------------------
# 主类 / Main Class
# ---------------------------------------------------------------------------
class NavigationInterface:
    def __init__(self, drone_instance=None, refresh_interval: float = 5.0):
        self.drone = drone_instance if drone_instance else System()

        # R01: 飞行区域边界（KML 导入，Shapely 使用经度在前）
        # R01: Flight area boundary (from KML; Shapely uses longitude-first)
        self.flight_area = Polygon([
            (-2.671720766408759, 51.42342595349562),
            (-2.670134027271237, 51.42124623420381),
            (-2.66568781888585,  51.42244011936099),
            (-2.667060227266051, 51.42469179370701)
        ])

        # R02: SSSI 禁飞区边界 / SSSI no-fly zone boundary
        self.sssi_area = Polygon([
            (-2.671451754138619, 51.42353586816967),
            (-2.669768242108598, 51.42215640321154),
            (-2.667705438815299, 51.42267105383615),
            (-2.668164601092489, 51.42335592245168),
            (-2.670043418345824, 51.42286082606338),
            (-2.670965419051837, 51.42326667015552),
            (-2.671324297543731, 51.42356862274763)
        ])

        # R04: 最大飞行高度 / Maximum altitude
        self.max_alt = 50.0

        # 刷新间隔（秒）/ Status refresh interval (seconds)
        self._refresh_interval = refresh_interval

        # ---------- 状态机内部数据 / State machine internal data ----------
        self._state: DroneState = DroneState.IDLE

        # 当前遥测数据 / Current telemetry snapshot
        self._telemetry = {
            "lat": None,
            "lon": None,
            "alt": None,
        }

        # 当前任务目标 / Active mission target
        self._target = {
            "lat": None,
            "lon": None,
            "alt": None,
        }

        # 任务进度数据 / Mission progress data
        self._mission = {
            "start_dist": None,   # 起始距离（米）/ Initial distance (m)
            "current_dist": None, # 当前剩余距离（米）/ Current remaining distance (m)
            "progress_pct": 0.0,  # 完成百分比 / Completion percentage
        }

        # 错误信息 / Error information
        self._error_reason: str = ""

        # 后台刷新任务句柄 / Background refresh task handle
        self._refresh_task: asyncio.Task | None = None

    # -----------------------------------------------------------------------
    # 状态机写入（内部使用）/ State transition (internal)
    # -----------------------------------------------------------------------
    def _set_state(self, new_state: DroneState, error_reason: str = ""):
        self._state = new_state
        self._error_reason = error_reason

    # -----------------------------------------------------------------------
    # 地面站接口：获取完整状态快照
    # Ground station interface: get a full status snapshot
    # -----------------------------------------------------------------------
    def get_status(self) -> dict:
        """
        返回当前无人机状态快照（地面站轮询入口）。
        所有字段均可直接序列化为 JSON。

        Returns the current UAV status snapshot (ground station polling entry point).
        All fields are directly JSON-serialisable.
        """
        return {
            # 状态机状态 / State machine state
            "state":          self._state.value,

            # 遥测位置 / Telemetry position
            "lat":            self._telemetry["lat"],
            "lon":            self._telemetry["lon"],
            "alt":            self._telemetry["alt"],

            # 当前任务目标 / Active mission target
            "target_lat":     self._target["lat"],
            "target_lon":     self._target["lon"],
            "target_alt":     self._target["alt"],

            # 任务进度 / Mission progress
            "progress_pct":   round(self._mission["progress_pct"], 1),
            "remaining_m":    round(self._mission["current_dist"], 1)
                              if self._mission["current_dist"] is not None else None,

            # 错误原因（无错误时为空字符串）/ Error reason (empty string when no error)
            "error":          self._error_reason,

            # 快照时间戳（Unix 秒）/ Snapshot timestamp (Unix seconds)
            "timestamp":      round(time.time(), 3),
        }

    # -----------------------------------------------------------------------
    # 后台定时刷新协程 / Background periodic refresh coroutine
    # -----------------------------------------------------------------------
    async def _refresh_loop(self):
        """
        每隔 self._refresh_interval 秒刷新一次遥测数据和任务进度。
        Refresh telemetry and mission progress every self._refresh_interval seconds.
        """
        while True:
            await asyncio.sleep(self._refresh_interval)

            # 仅在已连接时更新遥测 / Only update telemetry when connected
            if self._state in (DroneState.FLYING, DroneState.HOVERING,
                               DroneState.CONNECTED, DroneState.ARRIVED,
                               DroneState.RTH):
                try:
                    async for pos in self.drone.telemetry.position():
                        self._telemetry["lat"] = pos.latitude_deg
                        self._telemetry["lon"] = pos.longitude_deg
                        self._telemetry["alt"] = pos.absolute_altitude_m
                        break
                except Exception as e:
                    self._set_state(DroneState.ERROR, f"TELEMETRY_FAIL: {e}")
                    continue

            # 飞行中：更新任务进度 / While flying: update mission progress
            if self._state == DroneState.FLYING and self._target["lat"] is not None:
                try:
                    dist = await self.get_distance_to_target(
                        self._target["lat"], self._target["lon"]
                    )
                    self._mission["current_dist"] = dist

                    start = self._mission["start_dist"]
                    if start and start > 0:
                        self._mission["progress_pct"] = max(
                            0.0, min(100.0, (1 - dist / start) * 100)
                        )

                    # 到达判定：距目标 < 2 m / Arrival: within 2 m of target
                    if dist < 2.0:
                        self._set_state(DroneState.ARRIVED)
                        self._mission["progress_pct"] = 100.0
                        print("已到达目标 / Arrived at target.")

                    else:
                        print(
                            f"[状态/Status] {self._state.value} | "
                            f"进度/Progress: {self._mission['progress_pct']:.1f}% | "
                            f"剩余/Remaining: {dist:.1f} m"
                        )
                except Exception as e:
                    self._set_state(DroneState.ERROR, f"PROGRESS_FAIL: {e}")

    # -----------------------------------------------------------------------
    # 启动后台刷新任务 / Start background refresh task
    # -----------------------------------------------------------------------
    def start_refresh(self):
        """
        启动状态刷新后台协程（需在 asyncio 事件循环内调用）。
        Start the background status refresh coroutine (must be called inside an asyncio event loop).
        """
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.ensure_future(self._refresh_loop())

    def stop_refresh(self):
        """停止刷新任务 / Stop the refresh task."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()

    # -----------------------------------------------------------------------
    # 连接 / Connect
    # -----------------------------------------------------------------------
    async def connect(self, address=None):
        """
        智能连接接口。复用已有连接或按地址建立新连接，并自动启动状态刷新。
        Smart connection interface. Reuse an existing connection or connect to the
        given address, then automatically start the status refresh loop.
        """
        self._set_state(DroneState.CONNECTING)

        # 尝试复用已有连接 / Try to reuse an existing connection
        try:
            async for state in self.drone.core.connection_state():
                if state.is_connected:
                    print("Navigation module: Using existing active connection.")
                    self._set_state(DroneState.CONNECTED)
                    self.start_refresh()
                    return True
                break
        except Exception:
            print("No active connection found, attempting to connect...")

        # 建立新连接 / Establish a new connection
        # 推荐地址 / Recommended addresses:
        #   仿真 / Simulation : udp://:14540
        #   实机 / Real drone : serial:///dev/ttyAMA0:57600
        target_address = address if address else "udp://:14540"

        try:
            await self.drone.connect(system_address=target_address)
            print(f"Connecting to drone at {target_address}...")

            async for state in self.drone.core.connection_state():
                if state.is_connected:
                    print(f"Successfully connected to {target_address}")
                    self._set_state(DroneState.CONNECTED)
                    self.start_refresh()
                    return True
        except Exception as e:
            self._set_state(DroneState.ERROR, f"CONNECTION_FAIL: {e}")
            print(f"Connection failed: {e}")
            return False

    # -----------------------------------------------------------------------
    # 地理围栏安全检查 / Geofence safety check
    # -----------------------------------------------------------------------
    def check_safety(self, lat, lon, alt):
        """
        R30 自动地理围栏预检查。
        R30 automatic geofence pre-check. [cite: 28, 30]
        """
        p = Point(lon, lat)
        if not self.flight_area.contains(p):
            return False, "OUTSIDE_FLIGHT_AREA"
        if self.sssi_area.contains(p):
            return False, "INSIDE_SSSI_NFZ"
        if alt > self.max_alt:
            return False, "ALTITUDE_TOO_HIGH"
        return True, "SAFE"

    # -----------------------------------------------------------------------
    # Haversine 距离计算 / Haversine distance calculation
    # -----------------------------------------------------------------------
    async def get_distance_to_target(self, target_lat, target_lon):
        """
        从遥测流读取当前位置，用 Haversine 公式返回水平距离（米）。
        Read current position from telemetry and return horizontal distance (m) via Haversine.
        """
        async for pos in self.drone.telemetry.position():
            cur_lat = pos.latitude_deg
            cur_lon = pos.longitude_deg
            break

        R = 6_371_000  # 地球平均半径（米）/ Mean Earth radius (m)
        phi1, phi2 = math.radians(cur_lat), math.radians(target_lat)
        dphi = math.radians(target_lat - cur_lat)
        dlam = math.radians(target_lon - cur_lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # -----------------------------------------------------------------------
    # 核心导航指令 / Core navigation command
    # -----------------------------------------------------------------------
    async def goto(self, lat, lon, alt):
        """
        R30 核心导航：安全预检查 → 发送指令 → 状态机切换为 FLYING。
        进度由后台 _refresh_loop 定时更新，地面站通过 get_status() 轮询即可。

        R30 core navigation: safety pre-check → send command → state machine switches to FLYING.
        Progress is updated by the background _refresh_loop; ground station polls via get_status().
        """
        # 1. 安全预检查 / Safety pre-check
        is_safe, reason = self.check_safety(lat, lon, alt)
        if not is_safe:
            self._set_state(DroneState.ERROR, reason)
            print(f"安全拦截 / Safety interception: {reason}")
            return False

        # 2. 记录目标与起始距离 / Record target and initial distance
        start_dist = await self.get_distance_to_target(lat, lon)
        self._target = {"lat": lat, "lon": lon, "alt": alt}
        self._mission = {
            "start_dist":   start_dist,
            "current_dist": start_dist,
            "progress_pct": 0.0,
        }

        # 3. 发送飞控指令 / Send flight controller command
        await self.drone.action.goto_location(lat, lon, alt, 0)

        # 4. 切换状态，由后台协程接管进度监测
        # 4. Switch state; background coroutine takes over progress monitoring
        self._set_state(DroneState.FLYING)
        print(f"飞往目标 / Flying to target: lat={lat}, lon={lon}, alt={alt} m")
        return True

    # -----------------------------------------------------------------------
    # 悬停 / Hold
    # -----------------------------------------------------------------------
    async def hold(self):
        """
        R09: 立即中断任务并悬停。
        R09: Immediately interrupt the mission and hover in place. [cite: 28]
        """
        await self.drone.action.hold()
        self._set_state(DroneState.HOVERING)
        print("Mission Paused: Hovering")

    # -----------------------------------------------------------------------
    # 取消任务并悬停 / Cancel mission and hover
    # -----------------------------------------------------------------------
    async def cancel(self):
        """
        取消当前飞行任务：清空目标与进度数据，然后原地悬停。
        与 hold() 的区别：hold() 仅暂停，cancel() 会同时清除任务状态，
        之后需重新调用 goto() 才能继续飞行。

        Cancel the current flight mission: clear target and progress data, then hover.
        Difference from hold(): hold() only pauses, cancel() also clears mission state —
        a new goto() call is required to resume flight afterwards.
        """
        # 发送悬停指令给飞控 / Send hold command to flight controller
        await self.drone.action.hold()

        # 清空任务目标 / Clear mission target
        self._target = {"lat": None, "lon": None, "alt": None}

        # 重置进度数据 / Reset progress data
        self._mission = {
            "start_dist":   None,
            "current_dist": None,
            "progress_pct": 0.0,
        }

        # 切换至悬停状态 / Transition to HOVERING state
        self._set_state(DroneState.HOVERING)
        print("任务已取消，无人机悬停中 / Mission cancelled, drone hovering.")

    # -----------------------------------------------------------------------
    # 返航 / Return to launch
    # -----------------------------------------------------------------------
    async def rth(self):
        """
        R09: 触发自动返航（RTL）。
        R09: Trigger automatic Return to Launch (RTL). [cite: 28]
        """
        await self.drone.action.return_to_launch()
        self._set_state(DroneState.RTH)
        print("Returning to TOL")
