from flask import jsonify, Response, request
from flask_restful import Resource

from dbapi import api, db
from dbapi.models import Set, Category, Date, Show, Round, Value, External, Complete
from dbapi.schemas import set_schema, sets_schema, show_schema, shows_schema  # , category_schema, categories_schema

import datetime, zlib


class SetResource(Resource):
    def get(self, set_id: int) -> dict:
        set_ = Set.query.get_or_404(set_id)

        return jsonify(set_schema.dump(set_))

    def delete(self, set_id: int) -> dict:
        set_ = Set.query.get(set_id)

        db.session.delete(set_)
        db.session.commit()

        return jsonify({"delete": "success"})


class SetListResource(Resource):
    def get(self) -> dict:
        sets = Set.query.all()

        return jsonify(sets_schema.dump(sets))

    def post(self) -> dict:
        payload = request.json

        if (date := Date.query.filter_by(date=datetime.date.fromisoformat(payload["date"])).first()) is None:
            date = Date(date=datetime.date.fromisoformat(payload["date"]))
            db.session.add(date)

        if (show := Show.query.filter_by(number=payload["show"]).first()) is None:
            show = Show(number=payload["show"], date=date)
            db.session.add(show)

        if (round_ := Round.query.filter_by(number=payload["round"]).first()) is None:
            round_ = Round(number=payload["round"])
            db.session.add(round_)

        if (complete := Complete.query.filter_by(state=payload["complete"]).first()) is None:
            complete = Complete(state=payload["complete"])
            db.session.add(complete)

        if (category := Category.query.filter_by(name=payload["category"]).first()) is None:
            category = Category(name=payload["category"], show=show, round=round_, complete=complete, date=date)
            db.session.add(category)

        if (value := Value.query.filter_by(amount=payload["value"]).first()) is None:
            value = Value(amount=payload["value"], round=round_)
            db.session.add(value)

        if (external := External.query.filter_by(state=payload["external"]).first()) is None:
            external = External(state=payload["external"])
            db.session.add(external)

        hash = zlib.adler32(f'{payload["question"]}{payload["answer"]}{show.number}'.encode())

        if Set.query.filter_by(hash=hash).first() is None:
            set_ = Set(
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


api.add_resource(SetListResource, "/sets")
api.add_resource(SetResource, "/set/<int:set_id>")
# # api_base = ""  # /api/v1/"
# api.add_resource(ShowListResource, "/shows")
# api.add_resource(ShowResource, "/show/<int:show_id>")
