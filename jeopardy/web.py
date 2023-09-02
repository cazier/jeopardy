import sys
import pathlib

if "pytest" not in sys.modules:
    import eventlet

    eventlet.monkey_patch()

from flask import Flask

sys.path.append(str(pathlib.Path(__file__).parent.parent))

from jeopardy import api, config, rounds, routing, sockets
from jeopardy.api.schemas import ApiJSONProvider


def create_app():
    app = Flask(__name__)
    app.jinja_env.globals.update(game_name=config.game_name)
    app.jinja_env.globals.update(currency=config.currency)

    app.debug = config.debug
    app.config["TESTING"] = hasattr(config, "testing") and config.testing
    app.config["SECRET_KEY"] = config.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = config.api_db
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    api.models.db.init_app(app)
    app.json = ApiJSONProvider(app)

    app.register_blueprint(blueprint=rounds.rounds)
    app.register_blueprint(blueprint=routing.routing)
    app.register_blueprint(blueprint=api.bp)

    return app


if __name__ == "__main__":
    print("Loading database file from:", config.db_file)
    app = create_app()

    socketio = sockets.socketio
    socketio.init_app(app)
    socketio.run(app, host="0.0.0.0", debug=config.debug, port=config.port)
