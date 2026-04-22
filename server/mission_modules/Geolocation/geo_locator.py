# geo_locator.py
# Python 3.10

import math
from server.mission_modules.Geolocation.data_models import InputData, GeoResult


class GeoLocator:
    """
    Converts a pixel coordinate in an image to a GPS coordinate (lat/lon).
    将图像中的像素坐标转换为GPS坐标（经纬度）。

    Confirmed rules for this version:
    当前版本已确认规则：

    1. x, y are coordinates with the image center as origin.
       x, y 为以图像中心为原点的坐标。
    2. The center point corresponds to the UAV's current GPS position.
       中心点对应无人机当前经纬度。
    3. image_width_px = 1920
    4. image_height_px = 1020
    5. alt_agl_m = 10
    6. ground_width_m_at_10m = 23.47
    7. ground_height_m_at_10m = 33.91
    8. yaw = 0 points north. yaw=0 指北。
    9. yaw is positive clockwise. yaw 顺时针为正。
    """

    @staticmethod
    def locate(data: InputData) -> GeoResult:
        """
        Main entry point. Takes full input data and returns the target GPS coordinate.
        主入口。接收完整输入数据，返回目标点经纬度。
        """
        # Validate all input fields before any calculation.
        # 在计算前先校验所有输入字段。
        GeoLocator._validate_input(data)

        # Step 1: Convert pixel offset to local ground offset in meters.
        # 第一步：将像素偏移转换为局部地面偏移（单位：米）。
        east_local_m, north_local_m = GeoLocator._point_to_ground_offsets(data)

        # Step 2: Rotate local offset by yaw to get world East-North offset.
        # 第二步：将局部偏移按 yaw 旋转，得到世界坐标系下的东北偏移。
        east_world_m, north_world_m = GeoLocator._apply_yaw_rotation(
            east_local_m=east_local_m,
            north_local_m=north_local_m,
            yaw_deg=data.attitude.yaw_deg
        )

        # Step 3: Add world offset to UAV GPS position to get target GPS coordinate.
        # 第三步：将世界坐标偏移叠加到无人机经纬度，得到目标点经纬度。
        target_lat_deg, target_lon_deg = GeoLocator._offset_to_latlon(
            base_lat_deg=data.position.uav_lat_deg,
            base_lon_deg=data.position.uav_lon_deg,
            east_m=east_world_m,
            north_m=north_world_m
        )

        return GeoResult(
            target_lat_deg=target_lat_deg,
            target_lon_deg=target_lon_deg
        )

    @staticmethod
    def _validate_input(data: InputData) -> None:
        """
        Validates that all required input values are physically meaningful.
        校验所有输入值是否符合物理意义（必须大于0）。
        """
        # Image dimensions must be positive.
        # 图像尺寸必须大于0。
        if data.image.image_width_px <= 0:
            raise ValueError("image_width_px must be > 0")

        if data.image.image_height_px <= 0:
            raise ValueError("image_height_px must be > 0")

        # Altitude above ground must be positive.
        # 离地高度必须大于0。
        if data.altitude.alt_agl_m <= 0:
            raise ValueError("alt_agl_m must be > 0")

        # Ground coverage dimensions must be positive.
        # 地面覆盖范围必须大于0。
        if data.coverage.ground_width_m <= 0:
            raise ValueError("ground_width_m_at_10m must be > 0")

        if data.coverage.ground_height_m <= 0:
            raise ValueError("ground_height_m_at_10m must be > 0")

    @staticmethod
    def _point_to_ground_offsets(data: InputData) -> tuple[float, float]:
        """
        Converts (x, y) in the image center coordinate system to local ground offsets in meters.
        将图像中心坐标系中的 (x, y) 转换为局部地面偏移（单位：米）。

        Conventions:
        约定：
        - x is positive to the right.  x 向右为正。
        - y is positive upward.        y 向上为正。
        - When yaw=0, image up corresponds to true north.
          yaw=0 时，图像上方对应真实北方向。
        """
        # Calculate how many meters each pixel represents in x and y directions.
        # 计算每个像素在x方向和y方向上对应的地面距离（米/像素）。
        meters_per_px_x = (
            data.coverage.ground_width_m / data.image.image_width_px
        )
        meters_per_px_y = (
            data.coverage.ground_height_m / data.image.image_height_px
        )

        # Multiply pixel offset by meters-per-pixel to get ground offset in meters.
        # 像素偏移 × 米/像素 = 地面偏移（米）。
        east_local_m = data.point.x * meters_per_px_x
        north_local_m = data.point.y * meters_per_px_y

        return east_local_m, north_local_m

    @staticmethod
    def _apply_yaw_rotation(
        east_local_m: float,
        north_local_m: float,
        yaw_deg: float
    ) -> tuple[float, float]:
        """
        Rotates the local East-North offset by the UAV yaw angle to get the world East-North offset.
        将局部东北偏移按无人机 yaw 角旋转，得到世界坐标系下的东北偏移。

        yaw = 0 points north, positive clockwise.
        yaw=0 指北，顺时针为正。

        Rotation formula:
        旋转公式：
            east_world  =  cos(yaw) * east_local + sin(yaw) * north_local
            north_world = -sin(yaw) * east_local + cos(yaw) * north_local
        """
        # Convert yaw from degrees to radians for math functions.
        # 将 yaw 从度转换为弧度，用于三角函数计算。
        yaw_rad = math.radians(yaw_deg)

        cos_yaw = math.cos(yaw_rad)
        sin_yaw = math.sin(yaw_rad)

        # Apply 2D rotation matrix to transform local offset to world offset.
        # 应用二维旋转矩阵，将局部偏移转换为世界坐标偏移。
        east_world_m = cos_yaw * east_local_m + sin_yaw * north_local_m
        north_world_m = -sin_yaw * east_local_m + cos_yaw * north_local_m

        return east_world_m, north_world_m

    @staticmethod
    def _offset_to_latlon(
        base_lat_deg: float,
        base_lon_deg: float,
        east_m: float,
        north_m: float
    ) -> tuple[float, float]:
        """
        Converts metric East-North offset to a GPS coordinate using small-angle approximation.
        使用小范围近似将东北方向的米偏移转换为经纬度坐标。

        Approximation used:
        使用的近似公式：
        - 1 degree latitude  ≈ 111320 m
          纬度1度 ≈ 111320 米
        - 1 degree longitude ≈ 111320 * cos(latitude) m
          经度1度 ≈ 111320 * cos(纬度) 米
        """
        # Meters per degree latitude is approximately constant globally.
        # 纬度方向每度对应的米数，全球近似为常数。
        meters_per_deg_lat = 111320.0

        # Meters per degree longitude varies with latitude (shrinks toward the poles).
        # 经度方向每度对应的米数随纬度变化（越靠近极点越小）。
        meters_per_deg_lon = 111320.0 * math.cos(math.radians(base_lat_deg))

        # Guard against near-pole latitudes where longitude conversion breaks down.
        # 防止在极点附近经度转换失效（分母接近0）。
        if abs(meters_per_deg_lon) < 1e-12:
            raise ValueError("Invalid latitude for longitude conversion")

        # Convert meter offset to degree offset.
        # 将米偏移转换为度偏移。
        delta_lat_deg = north_m / meters_per_deg_lat
        delta_lon_deg = east_m / meters_per_deg_lon

        # Add degree offset to UAV base position to get target GPS coordinate.
        # 将度偏移叠加到无人机基准经纬度，得到目标点经纬度。
        target_lat_deg = base_lat_deg + delta_lat_deg
        target_lon_deg = base_lon_deg + delta_lon_deg

        return target_lat_deg, target_lon_deg