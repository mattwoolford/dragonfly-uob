import unittest

from server.controllers.Aircraft import Aircraft


class TestAircraft(unittest.TestCase):

    """
    Create your tests here

    For example:
    """
    def test_connection(self):
        aircraft = Aircraft()
        aircraft.connect('tcp:127.0.0.1:5762')
        self.assertTrue(aircraft.connected)
        self.assertIsNotNone(aircraft.master)


if __name__ == '__main__':
    unittest.main()
