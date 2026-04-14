import os
import time

from flask_socketio import SocketIO, join_room
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

from controllers.Mission import Mission
from server.controllers.Aircraft import Aircraft
from utils.env_flag import env_flag

for path in sorted(Path(".").glob(".env*")):
    if path.is_file():
        load_dotenv(path, override=True)


mission: Mission | None = None

from server.mission_modules.Delivery.Delivery import Delivery

from server.mission_modules.Delivery.Delivery import Delivery

app = Flask(__name__, static_folder="../front-end/dist")
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")


socketio = SocketIO(app, cors_allowed_origins=os.getenv("FLASK_CORS_ALLOWED_ORIGINS").split(','))


@socketio.on("connect")
def handle_connect():
    join_room("mission-clients")
    print("Connected client to the mission")


@socketio.on('get-assessment-image')
def get_assessment_image():
    global mission
    if mission is None:
        image = None
    else:
        image = mission.get_image_for_assessment()
    return {
        "data": {
            "image": image
        }
    }


@socketio.on('get-mission-status')
def get_mission_status() -> dict:
    global mission
    if mission is None:
        status = "Mission not started"
    else:
        status = mission.status
    return {
        "data": {
            "missionStatus": status
        }
    }


@socketio.on('image-inspection-pixel-coordinates-selected')
def handle_pixel_coordinates_selection(payload):
    global mission
    if mission is None:
        return
    data = payload["data"]
    u, v = data["u"], data["v"]
    mission.receive_image_assessment(u, v)


def start_mission() -> None:
    print("Starting mission")
    time.sleep(5)
    global mission
    aircraft = Aircraft()
    mission = Mission(aircraft, socketio_instance=socketio)
    print("Mission initialised")
    mission.start()


if __name__ == "__main__":
    debug = env_flag("FLASK_DEBUG", default=True)

    # Flask's debug reloader starts the module twice. Only schedule the
    # background mission from the active reloader process.
    is_active_process = not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if is_active_process:
        socketio.start_background_task(start_mission)

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=debug,
        allow_unsafe_werkzeug=debug,
        log_output=True
    )
