from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO

import random
import alex

COPYRIGHT_NAME = u'Jeopardy'
CURRENCY = u'¢'

app = Flask(__name__)
app.jinja_env.globals.update(copyright_protection = COPYRIGHT_NAME)
app.jinja_env.globals.update(currency = CURRENCY)

app.config[u'SECRET_KEY'] = u'secret!'
app.debug = True
socketio = SocketIO(app)

LIVE_GAME_CONTAINER = dict()

DATABASE = u'data/database.db'

@app.route(u'/')
def index_page():
	return render_template(template_name_or_list = u'index.html')


@app.route(u'/new')
def new_game():
	return render_template(template_name_or_list = u'new.html')

@app.route(u'/join')
def join_game():
	return render_template(template_name_or_list = u'join.html')


@app.route(u'/game', methods = [u'POST'])
def play_game():
	if request.form.get(u'host'):
		room = generate_room_code()
		room = 'ABCD' ##########################################################################
		LIVE_GAME_CONTAINER[room] = alex.Game(
			database_name = DATABASE,
			players = int(request.form.get(u'players')),
			size = int(request.form.get(u'categories')),
			copyright = COPYRIGHT_NAME)

		LIVE_GAME_CONTAINER[room].make_board()

		return render_template(template_name_or_list = u'game.html', group = u'host', room = room)

	elif request.form.get(u'player'):
		room = request.form.get(u'room')
		print(u'Adding player to room {room}'.format(room = room))
		print(LIVE_GAME_CONTAINER[room].score)
		LIVE_GAME_CONTAINER[room].add_player(request.form.get(u'name'))
		print(LIVE_GAME_CONTAINER[room].score)

		return redirect(url_for(u'show_player'))

@app.route(u'/play', methods = [u'POST'])
def show_player():
	room = request.form.get(u'room')

	print(room)
	print(LIVE_GAME_CONTAINER[room].score)

	return render_template(
		template_name_or_list = u'play.html',
		room = room,
		score = u'10',
		game = LIVE_GAME_CONTAINER[room])

@app.route(u'/board', methods = [u'POST'])
def show_board():
	room = request.form.get(u'room')
	return render_template(
		template_name_or_list = u'board.html',
		room = room,
		game = LIVE_GAME_CONTAINER[room])


def generate_room_code():
    letters = u''.join(random.sample(list(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 4))
    while letters in LIVE_GAME_CONTAINER.keys():
        return generate_room_code()

    return letters

if __name__ == u'__main__':
	socketio.run(app, host=u'0.0.0.0')