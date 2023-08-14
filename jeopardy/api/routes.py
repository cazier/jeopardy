import random
import typing as t
import datetime

from flask import jsonify, request
from sqlalchemy import Select, or_, and_, func, select
from flask_restful import Resource, abort

from jeopardy.api import KEYS, api, database
from jeopardy.api.models import Set, Base, Date, Show, Round, Value, Category, db
from jeopardy.api.schemas import set_schema, sets_schema, show_schema, shows_schema, category_schema, categories_schema

Q = t.TypeVar("Q", Select, Base)
session = db.session


class DetailsResource(Resource):
    def get(self) -> dict:
        categories = {
            "total": session.scalar(select(func.count()).select_from(Category)),
            "complete": session.scalar(select(func.count()).where(Category.complete == True)),  # noqa: E712
            "incomplete": session.scalar(select(func.count()).where(Category.complete == False)),  # noqa: E712
        }
        sets = {
            "total": session.scalar(select(func.count()).select_from(Set)),
            "has_external": session.scalar(select(func.count()).where(Set.external == True)),  # noqa: E712
            "no_external": session.scalar(select(func.count()).where(Set.external == True)),  # noqa: E712
        }

        shows = {"total": session.scalar(select(func.count()).select_from(Show))}

        if 0 in {categories["total"], sets["total"], shows["total"]}:
            no_results(message="there are no items currently in the database")

        shows.update(
            {
                "first_id": session.execute(select(Show).order_by(Show.id)).scalars().first().id,
                "last_id": session.execute(select(Show).order_by(Show.id.desc())).scalars().first().id,
                "first_number": session.execute(select(Show).order_by(Show.number)).scalars().first().number,
                "last_number": session.execute(select(Show).order_by(Show.number.desc())).scalars().first().number,
            }
        )

        air_dates = {
            "oldest": session.execute(select(Date).order_by(Date.date)).scalars().first().date,
            "most_recent": session.execute(select(Date).order_by(Date.date.desc())).scalars().first().date,
        }

        return jsonify({"categories": categories, "sets": sets, "shows": shows, "air_dates": air_dates})


class SetById(Resource):
    def get(self, set_id: int) -> dict:
        return jsonify(set_schema.dump(id_query(model=Set, id_=set_id)))

    def delete(self, set_id: int) -> dict:
        row = session.scalar(select(Set).filter_by(id=set_id))

        if row:
            session.delete(row)
            session.commit()

            return jsonify({"deleted": set_id})


class SetByRound(Resource):
    def get(self, round_number: str) -> dict:
        round_number = int(round_number)
        results = round_query(model=Set, number=round_number).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetByShowNumber(Resource):
    def get(self, show_number: int) -> dict:
        results = show_query(model=Set, identifier="number", value=show_number).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetByShowId(Resource):
    def get(self, show_id: int) -> dict:
        results = show_query(model=Set, identifier="id", value=show_id).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Set, year=year, month=month, day=day).order_by(Set.id)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetByYear(Resource):
    def get(self, start: int, stop: int) -> dict:
        results = date_query(model=Set, start=start, stop=stop).order_by(Date.date)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)


class SetMultiple(Resource):
    def get(self) -> dict:
        # TODO: Might be able to get rid of id == date_id if back refs are good?
        results = (
            select(Set)
            .join(Date, Date.id == Set.date_id)
            .join(Round, Round.id == Set.round_id)
            .join(Category, Category.id == Set.category_id)
            .join(Value, Value.id == Set.value_id)
        )

        results = results.order_by(Date.date, Set.round, Category.name, Value.amount)

        return paginate(model=results, schema=sets_schema.dump, indices=request.args)

    def post(self) -> dict:
        payload: dict[str, t.Any] = request.json
        if (set(payload.keys()) == KEYS) and all((len(str(value)) > 0 for value in payload.values())):
            try:
                resp = database.add(clue_data=payload, uses_shortnames=False)

                return jsonify(set_schema.dump(resp))

            except database.SetAlreadyExistsError:
                abort(400, message="The question set supplied is already in the database!")

        else:
            abort(400, message="The question set supplied is missing some data. Every field is required.")


class ShowById(Resource):
    def get(self, show_id: int) -> dict:
        return jsonify(show_schema.dump(id_query(model=Show, id_=show_id)))


class ShowByNumber(Resource):
    def get(self, show_number: int) -> dict:
        show = session.scalar(select(Show).where(Show.number == show_number))

        if show is None:
            no_results()

        else:
            return jsonify(show_schema.dump(show))


class ShowByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Show, year=year, month=month, day=day).order_by(Show.number)

        return paginate(model=results, schema=shows_schema.dump, indices=request.args)


class ShowByYears(Resource):
    def get(self, start: int, stop: int) -> dict:
        results = date_query(model=Show, start=start, stop=stop).order_by(Date.date)

        return paginate(model=results, schema=shows_schema.dump, indices=request.args)


class ShowMultiple(Resource):
    def get(self) -> dict:
        return paginate(model=select(Show), schema=shows_schema.dump, indices=request.args)


class CategoryById(Resource):
    def get(self, category_id: int) -> dict:
        return jsonify(category_schema.dump(id_query(model=Category, id_=category_id)))


class CategoryByDate(Resource):
    def get(self, year: int, month: int = -1, day: int = -1) -> dict:
        results = date_query(model=Category, year=year, month=month, day=day).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByYears(Resource):
    def get(self, start: int, stop: int) -> dict:
        results = date_query(model=Category, start=start, stop=stop).order_by(Date.date)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByCompletion(Resource):
    def get(self, completion: str = "", completion_string: str = "") -> dict:
        if completion != "":
            if completion.lower() == "true":
                completion = True

            elif completion.lower() == "false":
                completion = False

        if completion is True or completion_string.lower() == "complete":
            results = select(Category).where(Category.complete == True)  # noqa: E712

        elif completion is False or completion_string.lower() == "incomplete":
            results = select(Category).where(Category.complete == False)  # noqa: E712

        else:
            abort(400, message='The completion status must be one of either "True/False" or "Complete/Incomplete"')

        results = results.join(Date).join(Round).order_by(Date.date, Round.number, Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByName(Resource):
    def get(self, name_string: int) -> dict:
        results = (
            select(Category)
            .where(Category.name.like(f"%{name_string}%"))
            .join(Date)
            .join(Round)
            .order_by(Date.date, Round.number, Category.name)
        )

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByShowNumber(Resource):
    def get(self, show_number: int) -> dict:
        results = show_query(model=Category, identifier="number", value=show_number).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByRound(Resource):
    def get(self, round_number: str) -> dict:
        round_number = int(round_number)
        results = round_query(model=Category, number=round_number).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryByShowId(Resource):
    def get(self, show_id: int) -> dict:
        results = show_query(model=Category, identifier="id", value=show_id).order_by(Category.name)

        return paginate(model=results, schema=categories_schema.dump, indices=request.args)


class CategoryMultiple(Resource):
    def get(self) -> dict:
        return paginate(model=select(Category), schema=categories_schema.dump, indices=request.args)


# class BlankResource(Resource):
#     def get(self) -> dict:
#         return {"message": "hello!"}


class GameResource(Resource):
    def get(self) -> dict:
        size = int(request.args.get("size", 6))
        start = int(request.args.get("start", -1))
        stop = int(request.args.get("stop", -1))

        show_number = int(request.args.get("show_number", -1))
        show_id = int(request.args.get("show_id", -1))

        round_ = int(request.args.get("round", -1))

        allow_external = bool(request.args.get("allow_external", False))
        allow_incomplete = bool(request.args.get("allow_incomplete", False))

        if round_ == -1:
            categories = select(Category).join(Round).where(or_(Round.number == 0, Round.number == 1))

        elif 0 <= round_ <= 2:
            categories = select(Category).join(Round).where(Round.number == round_)

        else:
            abort(
                400,
                message="The round number must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)",
            )
            return

        if (start != -1) and (stop != -1):
            categories = date_query(model=Category, start=start, stop=stop, chained_results=categories)

        if show_number != -1 and show_id != -1:
            abort(400, message="Only one of Show Number or Show ID may be supplied at a time.")

        elif show_number != -1:
            categories = show_query(model=Category, identifier="number", value=show_number, chained_results=categories)

        elif show_id != -1:
            categories = show_query(model=Category, identifier="id", value=show_id, chained_results=categories)

        if not allow_incomplete:
            categories = categories.where(Category.complete == True)  # noqa: E712

        if not allow_external:
            categories = categories.where(select(Set).exists().where(Set.external == False))  # noqa: E712

        categories = session.scalars(categories.order_by(Category.id)).all()

        if (number_results := len(categories)) < size:
            abort(400, message=f"Unfortunately only {number_results} categories were found. Please reduce the size.")

        numbers = random.sample(range(0, number_results), min(number_results, size * 2))

        game = []

        while len(game) < size:
            try:
                category = categories[numbers.pop(0)]

            except IndexError:
                abort(
                    400, message=f"Unfortunately only {number_results} categories were found. Please reduce the size."
                )

            if category.name not in (i["category"]["name"] for i in game):
                sets = session.scalars(
                    select(Set).where(Set.category_id == category.id).join(Value).order_by(Set.value)
                ).all()

                game.append({"category": category_schema.dump(category), "sets": sets_schema.dump(sets)})

        return jsonify(game)


def paginate(model: Select, schema: callable, indices: dict[str, str]) -> dict:
    if (count := session.scalar(select(func.count()).select_from(model.subquery()))) == 0:
        no_results()

    start = int(indices.get("start", 0))
    number = min(int(indices.get("number", 100)), 200)

    if start > count:
        abort(400, message="start number too great")

    if not isinstance(model, Select):
        model = select(model)

    rows = session.scalars(model).all()

    if start + number > count:
        data = rows[start:]

    else:
        data = rows[start : start + number]

    return jsonify(
        {
            "start": start,
            "number": number,
            "data": schema(data),
            "results": count,
        }
    )


def date_query(
    model: Q, year: int = -1, month: int = -1, day: int = -1, start: int = -1, stop: int = -1, chained_results=None
) -> Q:
    if chained_results is not None:
        results = chained_results

    else:
        results = select(model)

    if year != -1:
        try:
            date = datetime.datetime.strptime(f"{year:04d}/{abs(month):02d}/{abs(day):02d}", "%Y/%m/%d")

        except ValueError:
            abort(
                400,
                message="That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)",
            )

        results = results.filter(model.date.has(year=date.year))

        if month != -1:
            results = results.filter(model.date.has(month=date.month))

            if day != -1:
                results = results.filter(model.date.has(day=date.day))

    elif (start != -1) and (stop != -1):
        if start > stop:
            abort(400, message="The stop year must come after the starting year.")

        if 1 > start or 1 > stop or 9999 < start or 9999 < stop:
            abort(400, message="year range must be between 0001 and 9999")

        if session.scalar(select(Date).where(start <= Date.year).where(Date.year <= stop)) is None:
            abort(
                400,
                message="There are no data in the database within that year span. Please double check your values.",
            )

        # TODO: New style
        results = results.join(Date, Date.id == model.date_id).filter(and_(start <= Date.year, Date.year <= stop))

    return results


def id_query(model: Q, id_: int) -> Q:
    results = session.scalar(select(model).filter_by(id=id_))

    if results is None:
        no_results()

    else:
        return results


def show_query(model: Q, identifier: str, value: int, chained_results=None) -> Q:
    if chained_results is not None:
        results = chained_results

    else:
        results = select(model)

    if identifier == "number":
        if session.scalar(select(Show).where(Show.number == value)) is None:
            abort(
                400,
                message="There is no show in the database with that number. Please double check your values.",
            )
        results = results.join(Show).where(Show.number == value)

    elif identifier == "id":
        if session.scalar(select(Show).where(Show.id == value)) is None:
            abort(
                400,
                message="There is no show in the database with that ID. Please double check your values.",
            )

        results = results.join(Show).where(Show.id == value)

    return results


def round_query(model: Q, number: int) -> Q:
    if not (0 <= number <= 2):
        abort(400, message="round number must be between 0 (jeopardy) and 2 (final jeopardy/tiebreaker)")

    return select(model).join(Round).where(Round.number == number)


def no_results(message: str = "no items were found with that query"):
    abort(404, message=message)


api.add_resource(SetMultiple, "/set")
api.add_resource(SetById, "/set/id/<int:set_id>")
api.add_resource(SetByRound, "/set/round/<round_number>")
api.add_resource(SetByShowNumber, "/set/show/number/<int:show_number>")
api.add_resource(SetByShowId, "/set/show/id/<int:show_id>")
api.add_resource(
    SetByDate,
    "/set/date/<int:year>",
    "/set/date/<int:year>/<int:month>",
    "/set/date/<int:year>/<int:month>/<int:day>",
)

api.add_resource(
    SetByYear,
    "/set/years/<int:start>/<int:stop>",
)


api.add_resource(ShowMultiple, "/show")
api.add_resource(ShowByNumber, "/show/number/<int:show_number>")
api.add_resource(ShowById, "/show/id/<int:show_id>")
api.add_resource(
    ShowByDate,
    "/show/date/<int:year>",
    "/show/date/<int:year>/<int:month>",
    "/show/date/<int:year>/<int:month>/<int:day>",
)

api.add_resource(ShowByYears, "/show/years/<int:start>/<int:stop>")


api.add_resource(CategoryMultiple, "/category")
api.add_resource(CategoryById, "/category/id/<int:category_id>")
api.add_resource(
    CategoryByDate,
    "/category/date/<int:year>",
    "/category/date/<int:year>/<int:month>",
    "/category/date/<int:year>/<int:month>/<int:day>",
)

api.add_resource(CategoryByYears, "/category/years/<int:start>/<int:stop>")

api.add_resource(CategoryByCompletion, "/category/complete/<completion>", "/category/<completion_string>")
api.add_resource(CategoryByName, "/category/name/<name_string>")
api.add_resource(CategoryByRound, "/category/round/<round_number>")
api.add_resource(CategoryByShowNumber, "/category/show/number/<int:show_number>")
api.add_resource(CategoryByShowId, "/category/show/id/<int:show_id>")

api.add_resource(DetailsResource, "/details")
api.add_resource(GameResource, "/game")
# api.add_resource(BlankResource, "/")
