import unittest

from server.controllers.MissionController import MissionController


class TestMissionController(unittest.TestCase):

    """
    Create your tests here

    For example:
    """
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here


    """
    Test the `start` method
    """
    def test_start(self):
        self.assertTrue(callable(MissionController.start)) # Replace this example


if __name__ == '__main__':
    unittest.main()
