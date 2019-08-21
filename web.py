from flask import Flask, render_template, request, session, redirect, url_for, abort, flash, get_flashed_messages
from flask_socketio import SocketIO, join_room

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

            socketio.emit(u'add_player_to_board', {
                u'room': room,
                u'player': name
                })

            session[u'name'] = name
            session[u'room'] = room

    elif request.method == u'GET' and session is not None:
        room = 'ABCD'#session[u'room']

    return render_template(
        template_name_or_list = u'play.html',
        session = session,
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

# @app.route(u'/score/<string:user>/<int:incrementer>')
# def add_score(user, incrementer):
#   LIVE_GAME_CONTAINER[u'ABCD'].score[user] += incrementer
#   print(LIVE_GAME_CONTAINER[u'ABCD'].score)
#   return u'Added {incrementer} to user {user}'.format(incrementer = incrementer, user = user)

@app.errorhandler(500)
def internal_server_error(error):
    return render_template(template_name_or_list = u'errors.html', error_code = error), 500

@socketio.on(u'question_clicked')
def reveal_host_clue(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]
    info = game.get(data[u'identifier'])

    if info[u'wager']:
        if game.round == 3:
            isDailyDouble = False
            footer_buttons = {
                u'Prompt For Wagers': u'btn btn-success',
                u'Reveal Question': u'btn btn-success disabled'
                }

        else:
            isDailyDouble = True
            footer_buttons = {
                u'Correct': u'btn btn-success disabled mr-auto',
                u'Incorrect': u'btn btn-danger disabled mr-auto',
                u'Reveal Question': u'btn btn-dark mr-auto'
                }


        socketio.emit(u'start_wager_round', {
            u'room': data[u'room'],
            u'isDailyDouble': isDailyDouble,
            u'players': list(game.score.keys()),
            u'buttons': footer_buttons
            })

        print(u'DAILY DOUBLE!!!')

    else: 
        socketio.emit(u'question_revealed', {
            u'room': data[u'room'],

            u'question': info[u'question'].replace(u'<br />', u'\n'),
            u'answer': info[u'answer']
            })

@socketio.on(u'finished_reading')
def enable_buzzers(data, incorrect_players: list = list()):
    socketio.emit(u'enable_buzzers', {
        u'room': data[u'room'],
        u'players': incorrect_players
        })


@socketio.on(u'correct_answer')
def host_correct_answer(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]
    game.score[game.buzzers[-1]] += game.standing_question.value

    socketio.emit(u'clear_modal', {
        u'room': data[u'room']
        })

    socketio.emit(u'update_scores', {
        u'room': data[u'room'],
        u'scores': game.score,
        u'final': False
        })

    end_question(data)

@socketio.on(u'incorrect_answer')
def host_incorrect_answer(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]
    game.score[game.buzzers[-1]] -= game.standing_question.value

    socketio.emit(u'update_scores', {
        u'room': data[u'room'],
        u'scores': game.score
        })

    enable_buzzers(data, incorrect_players = game.buzzers)


@socketio.on(u'buzzed_in')
def player_buzzed_in(data):
    LIVE_GAME_CONTAINER[data[u'room']].buzz(data[u'name'])

    socketio.emit(u'reset_player', {
        u'room': data[u'room'],
        u'player': None
        })

    socketio.emit(u'player_buzzed', {
        u'room': data[u'room'], 
        u'name': LIVE_GAME_CONTAINER[data[u'room']].buzzers[-1]
        })

@socketio.on(u'dismiss_modal')
def dismiss_modal(data):
    socketio.emit(u'clear_modal', {
        u'room': data[u'room']
        })

    end_question(data)

@socketio.on(u'start_next_round')
def start_next_round(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.next_round()

    socketio.emit(u'round_started')

@socketio.on(u'get_wagers')
def get_wagers(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    socketio.emit(u'start_wager_round', {
        u'room': data[u'room'],
        u'players': list(game.score.keys())
        });

@socketio.on(u'reveal_question')
def reveal_question(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    socketio.emit(u'final_question_revealed')

@socketio.on(u'wager_submitted')
def received_wager(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.wagered_round[data[u'name']] = {u'wager': data[u'wager']}

    socketio.emit('wagerer_received', {
        u'room': data[u'room'],
        u'name': data[u'name']
        })

@socketio.on(u'answer_submitted')
def received_answer(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.wagered_round[data[u'name']][u'answer'] = data[u'answer']

    socketio.emit('wagerer_received', {
        u'room': data[u'room'],
        u'name': data[u'name']
        })

@socketio.on(u'final_wagerer_reveal')
def wagerer_reveal(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]
    name = data[u'name'][:-8]

    socketio.emit('final_wager_received', {
        u'room': data[u'room'],
        u'name': name,
        u'wager': game.wagered_round[name][u'wager'],
        u'answer': game.wagered_round[name][u'answer']
        })

@socketio.on(u'reveal_answer')
def reveal_answer(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    socketio.emit(u'reveal_wager_answer', {
        u'room': data[u'room'],
        })

@socketio.on(u'correct_wager')
def correct_wager(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.score[data[u'name']] += game.wagered_round[data[u'name']][u'wager']

    game.wagered_round = dict()

    socketio.emit(u'update_scores', {
        u'room': data[u'room'],
        u'scores': game.score,
        u'final': True
        })

@socketio.on(u'incorrect_wager')
def incorrect_wager(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.score[data[u'name']] -= game.wagered_round[data[u'name']][u'wager']

    game.wagered_round = dict()

    socketio.emit(u'update_scores', {
        u'room': data[u'room'],
        u'scores': game.score,
        u'final': True
        })

@socketio.on(u'single_wager_prompt')
def single_wager_prompt(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.wagered_round[data[u'name'][:-15]] = dict()

    socketio.emit(u'single_wager_player_prompt', {
        u'room': data[u'room'],
        u'players': [data[u'name'][:-15]]
        })

@socketio.on(u'single_wager_submitted')
def received_wager(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    info = game.standing_question.get()

    if data[u'name'] in game.wagered_round.keys():

        game.wagered_round[data[u'name']] = {u'wager': data[u'wager']}

        socketio.emit(u'single_question_revealed', {
            u'room': data[u'room'],

            u'question': info[u'question'].replace(u'<br />', u'\n'),
            u'answer': info[u'answer']
            })

    else:
        pass
        ##TODO ERROR HANDLE THIS!

@socketio.on(u'player_selected')
def player_selected(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    if data[u'isDailyDouble']:
        game.wagered_round[data[u'name']] = {}

    print(u'WAGERER RECEIVED! They\'re name is:', data[u'name'])



@socketio.on(u'join')
def socket_join(data):
    join_room(data[u'room'])


def generate_room_code():
    letters = u''.join(random.sample(list(u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 4))
    while letters in LIVE_GAME_CONTAINER.keys():
        return generate_room_code()

    return letters

def end_question(data):
    game = LIVE_GAME_CONTAINER[data[u'room']]

    game.buzzers = list()
    game.standing_question = None

    print(u'=' * 40)
    print(u'ROUND ENDED', game.round)
    print(u'=' * 40)



    if game.remaining_questions <= 0 and game.round <= 3:
        socketio.emit(u'round_complete', {
            u'room': data[u'room'],
            u'current_round': LIVE_GAME_CONTAINER[data[u'room']].round_text(),
            u'next_round': LIVE_GAME_CONTAINER[data[u'room']].round_text(next_round = True)
            })

if __name__ == u'__main__':
    socketio.run(app, host=u'0.0.0.0')