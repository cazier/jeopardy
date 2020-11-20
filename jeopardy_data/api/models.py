from api import db

from sqlalchemy import extract
from sqlalchemy.ext.hybrid import hybrid_property


class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    date_id = db.Column(db.Integer, db.ForeignKey("date.id"), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
    value_id = db.Column(db.Integer, db.ForeignKey("value.id"), nullable=False)
    external_id = db.Column(db.Integer, db.ForeignKey("external.id"), nullable=False)
    complete_id = db.Column(db.Integer, db.ForeignKey("complete.id"), nullable=False)
    hash = db.Column(db.Integer, nullable=False, unique=True)

    answer = db.Column(db.String(1000))
    question = db.Column(db.String(255))

    def __repr__(self):
        return f"<Set {self.id}, (Hash={self.hash})>"


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    show_id = db.Column(db.Integer, db.ForeignKey("show.id"), nullable=False)
    date_id = db.Column(db.Integer, db.ForeignKey("date.id"), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
    complete_id = db.Column(db.Integer, db.ForeignKey("complete.id"), nullable=False)
    sets = db.relationship("Set", backref="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Date(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    sets = db.relationship("Set", backref="date")
    show = db.relationship("Show", backref="date", uselist=False)
    categories = db.relationship("Category", backref="date")

    @hybrid_property
    def year(self):
        return self.date.year

    @year.expression
    def year(cls):
        return extract("year", cls.date)

    @hybrid_property
    def month(self):
        return self.date.month

    @month.expression
    def month(cls):
        return extract("month", cls.date)

    @hybrid_property
    def day(self):
        return self.date.day

    @day.expression
    def day(cls):
        return extract("day", cls.date)

    def __repr__(self):
        return f"<Date {self.date}>"


class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    date_id = db.Column(db.Integer, db.ForeignKey("date.id"))
    sets = db.relationship("Set", backref="show")
    categories = db.relationship("Category", backref="show")

    def __repr__(self):
        return f"<Show {self.number}>"


class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    sets = db.relationship("Set", backref="round")
    categories = db.relationship("Category", backref="round")
    values = db.relationship("Value", backref="round")

    def __repr__(self):
        return f"<Round {self.number}>"


class Value(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
    sets = db.relationship("Set", backref="value")

    def __repr__(self):
        return f"<Value {self.amount}>"


class External(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.Boolean)
    sets = db.relationship("Set", backref="external")

    def __repr__(self):
        return f"<External {self.state}>"


class Complete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.Boolean)
    sets = db.relationship("Set", backref="complete")
    categories = db.relationship("Category", backref="complete")

    def __repr__(self):
        return f"<Complete {self.state}>"
