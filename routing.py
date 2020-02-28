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

import alex
import config
import storage

routing = Blueprint(name=u"routing", import_name=__name__)


@routing.route(u"/", methods=[u"GET"])
def route_index():
    """Display the home (index) page, with two buttons to start or join a game
    
    Only allows GET requests.
    """
    return render_template(template_name_or_list=u"index.html")


@routing.route(u"/new", methods=[u"GET"])
def route_new():
    """Display the option(s) available to start a new game. As of now, this only supports selecting the
    number of categories with which to play. Conceivably "infinte" number of players can join.
    
    Only allows GET requests.
    """
    return render_template(template_name_or_list=u"new.html")


@routing.route(u"/join", methods=[u"GET"])
def route_join():
    """Display the page to join a game. This does include some error handling, but largely is messy...
    
    - Players will enter their name, and the room code created by the host. No two players can have the same name
    - The "Board" will just enter a room code.
    - If the host gets disconnected, they can rejoin here too.
    
    Only allows GET requests.
    """
    return render_template(
        template_name_or_list=u"join.html", errors=get_flashed_messages()
    )


@routing.route(u"/host", methods=[u"GET", u"POST"])
def route_host():
    """Displays the page used by the game host to manage the gameplay. It can be "accessed" either from the `/new`
    endpoint or the `/join` endpoint, and will do different things, as needed.

    Allows both GET and POST requests, though the GET request is primarily intended for use in
    testing (using the `testing.html` template).
    """
    if request.method == u"POST":
        if request.form.get(u"players") and request.form.get(u"categories"):

            room = generate_room_code()

            storage.push(
                room=room,
                value=alex.Game(
                    room=room, size=int(request.form.get(u"categories", default=6)),
                ),
            )

            storage.pull(room=room).make_board()

            session[u"name"] = u"Host"
            session[u"room"] = room

        elif request.form.get(u"room"):
            room = request.form.get(u"room")

        else:
            abort(500)

    elif request.method == u"GET":
        if config.debug:
            session[u"name"] = u"Host"
            session[u"room"] = request.args.get(key="room")

        room = session[u"room"]

    return render_template(
        template_name_or_list=u"host.html",
        session=session,
        game=storage.pull(room=room),
    )


@routing.route(u"/play", methods=[u"GET", u"POST"])
def route_player():
    """Displays the page used by the players to "compete". The page will initially run a number of checks
    to verify that the room code was valid, or that the name entered can be done. If anything is invalid,
    reroute back to `/join` and display the messages.

    Allows both GET and POST requests.
    """
    if request.method == u"POST":
        error_occurred = False

        room = request.form.get(u"room").upper()
        name = request.form.get(u"name")

        if room not in storage.rooms():
            flash(
                message=u"The room code you entered was invalid. Please try again!",
                category=u"error",
            )
            error_occurred = True

        if name in storage.pull(room=room).score.keys():
            flash(
                message=u"The name you selected already exists. Please choose another one!",
                category=u"error",
            )
            error_occurred = True

        elif (len(name) < 1) or (name.isspace()):
            flash(
                message=u"The name you entered was invalid. Please try again!",
                category=u"error",
            )
            error_occurred = True

        if error_occurred:
            return redirect(url_for(u"route_join"))

        else:
            storage.pull(room=room).add_player(name)

            socketio.emit(u"add_player_to_board", {u"room": room, u"player": name})

            session[u"name"] = name
            session[u"room"] = room

    elif request.method == u"GET" and session is not None:
        if config.debug:
            session[u"name"] = request.args.get(key="name")
            session[u"room"] = request.args.get(key="room")

        room = session[u"room"]

    return render_template(
        template_name_or_list=u"play.html", session=session, game=storage.pull(room),
    )


@routing.route(u"/board", methods=[u"GET", u"POST"])
def route_board():
    """Displays the page used to display the board. As with `/play`, performs a small amount of error checking
    to ensure the room exists.

    Allows both GET and POST requests, though the GET request is primarily intended for use in
    testing (using the `testing.html` template).
    """
    if request.method == u"POST":
        room = request.form.get(u"room").upper()

        if room not in storage.rooms():
            flash(
                message=u"The room code you entered was invalid. Please try again!",
                category=u"error",
            )
            return redirect(url_for(u"route_join"))

    elif request.method == u"GET":
        if config.debug:
            session[u"room"] = request.args.get(key="room")

        room = session[u"room"]

    return render_template(
        template_name_or_list=u"board.html", game=storage.pull(room=room)
    )


@routing.route(u"/test", methods=[u"GET"])
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
            room=room, size=int(request.form.get(u"categories", default=6)),
        ),
    )

    storage.pull(room=room).make_board()

    return render_template(template_name_or_list=u"testing.html")


@routing.errorhandler(500)
def internal_server_error(error):
    """Directs Flask to load the error handling page on HTTP Status Code 500 (Server Errors)"""
    return render_template(template_name_or_list=u"errors.html", error_code=error), 500

