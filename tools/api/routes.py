from flask import jsonify, request
from flask_restful import Resource

import arrow

from api import api, db
from api.models import Set, Category, Date, Show, Round, Value, External, Complete
from api.schemas import *

import datetime, zlib, random


class DetailsResource(Resource):
    def get(self) -> dict:
        categories = Category.query.count()
        sets = Set.query.count()
        shows = Show.query.count()
        is_complete = Set.query.filter(Set.complete.has(state=True)).count()
        has_external = Set.query.filter(Set.external.has(state=True)).count()
        air_dates = Date.query.order_by(Date.date)

        return jsonify(
            {
                "categories": categories,
                "sets": sets,
                "shows": shows,
                "air_dates": {"oldest": air_dates[0].date, "most_recent": air_dates[-1].date},
                "is_complete": {True: is_complete, False: sets - is_complete},
                "has_external": {True: has_external, False: sets - has_external},
            }
        )


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
        return jsonify(paginate(model=Set, schema=sets_schema.dump, indices=request.args))

    def post(self) -> dict:
        payload = request.json
        if set(payload.keys()) == set(
            ("date", "show", "round", "complete", "category", "value", "external", "question", "answer")
        ) and all((len(str(v)) > 0 for k, v in payload.items())):
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

            if (category := Category.query.filter_by(name=key("category")).filter_by(date=date).first()) is None:
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

        else:
            return jsonify({"missing": "key or value"})


class ShowResourceByNumber(Resource):
    def get(self, entry: int) -> dict:
        show = Show.query.filter_by(number=entry).first()

        if show == None:
            return no_results()

        else:
            return jsonify(show_schema.dump(show))


class ShowResourceById(Resource):
    def get(self, entry: int) -> dict:
        show = Show.query.filter_by(id=entry).first()

        if show == None:
            return no_results()

        else:
            return jsonify(show_schema.dump(show))


class ShowResourceByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        return jsonify({"error": "not yet implemented"})
        # start = arrow.get(f"{year:04d}/01/01", "YYYY/MM/DD")
        # stop = start.shift(years=+1)

        # try:
        #     if month != -1:
        #         start = start.replace(month=month)

        # except ValueError:
        #     return jsonify({"error": "please check that your months and dates are valid"})

        # return jsonify({"year": year, "month": month, "day": day})


class ShowListResource(Resource):
    def get(self) -> dict:
        return jsonify(paginate(model=Show, schema=shows_schema.dump, indices=request.args))


# class CategoryResource(Resource):
#     def get(self, category_id: int) -> dict:
#         show = Show.query.get_or_404(show_id)

#         return jsonify(show_schema.dump(show))

#     def delete(self, show_id: int) -> dict:
#         show = Show.query.get(show_id)

#         db.session.delete(show)
#         db.session.commit()

#         return jsonify({"delete": "success"})


class CategoryListResource(Resource):
    def get(self) -> dict:
        return jsonify(paginate(model=Category, schema=categories_schema.dump, indices=request.args))


class GameResource(Resource):
    def get(self) -> dict:
        size = int(request.args.get("size", 6))
        year = int(request.args.get("year", -1))
        show = int(request.args.get("show", -1))

        round_ = request.args.get("round", None)

        if (round_ == None) or (round_ not in ["0", "1", "2", "jeopardy", "doublejeopardy", "finaljeopardy"]):
            return jsonify(
                {
                    "error": 'round number must be one of: (0, 1, or 2) OR ("jeopardy", "doublejeopardy", or "finaljeopardy")'
                }
            )

        if not round_.isnumeric():
            round_ = {"jeopardy": "0", "doublejeopardy": "1", "finaljeopardy": "2"}[round_]

        rounds = [r.id for r in Round.query.filter(Round.number == int(round_))]

        if year != -1:
            year = int(year)
            start = datetime.datetime.strptime(str(year), "%Y")
            stop = datetime.datetime.strptime(str(year + 1), "%Y")

            year_ = Date.query.filter(Date.date > start, Date.date < stop)
        else:
            year_ = Date.query.filter()

        years = [y.id for y in year_.all()]

        if show != -1:
            shows = Show.query.filter_by(number=show)
            categories = (
                Category.query.filter(Category.show == shows.first()).filter(Category.round_id.in_(rounds)).all()
            )

        else:
            categories = (
                Category.query.filter(Category.round_id.in_(rounds))
                .filter(Category.date_id.in_(years))
                .filter(Category.complete.has(state=True))
                .all()
            )
            random.shuffle(categories)

        column = 0
        sets = dict()

        while column < size:
            category = categories.pop()
            sets_ = sets_schema.dump(category.sets)

            if any([v["external"] for v in sets_]) and show == -1:
                continue

            elif len(sets_) > 5:
                continue

            else:
                sets[category.name] = sets_
                column += 1

        return jsonify(sets)


def paginate(model, schema, indices):
    start = int(indices.get("start", 0))
    number = min(int(indices.get("number", 100)), 200)

    if start > model.query.count():
        return {"error": "start number too great"}

    if start + number > model.query.count():
        return {"start": start, "number": number, "results": schema(model.query.filter(model.id >= start).all())}

    else:
        return {
            "start": start,
            "number": number,
            "results": schema(model.query.filter(model.id >= start, model.id < start + number).all()),
        }


def no_results():
    return jsonify({"error": "no results found"})


api.add_resource(SetListResource, "/sets")
api.add_resource(SetResource, "/set/<int:set_id>")

api.add_resource(ShowListResource, "/shows")
api.add_resource(ShowResourceByNumber, "/show/number/<int:entry>")
api.add_resource(ShowResourceById, "/show/id/<int:entry>")
api.add_resource(
    ShowResourceByDate,
    "/show/date/<int:year>/",
    "/show/date/<int:year>/<int:month>/",
    "/show/date/<int:year>/<int:month>/<int:day>/",
)

api.add_resource(CategoryListResource, "/categories")
# api.add_resource(CategoryResource, "/category/<int:category_id>")
api.add_resource(DetailsResource, "/details")
api.add_resource(GameResource, "/game")
# # api_base = ""  # /api/v1/"
