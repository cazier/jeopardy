from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


app = Flask(__name__)
db = SQLAlchemy(app=app)
ma = Marshmallow(app=app)
api = Api(app=app)


from api import routes

def run_api(debug, host, port, file):
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{file}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    app.run(debug=debug, host=host, port = port)
