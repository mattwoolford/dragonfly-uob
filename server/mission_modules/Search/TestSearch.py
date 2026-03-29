import unittest
from unittest.mock import patch

from .Search import Search


class TestSearch(unittest.TestCase):

    def setUp(self):
        self.search = Search()

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_full(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.5000001, -2.6000001),
            (51.5000002, -2.6000002),
        ]

        result = self.search.start({
            "mode": "full",
            "add_transit": False
        })

        self.assertEqual(result, [
            (51.5000001, -2.6000001),
            (51.5000002, -2.6000002),
        ])
        mock_running.assert_called_once_with(plb_geo=None)
        mock_save_route.assert_called_once_with(result)

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_plb(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.4230001, -2.6690001),
            (51.4230002, -2.6690002),
        ]

        plb_geo = [
            (51.4236844, -2.6698843),
            (51.4235388, -2.6689777),
            (51.4232478, -2.6698118),
        ]

        result = self.search.start({
            "mode": "plb",
            "plb_geo": plb_geo,
            "add_transit": False
        })

        self.assertEqual(result, [
            (51.4230001, -2.6690001),
            (51.4230002, -2.6690002),
        ])
        mock_running.assert_called_once_with(plb_geo=plb_geo)
        mock_save_route.assert_called_once_with(result)

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_plb_demo(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.4240001, -2.6680001),
            (51.4240002, -2.6680002),
        ]

        result = self.search.start({
            "mode": "plb_demo",
            "add_transit": False
        })

        self.assertEqual(result, [
            (51.4240001, -2.6680001),
            (51.4240002, -2.6680002),
        ])
        mock_running.assert_called_once()
        mock_save_route.assert_called_once_with(result)

    @patch("server.mission_modules.Search.Search._load_route")
    def test_start_reuse(self, mock_load_route):
        mock_load_route.return_value = [
            (51.4211111, -2.6611111),
            (51.4222222, -2.6622222),
        ]

        result = self.search.start({
            "mode": "reuse"
        })

        self.assertEqual(result, [
            (51.4211111, -2.6611111),
            (51.4222222, -2.6622222),
        ])
        mock_load_route.assert_called_once()

    def test_start_invalid_mode(self):
        with self.assertRaises(ValueError):
            self.search.start({
                "mode": "invalid_mode"
            })

    def test_start_invalid_options_type(self):
        with self.assertRaises(TypeError):
            self.search.start("not a dict")

    def test_start_invalid_add_transit_type(self):
        with self.assertRaises(ValueError):
            self.search.start({
                "mode": "full",
                "add_transit": "yes"
            })

    def test_start_plb_missing_polygon(self):
        with self.assertRaises(ValueError):
            self.search.start({
                "mode": "plb"
            })

    def test_start_plb_invalid_polygon_format(self):
        with self.assertRaises(ValueError):
            self.search.start({
                "mode": "plb",
                "plb_geo": [(51.42, -2.66)]
            })

    def test_start_plb_invalid_point_type(self):
        with self.assertRaises(ValueError):
            self.search.start({
                "mode": "plb",
                "plb_geo": [
                    (51.4236844, -2.6698843),
                    ("bad_lat", -2.6689777),
                    (51.4232478, -2.6698118),
                ]
            })


if __name__ == "__main__":
    unittest.main()