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
    elif session.get('active_hand'):
        flash("You need to finish your current hand before you can access the dashboard")
        return redirect('/play')
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
    card_values = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 10, 'Q': 10, 'K': 10, 'A': 11
    }
    return card_values


# defining functions for game end


def winnings(multiplier):
    '''SQL query to add winnings after a player wins a hand'''
    session['money'] += session['bet']*multiplier
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    sql = '''UPDATE Player SET money = ? WHERE id = ?'''
    cursor.execute(sql, (session['money'], session['user_id']))
    db.commit()
    db.close()


@app.route('/bet', methods=['POST', 'GET'])
def bet():
    '''The betting page before he game starts'''
    if not session.get('logged_in'):
        return render_template("not_logged_in.html")
    if session.get('active_hand'):
        flash("You need to finish your current hand before you can access the dashboard")
        return redirect('/play')

    # initialising variables
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
        (session['player_hand'],
         session['dealers_hidden_hand'],
         session['dealers_shown_hand'],
         session['player_hand_values'],
         session['dealer_hand_values'],
         session['natural']) = hand_start(session['bet'],
                                          session['shoe'],
                                          session['card_values'])

        return redirect('/play')

    return render_template("bet.html",
                           title="Play",
                           show_footer=False,
                           money=session['money'])


@app.route('/play')
def play():
    '''The actual game'''
    if not session.get('logged_in'):
        return render_template("not_logged_in.html")

    if session.get('active_hand'):

        if session.get('natural'):
            session['active_hand'] = False
            flash('Natural')
            return render_template("play.html",
                                   title="Play",
                                   show_footer=False,
                                    active_hand=False,
                                    dealers_hand=session['dealers_hidden_hand'],
                                    player_hand=session['player_hand'],
                                    player_hand_values=sum(session['player_hand_values']))
        else:
            return render_template("play.html",
                                title="Play",
                                show_footer=False,
                                active_hand=session['active_hand'],
                                dealers_hand=session['dealers_shown_hand'],
                                player_hand=session['player_hand'],
                                player_hand_values=sum(session['player_hand_values']))
    else:
        flash('Make a bet to play')
        return redirect('bet')


def hand_start(bet, shoe, card_values):
    '''Starts the game by dealing two cards to the player and dealer.'''
    natural = False
    player_hand = []
    dealers_hidden_hand = []
    dealers_shown_hand = []
    player_hand_values = []
    dealer_hand_values = []
    # Deal two cards to the player and dealer
    for i in range(2):
        player_hand.append(shoe[0])
        shoe.pop(0)
        dealers_hidden_hand.append(shoe[0])
        dealers_shown_hand.append(shoe[0])
        shoe.pop(0)
    dealers_shown_hand[0] = "Xx"  # hide one of the dealer's cards
    # calculate the initial hand values for the two cards dealt
    for card in player_hand:
        # card[0] takes the rank of the card
        player_hand_values.append(card_values[card[0]])
    for card in dealers_hidden_hand:
        dealer_hand_values.append(card_values[card[0]])
    # Pocket aces scenario
    # Sets one of the aces to 1
    if player_hand_values == [11, 11]:
        player_hand_values = [1, 11]
    if dealer_hand_values == [11, 11]:
        dealer_hand_values = [1, 11]
    # checking for naturals
    if sum(player_hand_values) == 21:
        natural = True
        if sum(dealer_hand_values) == 21:
            # dealer hits a natural
            flash("Both you and the dealer hit a natural")
            flash("You get your bet back.")
            winnings(1)
        else:
            #  you hit a natural but the dealer didn't
            flash("You hit a natural!")
            flash(f"You won ${bet * 2.5}!")
            winnings(2.5)

    elif sum(dealer_hand_values) == 21:
        # both players hit a natural
        natural = True
        flash("Dealer hit a natural!")
        flash(f"You lost your bet of ${bet}.")

    return player_hand, dealers_hidden_hand, dealers_shown_hand, player_hand_values, dealer_hand_values, natural


@app.route('/hit')
def hit():
    '''Player chooses to hit in Blackjack'''
    if not session['active_hand']:
        return redirect('play')
    session['can_double_down'] = False
    session['player_hand'].append(session['shoe'][0])
    session['shoe'].pop(0)
    (session['player_hand_values'],
     session['player_hand']) = calculate_hand_value(session['card_values'],
                                         hand=session['player_hand'],
                                         hand_values=session['player_hand_values'])
    flash(f"You drew: {session['player_hand'][-1]}")
    flash(f"Your Hand: {session['player_hand']}")
    flash(f"Your Hand Value: {sum(session['player_hand_values'])}")
    if sum(session['player_hand_values']) > 21:
        flash("You busted")
        flash(f"You lost your bet of ${session['bet']}")
        return hand_end_template()
    return redirect('/play')


@app.route('/stand')
def stand():
    flash("You chose to stand.")
    flash(f"Dealer's Hand was: {session['dealers_hidden_hand']}")
    while sum(session['dealer_hand_values']) < 17:
        session['dealers_hidden_hand'].append(session['shoe'][0])
        session['shoe'].pop(0)
        (session['dealer_hand_values'],
         session['dealers_hidden_hand']) = calculate_hand_value(session['card_values'],
                                                                hand=session['dealers_hidden_hand'],
                                                                hand_values=session['dealer_hand_values'])
        flash(f"Dealer drew: {session['dealers_hidden_hand'][-1]}")
    flash(f"Dealer's Hand: {session['dealers_hidden_hand']}")
    flash(f"Dealer's Hand Value: {sum(session['dealer_hand_values'])}")
    if sum(session['dealer_hand_values']) > 21:
        flash("Dealer went bust. ")
        flash(f"You won ${session['bet'] * 2}!")
        winnings(2)
        return hand_end_template()
    elif sum(session['dealer_hand_values']) > sum(session['player_hand_values']):
        flash("Dealer's hand was higher than yours")
        flash(f"You lost your bet of ${session['bet']}")
        return hand_end_template()
    elif sum(session['dealer_hand_values']) < sum(session['player_hand_values']):
        flash("Your hand was higher than the dealers")
        flash(f"You won ${session['bet'] * 2}!")
        winnings(2)
        return hand_end_template()
    elif sum(session['dealer_hand_values']) == sum(session['player_hand_values']):
        flash("It's a push!")
        flash(f"You get your bet of ${session['bet']} back.")
        winnings(1)
        return hand_end_template()


def end_hand():
    session.pop('active_hand', False)
    session.pop('bet', None)
    session.pop('player_hand', None)
    session.pop('player_hand_values', None)
    session.pop('dealers_shown_hand', None)
    session.pop('dealers_hidden_hand', None)
    session.pop('dealer_hand_value', None)
    session.pop('natural', None)


def hand_end_template():
    session['active_hand'] = False
    return render_template("play.html",
                                title="Play",
                                show_footer=False,
                                active_hand=session['active_hand'],
                                dealers_hand=session['dealers_hidden_hand'],
                                player_hand=session['player_hand'],
                                player_hand_values=sum(session['player_hand_values']))






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
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand before you can access the dashboard")
            return redirect('/play')
    return render_template("about.html",
                           title="About")


@app.route('/login', methods=['POST', 'GET'])
def login():
    '''This route is for the login page, which allows users to log in to their accounts.'''
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand before you can access the dashboard")
            return redirect('/play')
        else:
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
            session['shoe'] = new_deck()  # new shoe upon new session
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
        if session.get('active_hand'):
            flash("You need to finish your current hand before you can access the dashboard")
            return redirect('/play')
        else:
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
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand before you can access the dashboard")
            return redirect('/play')
        else:
            return redirect("/dashboard")
    elif not session.get("logged_in"):
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
