import unittest
from pathlib import Path

from dotenv import load_dotenv
import os

for path in sorted(Path(".").glob(".env*")):
    if path.is_file():
        load_dotenv(path, override=True)

from server.controllers.Aircraft import Aircraft

class TestAircraft(unittest.TestCase):

    def test_connection(self):
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        self.assertTrue(aircraft.connected)
        self.assertIsNotNone(aircraft.master)

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

if __name__ == '__main__':
    unittest.main()
