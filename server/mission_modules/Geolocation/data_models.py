# data_models.py
# Python 3.10

from dataclasses import dataclass


@dataclass
class PointData:
    """
    Target point coordinates in the image center coordinate system.
    目标点在图像中心坐标系中的坐标。

    Origin is the image center. x is positive right, y is positive up.
    原点为图像中心。x 向右为正，y 向上为正。
    """
    # Horizontal offset from image center in pixels. 目标点距图像中心的水平偏移（像素）。
    x: float
    # Vertical offset from image center in pixels. 目标点距图像中心的垂直偏移（像素）。
    y: float


@dataclass
class ImageData:
    """
    Image metadata. 图像元数据。
    """
    # Image width in pixels. 图像宽度（像素）。
    image_width_px: int
    # Image height in pixels. 图像高度（像素）。
    image_height_px: int
    # Unix timestamp of when the image was captured. 图像拍摄时刻的 Unix 时间戳。
    timestamp: float


@dataclass
class PositionData:
    """
    UAV GPS position at the moment the image was captured.
    图像拍摄时刻无人机的 GPS 位置。

    This corresponds to the center point of the image.
    该位置对应图像的正中心点。
    """
    # UAV latitude in degrees. 无人机纬度（度）。
    uav_lat_deg: float
    # UAV longitude in degrees. 无人机经度（度）。
    uav_lon_deg: float


@dataclass
class AttitudeData:
    """
    UAV attitude (orientation) at the moment the image was captured.
    图像拍摄时刻无人机的姿态（朝向）。

    roll and pitch are reserved for future use (currently assumed to be 0).
    roll 和 pitch 当前保留，暂不参与计算（假设无人机垂直拍摄）。
    yaw = 0 points north, positive clockwise.
    yaw=0 指北，顺时针为正。
    """
    # Roll angle in degrees. 横滚角（度）。
    roll_deg: float
    # Pitch angle in degrees. 俯仰角（度）。
    pitch_deg: float
    # Yaw angle in degrees. 偏航角（度）。
    yaw_deg: float


@dataclass
class AltitudeData:
    """
    UAV altitude above ground level (AGL) at the moment the image was captured.
    图像拍摄时刻无人机的离地高度（AGL，单位：米）。
    """
    # Altitude above ground level in meters. 离地高度（米）。
    alt_agl_m: float


@dataclass
class GroundCoverage:
    """
    Ground area covered by the image at 10m altitude.
    无人机在10米高度时，图像覆盖的地面范围。

    These values are fixed constants determined by the camera and lens.
    这两个值由相机和镜头决定，为固定常数。
    """
    # Ground width covered by the image at 10m altitude in meters. 10米高度时图像覆盖的地面宽度（米）。
    ground_width_m_at_10m: float
    # Ground height covered by the image at 10m altitude in meters. 10米高度时图像覆盖的地面高度（米）。
    ground_height_m_at_10m: float


@dataclass
class InputData:
    """
    Complete input bundle passed to GeoLocator.
    传入 GeoLocator 的完整输入数据包。

    Aggregates all six input data classes into one object.
    将六个输入数据类聚合为一个对象。
    """
    # Target point coordinates. 目标点坐标。
    point: PointData
    # Image metadata. 图像元数据。
    image: ImageData
    # UAV GPS position. 无人机GPS位置。
    position: PositionData
    # UAV attitude. 无人机姿态。
    attitude: AttitudeData
    # UAV altitude. 无人机高度。
    altitude: AltitudeData
    # Ground coverage. 地面覆盖范围。
    coverage: GroundCoverage


@dataclass
class GeoResult:
    """
    Output GPS coordinate of the target point.
    目标点的输出经纬度坐标。
    """
    # Target latitude in degrees. 目标点纬度（度）。
    target_lat_deg: float
    # Target longitude in degrees. 目标点经度（度）。
    target_lon_deg: float