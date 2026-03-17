# main.py
# Python 3.10

from config import (
    IMAGE_WIDTH_PX,
    IMAGE_HEIGHT_PX,
    ALT_AGL_M,
    GROUND_WIDTH_M_AT_10M,
    GROUND_HEIGHT_M_AT_10M,
)
from data_models import (
    PointData,
    ImageData,
    PositionData,
    AttitudeData,
    AltitudeData,
    GroundCoverage,
    InputData,
    GeoResult,
)
from geo_locator import GeoLocator


# ---------------------------------------------------------------------------
# API INTEGRATION  (FastAPI)
# API 接入（FastAPI）
#
# from fastapi import FastAPI
# from pydantic import BaseModel
#
# app = FastAPI()
#
# class GeoRequest(BaseModel):
#     px: float
#     py: float
#     uav_lat_deg: float
#     uav_lon_deg: float
#     yaw_deg: float
#     roll_deg: float = 0.0   # Reserved for future use. 预留，暂不启用，默认为0。
#     pitch_deg: float = 0.0  # Reserved for future use. 预留，暂不启用，默认为0。
#
# @app.post('/geolocate')
# def geolocate(req: GeoRequest):
#     result = main(
#         px=req.px,
#         py=req.py,
#         uav_lat_deg=req.uav_lat_deg,
#         uav_lon_deg=req.uav_lon_deg,
#         yaw_deg=req.yaw_deg,
#         # roll_deg=req.roll_deg,    # Reserved for future use. 预留，暂不启用。
#         # pitch_deg=req.pitch_deg,  # Reserved for future use. 预留，暂不启用。
#     )
#     return {
#         'target_lat_deg': result.target_lat_deg,
#         'target_lon_deg': result.target_lon_deg,
#     }
# ---------------------------------------------------------------------------


def main(
    px: float,
    py: float,
    uav_lat_deg: float,
    uav_lon_deg: float,
    yaw_deg: float,
    # roll_deg: float = 0.0,    # Reserved for future use. 预留，暂不启用，默认为0。
    # pitch_deg: float = 0.0,   # Reserved for future use. 预留，暂不启用，默认为0。
) -> GeoResult:
    """
    Entry point for geolocation calculation.
    地理定位计算主入口。

    Args / 参数:
        px:          Clicked pixel x (column, origin at top-left). 点击位置的像素列坐标（左上角为原点）。
        py:          Clicked pixel y (row, origin at top-left).    点击位置的像素行坐标（左上角为原点）。
        uav_lat_deg: UAV latitude at capture moment.               拍照时无人机纬度。
        uav_lon_deg: UAV longitude at capture moment.              拍照时无人机经度。
        yaw_deg:     UAV yaw at capture moment, 0=north, clockwise positive. 拍照时无人机偏航角，0=指北，顺时针为正。
        # roll_deg:  UAV roll at capture moment (reserved).  拍照时无人机横滚角（预留）。
        # pitch_deg: UAV pitch at capture moment (reserved). 拍照时无人机俯仰角（预留）。

    Returns / 返回:
        GeoResult: Target GPS coordinate. 目标点经纬度。
    """

    # Convert raw pixel coordinate to image center Cartesian coordinate.
    # 将原始像素坐标转换为以图像中心为原点的笛卡尔坐标。
    # x is positive right, y is positive up.
    # x 向右为正，y 向上为正。
    x = px - IMAGE_WIDTH_PX / 2        # Horizontal offset from center. 距中心的水平偏移。
    y = -(py - IMAGE_HEIGHT_PX / 2)    # Vertical offset from center (y-axis flipped). 距中心的垂直偏移（y轴翻转）。

    # Target point: offset of the clicked point relative to the image center.
    # 目标点：用户点击位置相对于图像中心的偏移。
    point = PointData(x=x, y=y)

    # Image metadata: resolution and capture timestamp.
    # 图像元数据：分辨率和拍摄时间戳。
    image = ImageData(
        image_width_px=IMAGE_WIDTH_PX,
        image_height_px=IMAGE_HEIGHT_PX,
        timestamp=0.0   # Reserved for future use. 保留字段，暂不使用。
    )

    # UAV GPS position at the moment of capture. Corresponds to the image center.
    # 图像拍摄时刻无人机的 GPS 位置，对应图像正中心。
    position = PositionData(
        uav_lat_deg=uav_lat_deg,    # UAV latitude.  无人机纬度。
        uav_lon_deg=uav_lon_deg     # UAV longitude. 无人机经度。
    )

    # UAV attitude at the moment of capture.
    # 图像拍摄时刻无人机的姿态。
    # roll and pitch are fixed at 0 (UAV assumed to be level and shooting vertically downward).
    # roll 和 pitch 固定为0（假设无人机水平且垂直向下拍摄）。
    attitude = AttitudeData(
        roll_deg=0.0,       # Roll fixed at 0.  横滚角固定为0。
        pitch_deg=0.0,      # Pitch fixed at 0. 俯仰角固定为0。
        # roll_deg=roll_deg,    # Uncomment when roll is enabled.   启用横滚角时取消注释。
        # pitch_deg=pitch_deg,  # Uncomment when pitch is enabled.  启用俯仰角时取消注释。
        yaw_deg=yaw_deg     # Yaw from input. 0 = north, clockwise positive. 偏航角由外部传入，0=指北，顺时针为正。
    )

    # UAV altitude above ground level. Fixed at 10m.
    # 无人机离地高度，固定为10米。
    altitude = AltitudeData(
        alt_agl_m=ALT_AGL_M    # Fixed at 10m. 固定为10米。
    )

    # Ground area covered by the image at 10m altitude.
    # 无人机在10米高度时图像覆盖的地面范围。
    coverage = GroundCoverage(
        ground_width_m_at_10m=GROUND_WIDTH_M_AT_10M,    # Ground width.  地面宽度。
        ground_height_m_at_10m=GROUND_HEIGHT_M_AT_10M   # Ground height. 地面高度。
    )

    # Bundle all inputs into a single object and pass to GeoLocator.
    # 将所有输入打包为一个对象，传入 GeoLocator。
    input_data = InputData(
        point=point,
        image=image,
        position=position,
        attitude=attitude,
        altitude=altitude,
        coverage=coverage
    )

    # Run the geolocation calculation and return the result.
    # 执行地理定位计算并返回结果。
    return GeoLocator.locate(input_data)


if __name__ == "__main__":

    print("=" * 50)
    print("  UAV Geolocation Demo  无人机地理定位演示")
    print("=" * 50)

    # --- User input. 用户输入。---
    px          = float(input("Clicked pixel x  点击像素列坐标 (px): "))
    py          = float(input("Clicked pixel y  点击像素行坐标 (py): "))

    uav_lat_deg = 51.4500  # Demo UAV latitude.  演示用无人机纬度。
    uav_lon_deg = -2.6000  # Demo UAV longitude. 演示用无人机经度。
    yaw_deg = 0.0  # Demo UAV yaw.       演示用无人机偏航角。

    result = main(
        px=px,
        py=py,
        uav_lat_deg=uav_lat_deg,
        uav_lon_deg=uav_lon_deg,
        yaw_deg=yaw_deg,
    )

    print()
    print("=" * 50)
    print("  Input Summary  输入摘要")
    print("=" * 50)
    print(f"  Clicked pixel x       点击像素列坐标   : {px}")
    print(f"  Clicked pixel y       点击像素行坐标   : {py}")
    print(f"  UAV latitude          无人机纬度       : {uav_lat_deg}")
    print(f"  UAV longitude         无人机经度       : {uav_lon_deg}")
    print(f"  UAV yaw               无人机偏航角     : {yaw_deg}° (0=north 指北, clockwise positive 顺时针为正)")
    print()
    print("=" * 50)
    print("  Result  计算结果")
    print("=" * 50)
    print(f"  Target latitude       目标点纬度       : {result.target_lat_deg}")
    print(f"  Target longitude      目标点经度       : {result.target_lon_deg}")
    print("=" * 50)