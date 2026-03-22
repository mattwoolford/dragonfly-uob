from __future__ import annotations
from pathlib import Path
from typing import Any


class Mission:

    """
    This mission controller acts as a state machine that guides the aircraft through a search and rescue mission.
    """

    def __init__(self, socketio_instance=None):
        self.socketio = socketio_instance

    def initiate_sockets(self, options: dict[str, Any] | None = None):
        socketio_instance = options.get("socketio") or self.socketio
        if socketio_instance is None:
            from server.main import socketio as default_socketio

            socketio_instance = default_socketio

        return socketio_instance

    def send_image_for_assessment(self, file_path):
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            self.socketio.emit("image-inspection", {"data": {
                "image": image_bytes
            }})


    def start(self, options: dict[str, Any] | None = None):
        """
        Start the mission.

        Socket.IO options:
        - `socketio`: explicit Socket.IO instance to emit with
        """
        options = options or {}
        socketio = self.initiate_sockets(options)

        BASE_DIR = Path(__file__).resolve().parent

        # TODO: Replace with image from search
        file_path = f"{BASE_DIR}/../assets/test-image.png"
        self.send_image_for_assessment(file_path)


