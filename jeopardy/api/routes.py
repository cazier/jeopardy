import re
import random
import typing as t
import datetime
import collections

from flask import abort, jsonify, request
from sqlalchemy import Select, ScalarResult, or_, and_, func, select
from flask.views import MethodView
from flask.typing import ResponseReturnValue
from flask.json.provider import DefaultJSONProvider

from jeopardy.api import KEYS, bp, database
from jeopardy.api.models import M, Q, Set, Date, Show, Round, Value, Category, db, or_none, or_zero

# from jeopardy.api.schemas import set_schema, sets_schema, show_schema, shows_schema, category_schema, categories_schema

session = db.session


class BaseResource(MethodView):
    methods = ["GET", "POST"]

    def dispatch_request(self, **kwargs: t.Any) -> ResponseReturnValue:
        try:
            return super().dispatch_request(**kwargs)
        except AssertionError as exc:
            if "Unimplemented method" in str(exc):
                return abort(405, description=str(exc))
            return abort(500, description="An unknown error occurred")


class DetailsResource(BaseResource):
    def get(self) -> ResponseReturnValue:
        categories = {
            "total": or_zero(session.scalar(select(func.count()).select_from(Category))),
            "complete": or_zero(session.scalar(select(func.count()).where(Category.complete == True))),  # noqa: E712
            "incomplete": or_zero(session.scalar(select(func.count()).where(Category.complete == False))),  # noqa: E712
        }
        sets = {
            "total": or_zero(session.scalar(select(func.count()).select_from(Set))),
            "has_external": or_zero(session.scalar(select(func.count()).where(Set.external == True))),  # noqa: E712
            "no_external": or_zero(session.scalar(select(func.count()).where(Set.external == True))),  # noqa: E712
        }

        shows = {"total": session.scalar(select(func.count()).select_from(Show))}

        if 0 in {categories["total"], sets["total"], shows["total"]}:
            no_results()

        shows.update(
            {
                "first_id": or_none(session.execute(select(Show).order_by(Show.id)).scalars().first()).id,
                "last_id": or_none(session.execute(select(Show).order_by(Show.id.desc())).scalars().first()).id,
                "first_number": or_none(session.execute(select(Show).order_by(Show.number)).scalars().first()).number,
                "last_number": or_none(
                    session.execute(select(Show).order_by(Show.number.desc())).scalars().first()
                ).number,
            }
        )

        air_dates = {
            "oldest": or_none(session.execute(select(Date).order_by(Date.date)).scalars().first()).date,
            "most_recent": or_none(session.execute(select(Date).order_by(Date.date.desc())).scalars().first()).date,
        }

        return jsonify({"categories": categories, "sets": sets, "shows": shows, "air_dates": air_dates})


class SetById(BaseResource):
    def get(self, set_id: int) -> ResponseReturnValue:
        return jsonify(id_query(model=Set, id_=set_id))

    def delete(self, set_id: int) -> ResponseReturnValue:
        row = session.scalar(select(Set).filter_by(id=set_id))

        if row:
            session.delete(row)
            session.commit()

            return jsonify({"deleted": set_id})

        return abort(404, description="id could not be found in the database")


class SetByRound(BaseResource):
    def get(self, round_number: int) -> ResponseReturnValue:
        results = round_query(model=Set, number=round_number).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByShowNumber(BaseResource):
    def get(self, show_number: int) -> ResponseReturnValue:
        results = show_query(model=Set, identifier="number", value=show_number).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByShowId(BaseResource):
    def get(self, show_id: int) -> ResponseReturnValue:
        results = show_query(model=Set, identifier="id", value=show_id).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByDate(BaseResource):
    def get(self, year: int, month: int = -1, day: int = -1) -> ResponseReturnValue:
        results = date_query(model=Set, year=year, month=month, day=day).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByYear(BaseResource):
    def get(self, start: int, stop: int) -> ResponseReturnValue:
        results = date_query(model=Set, start=start, stop=stop).order_by(Date.date)

        return paginate(model=results, indices=request.args)


class SetMultiple(BaseResource):
    def get(self) -> ResponseReturnValue:
        # TODO: Might be able to get rid of id == date_id if back refs are good?
        results = (
            select(Set)
            .join(Date, Date.id == Set.date_id)
            .join(Round, Round.id == Set.round_id)
            .join(Category, Category.id == Set.category_id)
            .join(Value, Value.id == Set.value_id)
        )

        results = results.order_by(Date.date, Set.round, Category.name, Value.amount)

        return paginate(model=results, indices=request.args)

    def post(self) -> ResponseReturnValue:
        payload: dict[str, t.Any] = request.json  # type: ignore[assignment]
        if (set(payload.keys()) == KEYS) and all((len(str(value)) > 0 for value in payload.values())):
            try:
                resp = database.add(clue_data=payload, uses_shortnames=False)

                return jsonify(resp)

            except database.SetAlreadyExistsError:
                abort(400, description="The question set supplied is already in the database!")

        else:
            abort(400, description="The question set supplied is missing some data. Every field is required.")


class ShowById(BaseResource):
    def get(self, show_id: int) -> ResponseReturnValue:
        return jsonify(id_query(model=Show, id_=show_id))


class ShowByNumber(BaseResource):
    def get(self, show_number: int) -> ResponseReturnValue:
        show = session.scalar(select(Show).where(Show.number == show_number))

        if show is None:
            no_results()

        else:
            return jsonify(show)


class ShowByDate(BaseResource):
    def get(self, year: int, month: int = -1, day: int = -1) -> ResponseReturnValue:
        results = date_query(model=Show, year=year, month=month, day=day).order_by(Show.number)

        return paginate(model=results, indices=request.args)


class ShowByYears(BaseResource):
    def get(self, start: int, stop: int) -> ResponseReturnValue:
        results = date_query(model=Show, start=start, stop=stop).order_by(Date.date)

        return paginate(model=results, indices=request.args)


class ShowMultiple(BaseResource):
    def get(self) -> ResponseReturnValue:
        return paginate(model=select(Show), indices=request.args)


class CategoryById(BaseResource):
    def get(self, category_id: int) -> ResponseReturnValue:
        return jsonify(id_query(model=Category, id_=category_id))


class CategoryByDate(BaseResource):
    def get(self, year: int, month: int = -1, day: int = -1) -> ResponseReturnValue:
        results = date_query(model=Category, year=year, month=month, day=day).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByYears(BaseResource):
    def get(self, start: int, stop: int) -> ResponseReturnValue:
        results = date_query(model=Category, start=start, stop=stop).order_by(Date.date)

        return paginate(model=results, indices=request.args)


class CategoryByCompletion(BaseResource):
    def get(self, completion: str = "") -> ResponseReturnValue:
        if completion.lower() in ("true", "complete", "1"):
            results = select(Category).where(Category.complete == True)  # noqa: E712

        elif completion.lower() in ("false", "incomplete", "0"):
            results = select(Category).where(Category.complete == False)  # noqa: E712

        else:
            abort(400, description="The completion status value is invalid")

        results = results.join(Date).join(Round).order_by(Date.date, Round.number, Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByName(BaseResource):
    def get(self, name_string: int) -> ResponseReturnValue:
        results = (
            select(Category)
            .where(Category.name.like(f"%{name_string}%"))
            .join(Date)
            .join(Round)
            .order_by(Date.date, Round.number, Category.name)
        )

        return paginate(model=results, indices=request.args)


class CategoryByShowNumber(BaseResource):
    def get(self, show_number: int) -> ResponseReturnValue:
        results = show_query(model=Category, identifier="number", value=show_number).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByRound(BaseResource):
    def get(self, round_number: int) -> ResponseReturnValue:
        results = round_query(model=Category, number=round_number).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByShowId(BaseResource):
    def get(self, show_id: int) -> ResponseReturnValue:
        results = show_query(model=Category, identifier="id", value=show_id).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryMultiple(BaseResource):
    def get(self) -> ResponseReturnValue:
        return paginate(model=select(Category), indices=request.args)


# class BlankResource(BaseResource):
#     def get(self) -> ResponseReturnValue:
#         return {"message": "hello!"}


class GameResource(BaseResource):
    def get(self) -> ResponseReturnValue:
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
                description="The round number must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)",
            )
            return

        if (start != -1) and (stop != -1):
            categories = date_query(model=Category, start=start, stop=stop, chained_results=categories)

        if show_number != -1 and show_id != -1:
            abort(400, description="Only one of Show Number or Show ID may be supplied at a time.")

        elif show_number != -1:
            categories = show_query(model=Category, identifier="number", value=show_number, chained_results=categories)

        elif show_id != -1:
            categories = show_query(model=Category, identifier="id", value=show_id, chained_results=categories)

        if not allow_incomplete:
            categories = categories.where(Category.complete == True)  # noqa: E712

        if not allow_external:
            categories = categories.where(select(Set).exists().where(Set.external == False))  # noqa: E712

        results = session.scalars(categories.order_by(Category.id)).all()

        if (number_results := len(results)) < size:
            abort(400, description=f"Only {number_results} categories were found.")

        numbers = random.sample(range(0, number_results), min(number_results, size * 2))

        # TODO: Narrow
        game: list[dict[str, t.Any]] = []

        while len(game) < size:
            try:
                category = results[numbers.pop(0)]

            except IndexError:
                abort(
                    400,
                    description=f"Only {number_results} categories were found.",
                )

            if category.name not in (i["category"].name for i in game):
                sets = session.scalars(
                    select(Set).where(Set.category_id == category.id).join(Value).order_by(Set.value)
                ).all()

                # game.append({"category": dump(category), "sets": dump(sets)})
                game.append({"category": category, "sets": sets})

        return jsonify(game)


def paginate(model: Select[tuple[Q]], indices: dict[str, str]) -> ResponseReturnValue:
    if (count := or_zero(session.scalar(select(func.count()).select_from(model.subquery())))) == 0:
        no_results()

    start = int(indices.get("start", 0))
    number = min(int(indices.get("number", 100)), 200)

    if start > count:
        abort(400, description="start number too great")

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
            # "data": dump(data),
            "data": data,
            "results": count,
        }
    )


def date_query(
    model: M,
    year: int = -1,
    month: int = -1,
    day: int = -1,
    start: int = -1,
    stop: int = -1,
    chained_results: t.Optional[Select[tuple[M]]] = None,
) -> Select[tuple[M]]:
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
                description="That date is invalid (0001 <= year <= 9999, 1 <= month <= 12, 1 <= day <= 31)",
            )

        results = results.join(Date).where(Date.year == date.year)

        if month != -1:
            results = results.where(Date.month == date.month)

            if day != -1:
                results = results.where(Date.day == date.day)

    elif (start != -1) and (stop != -1):
        if start > stop:
            abort(400, description="The stop year must come after the starting year.")

        if 1 > start or 1 > stop or 9999 < start or 9999 < stop:
            abort(400, description="year range must be between 0001 and 9999")

        if session.scalar(select(Date).where(start <= Date.year).where(Date.year <= stop)) is None:
            abort(
                400,
                description="There are no data in the database within that year span.",
            )

        results = results.join(Date).where(and_(start <= Date.year, Date.year <= stop))

    return results


def id_query(model, id_: int):
    results = session.scalar(select(model).filter_by(id=id_))

    if results is None:
        no_results()

    else:
        return results


def show_query(model, identifier: str, value: int, chained_results=None):
    if chained_results is not None:
        results = chained_results

    else:
        results = select(model)

    if identifier == "number":
        if session.scalar(select(Show).where(Show.number == value)) is None:
            abort(
                400,
                description="There is no show in the database with that number.",
            )
        results = results.join(Show).where(Show.number == value)

    elif identifier == "id":
        if session.scalar(select(Show).where(Show.id == value)) is None:
            abort(
                400,
                description="There is no show in the database with that ID.",
            )

        results = results.join(Show).where(Show.id == value)

    return results


def round_query(model, number: int):
    if not (0 <= number <= 2):
        abort(400, description="round number must be between 0 (jeopardy) and 2 (final jeopardy/tiebreaker)")

    return select(model).join(Round).where(Round.number == number)


def no_results(message: str = "no items were found with that query") -> t.NoReturn:
    abort(404, description=message)


def register_api(view: type[BaseResource], *rules: str, endpoints: tuple[str, ...] = ()) -> None:
    if not endpoints:
        endpoints = (re.sub("(?!^)([A-Z]+)", r"_\1", view.__name__).lower(),)

    for rule, endpoint in zip(rules, endpoints):
        bp.add_url_rule(rule, endpoint, view_func=view.as_view(endpoint))


@bp.errorhandler(400)
def resource_not_valid(e: Exception) -> ResponseReturnValue:
    return jsonify(message=str(e)), 400


@bp.errorhandler(404)
def items_not_found(e: Exception) -> ResponseReturnValue:
    return jsonify(message=str(e)), 404


@bp.errorhandler(405)
def unimplemented(e: Exception) -> ResponseReturnValue:
    return jsonify(message=str(e)), 405


# def register_error(*codes) -> None:
#     def _in_json_response(exc: Exception):

#     for code in codes:
#         bp.register_error_handler(code)

register_api(SetMultiple, "/set")
register_api(SetById, "/set/id/<int:set_id>")
register_api(SetByRound, "/set/round/<int:round_number>")
register_api(SetByShowNumber, "/set/show/number/<int:show_number>")
register_api(SetByShowId, "/set/show/id/<int:show_id>")
register_api(
    SetByDate,
    "/set/date/<int:year>",
    "/set/date/<int:year>/<int:month>",
    "/set/date/<int:year>/<int:month>/<int:day>",
    endpoints=("set_by_date_year", "set_by_date_month", "set_by_date_day"),
)


register_api(
    SetByYear,
    "/set/years/<int:start>/<int:stop>",
)


register_api(ShowMultiple, "/show")
register_api(ShowByNumber, "/show/number/<int:show_number>")
register_api(ShowById, "/show/id/<int:show_id>")
register_api(
    ShowByDate,
    "/show/date/<int:year>",
    "/show/date/<int:year>/<int:month>",
    "/show/date/<int:year>/<int:month>/<int:day>",
    endpoints=("show_by_date_year", "show_by_date_month", "show_by_date_day"),
)

register_api(ShowByYears, "/show/years/<int:start>/<int:stop>")


register_api(CategoryMultiple, "/category")
register_api(CategoryById, "/category/id/<int:category_id>")
register_api(
    CategoryByDate,
    "/category/date/<int:year>",
    "/category/date/<int:year>/<int:month>",
    "/category/date/<int:year>/<int:month>/<int:day>",
    endpoints=("category_by_date_year", "category_by_date_month", "category_by_date_day"),
)

register_api(CategoryByYears, "/category/years/<int:start>/<int:stop>")

register_api(
    CategoryByCompletion,
    "/category/complete/<completion>",
    "/category/<completion>",
    endpoints=("category_by_completion", "category_completion"),
)
register_api(CategoryByName, "/category/name/<name_string>")
register_api(CategoryByRound, "/category/round/<int:round_number>")
register_api(CategoryByShowNumber, "/category/show/number/<int:show_number>")
register_api(CategoryByShowId, "/category/show/id/<int:show_id>")

register_api(DetailsResource, "/details")
register_api(GameResource, "/game")
# api.add_resource(BlankResource, "/")

# register_error(400, 405)
