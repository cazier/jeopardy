# jeopardy_data

A collection of tools to work with Jeopardy! data.

## Features
- An API for the companion project [here](https://github.com/cazier/jeopardy)
- A scraper to download more game information from the [J-Archive](http://www.j-archive.com/). Please see below for some details!

## Usage
### Requirements
- Python3.8+ (Uses the assignment operator `:=`)
- Flask, Flask-RESTful, Flask-SQLAlchemy, Flask-Marshmallow (API)
- Requests, BeautifulSoup4, and pyjsparser (Scraper)

### Deployment
Run in a "development" environment super easily!

```
# Clone the files
git clone https://github.com/cazier/jeopardy_data

# Enter the directory
cd jeopardy_data

# Install requirements
python -m pip install -r requirements.txt

# (Optional) Set debug flag to see requests and details
export DEBUG_APP=1

# Run!
python jeopardy_data/core.py
```

Alternatively, you can run it using Docker pretty easily too! This is how I run it in "production". Make sure to forward port 5000 from the container as needed!

```
docker run -p 5001:5000 -it cazier/jeopardy_data:latest
```
