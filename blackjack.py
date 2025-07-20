'''Project Start 18/03/2025'''
from flask import Flask, render_template, request, flash, session, redirect
from flask_session import Session
import sqlite3
import random
DATABASE = "blackjack.db"


app = Flask(__name__)
# flask_session stuff
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = 'LETS GO GAMBLING!!! AW DANG IT!!'
Session(app)


@app.context_processor
def inject_variables():
    '''This function injects these variable into every route'''
    return dict(logged_in=session.get("logged_in"),
                show_footer=True)


@app.route('/')  # link with and without the /home will lead home
@app.route('/home')
def home():
    '''This route is for the home page, which is accessible when not logged in'''
    if session.get("logged_in"):
        return redirect('/dashboard')
    return render_template("home.html",
                           title="Home",)


@app.route('/dashboard')
def dashboard():
    '''This route is for the dashboard page'''
    if not session.get("logged_in"):
        return redirect('/home')
    user_id = session.get("user_id")
    username = session.get("username")
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    # finding duplicate usernames
    sql = "SELECT * FROM Player WHERE id = ?"
    cursor.execute(sql, (user_id,))
    stats_data = cursor.fetchone()
    sql = '''SELECT name, description, image FROM Award WHERE id IN(
    SELECT aid FROM PlayerAward WHERE pid=?);'''
    cursor.execute(sql, (user_id,))
    awards = [dict(row) for row in cursor.fetchall()]
    db.close()
    return render_template("dashboard.html",
                           title="Dashboard",
                           user_id=user_id,
                           username=username,
                           stats_data=stats_data,
                           awards=awards,)


# game stuff start
# defining functions for game start
def calculate_hand_value(card_values, hand_values, hand):
    '''Calculates the total value of a hand.'''
    hand_values.append(card_values[hand[-1][0]])
    if sum(hand_values) > 21 and 11 in hand_values:
        # If the hand value is over 21 and contains an Ace, Ace becomes 1
        hand_values[hand_values.index(11)] = 1
    return hand_values, hand


def new_deck():
    # 2s represents 2 of spades, Ah represents Ace of Hearts, etc.
    cards = [
        '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s', 'Ts', 'Js', 'Qs', 'Ks', 'As',
        '2h', '3h', '4h', '5h', '6h', '7h', '8h', '9h', 'Th', 'Jh', 'Qh', 'Kh', 'Ah',
        '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d', 'Td', 'Jd', 'Qd', 'Kd', 'Ad',
        '2c', '3c', '4c', '5c', '6c', '7c', '8c', '9c', 'Tc', 'Jc', 'Qc', 'Kc', 'Ac'
    ]
    _shoe = cards*6  # forms a 6 deck blackjack shoe
    random.shuffle(_shoe)  # shuffle shoe
    return _shoe


def create_card_values():
    '''Returns a dictionary of card values for blackjack.'''
    return {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 10, 'Q': 10, 'K': 10, 'A': 11
    }
# defining functions for game end


@app.route('/bet', methods=['POST', 'GET'])
def bet():
    '''The betting page before he game starts'''
    if not session.get('logged_in'):
        return render_template("not_logged_in.html")

    # initialising variables
    session['shoe'] = new_deck()
    session['card_values'] = create_card_values()
    session['player_hand_values'] = []
    session['dealer_hand_values'] = []
    session['bet'] = 0

    # If the shoe has less than 100 cards, reshuffle
    if len(session['shoe']) < 100:
        flash("Shoe has been reshuffled!")
        session['shoe'] = new_deck()

    # form processing
    if request.method == 'POST':
        session['bet'] = request.form['bet']
        # checking if the bet amount is valid
        if session['bet'].isdecimal():
            session['bet'] = int(session['bet'])
            if session['bet'] > session['money']:
                flash(f"You only have ${session['money']}")
                return render_template("bet.html",
                                       title="Play",
                                       money=session['money'],
                                       show_footer=False)
            if session['bet'] <= 0:
                flash("Bet must be a positive amount.")
                return render_template("bet.html",
                                       title="Play",
                                       money=session['money'],
                                       show_footer=False)
            if session['bet'] < 10:
                flash("Minimum bet is $10.")
                return render_template("bet.html",
                                       title="Play",
                                       money=session['money'],
                                       show_footer=False)
        else:
            flash("Invalid input. Please enter a valid amount.")
            return render_template("bet.html",
                                   title="Play",
                                   money=session['money'],
                                   show_footer=False)

        # processing bet after a valid input is accepted
        session['money'] -= session['bet']
        db = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        sql = '''UPDATE Player SET money = ? WHERE id = ?'''
        cursor.execute(sql, (session['money'], session['user_id']))
        db.commit()
        db.close()
        session['active_hand'] = True
        return redirect('/play')

    return render_template("bet.html",
                           title="Play",
                           money=session['money'],
                           show_footer=False)


@app.route('/play')
def play():
    '''This route is for the play page, which is only accessible if the user is logged in.'''
    if not session.get("logged_in"):
        flash("Login to play Blackjack")
        return redirect("/login")
    if not session['active_hand']:
        # /play will redirect to betting to start the game
        return redirect('/bet')

    return render_template("play.html",
                           title="Play",
                           show_footer=False)


# game stuff end


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
        SELECT aid FROM PlayerAward WHERE pid=?);'''
        cursor.execute(sql, (searched_id,))
        awards = [dict(row) for row in cursor.fetchall()]
        db.close()
        return render_template("stats.html", title="Stats",
                               searched_id=searched_id,
                               stats_data=stats_data,
                               awards=awards,)
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
        sql = "SELECT id, password, money FROM Player WHERE username = ?"
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
            session['money'] = results[2]
            session['bet'] = 0
            session['active_hand'] = False
            return redirect("/dashboard")
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
        username = request.form['username'].rstrip()
        password = request.form['password'].rstrip()
        # Checking the username is valid
        if len(username) < 4 or len(username) > 15:
            flash("Your username must be between 5~15 characters")
            return render_template("signup.html", title="Sign up")
        elif username.isdigit():
            flash("Your username must have a letter")
            return render_template("signup.html", title="Sign up")
        elif ' ' in username:
            flash("Your username must not have a space")
            return render_template("signup.html", title="Sign up")
        elif "'" in username or '"' in username or ';' in username:
            flash("Invalid username, please try again")
        elif '/' in username or '\\' in username or '=' in username:
            flash("Invalid username, please try again")
        elif '<' in username or '>' in username:
            flash("Invalid username, please try again")
            return render_template("signup.html", title="Sign up")

        # Checking the password is valid
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
        db.commit()
        db.close  # account created successfully

        # awarding the player with "Diamond_Create_Account"
        user_id = cursor.lastrowid
        db = sqlite3.connect(DATABASE)
        sql = '''INSERT INTO PlayerAward (pid, aid) VALUES (?, 1)'''
        cursor.execute(sql, (user_id,))
        sql = '''UPDATE Player SET award_count = award_count + 1
        WHERE id = ?;'''
        cursor.execute(sql, (user_id,))
        db.commit()
        db.close()
        user_id = None
        flash("Succesfully created an account, login again to play Blackjack")
        return render_template("login.html",
                               title="Login")
    return render_template("signup.html",
                           title="Sign Up")


@app.route('/settings')
def settings():
    '''This route is for the settings page, which allows users to change their account settings.'''
    if not session.get("logged_in"):
        return render_template("not_logged_in.html",
                               title="Settings")
    return render_template("settings.html",
                           title="Settings")


@app.route('/log_out')
def logout():
    '''This route is for logging out the user, clearing the session data.'''
    if not session.get("logged_in"):
        return redirect('/home')
    session.clear()
    return redirect('/login')


@app.errorhandler(404)
def page_not_found(e):
    '''custom 404 page not found page'''
    return render_template("404.html", title="Page Not Found"), 404


if __name__ == "__main__":
    app.run(debug=True)  # make this turned to off when you submit
