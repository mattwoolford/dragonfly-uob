# config.py
# Python 3.10

# Image resolution in pixels.
# 图像分辨率（像素）。
IMAGE_WIDTH_PX = 1920   # Image width.  图像宽度。
IMAGE_HEIGHT_PX = 1020  # Image height. 图像高度。

# UAV altitude above ground level in meters.
# 无人机离地高度（米）。
# Fixed at 30m for this version.
# 当前版本固定为30米。
ALT_AGL_M = 30.0

# Ground area covered by the image at 30m altitude in meters.
# 无人机在30米高度时，图像覆盖的地面范围（米）。
# These values are determined by the camera and lens, and remain constant.
# 这两个值由相机和镜头决定，为固定常数。
GROUND_WIDTH_M = 20.81   # Ground width covered.  图像覆盖的地面宽度。
GROUND_HEIGHT_M = 28.99  # Ground height covered. 图像覆盖的地面高度。