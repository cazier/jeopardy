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

import alex
import config
import storage

from sockets import socketio

routing = Blueprint(name="routing", import_name=__name__)


@routing.route("/", methods=["GET"])
def route_index():
    """Display the home (index) page, with two buttons to start or join a game
    
    Only allows GET requests.
    """
    return render_template(template_name_or_list="index.html")


@routing.route("/new", methods=["GET"])
def route_new():
    """Display the option(s) available to start a new game. As of now, this only supports selecting the
    number of categories with which to play. Conceivably "infinte" number of players can join.
    
    Only allows GET requests.
    """
    return render_template(template_name_or_list="new.html")


@routing.route("/join", methods=["GET"])
def route_join():
    """Display the page to join a game. This does include some error handling, but largely is messy...
    
    - Players will enter their name, and the room code created by the host. No two players can have the same name
    - The "Board" will just enter a room code.
    - If the host gets disconnected, they can rejoin here too.
    
    Only allows GET requests.
    """
    return render_template(
        template_name_or_list="join.html", errors=get_flashed_messages()
    )


@routing.route("/host", methods=["GET", "POST"])
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
            if room not in storage.rooms():
                flash(
                    message="The room code you entered was invalid. Please try again!",
                    category="error",
                )
                return redirect(url_for("routing.route_join"))

        # If the method has a number of categories supplied, the host is starting a
        # `/new` game.
        elif (category := request.form.get("categories")) :
            room = generate_room_code()

            storage.push(
                room=room, value=alex.Game(room=room, size=int(category)),
            )

            storage.pull(room=room).make_board()

            session["name"] = "Host"
            session["room"] = room

        else:
            abort(500)

    elif request.method == "GET":
        if (room := request.args.get(key="room", default=False)) :
            if config.debug:
                session["name"] = "Host"
                session["room"] = room

            if room not in storage.rooms():
                flash(
                    message="The room code you entered was invalid. Please try again!",
                    category="error",
                )
                return redirect(url_for("routing.route_join"))

        else:
            abort(500)

        room = session["room"]

    return render_template(
        template_name_or_list="host.html",
        session=session,
        game=storage.pull(room=room),
    )


@routing.route("/play", methods=["GET", "POST"])
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

        if name in storage.pull(room=room).score.keys():
            flash(
                message="The name you selected already exists. Please choose another one!",
                category="error",
            )
            error_occurred = True

        elif (len(name) < 1) or (name.isspace()):
            flash(
                message="The name you entered was invalid. Please try again!",
                category="error",
            )
            error_occurred = True

        if error_occurred:
            return redirect(url_for("routing.route_join"))

        else:
            storage.pull(room=room).add_player(name)

            socketio.emit("add_player_to_board_s-b", {"room": room, "player": name})

            session["name"] = name
            session["room"] = room

    elif request.method == "GET" and session is not None:
        if config.debug:
            session["name"] = request.args.get(key="name")
            session["room"] = request.args.get(key="room")

        room = session["room"]

    return render_template(
        template_name_or_list="play.html", session=session, game=storage.pull(room),
    )


@routing.route("/board", methods=["GET", "POST"])
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
        if config.debug:
            session["room"] = request.args.get(key="room")

        room = session["room"]

    return render_template(
        template_name_or_list="board.html", game=storage.pull(room=room)
    )


@routing.route("/test", methods=["GET"])
def route_test():
    """Displays a (rather convoluted) testing page with a number of iframes to show each user
    type. The test sets the `config.debug` variable to true, because it is assumed to be so,
    and creates a game (to facilitate loading each of the sub pages as GET requests).

    Only allows GET requests (for rather obvious reasons)
    """
    room = generate_room_code()

    storage.push(
        room=room,
        value=alex.Game(
            room=room, size=int(request.form.get("categories", default=6)),
        ),
    )

    storage.pull(room=room).make_board()

    return render_template(template_name_or_list="testing.html")


@routing.errorhandler(500)
def internal_server_error(error):
    """Directs Flask to load the error handling page on HTTP Status Code 500 (Server Errors)"""
    return render_template(template_name_or_list="errors.html", error_code=error), 500


def generate_room_code() -> str:
    if config.debug:
        return "ABCD"

    else:
        letters = "".join(random.sample(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), 4))
        while letters in storage.rooms():
            return generate_room_code()

        return letters
