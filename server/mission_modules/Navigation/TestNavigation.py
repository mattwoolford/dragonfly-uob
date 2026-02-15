import unittest

from server.mission_modules.Navigation.Navigation import Navigation


class TestNavigation(unittest.TestCase):

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
        self.assertTrue(callable(Navigation.start)) # Replace this example


if __name__ == '__main__':
    unittest.main()
