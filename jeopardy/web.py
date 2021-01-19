from flask import Flask
from flask_sqlalchemy import SQLAlchemy


import config

import api
import rounds
import routing
import sockets

app = Flask(__name__)
app.jinja_env.globals.update(game_name=config.game_name)
app.jinja_env.globals.update(currency=config.currency)

app.debug = config.debug
app.config["SECRET_KEY"] = config.secret_key
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////home/brendan/Documents/merge/jeopardy/questions.db"
db = SQLAlchemy(app=app)


app.register_blueprint(blueprint=rounds.rounds)
app.register_blueprint(blueprint=routing.routing)
app.register_blueprint(blueprint=api.bp)

socketio = sockets.socketio
socketio.init_app(app)


if __name__ == u"__main__":
    socketio.run(app, host=u"0.0.0.0")
