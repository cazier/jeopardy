# jeopardy
[![codecov](https://codecov.io/gh/cazier/jeopardy/branch/master/graph/badge.svg?token=YA25NBGZMX)](https://codecov.io/gh/cazier/jeopardy)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![CI/CD](https://github.com/cazier/jeopardy/workflows/CI/CD/badge.svg)


## Features
- Jeopardy!
- Multiplayer
- API for Games, Categories, Questions, and more
- Great for quarantines!

## Usage
### Requirements (for the Game)
- Python3.8+ (Uses the assignment operator `:=`)
- Game: [Flask](https://flask.palletsprojects.com/en/1.1.x/) and [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/)
- API: [Flask-RESTful](https://flask-restful.readthedocs.io/en/latest/), [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/), [Flask-Marshmallow](https://flask-marshmallow.readthedocs.io/en/latest/) (API)
- (Optional) [Eventlet](http://eventlet.net/) (See [here](https://flask-socketio.readthedocs.io/en/latest/#requirements) for more details)


### Deployment
Run in a "development" environment super easily!

```bash
# Clone the files
git clone https://github.com/cazier/jeopardy

# Enter the directory
cd jeopardy

# Install requirements
python -m pip install -r requirements.txt

# Run!
python jeopardy/web.py
```
Note, per the [Flask-SocketIO documentation](https://flask-socketio.readthedocs.io/en/latest/#embedded-server), if using either eventlet or gevent web servers, running that above command is enough for a production environment. If that's not the case, see the documentation for other deployment methods

There's also a Docker image you can use too! Just make sure to forward the port, as needed, and make sure that you're providing a database file, via a bind mount, if you want to use more than the sample.

```docker
docker run -p 5000:5000 --env DB_FILE=questions.db -v ${PWD}/questions.db:/home/jeopardy/app/questions.db --env APP_URL=https://<your_domain_here> -it -d cazier/jeopardy:latest
```

## API
The backbone of all the data that makes this game work is on an API. There are currently no API docs. (It's a work in progress...), but the endpoints can be found in [`routes.py`](jeopardy/api/routes.py), and you may be able to work out what they do from their. Docs are forthcoming!

## J-Archive
Without this website, this project wouldn't have happened. I couldn't find any terms of use or service that prohibited programmatic scraping of their content.

## Jeopardy!
Obviously the idea of Jeopardy!, the trivia data, all of that is property of Jeopardy!, and I claim no ownership of it. It's all theirs.
