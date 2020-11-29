from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app=app)
ma = Marshmallow(app=app)
api = Api(app=app)

KEYS = {"date", "show", "round", "complete", "category", "value", "external", "question", "answer"}

from . import routes

