from flask import Flask, render_template, request
from flask_socketio import SocketIO

import random
import alex

app = Flask(__name__)
app.config[u'SECRET_KEY'] = u'secret!'
app.debug = True
socketio = SocketIO(app)

LIVE_GAME_CONTAINER = dict()

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
			database_name = u'updated_database.db',
			players = int(request.form.get(u'players')),
			size = int(request.form.get(u'categories')))

		LIVE_GAME_CONTAINER[room].make_board()

		return render_template(template_name_or_list = u'game.html', group = u'host', room = room)

	elif request.form.get(u'player'):
		room = request.form.get(u'room')
		LIVE_GAME_CONTAINER[room].add_player(request.form.get(u'name'))

		return render_template(template_name_or_list = u'game.html', group = u'player', room = room)

@app.route(u'/board', methods = [u'POST'])
def show_board():
	room = request.form.get(u'room')
	return render_template(
		template_name_or_list = u'board.html',
		room = room,
		size = LIVE_GAME_CONTAINER[room].size,
		segment = LIVE_GAME_CONTAINER[room].round,
		game = LIVE_GAME_CONTAINER[room].board)


def generate_room_code():
    letters = u''.join(random.sample(list(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 4))
    while letters in LIVE_GAME_CONTAINER.keys():
        return generate_room_code()

    return letters

if __name__ == u'__main__':
	socketio.run(app, host=u'0.0.0.0')