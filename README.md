# jeopardy

A complete playable Jeopardy! clone for online, quarantine-safe, fun!

## Features
- Jeopardy!
- Multiplayer
- API for Games, Categories, Questions, and more
- Great for quarantines!

## Usage
### Requirements (for the Game)
- Python3.8+ (Uses the assignment operator `:=`)
- Game: [Flask](https://flask.palletsprojects.com/en/1.1.x/) and [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/
- API: [Flask-RESTful](https://flask-restful.readthedocs.io/en/latest/), [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/2.x/), [Flask-Marshmallow](https://flask-marshmallow.readthedocs.io/en/latest/) (API)
- (Optional) Eventlet (See [here](https://flask-socketio.readthedocs.io/en/latest/#requirements) for more details)


### Deployment
Run in a "development" environment super easily!

```bash
# Clone the files
git clone https://github.com/cazier/jeopardy

# Enter the directory
cd jeopardy

# Install requirements
python -m pip install -r requirements.txt

# (Optional) Set debug flag to see requests and details
export DEBUG_APP=1

# Run!
python jeopardy/web.py
```

Alternatively, you can run it using Docker pretty easily too! This is how I run it in "production". Make sure to forward port 5000 from the container as needed!

```
docker run -p 8080:5000 -it cazier/jeopardy:latest
```

## J-Archive
Without this website, this project wouldn't have happened. I couldn't find any terms of use or service that prohibited programmatic scraping of their content. However, their [robots.txt](http://j-archive.com/robots.txt) does ask that crawlers delay 20s between requests. That delay is set in [the code](jeopardy_data/tools/scrape.py#L21). Please be nice to websites when scraping, and don't overload their servers.