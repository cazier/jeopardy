# jeopardy

A complete playable Jeopardy! clone for online, quarantine-safe, fun!

## Features
- Jeopardy!
- Multiplayer
- Great for quarantines!

## Usage
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
python jeopardy/app.py
```

Alternatively, you can run it using Docker pretty easily too! This is how I run it in "production". Make sure to forward port 5000 from the container as needed!

```
docker run -p 8080:5000 -it cazier/jeopardy:latest
```
