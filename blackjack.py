'''Project Start 18/03/2025'''
# Imports
from flask import Flask, render_template, request, flash, session, redirect
from flask_session import Session
import sqlite3
import random

# Constants
DATABASE = "blackjack.db"
# flask
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = 'LETS GO GAMBLING!!! AW DANG IT!!'
Session(app)


# Routes and functions
@app.context_processor
def inject_variables():
    '''This function injects these variable into every route'''
    return dict(logged_in=session.get("logged_in"),
                show_footer=True,
                username=session.get('username'),
                user_id=session.get('user_id'))


def awarding_player(claimed_awards, cursor, user_id, criteria, aid, stat):
    for i in range(len(criteria)):
        if stat >= criteria[i]:
            # checking if player already has the award
            has_award = any(pid.get('aid') == aid[i] for pid in claimed_awards)
            if not has_award:
                # Awarding the player with the designated award
                sql = '''UPDATE Player
                        SET award_count = award_count + 1
                        WHERE id = ?;'''
                cursor.execute(sql, (user_id,))

                sql = '''INSERT INTO PlayerAward (pid, aid)
                        VALUES (?, ?)'''
                cursor.execute(sql, (user_id, aid[i]))


@app.route('/')  # link with and without the /home will lead home
@app.route('/home')
def home():
    '''
    This route is for the home page,
    which is accessible when not logged in.
    '''
    if session.get("logged_in"):
        return redirect('/dashboard')
    return render_template("home.html",
                           title="Home",)


@app.route('/dashboard')
def dashboard():
    '''This route is for the dashboard page.'''
    # User must be logged in and not in a hand
    if not session.get("logged_in"):
        return redirect('/home')
    elif session.get('active_hand'):
        flash("Please finish your active hand")
        return redirect('/play')

    user_id = session.get("user_id")
    username = session.get("username")

    with sqlite3.connect(DATABASE) as db:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        # Fetch player stats and awards
        sql = "SELECT * FROM Player WHERE id = ?"
        cursor.execute(sql, (user_id,))
        stats_data = cursor.fetchone()
        sql = '''SELECT name, description, image FROM Award WHERE id IN(
        SELECT aid FROM PlayerAward WHERE pid=?);'''
        cursor.execute(sql, (user_id,))
        awards = [dict(row) for row in cursor.fetchall()]

        # Leveling up
        if stats_data['xp'] >= 100:  # Player levels up every 100xp
            # xp is deducted and level is increased by 1
            sql = '''UPDATE Player SET xp = xp - 100, level = level + 1
            WHERE id = ?'''
            cursor.execute(sql, (user_id,))
            db.commit()

        # Fetch awards to check if player already has a given award
        sql = '''SELECT aid FROM PlayerAward WHERE pid = ?'''
        cursor.execute(sql, (user_id,))
        # results are put in a list of dictionaries
        claimed_awards = [dict(row) for row in cursor.fetchall()]

        # Claiming awards
        # Level up awards
        awarding_player(claimed_awards=claimed_awards,
                        cursor=cursor,
                        user_id=user_id,
                        criteria=[50, 25, 10],
                        aid=[7, 6, 5],
                        stat=stats_data['level']
                        )

        # awarding money won awards
        awarding_player(claimed_awards=claimed_awards,
                        cursor=cursor,
                        user_id=user_id,
                        criteria=[1000000, 500000, 100000],
                        aid=[4, 3, 2],
                        stat=stats_data['money_wins']
                        )

    # Calculating ratios for some stats
    # Win/loss ratio calculations
    if stats_data['wins']+stats_data['losses'] == 0:
        # Preventing division by zero
        hands_win_loss_ratio = 0
    else:
        hands_win_loss_ratio = stats_data['wins']/(stats_data['wins']+stats_data['losses'])
    # Money/loss ratio calculations
    if stats_data['money_wins'] == 0:
        # Preventing division by zero
        money_loss_ratio = 0
    else:
        money_loss_ratio = stats_data['money_wins']/stats_data['money_losses']

    db.commit()
    return render_template(
        "dashboard.html",
        title="Dashboard",
        user_id=user_id,
        username=username,
        stats_data=stats_data,
        awards=awards,
        hands_win_loss_ratio=round(hands_win_loss_ratio, 2)*100,
        money_loss_ratio=round(money_loss_ratio, 3)*100)


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
    '''Creates a shuffled, 6 deck blackjack shoe'''
    # 2s represents 2 of spades, Ah represents Ace of Hearts, etc.
    cards = [
        '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s', 'Ts', 'Js', 'Qs', 'Ks',
        '2h', '3h', '4h', '5h', '6h', '7h', '8h', '9h', 'Th', 'Jh', 'Qh', 'Kh',
        '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d', 'Td', 'Jd', 'Qd', 'Kd',
        '2c', '3c', '4c', '5c', '6c', '7c', '8c', '9c', 'Tc', 'Jc', 'Qc', 'Kc',
        'As', 'Ah', 'Ad', 'Ac'
    ]
    _shoe = cards*6  # forms a 6 deck blackjack shoe
    random.shuffle(_shoe)
    return _shoe


def create_card_values():
    '''Returns a dictionary of card values for blackjack.'''
    card_values = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 10, 'Q': 10, 'K': 10, 'A': 11
    }
    return card_values


def update_stats(stats, increase_stats, increase_xp, multiplier, cursor):
    '''SQL statement to update stats as the player plays Blackjack.
    This function has 5 parameters
    '''
    user_id = session['user_id']
    stats = list(stats)
    # Updating stat(s)
    increase_stats = list(increase_stats)
    for i in range(len(stats)):
        sql = f'''UPDATE Player SET {stats[i]} = {stats[i]} + ? WHERE id = ?'''
        cursor.execute(sql, (int(increase_stats[i]), user_id))
    # Adding XP
    sql = '''UPDATE Player SET xp = xp + ? WHERE id = ?'''
    cursor.execute(sql, (increase_xp, user_id))
    # winnings
    if multiplier != 0:
        # Undoing the change to money loss
        sql = '''UPDATE Player SET money_losses = money_losses - ?
        WHERE id = ?'''
        cursor.execute(sql, (session['bet'], user_id))
        # Updating money_win only if it's not a push
        if sum(session['dealer_hand_values']) != sum(session['player_hand_values']):
            sql = '''UPDATE Player SET money_wins = money_wins + ?
            WHERE id = ?'''
            cursor.execute(sql, (session['bet'], user_id))
        # Adding money to balance
        session['money'] += session['bet']*multiplier
        sql = '''UPDATE Player SET money = ? WHERE id = ?'''
        cursor.execute(sql, (session['money'], user_id))


def hand_end_template():
    '''Function for rendering the template after a hand has ended'''
    session['active_hand'] = False
    return render_template(
                "play.html",
                title="Play",
                show_footer=False,
                active_hand=session['active_hand'],
                dealers_hand=session['dealers_hidden_hand'],
                player_hand=session['player_hand'],
                player_hand_values=sum(session['player_hand_values']))
# defining functions for game end


@app.route('/bet', methods=['POST', 'GET'])
def bet():
    '''The betting page before the game starts'''
    # User needs to be logged in and in a hand
    if not session.get('logged_in'):
        return render_template("not_logged_in.html",
                               title="Play")
    if session.get('active_hand'):
        flash("Please finish your active hand")
        return redirect('/play')

    # Initialize variables
    session['card_values'] = create_card_values()
    session['player_hand_values'] = []
    session['dealer_hand_values'] = []
    session['natural'] = False
    session['bet'] = 0
    user_id = session['user_id']

    # Get the amount of money
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        sql = "SELECT money FROM Player WHERE id = ?"
        cursor.execute(sql, (user_id,))
        result = cursor.fetchone()
        session['money'] = result[0]

    # If the shoe has less than 100 cards, reshuffle
    if len(session['shoe']) < 100:
        flash("Shoe has been reshuffled!")
        session['shoe'] = new_deck()

    # Form processing
    if request.method == 'POST':
        session['bet'] = request.form['bet']
        if session['bet'].isdecimal():
            session['bet'] = int(session['bet'])
            if session['bet'] > session['money']:
                flash(f"You only have ${session['money']}")
                return render_template("bet.html", title="Play", money=session['money'], show_footer=False)
            if session['bet'] <= 0:
                flash("Bet must be a positive amount.")
                return render_template("bet.html", title="Play", money=session['money'], show_footer=False)
            if session['bet'] < 10:
                flash("Minimum bet is $10.")
                return render_template("bet.html", title="Play", money=session['money'], show_footer=False)
        else:
            flash("Invalid input. Please enter a valid amount.")
            return render_template("bet.html", title="Play", money=session['money'], show_footer=False)

        # Process the bet
        session['money'] -= session['bet']
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            sql = '''UPDATE Player SET money = ? WHERE id = ?'''
            cursor.execute(sql, (session['money'], session['user_id']))
            update_stats(['money_losses', 'hands_played'], [session['bet'], 1], 1, 0, cursor)

        # Start the hand
        session['active_hand'] = True
        (session['player_hand'],
         session['dealers_hidden_hand'],
         session['dealers_shown_hand'],
         session['player_hand_values'],
         session['dealer_hand_values'],
         session['natural']) = hand_start(session['bet'],
                                          session['shoe'],
                                          session['card_values'],
                                          cursor)
        return redirect('/play')

    return render_template("bet.html", title="Play",
                           show_footer=False,
                           money=session['money'])


@app.route('/play')
def play():
    '''Route for the game after the bet has been placed'''
    # User must be logged in and in a hand
    if not session.get('logged_in'):
        return render_template("not_logged_in.html",
                               title="Play")
    if session.get('active_hand'):
        if session.get('natural'):
            # immediately ends the hand if there is a natural
            session['active_hand'] = False
            return hand_end_template()
        else:
            return render_template(
                "play.html",
                title="Play",
                show_footer=False,
                active_hand=session['active_hand'],
                dealers_hand=session['dealers_shown_hand'],
                player_hand=session['player_hand'],
                player_hand_values=sum(session['player_hand_values'])
            )
    else:
        flash('Make a bet to play')
        return redirect('/bet')


def hand_start(bet, shoe, card_values, cursor):
    '''Starts the game by dealing two cards to the player and dealer.'''
    # Initialising variables
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
            update_stats(['wins'], [1,], 8, 1, cursor)
        else:
            #  you hit a natural but the dealer didn't
            flash("You hit a natural!")
            flash(f"You won ${bet * 2.5}!")
            update_stats(['wins'], [1,], 8, 2.5, cursor)
    elif sum(dealer_hand_values) == 21:
        # both players hit a natural
        natural = True
        flash("Dealer hit a natural!")
        flash(f"You lost your bet of ${bet}.")
        update_stats(['losses'], [1,], 1, 0, cursor)
    return (
        player_hand,
        dealers_hidden_hand,
        dealers_shown_hand,
        player_hand_values,
        dealer_hand_values,
        natural
        )


@app.route('/hit')
def hit():
    '''Player chooses to hit in Blackjack'''
    # Player must be logged in
    if session.get('logged_in'):
        if not session['active_hand']:
            return redirect('play')
    else:
        return render_template('not_logged_in.html',
                               title="Play")
    # Players can only double down on the first move
    session['can_double_down'] = False
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        update_stats(['hits',], [1,], 2, 0, cursor)

    # Deal one card from the shoe
    session['player_hand'].append(session['shoe'][0])
    session['shoe'].pop(0)
    # Calculate the new value for the hand
    (session['player_hand_values'],
     session['player_hand']) = calculate_hand_value(
                                    session['card_values'],
                                    hand=session['player_hand'],
                                    hand_values=session['player_hand_values'])
    if sum(session['player_hand_values']) > 21:
        flash("You busted")
        flash(f"You lost your bet of ${session['bet']}")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(['busts', 'losses'], [1, 1], 1, 0, cursor)

        return hand_end_template()
    return redirect('/play')


@app.route('/stand')
def stand():
    # user must be logged in and in a hand
    if session.get('logged_in'):
        if not session['active_hand']:
            return redirect('play')
    else:
        return render_template('not_logged_in.html',
                               title="You are not logged in")
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        update_stats(['stands',], [1,], 2, 0, cursor)
    while sum(session['dealer_hand_values']) < 17:
        session['dealers_hidden_hand'].append(session['shoe'][0])
        session['shoe'].pop(0)
        (
         session['dealer_hand_values'],
         session['dealers_hidden_hand']) = calculate_hand_value(
            session['card_values'],
            hand=session['dealers_hidden_hand'],
            hand_values=session['dealer_hand_values']
        )
    if sum(session['dealer_hand_values']) > 21:
        flash("Dealer went bust.")
        flash(f"You won ${session['bet'] * 2}!")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(['dealer_busts', 'wins'], [1, 1], 5, 2, cursor)

        return hand_end_template()
    elif sum(session['dealer_hand_values']) > sum(session['player_hand_values']):
        flash("Dealer's hand was higher than yours")
        flash(f"You lost your bet of ${session['bet']}")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(['dealer_higher', 'losses'], [1, 1], 1, 0, cursor)

        return hand_end_template()
    elif sum(session['dealer_hand_values']) < sum(session['player_hand_values']):
        flash("Your hand was higher than the dealers")
        flash(f"You won ${session['bet'] * 2}!")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(['player_higher', 'wins'], [1, 1], 5, 2, cursor)
        return hand_end_template()
    elif sum(session['dealer_hand_values']) == sum(session['player_hand_values']):
        flash("It's a push!")
        flash(f"You get your bet of ${session['bet']} back.")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(['pushes',], ['1',], 3, 1, cursor)

        return hand_end_template()
# game stuff end


@app.route('/stats', methods=['POST', 'GET'])
def stats():
    '''
    This route is for the stats page,
    which allows users to search for player stats by username.
    '''
    # Player bust be logged out or not in a hand
    if session.get('active_hand'):
        flash("You need to finish your current hand")
        return redirect('/play')
    if request.method == 'POST':
        searched_username = request.form.get('searched_username')
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        # finding duplicate usernames
        sql = "SELECT * FROM Player WHERE username = ?"
        cursor.execute(sql, (searched_username,))
        stats_data = cursor.fetchone()
        if stats_data is None:
            flash("No Player found with this exact username")
        else:
            sql = '''SELECT name, description, image FROM Award WHERE id IN(
            SELECT aid FROM PlayerAward WHERE pid=?);'''
            cursor.execute(sql, (stats_data['id'],))
            awards = [dict(row) for row in cursor.fetchall()]

            # Calculating ratios for some stats
            # Win/loss ratio calculations
            if stats_data['wins']+stats_data['losses'] == 0:
                # Preventing division by zero
                hands_win_loss_ratio = 0
            else:
                hands_win_loss_ratio = stats_data['wins']/(stats_data['wins']+stats_data['losses'])
            # Money/loss ratio calculations
            if stats_data['money_wins'] == 0:
                # Preventing division by zero
                money_loss_ratio = 0
            else:
                money_loss_ratio = stats_data['money_wins']/stats_data['money_losses']

            db.close()
            return render_template("stats.html",
                                   title="Stats",
                                   stats_data=stats_data,
                                   awards=awards,
                                   hands_win_loss_ratio=round(hands_win_loss_ratio*100, 1),
                                   money_loss_ratio=round(money_loss_ratio*100, 1),
                                   )
    return render_template("stats.html", title="Stats")


@app.route('/about')
def about():
    '''This route is for the about page, which provides information about the project.'''
    # User must not be in a hand
    if session.get('active_hand'):
        flash("You need to finish your current hand")
        return redirect('/play')
    return render_template("about.html",
                           title="About")


@app.route('/login', methods=['POST', 'GET'])
def login():
    '''This route is for the login page, which allows users to
    log in to their accounts.'''
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')
        return redirect('/dashboard')
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
    '''This route is for the signup page, which allows users to
    create a new account.'''
    # if user is logged in, redirect to dashboard
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')

    if request.method == 'POST':
        username = request.form['username'].rstrip()
        password = request.form['password'].rstrip()
        # Checking the username is valid
        # The code below ensures the username is between 4-15 characters
        # Some special characters also cannot be used
        if len(username) < 4 or len(username) > 15:
            flash("Your username must be between 5~15 characters")
            return render_template("signup.html", title="Sign up")
        elif ' ' in username:
            flash("Your username must not have a space")
            return render_template("signup.html", title="Sign up")
        elif "'" in username or '"' in username or ';' in username:
            flash("Invalid characters in username, please try again")
        elif '/' in username or '\\' in username or '=' in username:
            flash("Invalid username, please try again")
        elif '<' in username or '>' in username:
            flash("Invalid characters in username, please try again")
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
        # gets the last row id
        # it should be the id of the newly created account
        user_id = cursor.lastrowid
        # awarding the player with "Diamond_Create_Account"
        sql = '''INSERT INTO PlayerAward (pid, aid) VALUES (?, ?)'''
        cursor.execute(sql, (user_id, 1))
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


@app.route('/settings', methods=['POST', 'GET'])
def settings():
    '''This route is for the settings page, which allows users to change their account settings.'''
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')
    elif not session.get("logged_in"):
        return render_template("not_logged_in.html",
                               title="Settings")

    if request.method == 'POST':
        new_password = request.form['new_password']
        old_password = request.form['old_password']
        user_id = session.get('user_id')
        # Password must be 6~15 characters and contain a
        # number/special character
        if len(new_password) < 6 or len(new_password) > 15:
            flash("Your password must be between 6~15 characters")
            return render_template("signup.html", title="Sign up")
        elif new_password.isalpha():
            flash("Your password must have a number or special character")
            return render_template("signup.html", title="Sign up")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            sql = '''SELECT password FROM Player WHERE id = ?'''
            cursor.execute(sql, (user_id,))
            password = cursor.fetchone()
            password = password[0]
        if old_password != password:
            print(password)
            print(old_password)
            flash('Incorrect password')
        else:
            sql = '''UPDATE Player SET password = ? WHERE id = ?'''
            cursor.execute(sql, (new_password, user_id,))
            db.commit()
            flash('Password updated successfully')

    return render_template("settings.html",
                           title="Settings")


@app.route('/delete_account', methods=['POST', 'GET'])
def delete_account():
    '''This route is for a page where the user can delete their account.
    They will have to confirm it's deletion by inputting their password and
    checking a box'''
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')
    elif not session.get("logged_in"):
        return render_template("not_logged_in.html",
                               title="Delete Account")
    if request.method == 'POST':
        with sqlite3.connect(DATABASE) as db:
            user_id = session.get('user_id')
            print(user_id)
            cursor = db.cursor()
            sql = '''SELECT password FROM Player WHERE id = ?'''
            cursor.execute(sql, (user_id,))
            password = cursor.fetchone()
            password = password[0]
            input_password = request.form['password']
            checkbox = request.form.get('delete_account_checkbox')
            if checkbox == 'Checked':
                if input_password == password:
                    sql = '''DELETE FROM Player WHERE id = ?'''
                    cursor.execute(sql, (user_id,))
                    session.clear()
                    db.commit()
                    return redirect('/home')

                else:
                    flash('Password is incorrect')
            else:
                flash('Please check the box to delete your account')

    return render_template('delete_account.html',
                           title='Delete Account',
                           show_footer=False)


@app.route('/log_out')
def logout():
    '''This route is for logging out the user, clearing the session data.'''
    if not session.get("logged_in"):
        return redirect('/home')
    session.clear()
    print("User has been logged out")
    return redirect('/login')


# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    '''Custom 404 page not found page'''
    return render_template("404.html", title="Page Not Found"), 404


@app.errorhandler(500)
def error_500(e):
    '''Custom error 500 page'''
    render_template("500.html", title="Error 500"), 500


if __name__ == "__main__":
    app.run(debug=True)  # make this turned to off when you submit
