import unittest

from server.mission_modules.Search.Search import Search


class TestSearch(unittest.TestCase):

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
        self.assertTrue(callable(Search.start)) # Replace this example


if __name__ == '__main__':
    unittest.main()
