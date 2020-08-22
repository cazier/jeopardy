# import requests
import json
import tqdm
import datetime
import glob
import zlib
from dbapi import db
from dbapi.models import Set, Date, Category, Show, Round, Complete, External, Value

LEGEND = {"Jeopardy!": 1, "Double Jeopardy!": 2, "Final Jeopardy!": 3, "Tiebreaker": 4}
# with open("../json/by_year/1988.json", 'r') as json_file:
#     data = json.load(json_file)

for file in tqdm.tqdm(glob.glob("../json/by_show/0[3-9]*.json")):
    with open(file, "r") as json_file:
        file = json.load(json_file)

    for data in file:
        data["v"] = int(data["v"].replace("$", ""))
        data["r"] = LEGEND[data["r"]]
        if (date := Date.query.filter_by(date=datetime.date.fromisoformat(data["d"])).first()) is None:
            date = Date(date=datetime.date.fromisoformat(data["d"]))
            db.session.add(date)

        if (show := Show.query.filter_by(number=data["s"]).first()) is None:
            show = Show(number=data["s"], date=date)
            db.session.add(show)

        if (round_ := Round.query.filter_by(number=data["r"]).first()) is None:
            round_ = Round(number=data["r"])
            db.session.add(round_)

        if (complete := Complete.query.filter_by(state=data["f"]).first()) is None:
            complete = Complete(state=data["f"])
            db.session.add(complete)

        if (category := Category.query.filter_by(name=data["c"]).first()) is None:
            category = Category(name=data["c"], show=show, round=round_, complete=complete, date=date)
            db.session.add(category)

        if (value := Value.query.filter_by(amount=data["v"]).first()) is None:
            value = Value(amount=data["v"], round=round_)
            db.session.add(value)

        if (external := External.query.filter_by(state=data["e"]).first()) is None:
            external = External(state=data["e"])
            db.session.add(external)

        hash = zlib.adler32(f'{data["q"]}{data["a"]}{show.number}'.encode())

        if Set.query.filter_by(hash=hash).first() is None:
            set_ = Set(
                category=category,
                date=date,
                show=show,
                round=round_,
                answer=data["a"],
                question=data["q"],
                value=value,
                external=external,
                complete=complete,
                hash=hash,
            )

            db.session.add(set_)
            db.session.commit()

        # new = dict()
        # new["c"] = i["c"]
        # new["d"] = i["d"]
        # new["a"] = i["a"]
        # new["v"] = int(i["v"].replace("$", ""))
        # new["q"] = i["a"]
        # new["r"] = LEGEND[i["r"]]
        # new["s"] = i["s"]
        # new["e"] = i["e"]
        # new["f"] = i["f"]

        # requests.post("http://192.168.1.173:5000/sets", json=new)

