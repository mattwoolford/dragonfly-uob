import os
from flask_socketio import SocketIO
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv
from server.utils.env_flag import env_flag

for path in sorted(Path(".").glob(".env*")):
    if path.is_file():
        load_dotenv(path, override=True)
app = Flask(__name__, static_folder="../front-end/dist")
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")


socketio = SocketIO(app, cors_allowed_origins=os.getenv("FLASK_CORS_ALLOWED_ORIGINS").split(','))


@socketio.on('message')
def handle_message(data):
    print('received message: ' + str(data))


if __name__ == "__main__":
    debug = env_flag("FLASK_DEBUG", default=True)
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=debug,
        allow_unsafe_werkzeug=debug,
        log_output=True
    )
