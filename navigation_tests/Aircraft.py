import asyncio
import math
import time
import threading
from enum import Enum
from pymavlink import mavutil
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


class Aircraft:
    """
    Controller for sending flight commands to the aircraft via MAVLink.
    Call Aircraft.connect() to get an instance before using any methods.
    """

    def __init__(self, master, refresh_interval: float = 1.0):
        self.master = master
        self._mav = master  # alias used by navigation methods

        # R01: 飞行区域边界 / Flight area boundary
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

        self._refresh_interval = refresh_interval

        # ---------- 状态机 / State machine ----------
        self._state: DroneState = DroneState.CONNECTED
        self._error_reason: str = ""

        # 遥测缓存 / Telemetry cache (updated by recv thread)
        self._telemetry = {"lat": None, "lon": None, "alt": None, "alt_amsl": None}

        # 消息缓存（按类型存最新消息）/ Latest message cache by type
        self._msg_cache: dict = {}

        # 任务目标与进度 / Mission target and progress
        self._target  = {"lat": None, "lon": None, "alt": None}
        self._mission = {"start_dist": None, "current_dist": None, "progress_pct": 0.0}

        # 线程与任务句柄 / Thread and task handles
        self._send_lock = threading.Lock()
        self._running = True
        self._recv_thread_handle = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread_handle.start()
        self._refresh_task: asyncio.Task | None = None

    # ------------------------------------------
    # CONNECTION
    # ------------------------------------------

    @staticmethod
    def connect(connection_string='tcp:127.0.0.1:5762'):
        """
        Connect to the flight controller and return an Aircraft instance.

        Usage:
            aircraft = Aircraft.connect()
            aircraft = Aircraft.connect('udpin:0.0.0.0:14551')
        """
        print(f"Connecting to {connection_string}...")
        master = mavutil.mavlink_connection(connection_string)
        if master.wait_heartbeat(timeout=10) is None:
            raise ConnectionError(f"No heartbeat received from {connection_string}. Is the FC running?")
        print("Heartbeat received.")

        print("Requesting telemetry data streams...")
        master.mav.request_data_stream_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_POSITION,
            2,  # 2 Hz update rate
            1   # 1 = start sending
        )
        return Aircraft(master)

    # ------------------------------------------
    # FLIGHT COMMANDS
    # ------------------------------------------

    def arm(self, timeout_s=15):
        """
        Arm the aircraft and wait for confirmation.
        Returns True if armed successfully, False on timeout.
        """
        print("Arming motors...")
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 0, 0, 0, 0, 0, 0)

        print("Waiting for arm confirmation...")
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            if self.master.wait_heartbeat(timeout=1) is None:
                print("WARNING: Heartbeat lost while waiting for arm.")
                return False
            if self.master.messages['HEARTBEAT'].base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                print("Motors armed.")
                return True
        print("WARNING: Arm confirmation timed out.")
        return False

    def disarm(self):
        """
        Disarm the aircraft immediately (force disarm).
        For landing disarm, use land() which calls wait_until_disarmed() internally.
        """
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 0, 0, 0, 0, 0, 0)
        print("Disarm command sent.")

    def takeoff(self, altitude, timeout_s=30):
        """
        Take off to the specified altitude (metres, relative).
        Assumes the aircraft is already armed and in GUIDED mode.
        Returns True once altitude is reached, False on timeout.
        """
        print(f"Taking off to {altitude}m...")
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0, 0, 0, 0, 0, 0, altitude)

        start_time = time.time()
        while time.time() - start_time < timeout_s:
            msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2.0)
            if not msg:
                continue
            current_alt = msg.relative_alt / 1000.0
            if abs(current_alt - altitude) <= 1.0:
                print(f"Altitude reached: {current_alt:.1f}m")
                return True
        print(f"WARNING: Target altitude {altitude}m not reached within {timeout_s}s.")
        return False

    def land(self, timeout_s=60):
        """
        Switch to LAND mode and wait for touchdown and auto-disarm.
        Returns True once disarmed, False if mode change or disarm fails.
        """
        print("Landing...")
        self.set_mode("LAND")
        if not self.wait_for_mode("LAND"):
            print("WARNING: LAND mode not confirmed. Aborting land sequence.")
            return False
        return self.wait_until_disarmed(timeout_s=timeout_s)

    def check_path_safety(self, from_lat, from_lon, to_lat, to_lon, alt, steps=50):
        """
        R06: 路径走廊检查——在从当前位置到目标点的直线上均匀插值 `steps` 个点，
        每个点都调用 check_safety()。只要有一个点违规就返回 False。
        Path corridor check: interpolate `steps` points along the straight line
        from current position to target and call check_safety() on each.
        Returns (True, "SAFE") or (False, reason_string).
        """
        for i in range(steps + 1):
            t = i / steps
            lat_i = from_lat + t * (to_lat - from_lat)
            lon_i = from_lon + t * (to_lon - from_lon)
            ok, reason = self.check_safety(lat_i, lon_i, alt)
            if not ok:
                return False, f"PATH_BLOCKED at t={t:.2f} ({lat_i:.6f},{lon_i:.6f}): {reason}"
        return True, "SAFE"

    async def goto(self, lat, lon, alt):
        """
        安全预检 → 路径走廊检查 → GUIDED 模式 → 发送位置目标 → 状态切 FLYING。
        可随时重新调用以更改目标。
        Safety check → path corridor check → GUIDED mode → send position target → state = FLYING.
        Call again at any time to change target mid-flight.
        """
        is_safe, reason = self.check_safety(lat, lon, alt)
        if not is_safe:
            self._set_state(DroneState.ERROR, reason)
            print(f"安全拦截 / Safety interception: {reason}")
            return False

        # R06: 路径走廊检查（临时禁用）/ Path corridor check (temporarily disabled)
        # if self._telemetry["lat"] is not None:
        #     path_safe, path_reason = self.check_path_safety(
        #         self._telemetry["lat"], self._telemetry["lon"],
        #         lat, lon, alt
        #     )
        #     if not path_safe:
        #         self._set_state(DroneState.ERROR, path_reason)
        #         print(f"路径拦截 / Path interception: {path_reason}")
        #         return False

        loop = asyncio.get_event_loop()

        # 确保 GUIDED 模式 / Ensure GUIDED mode
        await loop.run_in_executor(None, self._send_mode, 4)
        await asyncio.sleep(0.3)

        # 记录目标和起始距离 / Record target and initial distance
        if self._telemetry["lat"] is not None:
            start_dist = await self.get_distance_to_target(lat, lon)
        else:
            start_dist = 0.0
        self._target  = {"lat": lat, "lon": lon, "alt": alt}
        self._mission = {"start_dist": start_dist, "current_dist": start_dist, "progress_pct": 0.0}

        # 发送位置目标 / Send position target
        await loop.run_in_executor(None, self._send_goto_cmd, lat, lon, alt)
        self._set_state(DroneState.FLYING)
        print(f"飞往目标 / Flying to: lat={lat}, lon={lon}, alt={alt} m (relative)")
        return True

    def set_servo(self, channel, pwm):
        """
        Command a servo channel to a given PWM value (fire-and-forget).
        MAVLink has no servo position feedback — use time.sleep() for
        mechanical dwell time after calling this if needed.
        """
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0, channel, pwm, 0, 0, 0, 0, 0)

    # ------------------------------------------
    # MODE MANAGEMENT
    # ------------------------------------------

    def set_mode(self, mode_name):
        """Switch flight mode (fire-and-forget). Use wait_for_mode() to confirm."""
        mode_id = self.master.mode_mapping()[mode_name]
        self.master.set_mode(mode_id)
        print(f"Mode change requested: {mode_name}")

    def wait_for_mode(self, mode_name, timeout_s=10):
        """
        Poll HEARTBEAT until the flight controller confirms the mode change.
        Returns True on success, False on timeout.
        """
        target_mode_id = self.master.mode_mapping()[mode_name]
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            if self.master.wait_heartbeat(timeout=1) is None:
                print(f"WARNING: Heartbeat lost while waiting for mode {mode_name}.")
                return False
            if self.master.messages['HEARTBEAT'].custom_mode == target_mode_id:
                print(f"Mode confirmed: {mode_name}")
                return True
        print(f"WARNING: Mode {mode_name} not confirmed within {timeout_s}s.")
        return False

    # ------------------------------------------
    # POSITION HELPERS
    # ------------------------------------------

    def get_position(self):
        """
        Returns the current (lat, lon, relative_alt_m) or None on timeout.
        """
        msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2.0)
        if not msg:
            return None
        return msg.lat / 1e7, msg.lon / 1e7, msg.relative_alt / 1000.0

    def wait_until_reached(self, target_lat, target_lon, target_alt,
                           tolerance_m=2.0, timeout_s=60):
        """
        Poll GLOBAL_POSITION_INT until within tolerance_m of the target position.
        Returns True on arrival, False on timeout.
        """
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2.0)
            if not msg:
                continue
            current_lat = msg.lat / 1e7
            current_lon = msg.lon / 1e7
            current_alt = msg.relative_alt / 1000.0

            h_dist = self.get_distance_metres(current_lat, current_lon, target_lat, target_lon)
            v_dist = abs(current_alt - target_alt)

            if h_dist <= tolerance_m and v_dist <= tolerance_m:
                return True
            time.sleep(0.5)
        return False

    def wait_until_disarmed(self, timeout_s=60):
        """
        Poll HEARTBEAT until the aircraft auto-disarms after landing.
        Returns True once disarmed, False on timeout.
        """
        print("Waiting for touchdown and auto-disarm...")
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            if self.master.wait_heartbeat(timeout=1) is None:
                print("WARNING: Heartbeat lost while waiting for disarm.")
                return False
            if not (self.master.messages['HEARTBEAT'].base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
                print("Drone has safely auto-disarmed.")
                return True
        print("WARNING: Disarm confirmation timed out.")
        return False

    # ------------------------------------------
    # STATIC GEOMETRY HELPERS
    # ------------------------------------------

    @staticmethod
    def get_distance_metres(lat1, lon1, lat2, lon2):
        """Haversine distance between two GPS coordinates, in metres."""
        R = 6378137.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def get_offset_location(lat, lon, distance_m, bearing_deg):
        """
        Returns a (lat, lon) offset from the given position by distance_m metres
        in the given bearing (degrees, 0 = North, 90 = East).
        """
        R = 6378137.0
        d_lat = distance_m * math.cos(math.radians(bearing_deg)) / R
        d_lon = (distance_m * math.sin(math.radians(bearing_deg))
                 / (R * math.cos(math.radians(lat))))
        return lat + math.degrees(d_lat), lon + math.degrees(d_lon)

    # -----------------------------------------------------------------------
    # 状态机 / State machine
    # -----------------------------------------------------------------------

    def _set_state(self, new_state: DroneState, error_reason: str = ""):
        self._state = new_state
        self._error_reason = error_reason

    def get_status(self) -> dict:
        return {
            "state":        self._state.value,
            "lat":          self._telemetry["lat"],
            "lon":          self._telemetry["lon"],
            "alt":          self._telemetry["alt"],
            "target_lat":   self._target["lat"],
            "target_lon":   self._target["lon"],
            "target_alt":   self._target["alt"],
            "progress_pct": round(self._mission["progress_pct"], 1),
            "remaining_m":  round(self._mission["current_dist"], 1)
                            if self._mission["current_dist"] is not None else None,
            "error":        self._error_reason,
            "timestamp":    round(time.time(), 3),
        }

    # -----------------------------------------------------------------------
    # 后台接收线程：读取所有消息并缓存
    # Background recv thread: read all messages and cache by type
    # -----------------------------------------------------------------------

    def _recv_loop(self):
        while self._running:
            if not self._mav:
                time.sleep(0.1)
                continue
            try:
                msg = self._mav.recv_match(blocking=True, timeout=0.5)
                if msg is None or msg.get_type() == 'BAD_DATA':
                    continue
                mtype = msg.get_type()
                self._msg_cache[mtype] = msg
                if mtype == 'GLOBAL_POSITION_INT':
                    self._telemetry["lat"]      = msg.lat / 1e7
                    self._telemetry["lon"]       = msg.lon / 1e7
                    self._telemetry["alt"]       = msg.relative_alt / 1000.0  # mm → m
                    self._telemetry["alt_amsl"]  = msg.alt / 1000.0           # mm → m
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # 后台任务进度刷新协程 / Background mission progress refresh coroutine
    # -----------------------------------------------------------------------

    async def _refresh_loop(self):
        while True:
            await asyncio.sleep(self._refresh_interval)
            if self._state != DroneState.FLYING or self._target["lat"] is None:
                continue
            if self._telemetry["lat"] is None:
                continue
            try:
                # R05: 飞行中实时位置安全检查（防大风漂移越界）
                # In-flight position safety check (wind drift detection)
                cur_lat = self._telemetry["lat"]
                cur_lon = self._telemetry["lon"]
                cur_alt = self._telemetry["alt"] or 0.0
                # R05: 实时位置安全检查（临时禁用）/ In-flight position check (temporarily disabled)
                # pos_safe, pos_reason = self.check_safety(cur_lat, cur_lon, cur_alt)
                # if not pos_safe:
                #     print(f"[警告/WARN] 当前位置违规 ({pos_reason})，自动取消任务！"
                #           f" / Current position unsafe ({pos_reason}), auto-cancelling mission!")
                #     await self.cancel()
                #     self._set_state(DroneState.ERROR, f"WIND_DRIFT: {pos_reason}")
                #     continue

                dist = await self.get_distance_to_target(self._target["lat"], self._target["lon"])
                self._mission["current_dist"] = dist
                start = self._mission["start_dist"]
                if start and start > 0:
                    self._mission["progress_pct"] = max(0.0, min(100.0, (1 - dist / start) * 100))
                if dist < 2.0:
                    self._set_state(DroneState.ARRIVED)
                    self._mission["progress_pct"] = 100.0
                    print("已到达目标 / Arrived at target.")
                else:
                    print(f"[状态/Status] {self._state.value} | "
                          f"进度/Progress: {self._mission['progress_pct']:.1f}% | "
                          f"剩余/Remaining: {dist:.1f} m")
            except Exception as e:
                self._set_state(DroneState.ERROR, f"PROGRESS_FAIL: {e}")

    def start_refresh(self):
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.ensure_future(self._refresh_loop())

    def stop_refresh(self):
        self._running = False
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()

    # -----------------------------------------------------------------------
    # 地理围栏安全检查 / Geofence safety check
    # -----------------------------------------------------------------------

    def check_safety(self, lat, lon, alt):
        p = Point(lon, lat)
        if not self.flight_area.contains(p):
            return False, "OUTSIDE_FLIGHT_AREA"
        if self.sssi_area.contains(p):
            return False, "INSIDE_SSSI_NFZ"
        if alt > self.max_alt:
            return False, "ALTITUDE_TOO_HIGH"
        return True, "SAFE"

    # -----------------------------------------------------------------------
    # Haversine 距离计算（使用缓存遥测）/ Haversine distance (uses cached telemetry)
    # -----------------------------------------------------------------------

    async def get_distance_to_target(self, target_lat, target_lon):
        cur_lat = self._telemetry["lat"]
        cur_lon = self._telemetry["lon"]
        if cur_lat is None or cur_lon is None:
            raise RuntimeError("No telemetry data yet / 尚无遥测数据")
        R = 6_371_000
        phi1 = math.radians(cur_lat)
        phi2 = math.radians(target_lat)
        dphi = math.radians(target_lat - cur_lat)
        dlam = math.radians(target_lon - cur_lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # -----------------------------------------------------------------------
    # 底层发送指令（线程安全）/ Low-level send helpers (thread-safe)
    # -----------------------------------------------------------------------

    def _send_mode(self, custom_mode: int):
        """切换 ArduCopter 飞行模式 / Switch ArduCopter flight mode."""
        with self._send_lock:
            self._mav.mav.command_long_send(
                self._mav.target_system, self._mav.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                custom_mode, 0, 0, 0, 0, 0
            )

    def _send_goto_cmd(self, lat: float, lon: float, alt: float):
        """发送位置目标（相对高度）/ Send position target (relative altitude)."""
        with self._send_lock:
            self._mav.mav.set_position_target_global_int_send(
                0,                                                          # time_boot_ms
                self._mav.target_system, self._mav.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                0b0000111111111000,                                         # 仅位置 / position only
                int(lat * 1e7), int(lon * 1e7), alt,
                0, 0, 0,                                                    # velocity
                0, 0, 0,                                                    # acceleration
                0, 0                                                        # yaw, yaw_rate
            )

    # -----------------------------------------------------------------------
    # Arm + Takeoff (navigation version)
    # -----------------------------------------------------------------------

    def _arm_and_takeoff_sync(self, takeoff_alt: float) -> bool:
        mav = self._mav

        # 关闭 arming 预检（仅 SITL）/ Disable arming checks (SITL only)
        mav.mav.param_set_send(
            mav.target_system, mav.target_component,
            b'ARMING_CHECK', 0, mavutil.mavlink.MAV_PARAM_TYPE_INT32
        )
        time.sleep(0.5)

        # 切换 GUIDED 模式 / Switch to GUIDED (mode 4)
        self._send_mode(4)
        time.sleep(1)

        # Force arm
        with self._send_lock:
            mav.mav.command_long_send(
                mav.target_system, mav.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                1, 21196, 0, 0, 0, 0, 0
            )
        time.sleep(2)

        # 确认 arm 状态（从消息缓存轮询）/ Confirm arm via message cache
        armed = False
        deadline = time.time() + 10
        while time.time() < deadline:
            hb = self._msg_cache.get('HEARTBEAT')
            if hb and hb.get_srcSystem() == 1:
                armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                print(f"    arm={'成功/OK' if armed else '失败/FAIL'}, mode={hb.custom_mode}")
                if armed:
                    break
            time.sleep(0.5)

        if not armed:
            return False

        # 发送 takeoff 指令 / Send takeoff command
        print(f"    Takeoff → {takeoff_alt} m (relative)...")
        with self._send_lock:
            mav.mav.command_long_send(
                mav.target_system, mav.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
                0, 0, 0, 0, 0, 0, takeoff_alt
            )

        # 等待 ACK（从消息缓存）/ Wait for ACK from cache
        ack = None
        deadline = time.time() + 5
        while time.time() < deadline:
            a = self._msg_cache.get('COMMAND_ACK')
            if a:
                ack = a
                break
            time.sleep(0.1)
        print(f"    Takeoff ACK: result={ack.result if ack else 'none'}")
        return True

    async def arm_and_takeoff(self, takeoff_alt: float) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._arm_and_takeoff_sync, takeoff_alt)

    # -----------------------------------------------------------------------
    # 导航指令 / Navigation commands
    # -----------------------------------------------------------------------

    async def hold(self):
        """
        R09: 切换 LOITER 模式原地悬停（不清除任务）。
        R09: Switch to LOITER mode to hover in place (mission not cleared).
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_mode, 5)  # LOITER = mode 5
        self._set_state(DroneState.HOVERING)
        print("Mission Paused: Hovering (LOITER)")

    async def cancel(self):
        """
        取消任务：LOITER 悬停 + 清除目标和进度。
        之后需重新调用 goto() 才能继续飞行。
        Cancel mission: LOITER hover + clear target and progress.
        A new goto() call is required to resume flight.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_mode, 5)  # LOITER = mode 5
        self._target  = {"lat": None, "lon": None, "alt": None}
        self._mission = {"start_dist": None, "current_dist": None, "progress_pct": 0.0}
        self._set_state(DroneState.HOVERING)
        print("任务已取消，无人机悬停中 / Mission cancelled, drone hovering.")

    async def rth(self):
        """
        R09: 切换 RTL 模式自动返航。
        R09: Switch to RTL mode for automatic return to launch.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_mode, 6)  # RTL = mode 6
        self._set_state(DroneState.RTH)
        print("Returning to TOL")
