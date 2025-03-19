from flask import Flask, render_template
import sqlite3


app = Flask(__name__)


@app.route('/home')
def home():
    return render_template("home.html", title="Home") 