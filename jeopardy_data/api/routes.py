from flask import jsonify, request
from flask_restful import Resource, abort

from . import api, db, KEYS
from . import database
from .models import *
from .schemas import *

import zlib
import random
import datetime


class DetailsResource(Resource):
    def get(self) -> dict:
        categories = {
            "total": Category.query.count(),
            "complete": Category.query.filter(Category.complete == True).count(),
            "incomplete": Category.query.filter(Category.complete == False).count(),
        }
        sets = {
            "total": Set.query.count(),
            "has_external": Set.query.filter(Set.external == True).count(),
            "no_external": Set.query.filter(Set.external == False).count(),
        }
        shows = Show.query.count()
        air_dates = Date.query.order_by(Date.date)

        if 0 in {categories["total"], sets["total"], shows}:
            no_results(message="there are no items currently in the database")

        return jsonify(
            {
                "categories": categories,
                "sets": sets,
                "shows": shows,
                "air_dates": {"oldest": air_dates[0].date, "most_recent": air_dates[-1].date,},
            }
        )


class SetById(Resource):
    def get(self, set_id: int) -> dict:
        return jsonify(set_schema.dump(id_query(model=Set, id_=set_id)))

    def delete(self, set_id: int) -> dict:
        set_ = Set.query.get(set_id)

        db.session.delete(set_)
        db.session.commit()

        return jsonify({"deleted": set_id})


class SetsByRound(Resource):
    def get(self, round_number: str) -> dict:
        round_number = int(round_number)
        results = round_query(model=Set, number=round_number).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetsByShowNumber(Resource):
    def get(self, show_number: int) -> dict:
        results = show_query(model=Set, identifier="number", value=show_number).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetsByShowId(Resource):
    def get(self, show_id: int) -> dict:
        results = show_query(model=Set, identifier="id", value=show_id).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetsByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Set, year=year, month=month, day=day).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetsMultiple(Resource):
    def get(self) -> dict:
        results = Set.query

        results = (
            results.join(Date, Date.id == Set.date_id)
            .join(Round, Round.id == Set.round_id)
            .join(Category, Category.id == Set.category_id)
            .join(Value, Value.id == Set.value_id)
        )

        results = results.order_by(Date.date, Set.round, Category.name, Value.amount)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)

    def post(self) -> dict:
        payload = request.json
        if (set(payload.keys()) == KEYS) and all((len(str(v)) > 0 for k, v in payload.items())):
            success, resp = database.add(clue_data=payload, uses_shortnames=False)

            if success:
                return jsonify(set_schema.dump(resp))

            else:
                abort(400, message="the supplied data is already in the database")

        else:
            abort(400, message="the posted data is missing some data")


class ShowById(Resource):
    def get(self, show_id: int) -> dict:
        return jsonify(show_schema.dump(id_query(model=Show, id_=show_id)))


class ShowByNumber(Resource):
    def get(self, show_number: int) -> dict:
        show = Show.query.filter_by(number=show_number).first()

        if show == None:
            no_results()

        else:
            return jsonify(show_schema.dump(show))


class ShowsByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Show, year=year, month=month, day=day).order_by(Show.number)

        return paginate(model=results, schema=shows_schema.dump, indices=request.args)


class ShowsMultiple(Resource):
    def get(self) -> dict:
        return paginate(model=Show.query, schema=shows_schema.dump, indices=request.args)


class CategoryById(Resource):
    def get(self, category_id: int) -> dict:
        return jsonify(category_schema.dump(id_query(model=Category, id_=category_id)))


class CategoriesByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Category, year=year, month=month, day=day).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoriesByCompletion(Resource):
    def get(self, completion: str = None, completion_string: str = "") -> dict:
        if completion != None:
            if completion.lower() == "true":
                completion = True

            elif completion.lower() == "false":
                completion = False

        if completion == True or completion_string == "complete":
            results = Category.query.filter(Category.complete == True)

        elif completion == False or completion_string == "incomplete":
            results = Category.query.filter(Category.complete == False)

        else:
            abort(400, message="completion status must be supplied either 'true' or 'false'")

        results = results.join(Date, Date.id == Category.date_id).join(Round, Round.id == Category.round_id)
        results = results.order_by(Date.date, Round.number, Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoriesByName(Resource):
    def get(self, name_string: int) -> dict:
        results = Category.query.filter(Category.name.like(f"%{name_string}%"))

        results = results.join(Date, Date.id == Category.date_id).join(Round, Round.id == Category.round_id)
        results = results.order_by(Date.date, Round.number, Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoriesByShowNumber(Resource):
    def get(self, show_number: int) -> dict:
        results = show_query(model=Category, identifier="number", value=show_number).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoriesByRound(Resource):
    def get(self, round_number: str) -> dict:
        round_number = int(round_number)
        results = round_query(model=Category, number=round_number).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoriesByShowId(Resource):
    def get(self, show_id: int) -> dict:
        results = show_query(model=Category, identifier="id", value=show_id).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoriesMultiple(Resource):
    def get(self) -> dict:
        return paginate(model=Category.query, schema=categories_schema.dump, indices=request.args)


class BlankResource(Resource):
    def get(self) -> dict:
        return {"message": "hello!"}


class GameResource(Resource):
    def get(self) -> dict:
        size = int(request.args.get("size", 6))
        year = int(request.args.get("year", -1))
        show = int(request.args.get("show", -1))

        round_ = request.args.get("round", None)

        if (round_ == None) or (round_ not in ["0", "1", "2", "jeopardy", "doublejeopardy", "finaljeopardy"]):
            return jsonify(
                {
                    "error": "round number must be one of: "
                    '(0, 1, or 2) OR ("jeopardy", "doublejeopardy", or "finaljeopardy")'
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


def paginate(model, schema, indices) -> dict:
    if (count := model.count()) == 0:
        no_results()

    start = int(indices.get("start", 0))
    number = min(int(indices.get("number", 100)), 200)

    if start > count:
        abort(400, message="start number too great")

    if start + number > count:
        data = model[start:]

    else:
        data = model[start : start + number]

    return jsonify({"start": start, "number": number, "data": schema(data), "results": count,})


def date_query(model, year: int, month: int, day: int, chained_results=None):
    try:
        date = datetime.datetime.strptime(f"{year:04d}/{abs(month):02d}/{abs(day):02d}", "%Y/%m/%d")

    except ValueError:
        abort(
            400,
            message="please check that your date is valid (year between 0001 and 9999, month between 1 and 12, and day between 1 and 31, as applicable)",
        )

    if chained_results != None:
        results = chained_results.filter(model.date.has(year=date.year))

    else:
        results = model.query.filter(model.date.has(year=date.year))

    if month != -1:
        results = results.filter(model.date.has(month=date.month))

        if day != -1:
            results = results.filter(model.date.has(day=date.day))

    return results


def id_query(model, id_: int) -> flask_sqlalchemy.BaseQuery:
    results = model.query.filter_by(id=id_).first()

    if results == None:
        no_results()

    else:
        return results


def show_query(model, identifier: str, value: int, chained_results=None) -> flask_sqlalchemy.BaseQuery:
    if chained_results != None:
        results = chained_results

    else:
        results = model.query

    if identifier == "number":
        results = results.filter(model.show.has(number=value))

    else:
        results = results.filter(model.show.has(id=value))

    return results


def round_query(model, number: int) -> flask_sqlalchemy.BaseQuery:
    if not (0 <= number <= 2):
        abort(400, message="round number must be between 0 (jeopardy) and 2 (final jeopardy/tiebreaker)")

    return model.query.filter(model.round.has(number=number))


def no_results(message: str = "no items were found with that query"):
    abort(404, message=message)


api.add_resource(SetsMultiple, "/set", "/sets")
api.add_resource(SetById, "/set/id/<int:set_id>", "/sets/id/<int:set_id>")
api.add_resource(SetsByRound, "/set/round/<round_number>")
api.add_resource(SetsByShowNumber, "/set/show/number/<int:show_number>")
api.add_resource(SetsByShowId, "/set/show/id/<int:show_id>")
api.add_resource(
    SetsByDate,
    "/set/date/<int:year>",
    "/sets/date/<int:year>",
    "/set/date/<int:year>/<int:month>",
    "/sets/date/<int:year>/<int:month>",
    "/set/date/<int:year>/<int:month>/<int:day>",
    "/sets/date/<int:year>/<int:month>/<int:day>",
)


api.add_resource(ShowsMultiple, "/show", "/shows")
api.add_resource(ShowByNumber, "/show/number/<int:show_number>", "/shows/number/<int:show_number>")
api.add_resource(ShowById, "/show/id/<int:show_id>", "/shows/id/<int:show_id>")
api.add_resource(
    ShowsByDate,
    "/show/date/<int:year>",
    "/shows/date/<int:year>",
    "/show/date/<int:year>/<int:month>",
    "/shows/date/<int:year>/<int:month>",
    "/show/date/<int:year>/<int:month>/<int:day>",
    "/shows/date/<int:year>/<int:month>/<int:day>",
)

api.add_resource(CategoriesMultiple, "/category/", "/categories")
api.add_resource(CategoryById, "/category/id/<int:category_id>", "/categories/id/<int:category_id>")
api.add_resource(
    CategoriesByDate,
    "/category/date/<int:year>",
    "/categories/date/<int:year>",
    "/category/date/<int:year>/<int:month>",
    "/categories/date/<int:year>/<int:month>",
    "/category/date/<int:year>/<int:month>/<int:day>",
    "/categories/date/<int:year>/<int:month>/<int:day>",
)
api.add_resource(CategoriesByCompletion, "/category/complete/<completion>", "/category/<completion_string>")
api.add_resource(CategoriesByName, "/category/name/<name_string>")
api.add_resource(CategoriesByRound, "/category/round/<round_number>")
api.add_resource(CategoriesByShowNumber, "/category/show/number/<int:show_number>")
api.add_resource(CategoriesByShowId, "/category/show/id/<int:show_id>")

# api.add_resource(CategoryResource, "/category/<int:category_id>")
api.add_resource(DetailsResource, "/details")
api.add_resource(GameResource, "/game")
api.add_resource(BlankResource, "/")
# # api_base = ""  # /api/v1/"
