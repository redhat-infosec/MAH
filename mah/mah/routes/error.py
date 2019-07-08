from mah import app
from flask import render_template

@app.unauthenticated_route('/')
def index():
    return render_template('configerror.html')
