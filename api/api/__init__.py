from flask import Flask, Response, request, jsonify
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow, fields

from pprint import pprint

import zlib
import datetime
import time

import models

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app=app)
ma = Marshmallow(app=app)
api = Api(app=app)


# class SetModel(db.Model):
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
#     date_id = db.Column(db.Integer, db.ForeignKey("date.id"), nullable=False)
#     show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
#     round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
#     value_id = db.Column(db.Integer, db.ForeignKey("value.id"), nullable=False)
#     external_id = db.Column(db.Integer, db.ForeignKey("external.id"), nullable=False)
#     complete_id = db.Column(db.Integer, db.ForeignKey("complete.id"), nullable=False)
#     hash = db.Column(db.Integer, nullable=False, unique=True)

#     answer = db.Column(db.String(1000))
#     question = db.Column(db.String(255))

#     def __repr__(self):
#         return f"<Set {self.id}, (Hash={self.hash})>"


# class Category(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
#     date_id = db.Column(db.Integer, db.ForeignKey("date.id"), nullable=False)
#     round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
#     complete_id = db.Column(db.Integer, db.ForeignKey("complete.id"), nullable=False)
#     sets = db.relationship("SetModel", backref="category")

#     def __repr__(self):
#         return f"<Category {self.name}>"


# class Date(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     date = db.Column(db.Date)
#     sets = db.relationship("SetModel", backref="date")
#     show = db.relationship("Show", backref="date", uselist=False)
#     categories = db.relationship("Category", backref="date")

#     def __repr__(self):
#         return f"<Date {self.date}>"


# class Show(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     number = db.Column(db.Integer)
#     date_id = db.Column(db.Integer, db.ForeignKey("date.id"))
#     sets = db.relationship("SetModel", backref="show")
#     categories = db.relationship("Category", backref="show")

#     def __repr__(self):
#         return f"<Show {self.number}>"


# class Round(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     number = db.Column(db.Integer)
#     sets = db.relationship("SetModel", backref="round")
#     categories = db.relationship("Category", backref="round")
#     values = db.relationship("Value", backref="round")

#     def __repr__(self):
#         return f"<Round {self.number}>"


# class Value(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     amount = db.Column(db.Integer)
#     round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
#     sets = db.relationship("SetModel", backref="value")

#     def __repr__(self):
#         return f"<Value {self.amount}>"


# class External(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     state = db.Column(db.Boolean)
#     sets = db.relationship("SetModel", backref="external")

#     def __repr__(self):
#         return f"<External {self.state}>"


# class Complete(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     state = db.Column(db.Boolean)
#     sets = db.relationship("SetModel", backref="complete")
#     categories = db.relationship("Category", backref="complete")

#     def __repr__(self):
#         return f"<Complete {self.state}>"


class DateSchema(ma.SQLAlchemySchema):
    # date = fields.fields.Function(lambda obj: obj.date.strftime("%Y-%d"))
    class Meta:
        model = models.Date
        fields = ("date",)


class ShowSchema(ma.SQLAlchemySchema):
    date = fields.fields.Pluck("DateSchema", "date")
    length = fields.fields.Function()

    class Meta:
        model = models.Show
        fields = (
            "id",
            "date",
            "number",
        )


class RoundSchema(ma.SQLAlchemySchema):
    class Meta:
        model = models.Round
        fields = ("number",)


class CategorySchema(ma.SQLAlchemySchema):
    class Meta:
        model = models.Category
        fields = (
            "id",
            "name",
        )


class ValueSchema(ma.SQLAlchemySchema):
    class Meta:
        model = models.Value
        fields = ("amount",)


class ExternalSchema(ma.SQLAlchemySchema):
    class Meta:
        model = models.External
        fields = ("state",)


class CompleteSchema(ma.SQLAlchemySchema):
    class Meta:
        model = models.Complete
        fields = ("state",)


class SetSchema(ma.SQLAlchemyAutoSchema):
    category = fields.fields.Pluck("CategorySchema", "name")
    date = fields.fields.Pluck("DateSchema", "date")
    show = fields.fields.Pluck("ShowSchema", "number")
    round = fields.fields.Pluck("RoundSchema", "number")
    value = fields.fields.Pluck("ValueSchema", "amount")
    external = fields.fields.Pluck("ExternalSchema", "state")
    complete = fields.fields.Pluck("CompleteSchema", "state")

    class Meta:
        model = models.Set
        fields = (
            "id",
            "category",
            "date",
            "show",
            "round",
            "answer",
            "question",
            "value",
            "external",
            "complete",
        )


set_schema = SetSchema()
sets_schema = SetSchema(many=True)

show_schema = ShowSchema()
shows_schema = ShowSchema(many=True)

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)


class SetResource(Resource):
    def get(self, set_id: int) -> dict:
        set_ = models.Set.query.get_or_404(set_id)

        return jsonify(set_schema.dump(set_))

    def delete(self, set_id: int) -> dict:
        set_ = models.Set.query.get(set_id)

        db.session.delete(set_)
        db.session.commit()

        return jsonify({"delete": "success"})


class SetListResource(Resource):
    def get(self) -> dict:
        sets = models.Set.query.all()

        return jsonify(sets_schema.dump(sets))

    def post(self) -> dict:
        payload = request.json

        if (date := models.Date.query.filter_by(date=datetime.date.fromisoformat(payload["date"])).first()) is None:
            date = models.Date(date=datetime.date.fromisoformat(payload["date"]))
            db.session.add(date)

        if (show := models.Show.query.filter_by(number=payload["show"]).first()) is None:
            show = models.Show(number=payload["show"], date=date)
            db.session.add(show)

        if (round_ := models.Round.query.filter_by(number=payload["round"]).first()) is None:
            round_ = models.Round(number=payload["round"])
            db.session.add(round_)

        if (complete := models.Complete.query.filter_by(state=payload["complete"]).first()) is None:
            complete = models.Complete(state=payload["complete"])
            db.session.add(complete)

        if (category := models.Category.query.filter_by(name=payload["category"]).first()) is None:
            category = models.Category(name=payload["category"], show=show, round=round_, complete=complete, date=date)
            db.session.add(category)

        if (value := models.Value.query.filter_by(amount=payload["value"]).first()) is None:
            value = models.Value(amount=payload["value"], round=round_)
            db.session.add(value)

        if (external := models.External.query.filter_by(state=payload["external"]).first()) is None:
            external = models.External(state=payload["external"])
            db.session.add(external)

        hash = zlib.adler32(f'{payload["question"]}{payload["answer"]}{show.number}'.encode())

        if models.Set.query.filter_by(hash=hash).first() is None:
            set_ = models.Set(
                category=category,
                date=date,
                show=show,
                round=round_,
                answer=payload["answer"],
                question=payload["question"],
                value=value,
                external=external,
                complete=complete,
                hash=hash,
            )

            db.session.add(set_)
            db.session.commit()

            return jsonify(set_schema.dump(set_))

        else:
            return jsonify({"already": "exists"})


class ShowResource(Resource):
    def get(self, show_id: int) -> dict:
        show = models.Show.query.get_or_404(show_id)
        return jsonify(show_schema.dump(show))


class ShowListResource(Resource):
    def get(self) -> dict:
        shows = models.Show.query.all()
        return jsonify(shows_schema.dump(shows))


api.add_resource(SetListResource, "/sets")
api.add_resource(SetResource, "/set/<int:set_id>")
# # api_base = ""  # /api/v1/"
api.add_resource(ShowListResource, "/shows")
api.add_resource(ShowResource, "/show/<int:show_id>")


if __name__ == "__main__":
    # db.drop_all()
    # db.create_all()
    app.run(debug=True, host="0.0.0.0")
