from flask import Blueprint
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


bp = Blueprint(name="api", import_name=__name__)
ma = Marshmallow(app=bp)
api = Api(app=bp, prefix="/api/v1")

KEYS = {"date", "show", "round", "complete", "category", "value", "external", "question", "answer"}

from . import routes
