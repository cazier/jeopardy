import typing as t
from functools import lru_cache

import sqlalchemy
from flask.json.provider import DefaultJSONProvider
from sqlalchemy.orm.mapper import Mapper

from jeopardy.api.models import Q, Base


@lru_cache
def schema_keys(model: type[Q]) -> list[tuple[str, t.Callable[[Q], t.Any]]]:
    """Get the name and serialization function for each column, which is intended to be included in the JSON data, for
    a particular model.

    Args:
        model (type[Q]): model to be serialized

    Returns:
        list[tuple[str, t.Callable[[Q], t.Any]]]: names (keys) and serialization functions
    """
    mapper: Mapper[Q] = sqlalchemy.inspect(model, raiseerr=True).mapper

    response = []

    for attr in mapper.attrs:
        if func := attr.info.get("serialize", None):
            response.append((attr.key, func))
            continue

        if func := getattr(type(model), attr.key).info.get("serialize", None):
            response.append((attr.key, func))

    return response


class ApiJSONProvider(DefaultJSONProvider):
    """Custom JSON provider for the API to automatically determine the serialization functions (and the actual included
    data) for each request response.
    """

    @staticmethod
    def default(data: t.Any) -> dict[str, t.Any]:
        """Provides a custom serialization method for objects the standard ``json.dumps`` doesn't know how to dump.

        Args:
            data (t.Any): object to be serialized, which may contain SQLAlchemy models

        Returns:
            dict[str, t.Any]: serialized json data
        """
        if isinstance(data, Base):
            resp: dict[str, t.Any] = {}

            for key, func in schema_keys(data):
                resp[key] = func(getattr(data, key))

            return resp

        return super(ApiJSONProvider, ApiJSONProvider).default(data)
