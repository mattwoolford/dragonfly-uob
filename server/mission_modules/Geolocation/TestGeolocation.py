import unittest

from server.mission_modules.Geolocation.Geolocation import Geolocation


class TestGeolocation(unittest.TestCase):
    """
    Unit tests for the Geolocation mission module.
    Geolocation 任务模块的单元测试。
    """

    def setUp(self):
        """
        Create a Geolocation module instance before each test.
        每个测试前创建一个 Geolocation 模块实例。
        """
        self.module = Geolocation()

    def test_start_is_callable(self):
        """
        Test that the start method exists and is callable.
        测试 start 方法存在且可调用。
        """
        self.assertTrue(callable(self.module.start))

    def test_start_returns_geo_result(self):
        """
        Test that start() returns a result with target latitude and longitude.
        测试 start() 能返回包含目标纬度和经度的结果。
        """
        options = {
            "px": 960.0,
            "py": 510.0,
            "uav_lat_deg": 51.4500,
            "uav_lon_deg": -2.5800,
            "yaw_deg": 0.0,
        }

        result = self.module.start(options)

        self.assertTrue(hasattr(result, "target_lat_deg"))
        self.assertTrue(hasattr(result, "target_lon_deg"))
        self.assertIsInstance(result.target_lat_deg, float)
        self.assertIsInstance(result.target_lon_deg, float)

    def test_start_center_pixel_returns_same_location(self):
        """
        Test that clicking the image center returns the UAV GPS position.
        测试点击图像中心时，返回无人机当前 GPS 坐标。
        """
        options = {
            "px": 960.0,
            "py": 510.0,
            "uav_lat_deg": 51.4500,
            "uav_lon_deg": -2.5800,
            "yaw_deg": 0.0,
        }

        result = self.module.start(options)

        self.assertAlmostEqual(result.target_lat_deg, 51.4500, places=6)
        self.assertAlmostEqual(result.target_lon_deg, -2.5800, places=6)

    def test_start_with_non_center_pixel_changes_location(self):
        """
        Test that a non-center pixel produces a different GPS result.
        测试非中心像素点会产生不同的 GPS 结果。
        """
        options = {
            "px": 1200.0,
            "py": 400.0,
            "uav_lat_deg": 51.4500,
            "uav_lon_deg": -2.5800,
            "yaw_deg": 0.0,
        }

        result = self.module.start(options)

        self.assertNotAlmostEqual(result.target_lat_deg, 51.4500, places=6)
        self.assertNotAlmostEqual(result.target_lon_deg, -2.5800, places=6)

    def test_start_raises_error_when_options_is_not_dict(self):
        """
        Test that start() raises TypeError when options is not a dict.
        测试当 options 不是字典时，start() 会抛出 TypeError。
        """
        with self.assertRaises(TypeError):
            self.module.start(None)

    def test_start_raises_error_when_required_key_is_missing(self):
        """
        Test that start() raises ValueError when required fields are missing.
        测试缺少必要字段时，start() 会抛出 ValueError。
        """
        options = {
            "px": 960.0,
            "py": 510.0,
            "uav_lat_deg": 51.4500,
            # "uav_lon_deg" is missing
            "yaw_deg": 0.0,
        }

        with self.assertRaises(ValueError):
            self.module.start(options)

    def test_start_raises_error_when_value_is_not_numeric(self):
        """
        Test that start() raises ValueError when an input value is not numeric.
        测试当输入值不是数字时，start() 会抛出 ValueError。
        """
        options = {
            "px": "abc",
            "py": 510.0,
            "uav_lat_deg": 51.4500,
            "uav_lon_deg": -2.5800,
            "yaw_deg": 0.0,
        }

        with self.assertRaises(ValueError):
            self.module.start(options)


if __name__ == '__main__':
    unittest.main()