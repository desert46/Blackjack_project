'''Project Start 18/03/2025'''
from flask import Flask, render_template, request, flash, session, redirect
from flask_session import Session
import sqlite3
DATABASE = "blackjack.db"

# flask_session stuff
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = 'LETS GO GAMBLING!!! AW DANG IT!!'
Session(app)


# logged_in variable will be injected into every route
@app.context_processor
def inject_logged_in():
    '''This function injects the logged_in variable into every route'''
    return dict(logged_in=session.get("logged_in"))


@app.route('/')  # link with and without the /home will lead home
@app.route('/home')
def home():
    '''This route is for the home page, which is accessible when not logged in.'''
    if session.get("logged_in"):
        return redirect('/dashboard')
    return render_template("home.html",
                           title="Home",)


@app.route('/dashboard')
def dashboard():
    '''This route is for the dashboard page, which is only accessible if the user is logged in.'''
    if session.get("logged_in"):
        login_msg = "You are logged in as"
        user_id = session.get("user_id")
        username = session.get("username")
        print(username)
        return render_template("dashboard.html",
                               title="Dashboard",
                               user_id=user_id,
                               username=username,
                               login_msg=login_msg)
    else:
        return render_template("not_logged_in.html",
                               title="Dashboard",)


@app.route('/play')
def play():
    '''This route is for the play page, which is only accessible if the user is logged in.'''
    if session.get("logged_in"):
        return render_template("play.html")
    else:
        return render_template("not_logged_in.html",
                               title="Play")


@app.route('/stats', methods=['POST', 'GET'])
def stats():
    '''This route is for the stats page, which allows users to search for player stats by ID.'''
    if request.method == 'POST':
        searched_id = request.form['searched_id']
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        # finding duplicate usernames
        sql = "SELECT * FROM Player WHERE id = ?"
        cursor.execute(sql, (searched_id,))
        stats_data = cursor.fetchone()
        if stats_data is None:
            flash("No Player found with this ID")
        sql = '''SELECT name, description, image FROM Award WHERE id IN(
        SELECT aid FROM PlayerAward WHERE pid=?'''
        db.close()
        return render_template("stats.html", title="Stats",
                               searched_id=searched_id,
                               stats_data=stats_data,)
    return render_template("stats.html", title="Stats")


@app.route('/about')
def about():
    '''This route is for the about page, which provides information about the project.'''
    return render_template("about.html",
                           title="About")


@app.route('/login', methods=['POST', 'GET'])
def login():
    '''This route is for the login page, which allows users to log in to their accounts.'''
    if session.get("logged_in"):
        return redirect("/dashboard")
    username = request.form.get('username')
    password = request.form.get('password')
    if username is not None:
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        sql = "SELECT id, password FROM Player WHERE username = ?"
        cursor.execute(sql, (username,))
        results = cursor.fetchone()
        db.close()
        if results is None:
            flash("Your Username or Password is incorrect")
            return render_template("login.html",
                                   title="Login")
        # gets password from the results and compares them
        if password == results[1]:
            # gets user_id if passwords match
            session['logged_in'] = True
            session['user_id'] = results[0]
            session['username'] = username
            session['password'] = results[1]
            return render_template("dashboard.html", title="Dashboard")
        else:
            flash("Your Username or Password is incorrect")
            return render_template("login.html",
                                   title="Login")
    return render_template("login.html",
                           title="Login")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    '''This route is for the signup page, which allows users to create a new account.'''
    # if user is logged in, redirect to dashboard
    if session.get("logged_in"):
        return redirect("/dashboard")
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Checking the legnth is valid
        if len(username) < 4 or len(username) > 15:
            flash("Your username must be between 5~15 characters")
            return render_template("signup.html", title="Sign up")
        if len(password) < 6 or len(password) > 15:
            flash("Your password must be between 6~15 characters")
            return render_template("signup.html", title="Sign up")
        elif password.isalpha():
            print(password.isalpha())
            flash("Your password must have a number or special character")
            return render_template("signup.html", title="Sign up")
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        # finding duplicate usernames
        sql = "SELECT * FROM Player WHERE username = ?"
        cursor.execute(sql, (username,))
        existing_user = cursor.fetchone()
        if existing_user:  # checking for duplicate usernames
            db.close()
            flash('This username is already taken, try again')
            return render_template("signup.html", title="Sign Up")
        sql = '''
        INSERT INTO Player (username, password)
        VALUES (?, ?)'''  # sql query to create an account
        cursor.execute(sql, (username, password))
        db.commit()  # commits so data is saved
        db.close()
        flash("You succesfully created an account, login again to play Blackjack")
        return render_template("login.html",
                               title="Login")
    return render_template("signup.html",
                           title="Sign Up")


@app.route('/settings')
def settings():
    '''This route is for the settings page, which allows users to change their account settings.'''
    return render_template("settings.html",
                           title="Settings")


@app.route('/log_out')
def logout():
    '''This route is for logging out the user, clearing the session data.'''
    session.clear()
    return render_template("log_out.html",
                           title="Logged Out")


if __name__ == "__main__":
    app.run(debug=True)  # make this turned to off when you submit
