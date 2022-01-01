from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemySchema
from marshmallow_sqlalchemy.schema import auto_field

from . import models


class RoundSchema(SQLAlchemySchema):
    model = models.Round

    number = fields.Integer(required=True)


class ValueSchema(SQLAlchemySchema):
    model = models.Value

    amount = fields.Integer(required=True)


class DateSchema(SQLAlchemySchema):
    model = models.Date

    date = fields.Date(format="iso", required=True)


class ShowSchema(SQLAlchemySchema):
    model = models.Show

    id = fields.Integer(required=True)
    number = fields.Integer(required=True)

    date = fields.Pluck("DateSchema", "date", required=True)


class CategorySchema(SQLAlchemySchema):
    model = models.Category

    id = fields.Integer(required=True)
    name = fields.String(required=True)
    complete = fields.Boolean(required=True)

    date = fields.Pluck("DateSchema", "date")
    show = fields.Pluck("ShowSchema", "number")
    round = fields.Pluck("RoundSchema", "number")


class SetSchema(SQLAlchemySchema):
    model = models.Set

    id = fields.Integer(required=True)
    answer = fields.String(required=True)
    question = fields.String(required=True)
    external = fields.Boolean(required=True)
    complete = fields.Boolean(required=True)

    category = fields.Pluck("CategorySchema", "name")
    date = fields.Pluck("DateSchema", "date")
    show = fields.Pluck("ShowSchema", "number")
    round = fields.Pluck("RoundSchema", "number")
    value = fields.Pluck("ValueSchema", "amount")


set_schema = SetSchema()
sets_schema = SetSchema(many=True)

show_schema = ShowSchema()
shows_schema = ShowSchema(many=True)

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

date_schema = DateSchema()
dates_schema = DateSchema(many=True)
