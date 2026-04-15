from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

from server.controllers.Aircraft import Aircraft
from server.mission_modules.Delivery.Delivery import Delivery
from server.mission_modules.Geolocation.Geolocation import Geolocation
from server.mission_modules.Navigation.Navigation import Navigation
from server.mission_modules.Search.Search import Search


class Mission:

    """
    This mission controller acts as a state machine that guides the aircraft through a search and rescue mission.
    """

    def __init__(self, aircraft: Aircraft, socketio_instance=None):
        self._assessment_image = None
        self.aircraft = aircraft
        self.altitude = 50
        self.complete = False
        self.home = None
        self.route = []
        self.socketio = socketio_instance  # SocketIO instance
        self.status = None
        self.set_status("Mission not started") # Initialise the mission status
        self.steps_queue = []  # Steps to be executed (list of methods)
        self.suspend = False # Whether to pause the mission (for example, when waiting for input)
        self.target_coordinates = None  # Coordinates of SAR subject

    def add_step(self, next_step: Callable):
        self.steps_queue.append(next_step)

    def _fetch_next_image(self):
        if len(self.route) == 0:
            return
        self.set_status("Searching for the target")
        lat, lon = self.route.pop(0)
        self._position_aircraft(lat, lon, self.altitude)
        print("Capturing image...")
        image_info = self.aircraft.take_photo_with_position()
        # BASE_DIR = Path(__file__).resolve().parent
        # lat, lon, alt, hdg = self.aircraft.get_position()
        # image_info = {
        #     "latitude": lat,
        #     "longitude": lon,
        #     "relative_altitude_m": alt,
        #     "heading": hdg,
        #     "path_to_image": f"{BASE_DIR}/../assets/test-image.png",
        # }
        self.request_image_assessment(image_info["path_to_image"])


    def get_image_for_assessment(self):
        return self._assessment_image

    def _get_location_from_target_coordinates(self):
        if self.target_coordinates is None:
            raise ValueError("Could not get location from target coordinates: Target coordinates have not been set")
        u, v = self.target_coordinates
        lat, lon, alt, hdg = self.aircraft.get_position()
        geolocation = Geolocation()
        location = geolocation.start({
            "px":          u,
            "py":          v,
            "uav_lat_deg": lat,
            "uav_lon_deg": lon,
            "heading":     hdg
        })
        return location.target_lat_deg, location.target_lon_deg

    def _deliver_to_target(self):
        self.set_status("Delivering care kit to the target")
        delivery = Delivery(self.socketio)
        lat, lon = self._get_location_from_target_coordinates()
        delivered = delivery.start({
            "casualty_lat": lat,
            "casualty_lon": lon,
            "aircraft": self.aircraft,
            "home_lat": self.home[0],
            "home_lon": self.home[1]

        })
        if delivered:
            self.complete = True
        else:
            self.aircraft.set_mode("RTL")

    def _initiate_sockets(self, options: dict[str, Any] | None = None):
        socketio_instance = options.get("socketio") or self.socketio
        if socketio_instance is None:
            from server.main import socketio as default_socketio

            socketio_instance = default_socketio

        return socketio_instance

    def request_image_assessment(self, file_path):
        self.suspend = True
        self.set_status("Waiting for image assessment")
        print("Waiting for image assessment...")
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            self._assessment_image = image_bytes
            self.socketio.emit("image-inspection", {
                "data": {
                    "image": image_bytes
                }
            }, to="mission-clients")

    def request_interaction(self, prompt, options: dict[str, Any]):
        self.suspend = True
        self.set_status("Waiting for user interaction")
        print("Waiting for user interaction...")
        self.socketio.emit("interaction", {
            "data": {
                "prompt": prompt,
                "options": options
            }
        }, to="mission-clients")

    def receive_image_assessment(self, u: int | None, v: int | None):
        if not self.suspend:
            return
        if u is None or v is None:
            print("A target subject could not be found by the user")
            self.add_step(self._fetch_next_image)
            self.suspend = False
            return
        self.set_target_coordinates(u, v)

    def set_target_coordinates(self, u, v):
        coordinates = (u, v)
        self.target_coordinates = coordinates
        self.set_status("Target found")
        self._assessment_image = None
        self.suspend = False
        print(f"Target coordinates set to {coordinates}")
        self.add_step(self._deliver_to_target)

    def _launch_aircraft(self):
        self.aircraft.set_mode("GUIDED")
        self.aircraft.wait_for_mode("GUIDED")
        self.home = self.aircraft.get_position()

        self.set_status("Mission started")
        time.sleep(2)

        lat, lon, alt, hdg = self.aircraft.get_position()
        if alt < 5:
            for i in range(5):
                self.set_status(f"Arming aircraft in {5 - i}s...")
                print(f"\rArming aircraft in {5 - i}s...", end=("" if i < 4 else "\n"), flush=True)
                time.sleep(1)
            self.set_status("Arming aircraft")
            print("WARNING! Stand clear. Aircraft arming...")
            time.sleep(1)
            if not self.aircraft.arm():
                raise Exception("Could not arm the aircraft")
        else:
            print("Aircraft is airborne")

        self.set_status("Taking off")
        print("Taking off...")
        if not self.aircraft.takeoff(self.altitude, 30):
            raise Exception("Aircraft could not take off")

    def next_step(self):
        next_step_in_queue = self.steps_queue.pop(0)
        next_step_in_queue()

    def _position_aircraft(self, lat, lon, alt):
        navigation_accepted = self.aircraft.goto(lat, lon, alt)
        journey_time = 0
        journey_complete = False
        while not journey_complete and navigation_accepted:
            journey_complete = self.aircraft.check_if_journey_complete()
            print(f"\rTravelling to ({lat}, {lon}) [{journey_time}s]",
                  end=("" if not journey_complete else "\n"),
                  flush=True)
            journey_time += 1
        if not navigation_accepted:
            raise Exception(f"Could not continue the mission: Navigation to ({lat}, {lon}) at altitude {search_alt}m was out of bounds")
        print(f"Journey to ({lat}, {lon}) completed in {journey_time}s")

    def set_status(self, status: str):
        self.status = status
        self.socketio.emit("mission-status-change", {
            "data": {
                "missionStatus": status
            }
        }, to="mission-clients")

    def start(self, options: dict[str, Any] | None = None):
        """
        Start the mission.

        Socket.IO options:
        - `socketio`: explicit Socket.IO instance to emit with
        """

        options = options or { }
        self._initiate_sockets(options)

        try:
            if not self.aircraft.connected:
                self.aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))

            if not self.aircraft.connected:
                raise ConnectionError("Could not start the mission: Failed to connect to the aircraft")

            # Prepare the mission

            self.set_status("Preparing search")

            # Check in safe zone before start
            curr_lat, curr_lon, curr_alt, heading = self.aircraft.get_position()
            if not Navigation.check_point(curr_lat, curr_lon, self.altitude):
                raise Exception("Aircraft not in the safe zone")

            # Get search route waypoints
            search = Search()
            route = search.start({
                "mode": "full"
            })

            route_is_possible = all([Navigation.check_path(lat1, lon1, lat2, lon2, self.altitude) for (lat1, lon1), (lat2, lon2) in zip([(curr_lat, curr_lon), *route], route[1:])])

            if len(route) < 1 or not route_is_possible:
                raise Exception("Could not start the mission: No route found for searching for the target")

            self.route = route

            self._launch_aircraft()
            time.sleep(2)

            self.add_step(self._fetch_next_image)
            while not self.complete:
                if self.suspend:
                    continue
                if len(self.steps_queue) > 0:
                    self.next_step()
            self.set_status("Mission complete")


        except Exception as e:
            self.aircraft.set_mode("LOITER")
            self.set_status("Mission failed")
            raise e



            # while not self.target_coordinates and not self.suspend:
            # self.add_step(self._search)
            # self.next_step()
