from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable


class Mission:

    """
    This mission controller acts as a state machine that guides the aircraft through a search and rescue mission.
    """

    def __init__(self, socketio_instance=None):
        self._assessment_image = None
        self.socketio = socketio_instance  # SocketIO instance
        self.set_status("Mission not started") # Initialise the mission status
        self.steps_queue = []  # Steps to be executed (list of methods)
        self.target_coordinates = None  # Coordinates of SAR subject

    def add_step(self, next_step: Callable):
        self.steps_queue.append(next_step)

    def get_image_for_assessment(self):
        return self._assessment_image

    def _initiate_sockets(self, options: dict[str, Any] | None = None):
        socketio_instance = options.get("socketio") or self.socketio
        if socketio_instance is None:
            from server.main import socketio as default_socketio

            socketio_instance = default_socketio

        return socketio_instance

    def _send_image_for_assessment(self, file_path):
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            self._assessment_image = image_bytes
            self.socketio.emit("image-inspection", {
                "data": {
                    "image": image_bytes
                }
            })

    def set_target_coordinates(self, coordinates: tuple[float, float]):
        self.target_coordinates = coordinates
        self.set_status("Target found")
        # TODO: Set next step to be geolocation from image
        print(f"Target coordinates set to {coordinates}")

    def next_step(self):
        next = self.steps_queue.pop(0)
        next()

    # TODO: Replace with actual search module
    def _search(self):
        # TODO: Replace with image from search
        self.set_status("Navigating to the search area...")
        time.sleep(5)
        self.set_status("Image capture in progress...")
        time.sleep(5)
        BASE_DIR = Path(__file__).resolve().parent
        file_path = f"{BASE_DIR}/../assets/test-image.png"
        self._send_image_for_assessment(file_path)

    def set_status(self, status: str):
        self.status = status
        self.socketio.emit("mission-status-change", {
            "data": {
                "missionStatus": status
            }
        })


    def start(self, options: dict[str, Any] | None = None):
        """
        Start the mission.

        Socket.IO options:
        - `socketio`: explicit Socket.IO instance to emit with
        """

        options = options or { }
        socketio = self._initiate_sockets(options)

        # Update mission status to reflect start
        self.set_status("Mission started")
        time.sleep(2)

        # TODO: Enter search loop
        # while not self.target_coordinates:
        self.add_step(self._search)
        self.next_step()
