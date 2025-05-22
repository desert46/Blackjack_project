'''Project Start 18/03/2025'''
from flask import Flask, render_template, request
import hashlib
import sqlite3
DATABASE = "blackjack.db"


app = Flask(__name__)

@app.route('/')  # link with and without the /home will lead home
@app.route('/home')
def home():
    return render_template("home.html", title="Home")


@app.route('/play')
def play():
    return render_template("play.html", title="Play")


@app.route('/stats')
def stats():
    return render_template("stats.html", title="Stats")


@app.route('/about')
def about():
    return render_template("about.html", title="About")


@app.route('/login')
def login():
    return render_template("login.html", title="Login")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        sql = f'''
        INSERT INTO player (username, password, xp, level, award_count, 
        hands_played, wins, losses, pushes, money_wins, money_losses, hits, 
        busts, stands, dealer_higher, dealer_busts, player_higher)
        VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        ''' # sql query to create an account
        cursor.execute(sql, (username, password))
        db.commit()   # commits so data is saved
        db.close()
        return render_template("signup.html", title="Sign Up")
    return render_template("signup.html", title="Sign Up")
    

@app.route('/settings')
def settings():
    return render_template("settings.html", title="Settings")


if __name__ == "__main__":
    app.run(debug=True)  # make this turned to off when you submit
