from flask import Blueprint
from flask_restful import Api
from flask_marshmallow import Marshmallow

from jeopardy import config

bp = Blueprint(name="api", import_name=__name__)
ma = Marshmallow(app=bp)
api = Api(app=bp, prefix=f"/api/v{config.api_version}")

KEYS = {"date", "show", "round", "complete", "category", "value", "external", "question", "answer"}

from . import routes  # noqa: E402,F401
