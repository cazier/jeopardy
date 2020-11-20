from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f":memory:"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app=app)
ma = Marshmallow(app=app)
api = Api(app=app)


from api import routes
