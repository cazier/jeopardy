from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    abort,
    flash,
    get_flashed_messages,
)
from flask_socketio import SocketIO, join_room

import random

import alex
import config
import storage

import rounds
import routing
import sockets

import wagers

app = Flask(__name__)
app.register_blueprint(blueprint=rounds.rounds)
app.register_blueprint(blueprint=routing.routing)

app.jinja_env.globals.update(game_name=config.game_name)
app.jinja_env.globals.update(currency=config.currency)

app.config[u"SECRET_KEY"] = config.app_secret
app.debug = config.debug

socketio = sockets.socketio
socketio.init_app(app)

if __name__ == u"__main__":
    socketio.run(app, host=u"0.0.0.0")
