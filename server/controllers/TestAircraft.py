import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from server.controllers.Aircraft import Aircraft
from server.controllers.Camera import Camera


class FakeCamera:
    """
    Minimal fake camera used for realistic file-save tests.
    """
    def __init__(self):
        self.saved_paths = []

    def capture_file(self, path: str):
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_bytes(b"fake_image_data")
        self.saved_paths.append(path)


class FakeMaster:
    """
    Minimal fake MAVLink master for get_position tests.
    Returns messages from a predefined queue in order.
    """
    def __init__(self, messages):
        self._messages = list(messages)

    def recv_match(self, type=None, blocking=True, timeout=2.0):
        if not self._messages:
            return None
        return self._messages.pop(0)


class TestAircraft(unittest.TestCase):
    def test_get_position_uses_global_position_hdg(self):
        aircraft = Aircraft()

        msg = SimpleNamespace(
            lat=int(51.4212345 * 1e7),
            lon=int(-2.6678901 * 1e7),
            relative_alt=int(23.4 * 1000),
            hdg=12345,  # 123.45 deg
        )
        aircraft.master = FakeMaster([msg])

        result = aircraft.get_position()

        self.assertIsNotNone(result)
        lat, lon, rel_alt, heading = result
        self.assertAlmostEqual(lat, 51.4212345, places=6)
        self.assertAlmostEqual(lon, -2.6678901, places=6)
        self.assertAlmostEqual(rel_alt, 23.4, places=3)
        self.assertAlmostEqual(heading, 123.45, places=2)

    def test_get_position_falls_back_to_attitude_yaw(self):
        aircraft = Aircraft()

        global_msg = SimpleNamespace(
            lat=int(51.5000000 * 1e7),
            lon=int(-2.6000000 * 1e7),
            relative_alt=int(10.0 * 1000),
            hdg=65535,  # unknown
        )
        attitude_msg = SimpleNamespace(
            yaw=math.radians(-90.0)
        )

        aircraft.master = FakeMaster([global_msg, attitude_msg])

        result = aircraft.get_position()

        self.assertIsNotNone(result)
        lat, lon, rel_alt, heading = result
        self.assertAlmostEqual(lat, 51.5, places=6)
        self.assertAlmostEqual(lon, -2.6, places=6)
        self.assertAlmostEqual(rel_alt, 10.0, places=3)
        self.assertAlmostEqual(heading, 270.0, places=3)

    def test_get_position_returns_none_when_no_global_position(self):
        aircraft = Aircraft()
        aircraft.master = FakeMaster([])

        result = aircraft.get_position()

        self.assertIsNone(result)

    def test_get_position_returns_none_when_hdg_missing_and_no_attitude(self):
        aircraft = Aircraft()

        global_msg = SimpleNamespace(
            lat=int(51.4 * 1e7),
            lon=int(-2.6 * 1e7),
            relative_alt=int(15.0 * 1000),
            hdg=65535,
        )

        aircraft.master = FakeMaster([global_msg])

        result = aircraft.get_position()

        self.assertIsNone(result)

    @patch("server.controllers.Aircraft.Camera")
    def test_take_photo_with_position_success(self, mock_camera_class):
        aircraft = Aircraft(camera="CAMERA_OBJECT", camera_image_save_directory="drone_images")

        aircraft.get_position = Mock(return_value=(51.421, -2.667, 20.0, 135.0))

        mock_camera_helper = Mock()
        mock_camera_helper.capture_and_save_image.return_value = (
            "/tmp/drone_images/img_123.jpg",
            "/tmp/drone_images/img_123.jpg",
        )
        mock_camera_class.return_value = mock_camera_helper

        result = aircraft.take_photo_with_position()

        self.assertEqual(result["latitude"], 51.421)
        self.assertEqual(result["longitude"], -2.667)
        self.assertEqual(result["relative_altitude_m"], 20.0)
        self.assertEqual(result["heading"], 135.0)
        self.assertEqual(
            result["path_to_image"],
            ("/tmp/drone_images/img_123.jpg", "/tmp/drone_images/img_123.jpg"),
        )

        mock_camera_helper.capture_and_save_image.assert_called_once_with(
            camera="CAMERA_OBJECT",
            save_dir_path="drone_images",
        )

    def test_take_photo_with_position_raises_when_position_missing(self):
        aircraft = Aircraft(camera="CAMERA_OBJECT", camera_image_save_directory="drone_images")
        aircraft.get_position = Mock(return_value=None)

        with self.assertRaises(RuntimeError) as ctx:
            aircraft.take_photo_with_position()

        self.assertIn("Failed to get aircraft position", str(ctx.exception))

    @patch("server.controllers.Aircraft.Camera")
    def test_take_photo_with_position_propagates_camera_failure(self, mock_camera_class):
        aircraft = Aircraft(camera="CAMERA_OBJECT", camera_image_save_directory="drone_images")
        aircraft.get_position = Mock(return_value=(51.421, -2.667, 20.0, 45.0))

        mock_camera_helper = Mock()
        mock_camera_helper.capture_and_save_image.side_effect = RuntimeError("Capture failed")
        mock_camera_class.return_value = mock_camera_helper

        with self.assertRaises(RuntimeError) as ctx:
            aircraft.take_photo_with_position()

        self.assertIn("Capture failed", str(ctx.exception))


class TestCamera(unittest.TestCase):
    def test_capture_and_save_image_with_absolute_path(self):
        camera_helper = Camera()
        fake_camera = FakeCamera()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "images"

            local_path, remote_path = camera_helper.capture_and_save_image(
                camera=fake_camera,
                save_dir_path=str(save_dir),
                filename="test_image"
            )

            self.assertTrue(Path(local_path).exists())
            self.assertTrue(local_path.endswith("test_image.jpg"))
            self.assertEqual(remote_path, local_path)
            self.assertEqual(len(fake_camera.saved_paths), 1)

    def test_capture_and_save_image_with_relative_folder_goes_to_desktop(self):
        camera_helper = Camera()
        fake_camera = FakeCamera()

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)

            with patch("server.controllers.Camera.Path.home", return_value=fake_home):
                local_path, remote_path = camera_helper.capture_and_save_image(
                    camera=fake_camera,
                    save_dir_path="drone_images",
                    filename="demo.jpg"
                )

            expected_dir = fake_home / "Desktop" / "drone_images"
            self.assertTrue(Path(local_path).exists())
            self.assertTrue(str(local_path).startswith(str(expected_dir)))
            self.assertEqual(remote_path, local_path)

    def test_capture_and_save_image_generates_default_filename(self):
        camera_helper = Camera()
        fake_camera = FakeCamera()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "images"

            local_path, remote_path = camera_helper.capture_and_save_image(
                camera=fake_camera,
                save_dir_path=str(save_dir),
                filename=None
            )

            self.assertTrue(Path(local_path).exists())
            self.assertTrue(Path(local_path).name.startswith("img_"))
            self.assertTrue(Path(local_path).suffix.lower() == ".jpg")
            self.assertEqual(remote_path, local_path)

    def test_capture_and_save_image_raises_when_camera_is_none(self):
        camera_helper = Camera()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "images"

            with self.assertRaises(RuntimeError) as ctx:
                camera_helper.capture_and_save_image(
                    camera=None,
                    save_dir_path=str(save_dir),
                    filename="bad.jpg"
                )

        self.assertIn("Capture failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()