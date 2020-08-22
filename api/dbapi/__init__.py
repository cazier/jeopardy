from flask import Flask
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow, fields

import zlib
import datetime
import time


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app=app)
ma = Marshmallow(app=app)
api = Api(app=app)

# class ShowResource(Resource):
#     def get(self, show_id: int) -> dict:
#         show = models.Show.query.get_or_404(show_id)
#         return jsonify(show_schema.dump(show))


# class ShowListResource(Resource):
#     def get(self) -> dict:
#         shows = models.Show.query.all()
#         return jsonify(shows_schema.dump(shows))

from dbapi import routes

