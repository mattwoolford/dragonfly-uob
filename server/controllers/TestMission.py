import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from server.controllers.Mission import Mission


class TestMission(unittest.TestCase):

    def test_start_emits_string_image_payload(self):
        socketio = Mock()
        mission = Mission(socketio)
        image_data = "data:image/jpeg;base64,ZmFrZQ=="

        result = mission.start({"image_data": image_data})

        self.assertEqual(image_data, result)
        socketio.emit.assert_called_once_with(
            "image-inspection",
            {"image_payload": image_data},
        )

    def test_start_emits_file_bytes_payload(self):
        socketio = Mock()
        mission = Mission(socketio)
        expected_bytes = b"fake-image-bytes"

        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "frame.jpg"
            image_path.write_bytes(expected_bytes)

            result = mission.start({"image_path": image_path})

        self.assertEqual(expected_bytes, result)
        socketio.emit.assert_called_once_with(
            "image-inspection",
            {"image_payload": expected_bytes},
        )

    def test_start_reads_generated_tmp_image_before_emit(self):
        socketio = Mock()
        mission = Mission(socketio)
        expected_bytes = b"generated-image-bytes"

        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "generated.png"
            image_path.write_bytes(expected_bytes)

            with patch("server.controllers.Mission.Faker") as faker_cls:
                faker = faker_cls.return_value
                faker.png_file.return_value = str(image_path)

                result = mission.start()

        self.assertEqual(expected_bytes, result)
        socketio.emit.assert_called_once_with(
            "image-inspection",
            {"image_payload": expected_bytes},
        )


if __name__ == '__main__':
    unittest.main()
