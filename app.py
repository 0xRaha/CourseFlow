from flask import Flask, render_template
from .models import Database
from .utils import *

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


app.run(debug=True)