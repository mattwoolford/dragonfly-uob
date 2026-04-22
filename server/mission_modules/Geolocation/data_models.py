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
    x: float  # Horizontal offset from image center in pixels. 目标点距图像中心的水平偏移（像素）。
    y: float  # Vertical offset from image center in pixels.   目标点距图像中心的垂直偏移（像素）。


@dataclass
class ImageData:
    """
    Image metadata.
    图像元数据。
    """
    image_width_px: int   # Image width in pixels. 图像宽度（像素）。
    image_height_px: int  # Image height in pixels. 图像高度（像素）。
    timestamp: float      # Unix timestamp of image capture. 图像拍摄时刻的 Unix 时间戳。


@dataclass
class PositionData:
    """
    UAV GPS position at the moment the image was captured.
    图像拍摄时刻无人机的 GPS 位置。

    This corresponds to the center point of the image.
    该位置对应图像正中心点。
    """
    uav_lat_deg: float  # UAV latitude in degrees. 无人机纬度（度）。
    uav_lon_deg: float  # UAV longitude in degrees. 无人机经度（度）。


@dataclass
class AttitudeData:
    """
    UAV attitude (orientation) at the moment the image was captured.
    图像拍摄时刻无人机的姿态（朝向）。

    roll and pitch are reserved for future use and currently assumed to be 0.
    roll 和 pitch 当前保留，暂不参与计算，当前默认取 0。
    yaw = 0 points north, positive clockwise.
    yaw=0 指北，顺时针为正。
    """
    roll_deg: float   # Roll angle in degrees. 横滚角（度）。
    pitch_deg: float  # Pitch angle in degrees. 俯仰角（度）。
    yaw_deg: float    # Yaw angle in degrees. 偏航角（度）。


@dataclass
class AltitudeData:
    """
    UAV altitude above ground level (AGL) at the moment the image was captured.
    图像拍摄时刻无人机的离地高度（AGL，单位：米）。
    """
    alt_agl_m: float  # Altitude above ground level in meters. 离地高度（米）。


@dataclass
class GroundCoverage:
    """
    Ground area covered by the image at 30m altitude.
    无人机在30米高度时，图像覆盖的地面范围。

    These values are fixed constants determined by the camera and lens.
    这两个值由相机和镜头决定，为固定常数。
    """
    ground_width_m: float   # Ground width covered at 30m altitude. 30米高度时图像覆盖的地面宽度（米）。
    ground_height_m: float  # Ground height covered at 30m altitude. 30米高度时图像覆盖的地面高度（米）。


@dataclass
class InputData:
    """
    Complete input bundle passed to GeoLocator.
    传入 GeoLocator 的完整输入数据包。

    Aggregates all input data classes into one object.
    将所有输入数据类聚合为一个对象。
    """
    point: PointData        # Target point coordinates. 目标点坐标。
    image: ImageData        # Image metadata. 图像元数据。
    position: PositionData  # UAV GPS position. 无人机 GPS 位置。
    attitude: AttitudeData  # UAV attitude. 无人机姿态。
    altitude: AltitudeData  # UAV altitude. 无人机高度。
    coverage: GroundCoverage  # Ground coverage. 地面覆盖范围。


@dataclass
class GeoResult:
    """
    Output GPS coordinate of the target point.
    目标点输出的经纬度坐标。
    """
    target_lat_deg: float  # Target latitude in degrees. 目标点纬度（度）。
    target_lon_deg: float  # Target longitude in degrees. 目标点经度（度）。