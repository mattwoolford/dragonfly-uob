# geolocation.py
# Python 3.10

from server.interfaces.MissionModule import MissionModule

from config import (
    IMAGE_WIDTH_PX,
    IMAGE_HEIGHT_PX,
    ALT_AGL_M,
    GROUND_WIDTH_M,
    GROUND_HEIGHT_M,
)
from data_models import (
    PointData,
    ImageData,
    PositionData,
    AttitudeData,
    AltitudeData,
    GroundCoverage,
    InputData,
)
from geo_locator import GeoLocator


class Geolocation(MissionModule):
    """
    This mission module implements a methodology to map geographical
    coordinates onto an image, and therefore can identify the geographical
    coordinates of a selected portion of a given image in a search and
    rescue context.

    该任务模块实现图像坐标到地理坐标的映射，
    可用于在搜救场景中识别图像中指定区域对应的地理坐标。
    """

    def _validate_and_extract_options(
        self, options
    ) -> tuple[float, float, float, float, float]:
        """
        Validate input options and extract required fields.
        校验输入参数并提取必要字段。

        Expected options:
        期望输入：
            {
                "px": float,
                "py": float,
                "uav_lat_deg": float,
                "uav_lon_deg": float,
                "yaw_deg": float
            }
        """
        if not isinstance(options, dict):
            raise TypeError("options must be a dict")

        required_keys = ["px", "py", "uav_lat_deg", "uav_lon_deg", "yaw_deg"]
        missing_keys = [key for key in required_keys if key not in options]

        if missing_keys:
            raise ValueError(f"Missing required option(s): {missing_keys}")

        try:
            px = float(options["px"])
            py = float(options["py"])
            uav_lat_deg = float(options["uav_lat_deg"])
            uav_lon_deg = float(options["uav_lon_deg"])
            yaw_deg = float(options["yaw_deg"])
        except (TypeError, ValueError) as exc:
            raise ValueError("All required options must be numeric") from exc

        return px, py, uav_lat_deg, uav_lon_deg, yaw_deg

    def _build_input_data(
        self,
        px: float,
        py: float,
        uav_lat_deg: float,
        uav_lon_deg: float,
        yaw_deg: float,
    ) -> InputData:
        """
        Build the InputData object for GeoLocator.
        为 GeoLocator 构建 InputData 输入对象。
        """
        # Convert raw pixel coordinates to image-center Cartesian coordinates.
        # 将原始像素坐标转换为以图像中心为原点的笛卡尔坐标。
        #
        # Convention:
        # x -> right positive
        # y -> up positive
        # 坐标约定：
        # x 向右为正
        # y 向上为正
        x = px - IMAGE_WIDTH_PX / 2
        y = -(py - IMAGE_HEIGHT_PX / 2)

        point = PointData(x=x, y=y)

        image = ImageData(
            image_width_px=IMAGE_WIDTH_PX,
            image_height_px=IMAGE_HEIGHT_PX,
            timestamp=0.0,  # Reserved for future synchronization. 预留给后续时间同步。
        )

        position = PositionData(
            uav_lat_deg=uav_lat_deg,
            uav_lon_deg=uav_lon_deg,
        )

        attitude = AttitudeData(
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=yaw_deg,
        )

        altitude = AltitudeData(
            alt_agl_m=ALT_AGL_M,
        )

        coverage = GroundCoverage(
            ground_width_m=GROUND_WIDTH_M,
            ground_height_m=GROUND_HEIGHT_M,
        )

        return InputData(
            point=point,
            image=image,
            position=position,
            attitude=attitude,
            altitude=altitude,
            coverage=coverage,
        )

    def start(self, options):
        """
        Start the mission module.

        If you need information to start with, then these can be provided in
        the `options` parameter.

        启动任务模块。
        如果模块启动时需要输入信息，则通过 `options` 传入。

        Expected options / 期望输入：
            {
                "px": float,
                "py": float,
                "uav_lat_deg": float,
                "uav_lon_deg": float,
                "yaw_deg": float
            }

        Returns / 返回：
            GeoResult:
                Contains target_lat_deg and target_lon_deg.
                返回目标点经纬度结果。
        """
        px, py, uav_lat_deg, uav_lon_deg, yaw_deg = self._validate_and_extract_options(options)

        input_data = self._build_input_data(
            px=px,
            py=py,
            uav_lat_deg=uav_lat_deg,
            uav_lon_deg=uav_lon_deg,
            yaw_deg=yaw_deg,
        )

        return GeoLocator.locate(input_data)