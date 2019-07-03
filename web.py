from flask import Flask, render_template, request, session, redirect, url_for, abort, flash, get_flashed_messages
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


@app.route(u'/new', methods = [u'GET'])
def new_game():
	return render_template(template_name_or_list = u'new.html')

@app.route(u'/join', methods = [u'GET'])
def join_game():
	return render_template(template_name_or_list = u'join.html', errors = get_flashed_messages())


@app.route(u'/host', methods = [u'POST'])
def show_host():
	if request.form.get(u'players') and request.form.get(u'categories'):
		room = generate_room_code()
		room = 'ABCD' ##########################################################################
		LIVE_GAME_CONTAINER[room] = alex.Game(
			database_name = DATABASE, copyright = COPYRIGHT_NAME, room = room,
			players = int(request.form.get(u'players')),
			size = int(request.form.get(u'categories')))

		LIVE_GAME_CONTAINER[room].make_board()

	elif request.form.get(u'room'):
		room = request.form.get(u'room')

	else:
		abort(500)

	return render_template(
		template_name_or_list = u'host.html', 
		game = LIVE_GAME_CONTAINER[room])


@app.route(u'/play', methods = [u'GET', u'POST'])
def show_player():
	print(session)
	if request.method == u'POST':
		error_occurred = False

		room = request.form.get(u'room').upper()
		name = request.form.get(u'name')

		if room not in LIVE_GAME_CONTAINER.keys():
			flash(message = u'The room code you entered was invalid. Please try again!', category = u'error')
			error_occurred = True

		elif name in LIVE_GAME_CONTAINER[room].score.keys():
			flash(message = u'The name you selected already exists. Please choose another one!', category = u'error')
			error_occurred = True

		if (len(name) < 1) or (name.isspace()):
			flash(message = u'The name you entered was invalid. Please try again!', category = u'error')
			error_occurred = True

		if error_occurred:
			return redirect(url_for(u'join_game'))

		else:
			LIVE_GAME_CONTAINER[room].add_player(name)
			session[u'name'] = name
			session[u'room'] = room

	elif request.method == u'GET' and session is not None:
		room = session[u'room']

	return render_template(
		template_name_or_list = u'play.html',
		score = u'10', session = session,
		game = LIVE_GAME_CONTAINER[room])

@app.route(u'/board', methods = [u'POST'])
def show_board():
	room = request.form.get(u'room').upper()

	if room not in LIVE_GAME_CONTAINER.keys():
		flash(message = u'The room code you entered was invalid. Please try again!', category = u'error')
		return redirect(url_for(u'join_game'))


	return render_template(
		template_name_or_list = u'board.html',
		game = LIVE_GAME_CONTAINER[room])

@app.route(u'/score/<string:user>/<int:incrementer>')
def add_score(user, incrementer):
	LIVE_GAME_CONTAINER[u'ABCD'].score[user] += incrementer
	print(LIVE_GAME_CONTAINER[u'ABCD'].score)
	return u'Added {incrementer} to user {user}'.format(incrementer = incrementer, user = user)

@app.errorhandler(500)
def internal_server_error(error):
	return render_template(template_name_or_list = u'errors.html', error_code = error), 500

@socketio.on(u'question_clicked')
def reveal_host_clue(data):
	info = LIVE_GAME_CONTAINER[data[u'room']].get(data[u'identifier'])

	socketio.emit(u'question_revealed', {
		u'room': data[u'room'],
		u'identifier': data[u'identifier'],

		u'question': info[u'question'],
		u'answer': info[u'answer']
		})

@socketio.on(u'finished_reading')
def host_finished_reading(data):
	socketio.emit(u'host_finished_reading', {
		u'room': data[u'room']
		})

	LIVE_GAME_CONTAINER[data[u'room']].buzzers = list()

@socketio.on(u'buzzed_in')
def player_buzzed_in(data):
	LIVE_GAME_CONTAINER[data[u'room']].buzz(data[u'name'])

	socketio.emit(u'player_buzzed', {
		u'room': data[u'room'], 
		u'player': LIVE_GAME_CONTAINER[data[u'room']].buzzers[0]
		})


def generate_room_code():
    letters = u''.join(random.sample(list(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 4))
    while letters in LIVE_GAME_CONTAINER.keys():
        return generate_room_code()

    return letters

if __name__ == u'__main__':
	socketio.run(app, host=u'0.0.0.0')