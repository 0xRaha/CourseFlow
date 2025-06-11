from flask import Flask
from .models import *

app = Flask(__name__)

app.run(debug=True)