import unittest
from unittest.mock import MagicMock, patch

from server.controllers.Aircraft import Aircraft


class TestAircraft(unittest.TestCase):

    @patch("server.controllers.Aircraft.Camera")
    def test_take_photo_with_position_success(self, MockCamera):
        # Create aircraft instance
        aircraft = Aircraft()

        # Mock required attributes
        aircraft.camera = MagicMock()
        aircraft.camera_image_save_directory = "drone_images"

        # Mock position
        aircraft.get_position = MagicMock(return_value=(51.4218, -2.6699, 50.0))

        # Mock camera helper return
        mock_camera_helper = MockCamera.return_value
        mock_camera_helper.capture_and_save_image.return_value = "/home/pi/Desktop/drone_images/img_123.jpg"

        # Run
        result = aircraft.take_photo_with_position()

        # Check result content
        self.assertEqual(result["latitude"], 51.4218)
        self.assertEqual(result["longitude"], -2.6699)
        self.assertEqual(result["relative_altitude_m"], 50.0)
        self.assertEqual(
            result["path_to_image"],
            "/home/pi/Desktop/drone_images/img_123.jpg"
        )

        # Check camera function was called once
        mock_camera_helper.capture_and_save_image.assert_called_once_with(
            camera=aircraft.camera,
            save_dir_path=aircraft.camera_image_save_directory
        )

    @patch("server.controllers.Aircraft.Camera")
    def test_take_photo_with_position_no_position(self, MockCamera):
        aircraft = Aircraft()

        aircraft.camera = MagicMock()
        aircraft.camera_image_save_directory = "drone_images"
        aircraft.get_position = MagicMock(return_value=None)

        with self.assertRaises(RuntimeError) as context:
            aircraft.take_photo_with_position()

        self.assertIn("Failed to get aircraft position", str(context.exception))


if __name__ == "__main__":
    unittest.main()