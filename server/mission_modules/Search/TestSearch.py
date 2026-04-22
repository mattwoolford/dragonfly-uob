import unittest
from unittest.mock import patch

from server.mission_modules.Search.Search import Search, TRANSIT_POINTS_GEO


class TestSearch(unittest.TestCase):
    """
    Test the `start` method of the Search mission module.
    """

    def setUp(self):
        self.search = Search()

    def _base_options(self):
        """
        Helper — returns a basic valid options dict.
        """
        return {
            "mode": "full",
            "add_transit": False
        }

    def _assert_route_format(self, route):
        """
        Assert route is a list of numeric (lat, lon) tuples.
        """
        self.assertIsInstance(route, list)
        for p in route:
            self.assertIsInstance(p, tuple)
            self.assertEqual(len(p), 2)
            self.assertIsInstance(p[0], float)
            self.assertIsInstance(p[1], float)

    # ------------------------------------------
    # ROUTE MODES
    # ------------------------------------------

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_full(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.5000001, -2.6000001),
            (51.5000002, -2.6000002),
        ]

        options = self._base_options()
        result = self.search.start(options)

        self.assertEqual(result, [
            (51.5000001, -2.6000001),
            (51.5000002, -2.6000002),
        ])
        mock_running.assert_called_once_with(plb_geo=None)
        mock_save_route.assert_called_once_with(result)

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_uses_default_options(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.5000001, -2.6000001),
            (51.5000002, -2.6000002),
        ]

        result = self.search.start({})

        expected = TRANSIT_POINTS_GEO + mock_running.return_value
        self.assertEqual(result, expected)
        mock_running.assert_called_once_with(plb_geo=None)
        mock_save_route.assert_called_once_with(expected)

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_accepts_none_options(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.5000001, -2.6000001),
            (51.5000002, -2.6000002),
        ]

        result = self.search.start(None)

        expected = TRANSIT_POINTS_GEO + mock_running.return_value
        self.assertEqual(result, expected)
        mock_running.assert_called_once_with(plb_geo=None)
        mock_save_route.assert_called_once_with(expected)

    @patch("server.mission_modules.Search.Search._save_route")
    @patch("server.mission_modules.Search.Search.running")
    def test_start_does_not_add_transit_when_disabled(self, mock_running, mock_save_route):
        mock_running.return_value = [
            (51.5000001, -2.6000001),
        ]

        result = self.search.start({
            "mode": "full",
            "add_transit": False
        })

        self.assertEqual(result, [
            (51.5000001, -2.6000001),
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

        options = self._base_options()
        options["mode"] = "plb"
        options["plb_geo"] = plb_geo

        result = self.search.start(options)

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
        mock_running.assert_called_once_with(plb_geo=[
            (51.4236844, -2.6698843),
            (51.4235388, -2.6689777),
            (51.4232478, -2.6698118),
            (51.4233465, -2.6700774),
        ])
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

    # ------------------------------------------
    # REAL PLB INTEGRATION TESTS
    # ------------------------------------------

    @patch("server.mission_modules.Search.Search._save_route")
    def test_start_plb_real_example_polygon(self, mock_save_route):
        """
        Real integration test:
        use the original demo PLB polygon and ensure the whole chain runs.
        """
        plb_geo = [
            (51.4236844, -2.6698843),
            (51.4235388, -2.6689777),
            (51.4232478, -2.6698118),
            (51.4233465, -2.6700774),
        ]

        result = self.search.start({
            "mode": "plb",
            "plb_geo": plb_geo,
            "add_transit": False
        })

        self._assert_route_format(result)
        self.assertGreater(len(result), 0)
        mock_save_route.assert_called_once_with(result)

    @patch("server.mission_modules.Search.Search._save_route")
    def test_start_plb_real_near_boundary_repair_only(self, mock_save_route):
        """
        Real integration test:
        use a tiny PLB near the boundary / protected zone where good cells
        are likely to be absent, so the planner should still run without error.
        """
        plb_geo = [
            (51.423555, -2.67136),
            (51.42352,  -2.67120),
            (51.42340,  -2.67128),
        ]

        result = self.search.start({
            "mode": "plb",
            "plb_geo": plb_geo,
            "add_transit": False
        })

        self._assert_route_format(result)
        mock_save_route.assert_called_once_with(result)

    @patch("server.mission_modules.Search.Search._save_route")
    def test_start_plb_real_tiny_polygon_allows_empty_route(self, mock_save_route):
        """
        Real integration test:
        use an even smaller polygon that may produce neither good nor repair cells.
        This should return an empty route instead of raising an error.
        """
        plb_geo = [
            (51.42353, -2.67130),
            (51.42350, -2.67124),
            (51.42347, -2.67130),
        ]

        result = self.search.start({
            "mode": "plb",
            "plb_geo": plb_geo,
            "add_transit": False
        })

        self.assertIsInstance(result, list)
        self.assertEqual(result, [])
        mock_save_route.assert_called_once_with(result)

    # ------------------------------------------
    # INPUT VALIDATION
    # ------------------------------------------

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

    # ------------------------------------------
    # PLB VALIDATION HELPER
    # ------------------------------------------

    def test_validate_plb_geo_accepts_numeric_points(self):
        plb_geo = [
            (51.4236844, -2.6698843),
            [51.4235388, -2.6689777],
            (51.4232478, -2.6698118),
        ]

        result = self.search._validate_plb_geo(plb_geo)

        self.assertEqual(result, [
            (51.4236844, -2.6698843),
            (51.4235388, -2.6689777),
            (51.4232478, -2.6698118),
        ])

    def test_validate_plb_geo_rejects_none(self):
        with self.assertRaises(ValueError):
            self.search._validate_plb_geo(None)


if __name__ == "__main__":
    unittest.main()