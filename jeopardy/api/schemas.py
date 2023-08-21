import typing as t
from functools import lru_cache

import sqlalchemy
from flask.json.provider import DefaultJSONProvider
from sqlalchemy.orm.mapper import Mapper

from jeopardy.api.models import Q, Base


@lru_cache
def schema_keys(model: type[Q]) -> t.Iterator[tuple[str, t.Callable[[Q], t.Any]]]:
    mapper: Mapper = sqlalchemy.inspect(model)

    response: list[tuple[str, t.Callable[[Q], t.Any]]] = []

    for attr in mapper.attrs:
        if func := getattr(type(model), attr.key).info.get("serialize", None):
            response.append((attr.key, func))

    return response


class ApiJSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(o: t.Any) -> t.Any:
        if isinstance(o, Base):
            resp: dict[str, t.Any] = {}

            for key, func in schema_keys(o):
                resp[key] = func(getattr(o, key))

            return resp

        return super(ApiJSONProvider, ApiJSONProvider).default(o)
