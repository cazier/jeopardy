from flask import Blueprint

from jeopardy import config

bp = Blueprint(name="api", import_name=__name__, url_prefix=f"/api/v{config.api_version}")

KEYS = {"date", "show", "round", "complete", "category", "value", "external", "question", "answer"}

from . import routes  # noqa: E402,F401
