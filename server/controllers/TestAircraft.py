import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from server.controllers.Aircraft import Aircraft
from dotenv import load_dotenv
import os

for path in sorted(Path(".").glob(".env*")):
    if path.is_file():
        load_dotenv(path, override=True)



class TestAircraft(unittest.TestCase):

    def test_connection(self):
    @patch("server.controllers.Aircraft.Camera")
    def test_take_photo_with_position_success(self, MockCamera):
        # Create aircraft instance
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        self.assertTrue(aircraft.connected)
        self.assertIsNotNone(aircraft.master)

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

    def test_aircraft_arm(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        self.assertTrue(aircraft.arm())

    def test_aircraft_takeoff(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        aircraft.set_mode("GUIDED")
        aircraft.wait_for_mode("GUIDED")
        aircraft.arm()
        self.assertTrue(aircraft.takeoff(10))

    def test_aircraft_land(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        aircraft.set_mode("GUIDED")
        aircraft.wait_for_mode("GUIDED")
        self.assertTrue(aircraft.land())

    def test_aircraft_goto(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        aircraft.set_mode("GUIDED")
        aircraft.wait_for_mode("GUIDED")
        # Fly to a point 10m North of current position
        pos = aircraft.get_position()
        self.assertIsNotNone(pos)
        lat, lon, _ = pos
        target_lat, target_lon = Aircraft.get_offset_location(lat, lon, 10, 0)
        self.assertTrue(aircraft.goto(target_lat, target_lon, 20))

    def test_wait_until_reached(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        aircraft.set_mode("GUIDED")
        aircraft.wait_for_mode("GUIDED")
        aircraft.arm()
        aircraft.takeoff(20)
        pos = aircraft.get_position()
        self.assertIsNotNone(pos)
        lat, lon, _ = pos
        target_lat, target_lon = Aircraft.get_offset_location(lat, lon, 10, 90)
        aircraft.goto(target_lat, target_lon, 20)
        self.assertTrue(aircraft.wait_until_reached(target_lat, target_lon, 20))

    #Do straight after the previous
    def test_wait_until_disarmed(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        aircraft.set_mode("LAND")
        aircraft.wait_for_mode("LAND")
        self.assertTrue(aircraft.wait_until_disarmed())
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