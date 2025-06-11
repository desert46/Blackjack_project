'''Project Start 18/03/2025'''
from flask import Flask, render_template, request, flash, session
from flask_session import Session
import hashlib
import sqlite3
DATABASE = "blackjack.db"


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = 'your_secret_key'
Session(app)


@app.route('/')  # link with and without the /home will lead home
@app.route('/home')
def home():
    return render_template("home.html", title="Home")


@app.route('/play')
def play():
    return render_template("play.html", title="Play")


@app.route('/stats', methods=['POST', 'GET'])
def stats():
    if session.get("logged_in"):
        user_id = session.get("user_id")
        username = session.get("username")
        password = session.get("password")
        flash("You are logged in")
        return render_template("stats.html", title="Stats", user_id=user_id, username=username, password=password)
    else:
        flash("You are not logged in")
        return render_template("stats.html", title="Stats")


@app.route('/about')
def about():
    return render_template("about.html", title="About")


@app.route('/login', methods=['POST', 'GET'])
def login():
    username = request.args.get('username')
    password = request.args.get('password')
    if username is not None:
        print(username)
        print(password)
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        sql = "SELECT id, password FROM Player WHERE username = ?"
        cursor.execute(sql, (username,))
        results = cursor.fetchone()
        if password == results[1]:  # gets password from the results and compares them
            # gets id if passwords match
            session['logged_in'] = True
            session['user_id'] = results[0]
            session['username'] = username
            session['password'] = results[1]
            flash('You were successfully logged in')
            print("valid")
            return render_template("play.html", title="Play")
        else:
            flash("invalid")
            return render_template("login.html", title="Login")
    return render_template("login.html", title="Login")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        # finding duplicate usernames
        sql = "SELECT * FROM Player WHERE username = ?"
        cursor.execute(sql, (username,))
        existing_user = cursor.fetchone()
        if existing_user:  # checking for duplictae usernames
            db.close()
            flash('This username is already taken, try again')
            return render_template("signup.html", title="Sign Up")
        sql = f'''
        INSERT INTO Player (username, password)
        VALUES (?, ?)
        '''  # sql query to create an account
        cursor.execute(sql, (username, password))
        db.commit()  # commits so data is saved
        db.close()
        return render_template("signup.html", title="Sign Up")
    return render_template("signup.html", title="Sign Up")


@app.route('/settings')
def settings():
    return render_template("settings.html", title="Settings")


if __name__ == "__main__":
    app.run(debug=True)  # make this turned to off when you submit
