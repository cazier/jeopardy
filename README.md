# jeopardy

A complete playable Jeopardy! clone for online, quarantine-safe, fun!

## Features
- Jeopardy!
- Multiplayer
- Great for quarantines!

## Usage
### Requirements
- Python3.8+ (Uses the assignment operator `:=`)
- Flask and Flask-SocketIO
- (Optional) Eventlet (See [here](https://flask-socketio.readthedocs.io/en/latest/#requirements) for more details)

> HEADS UP!
> This version of jeopardy (currently) requires the companion project [jeopardy_data](https://www.github.com/cazier/jeopardy_data) running in order to create games.

### Deployment
Run in a "development" environment super easily!

```
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
