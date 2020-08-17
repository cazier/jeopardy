from flask import Flask, Response, request, jsonify
from flask_restful import Resource

app = Flask(__name__)
app.debug=True

api_base = '/api/v1/'

@app.route('/')
def index():
    return 'Hello, World!'

@app.route(f'{api_base}/show/<int:number>')
def get_show(number):
    return jsonify(data[])

@app.route(f'{api_base}/random/<int:number>')
def random(number):
    print(number)
    return 'Hello, World!'

if __name__ == "__main__":
    app.run()