from flask import jsonify, request
from flask_restful import Resource, abort

from . import api, db, KEYS
from . import database
from .models import *
from .schemas import *

import datetime, zlib, random


class DetailsResource(Resource):
    def get(self) -> dict:
        categories = Category.query.count()
        sets = Set.query.count()
        shows = Show.query.count()
        is_complete = Set.query.filter(Set.complete.has(state=True)).count()
        has_external = Set.query.filter(Set.external.has(state=True)).count()
        air_dates = Date.query.order_by(Date.date)

        if 0 in {categories, sets, shows, is_complete, has_external}:
            no_results(message="there are no items currently in the database")

        return jsonify(
            {
                "categories": categories,
                "sets": sets,
                "shows": shows,
                "air_dates": {"oldest": air_dates[0].date, "most_recent": air_dates[-1].date,},
                "is_complete": {True: is_complete, False: sets - is_complete},
                "has_external": {True: has_external, False: sets - has_external},
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
            return no_results()

        else:
            return jsonify(show_schema.dump(show))


class ShowsByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Show, ordered=Show.number, year=year, month=month, day=day)

        return paginate(model=results, schema=shows_schema.dump, indices=request.args)


class ShowsMultiple(Resource):
    def get(self) -> dict:
        return paginate(model=Show.query, schema=shows_schema.dump, indices=request.args)


# class CategoryResource(Resource):
#     def get(self, category_id: int) -> dict:
#         show = Show.query.get_or_404(show_id)

#         return jsonify(show_schema.dump(show))

#     def delete(self, show_id: int) -> dict:
#         show = Show.query.get(show_id)

#         db.session.delete(show)
#         db.session.commit()

#         return jsonify({"delete": "success"})
class CategoryById(Resource):
    def get(self, category_id: int) -> dict:
        return jsonify(category_schema.dump(id_query(model=Category, id_=category_id)))


class CategoriesByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Category, ordered=Category.name, year=year, month=month, day=day)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByCompletion(Resource):
    def get(self, completion: bool = None, completion_string: str = "") -> dict:
        if completion == True or completion_string == "complete":
            results = Category.query.filter(Category.complete.has(state=True))

        elif completion == False or completion_string == "incomplete":
            results = Category.query.filter(Category.complete.has(state=False))

        else:
            abort(400, message="completion status must be supplied")

        results = results.join(Date, Date.id == Category.date_id).join(Round, Round.id == Category.round_id)

        results = results.order_by(Date.date, Round.number, Category.name)

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
        return no_results()

    start = int(indices.get("start", 0))
    number = min(int(indices.get("number", 100)), 200)

    if start > count:
        abort(400, message="start number too great")

    if start + number > count:
        data = model[start:]

    else:
        data = model[start : start + number]

    return jsonify({"start": start, "number": number, "data": schema(data), "results": count,})


def date_query(model, ordered, year: int, month: int, day: int):
    try:
        date = datetime.datetime.strptime(f"{year:04d}/{abs(month):02d}/{abs(day):02d}", "%Y/%m/%d")

    except ValueError:
        abort(
            400,
            message="please check that your date is valid (year between 0001 and 9999, month between 1 and 12, and day between 1 and 31, as applicable)",
        )

    results = model.query.filter(model.date.has(year=date.year))

    if month != -1:
        results = results.filter(model.date.has(month=date.month))

        if day != -1:
            results = results.filter(model.date.has(day=date.day))

    return results.order_by(ordered)


def id_query(model, id_: int) -> dict:
    results = model.query.filter_by(id=id_).first()

    if results == None:
        return no_results()

    else:
        return results


def no_results(message: str = "no items were found with that query"):
    abort(404, message=message)


api.add_resource(SetsMultiple, "/set", "/sets")
api.add_resource(SetById, "/set/<int:set_id>", "/sets/<int:set_id>")

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
api.add_resource(CategoryByCompletion, "/category/complete/<completion>", "/category/<completion_string>")

# api.add_resource(CategoryResource, "/category/<int:category_id>")
api.add_resource(DetailsResource, "/details")
api.add_resource(GameResource, "/game")
api.add_resource(BlankResource, "/")
# # api_base = ""  # /api/v1/"
