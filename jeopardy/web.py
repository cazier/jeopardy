from flask import Flask
from flask_sqlalchemy import SQLAlchemy

try:
    import config
    import api
    import rounds
    import routing
    import sockets

except ImportError:
    from jeopardy import config
    from jeopardy import api
    from jeopardy import rounds
    from jeopardy import routing
    from jeopardy import sockets


def create_app():
    app = Flask(__name__)
    app.jinja_env.globals.update(game_name=config.game_name)
    app.jinja_env.globals.update(currency=config.currency)

    app.debug = config.debug
    app.config["SECRET_KEY"] = config.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = config.api_db
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    api.models.db.init_app(app)

    app.register_blueprint(blueprint=rounds.rounds)
    app.register_blueprint(blueprint=routing.routing)
    app.register_blueprint(blueprint=api.bp)

    return app


if __name__ == u"__main__":
    app = create_app()

    socketio = sockets.socketio
    socketio.init_app(app)

    socketio.run(app, host=u"0.0.0.0", debug=config.debug, port=config.port)
