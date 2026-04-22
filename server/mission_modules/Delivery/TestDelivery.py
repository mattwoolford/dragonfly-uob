import unittest
from pathlib import Path
from dotenv import load_dotenv
import os

for path in sorted(Path(".").glob(".env*")):
    if path.is_file():
        load_dotenv(path, override=True)

from server.controllers.Aircraft import Aircraft
from server.mission_modules.Delivery.Delivery import Delivery


class TestDelivery(unittest.TestCase):
    """
    Test the `start` method of the Delivery mission module.
    """

    def _make_aircraft(self):
        """Helper — creates and connects a fresh Aircraft instance."""
        aircraft = Aircraft()
        aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))
        self.assertTrue(aircraft.connected)
        self.assertIsNotNone(aircraft.master)
        return aircraft  # Bug 1 fix: was missing this

    def _base_options(self, aircraft):
        """Helper — returns a full valid options dict with the connected aircraft."""
        return {
            'aircraft':     aircraft,
            'casualty_lat': 51.4235372,
            'casualty_lon': -2.6702034,
            'servo_chan':    14,
        }

    # ------------------------------------------
    # CONNECTION HANDOFF
    # ------------------------------------------

    def test_start_uses_provided_aircraft(self):
        # Delivery should use the aircraft from options, not create its own
        aircraft = self._make_aircraft()
        options = self._base_options(aircraft)
        delivery = Delivery()
        self.assertTrue(delivery.start(options))

    def test_start_connects_if_not_connected(self):
        # Delivery should call connect() itself if aircraft.connected is False
        aircraft = Aircraft()  # not yet connected
        self.assertFalse(aircraft.connected)
        options = self._base_options(aircraft)
        delivery = Delivery()
        self.assertTrue(delivery.start(options))
        self.assertTrue(aircraft.connected)

    # ------------------------------------------
    # OPTIONS HANDLING
    # ------------------------------------------

    def test_start_uses_default_coordinates(self):
        # Omitting lat/lon from options should fall back to Fenswood defaults
        aircraft = self._make_aircraft()
        options = {
            'aircraft':  aircraft,
            'servo_chan': 14,
            # casualty_lat and casualty_lon intentionally omitted
        }
        delivery = Delivery()
        self.assertTrue(delivery.start(options))

    def test_start_uses_custom_coordinates(self):
        aircraft = self._make_aircraft()
        options = self._base_options(aircraft)
        options['casualty_lat'] = 51.4240000
        options['casualty_lon'] = -2.6710000
        delivery = Delivery()
        self.assertTrue(delivery.start(options))

    def test_start_uses_custom_servo_channel(self):
        aircraft = self._make_aircraft()
        options = self._base_options(aircraft)
        options['servo_chan'] = 15
        delivery = Delivery()
        self.assertTrue(delivery.start(options))

    # ------------------------------------------
    # FULL MISSION
    # ------------------------------------------

    def test_start(self):  # Bug 2 fix: removed the duplicate placeholder above
        aircraft = self._make_aircraft()
        delivery = Delivery()
        self.assertTrue(delivery.start(self._base_options(aircraft)))


if __name__ == '__main__':
    unittest.main()