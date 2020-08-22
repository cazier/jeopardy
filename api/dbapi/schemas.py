from flask_marshmallow import fields

from dbapi import ma
from dbapi.models import Set, Category, Date, Show, Round, Value, External, Complete


class DateSchema(ma.SQLAlchemySchema):
    # date = fields.fields.Function(lambda obj: obj.date.strftime("%Y-%d"))
    class Meta:
        model = Date
        fields = ("date",)


class ShowSchema(ma.SQLAlchemySchema):
    date = fields.fields.Pluck("DateSchema", "date")
    length = fields.fields.Function()

    class Meta:
        model = Show
        fields = (
            "id",
            "date",
            "number",
        )


class RoundSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Round
        fields = ("number",)


class CategorySchema(ma.SQLAlchemySchema):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
        )


class ValueSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Value
        fields = ("amount",)


class ExternalSchema(ma.SQLAlchemySchema):
    class Meta:
        model = External
        fields = ("state",)


class CompleteSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Complete
        fields = ("state",)


class SetSchema(ma.SQLAlchemyAutoSchema):
    category = fields.fields.Pluck("CategorySchema", "name")
    date = fields.fields.Pluck("DateSchema", "date")
    show = fields.fields.Pluck("ShowSchema", "number")
    round = fields.fields.Pluck("RoundSchema", "number")
    value = fields.fields.Pluck("ValueSchema", "amount")
    external = fields.fields.Pluck("ExternalSchema", "state")
    complete = fields.fields.Pluck("CompleteSchema", "state")

    class Meta:
        model = Set
        fields = (
            "id",
            "category",
            "date",
            "show",
            "round",
            "answer",
            "question",
            "value",
            "external",
            "complete",
        )


set_schema = SetSchema()
sets_schema = SetSchema(many=True)

show_schema = ShowSchema()
shows_schema = ShowSchema(many=True)

# category_schema = CategorySchema()
# categories_schema = CategorySchema(many=True)
