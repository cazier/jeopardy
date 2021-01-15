from flask import Flask

import config

import rounds
import routing
import sockets

app = Flask(__name__)
app.register_blueprint(blueprint=rounds.rounds)
app.register_blueprint(blueprint=routing.routing)

app.jinja_env.globals.update(game_name=config.game_name)
app.jinja_env.globals.update(currency=config.currency)

app.config["SECRET_KEY"] = config.secret_key

app.debug = config.debug

socketio = sockets.socketio
socketio.init_app(app)

if __name__ == u"__main__":
    socketio.run(app, host=u"0.0.0.0")
