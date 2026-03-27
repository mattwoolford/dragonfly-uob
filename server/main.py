from flask import Flask

from server.mission_modules.Delivery.Delivery import Delivery

app = Flask(__name__, static_folder="../front-end/dist")

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"
