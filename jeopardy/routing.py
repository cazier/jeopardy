from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    abort,
    flash,
    get_flashed_messages,
)

import random

try:
    import alex
    import config
    import storage

    from sockets import socketio, get_room

except ImportError:
    from jeopardy import alex
    from jeopardy import config
    from jeopardy import storage
    
    from jeopardy.sockets import socketio, get_room


routing = Blueprint(name="routing", import_name=__name__)


@routing.route("/", methods=["GET"])
def route_index():
    """Display the home (index) page, with two buttons to start or join a game

    Only allows GET requests.
    """
    return render_template(template_name_or_list="index.html")


@routing.route("/new/", methods=["GET"])
def route_new():
    """Display the option(s) available to start a new game. As of now, this only supports selecting the
    number of categories with which to play. Conceivably "infinte" number of players can join.

    Only allows GET requests.
    """
    return render_template(template_name_or_list="new.html", errors=get_flashed_messages())


@routing.route("/join/<room>", methods=["GET"])
@routing.route("/join/", methods=["GET"])
def route_join(room: str = ""):
    """Display the page to join a game. This does include some error handling, but largely is messy...

    - Players will enter their name, and the room code created by the host. No two players can have the same name
    - The "Board" will just enter a room code.
    - If the host gets disconnected, they can rejoin here too.
    - Whoever starts the game can also create a "magic link" that will allow people to direcly join without typing in
      the room code.

    Only allows GET requests.
    """
    if room != "" and room in storage.rooms():
        room = room

    else:
        room = ""

    return render_template(template_name_or_list="join.html", errors=get_flashed_messages(), room_code=room.upper())


@routing.route("/host/", methods=["GET", "POST"])
def route_host():
    """Displays the page used by the game host to manage the gameplay. It can be "accessed" either from the `/new`
    endpoint or the `/join` endpoint, and will do different things, as needed.

    Allows both GET and POST requests, though the GET request is primarily intended for use in
    testing (using the `testing.html` template).
    """

    # Typical (Production) routing will use a POST request.
    if request.method == "POST":
        # If the request has a room code supplied, the host is `/join`ing the game.
        if (room := request.form.get("room")) :
            room = room

        # If the method has a size supplied (because it's a required field), the host is starting a
        # `/new` game.
        elif request.form.get("size", False):
            game_settings: dict = {"room": generate_room_code()}

            game_settings["size"] = int(request.form.get("size"))

            start = request.form.get("start")
            stop = request.form.get("stop")

            if start != "" and stop != "":
                game_settings["start"] = int(start)
                game_settings["stop"] = int(stop)

            elif start == "" and stop == "":
                pass

            else:
                flash(
                    message="If specifying years to get games, you must include both a start and stop year.",
                    category="error",
                )
                return redirect(url_for("routing.route_new"))

            if (style := request.form.get("qualifier")) != "":
                game_settings[style] = int(show if (show := request.form.get("show")) != "" else -1)

            game = alex.Game(game_settings=game_settings)
            game.make_board()

            storage.push(
                room=game_settings["room"],
                value=game,
            )

            room = game_settings["room"]

            session["name"] = "Host"
            session["room"] = room

        else:
            abort(500)

    elif request.method == "GET":
        if (room := request.args.get(key="room", default=False)) :
            if "/test/" in request.headers["Referer"]:
                session["name"] = "Host"
                session["room"] = room

        else:
            abort(500)

        room = session["room"]

    if room not in storage.rooms():
        flash(
            message="The room code you entered was invalid. Please try again!",
            category="error",
        )
        return redirect(url_for("routing.route_join"))

    return render_template(
        template_name_or_list="host.html",
        session=session,
        game=storage.pull(room=room),
    )


@routing.route("/play/", methods=["GET", "POST"])
def route_player():
    """Displays the page used by the players to "compete". The page will initially run a number of checks
    to verify that the room code was valid, or that the name entered can be done. If anything is invalid,
    reroute back to `/join` and display the messages.

    Allows both GET and POST requests.
    """
    if request.method == "POST":
        error_occurred = False

        room = request.form.get("room").upper()
        name = request.form.get("name")

        if room not in storage.rooms():
            flash(
                message="The room code you entered was invalid. Please try again!",
                category="error",
            )
            error_occurred = True
            error_room = ""

        if name in storage.pull(room=room).score:
            flash(
                message="The name you selected already exists. Please choose another one!",
                category="error",
            )
            error_occurred = True
            error_room = room

        elif (len(name) < 1) or (name.isspace()):
            flash(
                message="The name you entered was invalid. Please try again!",
                category="error",
            )
            error_occurred = True
            error_room = room

        if error_occurred:
            return redirect(url_for("routing.route_join", room=error_room))

        else:
            storage.pull(room=room).add_player(name)

            socketio.emit(event="add_player_to_board-s>b", data={"player": name}, room=room)

            session["name"] = name
            session["room"] = room

    elif request.method == "GET" and session is not None:
        if "/test/" in request.headers["Referer"]:
            session["name"] = request.args.get(key="name")
            session["room"] = request.args.get(key="room")

        room = session["room"]

    return render_template(
        template_name_or_list="play.html",
        session=session,
        game=storage.pull(room),
    )


@routing.route("/board/", methods=["GET", "POST"])
def route_board():
    """Displays the page used to display the board. As with `/play`, performs a small amount of error checking
    to ensure the room exists.

    Allows both GET and POST requests, though the GET request is primarily intended for use in
    testing (using the `testing.html` template).
    """
    if request.method == "POST":
        room = request.form.get("room").upper()

        if room not in storage.rooms():
            flash(
                message="The room code you entered was invalid. Please try again!",
                category="error",
            )
            return redirect(url_for("routing.route_join"))

    elif request.method == "GET":
        if "/test/" in request.headers["Referer"]:
            session["room"] = request.args.get(key="room")

        room = session["room"]

    return render_template(template_name_or_list="board.html", game=storage.pull(room=room))


@routing.route("/results/", methods=["POST", "GET"])
def route_results():
    """Displays a final results page, ranking the players from first to last. There are also a number of
    buttons to allow the host to choose to restart the game with the same, or new, players.

    Allows only POST requests.
    """
    if request.method == "POST":
        room = request.form.get("room").upper()
        player = request.form.get("name", None)
        type_ = request.form.get("type", "player")

        game = storage.pull(room=room)
        results = [[name, game.score[name]] for name in game.score.sort(reverse=True)]

        return render_template(template_name_or_list="results.html", results=results, you=player)

    elif request.method == "GET" and config.debug:
        session = "A"
        game = "B"
        results = [
            ["Alex", 1000],
            ["Brad", 500],
            ["Carl", 250],
            ["Dani", 100],
            ["Erik", 50],
        ]
        return render_template(template_name_or_list="results.html", results=results, you="Alex")

    else:
        return redirect(url_for("routing.route_index"))


# @routing.route("/test/", methods=["GET"])
# def route_test():
#     """Displays a (rather convoluted) testing page with a number of iframes to show each user
#     type. The test sets the `config.debug` variable to true, because it is assumed to be so,
#     and creates a game (to facilitate loading each of the sub pages as GET requests).

#     Only allows GET requests (for rather obvious reasons)
#     """

#     config.debug = True

#     game_settings: dict = {"room": generate_room_code(), "size": int(request.form.get("size", 6))}

#     game = alex.Game(game_settings=game_settings)
#     game.make_board()

#     game.add_player("Alex")
#     game.add_player("Brad")
#     game.add_player("Carl")

#     storage.push(room=game_settings["room"], value=game)

#     return render_template(template_name_or_list="testing.html", room=game_settings["room"])


@routing.errorhandler(500)
def internal_server_error(error):
    """Directs Flask to load the error handling page on HTTP Status Code 500 (Server Errors)"""
    return render_template(template_name_or_list="errors.html", error_code=error), 500


@socketio.on("join")
def on_join(data):
    """Connects the player to the specific room associated with the game"""

    join_room(room=data["room"])


def generate_room_code() -> str:
    if config.debug:
        return "ABCD"

    else:
        letters = "".join(random.sample(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), 4))
        while letters in storage.rooms():
            return generate_room_code()

        return letters
