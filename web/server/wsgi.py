"""Tail demo server"""

from flask import Flask, send_from_directory

app = Flask(__name__, static_url_path='')

@app.route('/')
@app.route('/map')
@app.route('/list')
def index():
    return send_from_directory(app.static_folder, 'index.html')
