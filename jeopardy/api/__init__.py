from flask import Blueprint

from jeopardy import config

# from flask_marshmallow import Marshmallow


bp = Blueprint(name="api", import_name=__name__, url_prefix=f"/api/v{config.api_version}")
# ma = Marshmallow(app=bp)

KEYS = {"date", "show", "round", "complete", "category", "value", "external", "question", "answer"}

from . import routes  # noqa: E402,F401
