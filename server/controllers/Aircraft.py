import math
import time
from pymavlink import mavutil

from server.controllers.Camera import Camera

class Aircraft:
    """
    Controller for sending flight commands to the aircraft via MAVLink.
    Call Aircraft.connect() to get an instance before using any methods.
    """

    def __init__(self, camera=None, camera_image_save_directory=None):
        self.master = None
        self.connected = False
        self.camera = camera
        self.camera_image_save_directory = camera_image_save_directory

    # ------------------------------------------
    # CONNECTION
    # ------------------------------------------

    def connect(self, connection_string='tcp:127.0.0.1:5762'):
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
        self.connected = True

        print("Requesting telemetry data streams...")
        master.mav.request_data_stream_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_POSITION,
            2,  # 2 Hz update rate
            1   # 1 = start sending
        )
        self.master = master
        return master

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

    def goto(self, lat, lon, alt, tolerance_m=2.0, timeout_s=60):
        """
        Fly to the given GPS coordinates at the specified altitude (metres, relative).
        Blocks until the position is reached or timeout expires.
        Returns True on arrival, False on timeout.
        """
        self.master.mav.set_position_target_global_int_send(
            0, self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            int(0b110111111000),
            int(lat * 1e7), int(lon * 1e7), alt,
            0, 0, 0, 0, 0, 0, 0, 0)
        return self.wait_until_reached(lat, lon, alt, tolerance_m=tolerance_m, timeout_s=timeout_s)

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

    def get_position(self, timeout_s=2.0):
        """
        Returns the current (lat, lon, relative_alt_m, yaw_deg)
        or None on timeout.

        返回当前 (纬度, 经度, 相对高度, 偏航角)，
        超时则返回 None。
        """
        msg = self.master.recv_match(
            type='GLOBAL_POSITION_INT',
            blocking=True,
            timeout=timeout_s
        )
        if not msg:
            return None

        # Try to get yaw from GLOBAL_POSITION_INT.hdg first.
        # 优先从 GLOBAL_POSITION_INT 的 hdg 获取偏航角。
        #
        # hdg unit:
        # - centi-degrees (0.01 degree)
        # - 65535 means unknown
        # hdg 单位：
        # - 0.01 度
        # - 65535 表示未知
        if hasattr(msg, 'hdg') and msg.hdg != 65535:
            yaw_deg = msg.hdg / 100.0
        else:
            # Fallback to ATTITUDE.yaw if hdg is unavailable.
            # 如果没有 hdg，则退回使用 ATTITUDE.yaw。
            att_msg = self.master.recv_match(
                type='ATTITUDE',
                blocking=True,
                timeout=timeout_s
            )
            if not att_msg:
                return None

            yaw_deg = math.degrees(att_msg.yaw)

            # Convert yaw from [-180, 180] to [0, 360).
            # 将 yaw 从 [-180, 180] 转换到 [0, 360)。
            if yaw_deg < 0:
                yaw_deg += 360.0

        return (
            msg.lat / 1e7,
            msg.lon / 1e7,
            msg.relative_alt / 1000.0,
            yaw_deg
        )

    

    def take_photo_with_position(self):
        """
        Capture one image, upload it to the host computer, and return
        the aircraft position together with the image paths.
        """
        position = self.get_position()
        if position is None:
            raise RuntimeError("Failed to get aircraft position before taking photo.")

        lat, lon, rel_alt = position

        camera_helper = Camera()
        path_to_image = camera_helper.capture_and_save_image(
            camera=self.camera,
            save_dir_path=self.camera_image_save_directory
        )

        return {
            "latitude": lat,
            "longitude": lon,
            "relative_altitude_m": rel_alt,
            "path_to_image": path_to_image,
        }

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

    # ------------------------------------------
    # OPERATOR INTERFACE
    # ------------------------------------------

    @staticmethod
    def ask_hitl(prompt_text):
        """
        Block for a Human-In-The-Loop confirmation at the terminal.
        Returns True if the operator confirms with 'y', False otherwise.
        """
        response = input(f"\n>>> [HITL] {prompt_text} (y/n): ").strip().lower()
        return response == 'y'