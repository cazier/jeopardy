import re
import random
import typing as t
import functools

from flask import Response, abort
from flask import jsonify as flask_jsonify
from flask import request
from sqlalchemy import Select, or_, func, select
from flask.views import MethodView
from flask.typing import ResponseReturnValue

from jeopardy.api import KEYS, bp, database
from jeopardy.api.models import M, N, Set, Date, Show, Round, Value, Category, db, or_none, or_zero

session = db.session

P = t.ParamSpec("P")
T = t.TypeVar("T")
F = t.TypeVar("F", bound=t.Callable[..., t.Any])


def query_check(model: "M") -> t.Callable[[F], F]:
    def wrapped(function: t.Callable[P, T]) -> t.Callable[P, T]:
        @functools.wraps(function)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            key = "/".join(kwargs.keys())

            if len(kwargs) > 1:
                query = {"date": kwargs}

            else:
                query = kwargs.copy()  # type: ignore[assignment]

            selection = select(func.count()).select_from(model).filter_by(**query)
            if db.session.scalar(selection) == 0:
                abort(
                    400,
                    description=f"There is no {model.__name__.lower()} in the database with that {key}.",
                )

            return function(*args, **kwargs)

        return inner

    return wrapped  # type: ignore[return-value]


def validate(model: "M") -> t.Callable[[F], F]:
    def wrapped(function: t.Callable[P, T]) -> t.Callable[P, T]:
        @functools.wraps(function)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if error := model.valid_inputs(**kwargs):  # type: ignore[arg-type]
                abort(400, description=error)

            return function(*args, **kwargs)

        return inner

    return wrapped  # type: ignore[return-value]


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
            return jsonify()

        shows.update(
            {
                "first_id": or_none(session.scalars(select(Show).order_by(Show.id)).first()).id,
                "last_id": or_none(session.scalars(select(Show).order_by(Show.id.desc())).first()).id,
                "first_number": or_none(session.scalars(select(Show).order_by(Show.number)).first()).number,
                "last_number": or_none(session.scalars(select(Show).order_by(Show.number.desc())).first()).number,
            }
        )

        air_dates = {
            "oldest": or_none(session.scalars(select(Date).order_by(Date.date)).first()).date,
            "most_recent": or_none(session.scalars(select(Date).order_by(Date.date.desc())).first()).date,
        }

        return jsonify({"categories": categories, "sets": sets, "shows": shows, "air_dates": air_dates})


class SetById(BaseResource):
    def get(self, id: int) -> ResponseReturnValue:
        results = select(Set).where(Set.id == id)

        return jsonify(session.scalar(results))

    def delete(self, id: int) -> ResponseReturnValue:
        row = session.scalar(select(Set).filter_by(id=id))

        if row:
            session.delete(row)
            session.commit()

            return jsonify({"deleted": id})

        return abort(404, description="id could not be found in the database")


class SetByRound(BaseResource):
    decorators = [query_check(Round), validate(Round)]

    def get(self, number: int) -> ResponseReturnValue:
        results = select(Set).join(Round).where(Round.number == number).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByShowNumber(BaseResource):
    def get(self, number: int) -> ResponseReturnValue:
        results = select(Set).join(Show).where(Show.number == number).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByShowId(BaseResource):
    def get(self, id: int) -> ResponseReturnValue:
        results = select(Set).join(Show).where(Show.id == id).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByDate(BaseResource):
    decorators = [query_check(Date), validate(Date)]

    def get(self, year: int, month: int = -1, day: int = -1) -> ResponseReturnValue:
        results = select(Set).join(Date).where(Date.date == {"year": year, "month": month, "day": day}).order_by(Set.id)

        return paginate(model=results, indices=request.args)


class SetByYear(BaseResource):
    decorators = [query_check(Date), validate(Date)]

    def get(self, start: int, stop: int) -> ResponseReturnValue:
        results = select(Set).join(Date).where(Date.date == {"start": start, "stop": stop}).order_by(Date.date)

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
        payload = t.cast(dict[str, str | int | bool], request.json)
        if (set(payload.keys()) == KEYS) and all((len(str(value)) > 0 for value in payload.values())):
            try:
                resp = database.add(clue_data=payload, uses_shortnames=False)

                return jsonify(resp)

            except database.SetAlreadyExistsError:
                abort(400, description="The question set supplied is already in the database!")

        else:
            abort(400, description="The question set supplied is missing some data. Every field is required.")


class ShowById(BaseResource):
    def get(self, id: int) -> ResponseReturnValue:
        results = select(Show).where(Show.id == id)

        return jsonify(session.scalar(results))


class ShowByNumber(BaseResource):
    def get(self, number: int) -> ResponseReturnValue:
        results = select(Show).where(Show.number == number)

        return jsonify(session.scalar(results))


class ShowByDate(BaseResource):
    decorators = [query_check(Date), validate(Date)]

    def get(self, year: int, month: int = -1, day: int = -1) -> ResponseReturnValue:
        results = (
            select(Show).join(Date).where(Date.date == {"year": year, "month": month, "day": day}).order_by(Show.id)
        )

        return paginate(model=results, indices=request.args)


class ShowByYears(BaseResource):
    decorators = [query_check(Date), validate(Date)]

    def get(self, start: int, stop: int) -> ResponseReturnValue:
        results = select(Show).join(Date).where(Date.date == {"start": start, "stop": stop}).order_by(Date.date)

        return paginate(model=results, indices=request.args)


class ShowMultiple(BaseResource):
    def get(self) -> ResponseReturnValue:
        return paginate(model=select(Show), indices=request.args)


class CategoryById(BaseResource):
    def get(self, category_id: int) -> ResponseReturnValue:
        results = select(Category).where(Category.id == category_id)

        return jsonify(session.scalar(results))


class CategoryByDate(BaseResource):
    decorators = [query_check(Date), validate(Date)]

    def get(self, year: int, month: int = -1, day: int = -1) -> ResponseReturnValue:
        results = select(Category).join(Date).where(Date.date == {"year": year, "month": month}).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByYears(BaseResource):
    decorators = [query_check(Date), validate(Date)]

    def get(self, start: int, stop: int) -> ResponseReturnValue:
        results = select(Category).join(Date).where(Date.date == {"start": start, "stop": stop}).order_by(Date.date)

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
            .where(Category.name.ilike(f"%{name_string}%"))
            .join(Date)
            .join(Round)
            .order_by(Date.date, Round.number, Category.name)
        )

        return paginate(model=results, indices=request.args)


class CategoryByShowNumber(BaseResource):
    decorators = [query_check(Show)]

    def get(self, number: int) -> ResponseReturnValue:
        results = select(Category).join(Show).where(Show.number == number).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByRound(BaseResource):
    decorators = [query_check(Round), validate(Round)]

    def get(self, number: int) -> ResponseReturnValue:
        results = select(Category).join(Round).where(Round.number == number).order_by(Category.name)

        return paginate(model=results, indices=request.args)


class CategoryByShowId(BaseResource):
    decorators = [query_check(Show)]

    def get(self, id: int) -> ResponseReturnValue:
        results = select(Category).join(Show).where(Show.id == id).order_by(Category.name)
        return paginate(model=results, indices=request.args)


class CategoryMultiple(BaseResource):
    def get(self) -> ResponseReturnValue:
        return paginate(model=select(Category), indices=request.args)


class GameResource(BaseResource):
    def get(self) -> ResponseReturnValue:
        size = int(request.args.get("size", 6))
        start = int(request.args.get("start", -1))
        stop = int(request.args.get("stop", -1))

        show_number = int(request.args.get("show_number", -1))
        show_id = int(request.args.get("show_id", -1))

        round = int(request.args.get("round", -1))

        allow_external = bool(request.args.get("allow_external", False))
        allow_incomplete = bool(request.args.get("allow_incomplete", False))

        if round == -1:
            categories = select(Category).join(Round).where(or_(Round.number == 0, Round.number == 1))

        elif 0 <= round <= 2:
            categories = select(Category).join(Round).where(Round.number == round)

        else:
            message = "The round number must be one of 0 (Jeopardy!), 1 (Double Jeopardy!), or 2 (Final Jeopardy!)"

            abort(400, description=message)

        if (start != -1) and (stop != -1):
            categories = categories.join(Date).where(Date.date == {"start": start, "stop": stop})

        if show_number != -1 and show_id != -1:
            abort(400, description="Only one of Show Number or Show ID can be supplied at a time.")

        elif show_number != -1:
            categories = categories.join(Show).where(Show.number == show_number)

        elif show_id != -1:
            categories = categories.join(Show).where(Show.id == show_id)

        if not allow_incomplete:
            categories = categories.where(Category.complete == True)  # noqa: E712

        if not allow_external:
            categories = categories.where(select(Set).exists().where(Set.external == False))  # noqa: E712

        results = session.scalars(categories.order_by(Category.id)).all()

        if (number_results := len(results)) < size:
            abort(400, description=f"Only {number_results} categories were found.")

        numbers = random.sample(range(0, number_results), min(number_results, size * 2))

        # TODO: Narrow
        selected: set[str] = set()
        game: list[dict[str, t.Any]] = []

        while len(game) < size:
            try:
                category = results[numbers.pop()]

            except IndexError:
                abort(400, description=f"Only {number_results} categories were found.")

            if category.name not in selected:
                sets = session.scalars(
                    select(Set).where(Set.category_id == category.id).join(Value).order_by(Set.value)
                ).all()

                selected.add(category.name)
                game.append({"category": category, "sets": sets})

        return jsonify(game)


def paginate(model: Select[tuple[N]], indices: dict[str, str], missing: str = "") -> ResponseReturnValue:
    if (count := or_zero(session.scalar(select(func.count()).select_from(model.subquery())))) == 0:
        return jsonify()

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
            "data": data,
            "results": count,
        }
    )


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


def jsonify(*args: t.Any, **kwargs: t.Any) -> Response:
    resp = flask_jsonify(*args, **kwargs)

    if not resp.json:
        abort(404, description="no items were found with that query")

    return resp


register_api(SetMultiple, "/set")
register_api(SetById, "/set/id/<int:id>")
register_api(SetByRound, "/set/round/<int:number>")
register_api(SetByShowNumber, "/set/show/number/<int:number>")
register_api(SetByShowId, "/set/show/id/<int:id>")
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
register_api(ShowByNumber, "/show/number/<int:number>")
register_api(ShowById, "/show/id/<int:id>")
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
register_api(CategoryByRound, "/category/round/<int:number>")
register_api(CategoryByShowNumber, "/category/show/number/<int:number>")
register_api(CategoryByShowId, "/category/show/id/<int:id>")

register_api(DetailsResource, "/details")
register_api(GameResource, "/game")
