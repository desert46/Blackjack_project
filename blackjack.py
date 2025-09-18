'''
Project Start 18/03/2025 - DD/MM/YYYY

Created by Alex Yao

This project is a site where players can play blackjack using a custom
blackjack engine. This project keeps track of players statistics as the they
play blackjack. Awards are also awarded to players during specific
statistics milestones. Players can create their
own accounts, change password, and delete accounts when they please.

Project End 18/09/2025 - DD/MM/YYYY
'''
# Imports
from flask import Flask, render_template, request, flash, session, redirect
from flask_session import Session
import sqlite3
import random
import hashlib

# Constants
DATABASE = "blackjack.db"
# flask stuff
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


@app.before_request
def before_request():
    '''
    This route is used to to update the players level
    and award the player live
    '''
    # Leveling up occurs before every request
    if session.get('logged_in') is True:
        with sqlite3.connect(DATABASE) as db:
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            user_id = session.get('user_id')
            # Fetching player data so data can be used to check if player meets
            # award criterias, leveling up milestones etc
            sql = '''SELECT * FROM Player WHERE id=?'''
            cursor.execute(sql, (user_id,))
            stats_data = cursor.fetchone()

            if stats_data['xp'] >= 100:  # Player levels up every 100xp
                # 100xp is deducted and level is increased by 1
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
            # Awarding Level up awards
            awarding_player(claimed_awards=claimed_awards,
                            cursor=cursor,
                            user_id=user_id,
                            criteria=[50, 25, 10],
                            aid=[7, 6, 5],
                            stat=stats_data['level']
                            )

            # Awarding money won awards
            awarding_player(claimed_awards=claimed_awards,
                            cursor=cursor,
                            user_id=user_id,
                            criteria=[1000000, 500000, 100000],
                            aid=[4, 3, 2],
                            stat=stats_data['money_wins']
                            )


def awarding_player(claimed_awards, cursor, user_id, criteria, aid, stat):
    '''
    This function is used to award players once they reach a certain criteria
    like levels and money wins. The function increases the players award count
    and awards the award to the player if the player does not already have the
    award
    '''
    for i in range(len(criteria)):
        if stat >= criteria[i]:
            # checking if player already has the award so player
            # is not awarded again
            has_award = any(pid.get('aid') == aid[i] for pid in claimed_awards)
            if not has_award:
                # Awarding the player with the designated award
                sql = '''UPDATE Player
                        SET award_count = award_count + 1
                        WHERE id = ?;'''
                cursor.execute(sql, (user_id,))  # Updating award count
                sql = '''INSERT INTO PlayerAward (pid, aid)
                        VALUES (?, ?)'''
                cursor.execute(sql, (user_id, aid[i]))  # Awarding the award


@app.route('/')  # link with and without the /home will lead home
@app.route('/home')
def home():
    '''
    This route is for the home page,
    which is accessible when not logged in.
    Logged in users will be redirected to the dashboard.
    '''
    if session.get("logged_in"):
        return redirect('/dashboard')
    return render_template("home.html",
                           title="Home",)


@app.route('/dashboard')
def dashboard():
    '''
    This route is for the dashboard page. The player must
    be logged in and not in a hand to access this page
    '''
    if not session.get("logged_in"):
        return redirect('/home')
    elif session.get('active_hand'):
        flash("Please finish your active hand")
        return redirect('/play')

    # initialising some variables for SQL queries
    user_id = session.get("user_id")
    username = session.get("username")

    # fetching awards
    with sqlite3.connect(DATABASE) as db:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        sql = "SELECT * FROM Player WHERE id = ?"
        cursor.execute(sql, (user_id,))
        stats_data = cursor.fetchone()
        sql = '''SELECT name, description, image FROM Award WHERE id IN(
        SELECT aid FROM PlayerAward WHERE pid=?);'''
        cursor.execute(sql, (user_id,))
        awards = [dict(row) for row in cursor.fetchall()]

    # Calculating ratios for some stats
    # Win/loss ratio calculations
    if stats_data['wins']+stats_data['losses'] == 0:
        # Preventing division by zero
        hands_win_loss_ratio = 0
    else:
        hands_win_loss_ratio = stats_data['wins']/(stats_data['wins']+stats_data['losses'])

    # Money/loss ratio calculations
    if stats_data['money_losses'] == 0:
        # Preventing division by zero
        money_loss_ratio = 0
    else:
        money_loss_ratio = stats_data['money_wins']/stats_data['money_losses']

    return render_template(
        "dashboard.html",
        title="Dashboard",
        user_id=user_id,
        username=username,
        stats_data=stats_data,
        awards=awards,
        hands_win_loss_ratio=round(hands_win_loss_ratio*100, 2),
        money_loss_ratio=round(money_loss_ratio*100, 2))


# Blackjack engine routes and functions start
def calculate_hand_value(card_values, hand_values, hand):
    '''
    Calculates the total value of a hand
    and appends it to the hand_values list
    '''
    hand_values.append(card_values[hand[-1][0]])
    if sum(hand_values) > 21 and 11 in hand_values:
        # If the hand value is over 21 and contains an Ace, Ace becomes 1
        # takes the first 11 and transforms it into a 1
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
    }  # Ace initially starts as 11 but can be changed to 1 later
    return card_values


def update_stats(stats, increase_stats, increase_xp, multiplier, cursor):
    '''
    SQL statement to update stats as the player plays Blackjack.
    This function has 5 parameters.
    The stat parameter specified what stat/s are updated.
    The increases_stats specifies how much that stat is increased respectively.
    The increase_xp specifies how much xp the player earns
    The multiplier specifies how much money the player earns based off
    the bet size times the multiplier upon a win.
    The cursor is the cursor for SQL queries.
    '''
    user_id = session.get('user_id')
    stats = list(stats)
    # Updating stats
    increase_stats = list(increase_stats)
    # A list of names of columns in the sql tables is parsed into this function
    # a list of increase_stats is also parsed in and contains the numbers of
    # how much each column should be updated respectively
    # The for loop loops through each stat in the list of stats and updates
    # them using the respective number in the increase_stats list
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

        print(f'Multipler: {multiplier}')
        # Updating money_win only if it's not a push
        if sum(session['dealer_hand_values']) != sum(session['player_hand_values']):
            if multiplier == 2.5:  # Player hit natural
                sql = '''UPDATE Player SET money_wins = money_wins + ?
                WHERE id = ?'''
                cursor.execute(sql, (session['bet']*1.5, user_id))
            else:
                # updating money wins SQL
                sql = '''UPDATE Player SET money_wins = money_wins + ?
                WHERE id = ?'''
                cursor.execute(sql, (session['bet'], user_id))

        # Adding money to balance
        session['money'] += session['bet'] * multiplier
        sql = '''UPDATE Player SET money = ? WHERE id = ?'''
        cursor.execute(sql, (session['money'], user_id))


def hand_end_template():
    '''
    Function for rendering the template after a hand has ended.
    This function was created to shorten/simplify some code
    '''
    session['active_hand'] = False
    return render_template(
                "play.html",
                title="Play",
                show_footer=False,
                active_hand=session['active_hand'],
                dealers_hand=session['dealers_hidden_hand'],
                player_hand=session['player_hand'],
                player_hand_values=sum(session['player_hand_values']))


@app.route('/bet', methods=['POST', 'GET'])
def bet():
    '''
    The betting page before the game starts. Player must be logged in
    and not in a hand to access this page
    '''
    # User needs to be logged in and in a hand
    if not session.get('logged_in'):
        return render_template("not_logged_in.html",
                               title="Play")
    if session.get('active_hand'):
        flash("Please finish your active hand")
        return redirect('/play')

    # Initialize variables that are needed when the hand starts
    session['card_values'] = create_card_values()
    session['player_hand_values'] = []
    session['dealer_hand_values'] = []
    session['natural'] = False
    session['bet'] = 0
    user_id = session['user_id']

    # Get the amount of money the player has and updates the session money
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        sql = "SELECT money FROM Player WHERE id = ?"
        cursor.execute(sql, (user_id,))
        result = cursor.fetchone()
        session['money'] = result[0]

    # If the shoe has less than 100 cards, discard shoe and reshuffle new show
    if len(session['shoe']) < 100:
        flash("Shoe has been reshuffled!")
        session['shoe'] = new_deck()

    # Form processing
    # This code ensures the bet size is a number 10 or above
    # The bet must also be <30 digits long
    if request.method == 'POST':
        session['bet'] = request.form.get('bet')
        # Storing previous bet so users do not have to re enter their bets
        session['previous_bet'] = request.form.get('bet', None)

        if session['bet'] is None:
            flash('Invalid input, try again')
            return render_template("bet.html",
                                   title="Play",
                                   money=session['money'],
                                   show_footer=False,
                                   previous_bet=session.get('previous_bet', ''))
        if len(session['bet']) > 30:
            flash('Your bet size was too large, '
                  'bet size must be below 30 digits long')
            return render_template("bet.html",
                                   title="Play",
                                   money=session['money'],
                                   show_footer=False,
                                   previous_bet=session.get('previous_bet', ''))
        if session['bet'].isdecimal():
            session['bet'] = int(session['bet'])
            if session['bet'] > session['money']:
                flash(f"You only have ${session['money']}")
                return render_template("bet.html",
                                       title="Play",
                                       money=session['money'],
                                       show_footer=False,
                                       previous_bet=session.get('previous_bet', ''))
            if session['bet'] < 10:
                flash("Minimum bet is $10.")
                return render_template("bet.html",
                                       title="Play",
                                       money=session['money'],
                                       show_footer=False,
                                       previous_bet=session.get('previous_bet', ''))
        else:
            flash("Invalid input. Please enter a valid amount.")
            return render_template("bet.html",
                                   title="Play",
                                   money=session['money'],
                                   show_footer=False,
                                   previous_bet=session.get('previous_bet', ''))

        # deducting money from player
        # If the player wins the hand or a push occurs, this will be undone
        session['money'] -= session['bet']
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            sql = '''UPDATE Player SET money = ? WHERE id = ?'''
            cursor.execute(sql, (session['money'], session['user_id']))
            # money losses increases
            # this wil be undone if the player wins the hand
            update_stats(['money_losses',
                         'hands_played'],
                         [session['bet'], 1],
                         1,
                         0,
                         cursor)

        # Starting the hand
        session['active_hand'] = True
        (session['player_hand'],
         session['dealers_hidden_hand'],
         session['dealers_shown_hand'],
         session['player_hand_values'],
         session['dealer_hand_values'],
         session['natural']) = hand_start(session['bet'],
                                          session['shoe'],
                                          session['card_values'],)
        return redirect('/play')

    return render_template("bet.html",
                           title="Play",
                           show_footer=False,
                           money=session['money'],
                           previous_bet=session.get('previous_bet', ''))


@app.route('/play')
def play():
    '''
    Route for the game after the bet has been placed.
    This is the page that contains the buttons and cards the player
    interacts with.
    Player must be in a hand and logged in to access this page
    '''
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


def hand_start(bet, shoe, card_values):
    '''
    Starts the game by dealing two cards to the player and dealer.
    Any naturals are also dealt with in this function.
    This function returns the player and dealer hands with two random cards.
    Initial hand values for the two card are also calculated and returned.
    '''
    # Initialising variables needed for the hand
    natural = False
    player_hand = []
    dealers_hidden_hand = []
    dealers_shown_hand = []
    player_hand_values = []
    dealer_hand_values = []

    # Deal two cards to the player and dealer from the show
    for i in range(2):
        player_hand.append(shoe[0])
        shoe.pop(0)
        dealers_hidden_hand.append(shoe[0])
        dealers_shown_hand.append(shoe[0])
        shoe.pop(0)
    # This hand will be shown to the player during the hand
    # Only the hidden hand is revealed after the hand
    dealers_shown_hand[0] = "Xx"  # hide one of the dealer's cards
    # calculate the initial hand values for the two cards dealt
    for card in player_hand:
        # card[0] takes the rank of the card
        player_hand_values.append(card_values[card[0]])
    for card in dealers_hidden_hand:
        dealer_hand_values.append(card_values[card[0]])
    # Pocket aces scenario
    # Sets one of the aces to 1, this decreases the sum of
    # the hand value from 22 to 12
    if player_hand_values == [11, 11]:
        player_hand_values = [1, 11]
    if dealer_hand_values == [11, 11]:
        dealer_hand_values = [1, 11]

    session['player_hand_values'] = player_hand_values
    session['dealer_hand_values'] = dealer_hand_values

    # checking for naturals by seeing if any hands have a value of 21
    # Opening up database connection
    with sqlite3.connect(DATABASE) as db:
        cur = db.cursor()
        if sum(player_hand_values) == 21:
            natural = True
            if sum(dealer_hand_values) == 21:
                # dealer and player hit a natural
                flash("Both you and the dealer hit a natural")
                flash("You get your bet back.")
                # record a push, give push XP (3), multiplier 1 returns the bet
                update_stats(stats=['pushes'],
                             increase_stats=[1,],
                             increase_xp=3,
                             multiplier=1,
                             cursor=cur)
            else:
                print('Only player hit a natural')
                flash('You hit a natural')
                flash(f'You win ${bet*2.5}')
                update_stats(stats=['wins', 'player_higher'],
                             increase_stats=[1, 1],
                             increase_xp=8,
                             multiplier=2.5,
                             cursor=cur)

        elif sum(dealer_hand_values) == 21:
            # only dealer hit a natural
            # Player loses bet and stats are updated
            natural = True
            flash("Dealer hit a natural!")
            flash(f"You lost your bet of ${bet}.")
            update_stats(stats=['losses', 'dealer_higher'],
                         increase_stats=[1, 1],
                         increase_xp=1,
                         multiplier=0,
                         cursor=cur)
    db.commit()
    return (
        player_hand,
        dealers_hidden_hand,
        dealers_shown_hand,
        player_hand_values,
        dealer_hand_values,
        natural)


@app.route('/hit')
def hit():
    '''
    Player chooses to hit in Blackjack. The hit will only work
    if the player is in a hand
    '''
    # Player must be logged in
    if session.get('logged_in'):
        if not session['active_hand']:
            return redirect('play')
    else:
        return render_template('not_logged_in.html',
                               title="Play")
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        update_stats(stats=['hits',],
                     increase_stats=[1,],
                     increase_xp=2,
                     multiplier=0,
                     cursor=cursor)

    # Deal one card from the shoe
    session['player_hand'].append(session['shoe'][0])
    session['shoe'].pop(0)

    # Calculate the new value for the hand
    # The new cards value is taken and appended into the hand value list
    (session['player_hand_values'],
     session['player_hand']) = calculate_hand_value(
                                    session['card_values'],
                                    hand=session['player_hand'],
                                    hand_values=session['player_hand_values'])

    # If the player hand exceeds 21, the hand ends and the player loses
    # Bet is lost and stats updated
    if sum(session['player_hand_values']) > 21:
        flash("You busted")
        flash(f"You lost your bet of ${session['bet']}")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(stats=['busts', 'losses'],
                         increase_stats=[1, 1],
                         increase_xp=1,
                         multiplier=0,
                         cursor=cursor)
        return hand_end_template()
    return redirect('/play')


@app.route('/stand')
def stand():
    '''
    Route for the player to stand while playing blackjack.
    Stand will end the hand. It will only work if the player is in a hand
    '''
    if session.get('logged_in'):
        if not session['active_hand']:
            return redirect('play')
    else:
        return render_template('not_logged_in.html',
                               title="You are not logged in")

    # Updating stand stat by 1
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        update_stats(['stands',], [1,], 2, 0, cursor)
    # The dealer will continue to draw cards until hand value is >17
    # List of dealers hand and hand values will grow until this point
    while sum(session['dealer_hand_values']) < 17:
        # Drawing a card from the shoe
        session['dealers_hidden_hand'].append(session['shoe'][0])
        session['shoe'].pop(0)
        (
         session['dealer_hand_values'],
         session['dealers_hidden_hand']) = calculate_hand_value(
            session['card_values'],
            hand=session['dealers_hidden_hand'],
            hand_values=session['dealer_hand_values']
        )

    # If the dealers hand exceeds 21, the player wins and stats are updated
    if sum(session['dealer_hand_values']) > 21:
        flash("Dealer went bust.")
        flash(f"You won ${session['bet'] * 2}!")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(stats=['dealer_busts', 'wins'],
                         increase_stats=[1, 1],
                         increase_xp=5,
                         multiplier=2,
                         cursor=cursor)
            db.commit()
        return hand_end_template()

    # If the dealers hand is higher, player loses and stats are updated
    elif sum(session['dealer_hand_values']) > sum(session['player_hand_values']):
        flash("Dealer's hand was higher than yours")
        flash(f"You lost your bet of ${session['bet']}")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(stats=['dealer_higher', 'losses'],
                         increase_stats=[1, 1],
                         increase_xp=1,
                         multiplier=0,
                         cursor=cursor)
            db.commit()
        return hand_end_template()

    # If the player hand is higher, the player wins and stats are updated
    elif sum(session['dealer_hand_values']) < sum(session['player_hand_values']):
        flash("Your hand was higher than the dealers")
        flash(f"You won ${session['bet'] * 2}!")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(stats=['player_higher', 'wins'],
                         increase_stats=[1, 1],
                         increase_xp=5,
                         multiplier=2,
                         cursor=cursor)
            db.commit()
        return hand_end_template()

    # If the hands are equal in values, player's bet is
    # returned and stats are updated
    elif sum(session['dealer_hand_values']) == sum(session['player_hand_values']):
        flash("It's a push!")
        flash(f"You get your bet of ${session['bet']} back.")
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            update_stats(stats=['pushes',],
                         increase_stats=['1',],
                         increase_xp=3,
                         multiplier=1,
                         cursor=cursor)
            db.commit()
        return hand_end_template()
# Blackjack engine routes and functions end


@app.route('/stats', methods=['POST', 'GET'])
def stats():
    '''
    This route is for the stats page,
    which allows users to search for player stats by username.
    Player needs to not be in a hand to access this page.
    '''
    if session.get('active_hand'):
        flash("You need to finish your current hand")
        return redirect('/play')

    if request.method == 'POST':
        searched_username = request.form.get('searched_username')
        if searched_username is None:
            flash('Invalid input, try again')
            return render_template("stats.html", title="Stats")
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        # Searching database using the username provided in the form
        sql = "SELECT * FROM Player WHERE username = ?"
        cursor.execute(sql, (searched_username,))
        stats_data = cursor.fetchone()
        if stats_data is None:
            # No username found that matched in the database
            flash("No Player found with this exact username")
        else:
            # Username matched one found in the database
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
            if stats_data['money_losses'] == 0:
                # Preventing division by zero
                money_loss_ratio = 0
            else:
                money_loss_ratio = stats_data['money_wins']/stats_data['money_losses']

            db.close()
            return render_template("stats.html",
                                   title="Stats",
                                   stats_data=stats_data,
                                   awards=awards,
                                   hands_win_loss_ratio=round(hands_win_loss_ratio*100, 2),
                                   money_loss_ratio=round(money_loss_ratio*100, 2),
                                   )
    return render_template("stats.html", title="Stats")


@app.route('/about')
def about():
    '''
    This route is for the about page, which provides information about the
    project and how to play the game. Player must not be in a hand
    to access this page
    '''
    if session.get('active_hand'):
        flash("You need to finish your current hand")
        return redirect('/play')
    return render_template("about.html",
                           title="About")


@app.route('/login', methods=['POST', 'GET'])
def login():
    '''
    This route is for the login page, which allows users to
    log in to their accounts.
    '''
    # User needs to be logged in and not in a hand to access this page
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

        # Preventing an error is no input is entered
        if results is None:
            flash("Username or Password is incorrect")
            return render_template("login.html",
                                   title="Login")
        if password is None:
            flash('Please try again')
            return render_template("login.html",
                                   title="Login")

        # Hashing the inputted password
        h = hashlib.new("SHA256")  # create hash object using SHA256 algorithm
        h.update(password.encode())  # turns password into bytes
        hashed_input_password = h.hexdigest()  # converts into hexadecimal str

        # gets hashed password from the results and compares the hashes
        if hashed_input_password == results[1]:
            # gets user_id if passwords match

            # Initialising variables needed for the game upon login
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
    flash("Login to play Blackjack")
    return render_template("login.html",
                           title="Login")


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    '''
    This route is for the signup page, which allows users to
    create a new account.
    The user needs to be logged out to access this page.
    '''
    # User needs to be logged in and not in a hand to access this page
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')
        return redirect('/dashboard')

    # Preventing an error is no input is entered
    if request.method == 'POST':
        username = request.form.get('username').rstrip()
        password = request.form.get('password').rstrip()
        if username is None or password is None:
            flash('Please provide a valid Username and Password')
            return render_template("signup.html",
                                   title="Sign Up")

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
            # If a duplicate username is found, the account creation will fail
            db.close()
            flash('This username is already taken, select another username')
            return render_template("signup.html",
                                   title="Sign Up")

        # Hashing the password
        h = hashlib.new("SHA256")
        h.update(password.encode())
        hashed_password = h.hexdigest()

        # sql query to create an account
        sql = '''INSERT INTO Player (username, password) VALUES (?, ?)'''
        cursor.execute(sql, (username, hashed_password))
        # gets the last row id so the player can be awarded
        # it should be the id of the newly created account
        user_id = cursor.lastrowid
        # awarding the player with "Diamond_Create_Account"
        # Also updates award_count of player
        sql = '''INSERT INTO PlayerAward (pid, aid) VALUES (?, ?)'''
        cursor.execute(sql, (user_id, 1))
        # Updating award count stat
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
    '''
    This route is for the settings page, which allows users to change their
    account settings. The user needs to be logged in and not in a hand
    to access this page
    '''
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')
    elif not session.get("logged_in"):
        return render_template("not_logged_in.html",
                               title="Settings")

    # Preventing an error if no input is entered
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        old_password = request.form.get('old_password')
        if new_password is None or old_password is None:
            flash('Please provide a vaild input')
            return render_template("settings.html",
                                   title="Settings")

        user_id = session.get('user_id')
        # Password must be 6~15 characters and contain a
        # number/special character
        # Password change will fail if this is not satisfied
        if len(new_password) < 6 or len(new_password) > 15:
            flash("Your password must be between 6~15 characters")
            return render_template("settings.html", title="Settings")
        elif new_password.isalpha():
            flash("Your password must have a number or special character")
            return render_template("settings.html", title="Settings")

        # Selecting the old password to compare to the one entered
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            sql = '''SELECT password FROM Player WHERE id = ?'''
            cursor.execute(sql, (user_id,))
            password = cursor.fetchone()
            password = password[0]

        # Hashing old password to compare the hashes to the current password
        h = hashlib.new("SHA256")
        h.update(old_password.encode())
        old_hashed_password = h.hexdigest()

        # checking that the hashed passwords match
        if old_hashed_password != password:
            flash('Incorrect password')
        else:
            # Hashing the new password
            h = hashlib.new("SHA256")
            h.update(new_password.encode())
            new_hashed_password = h.hexdigest()

            # Updating password with new hased password
            sql = '''UPDATE Player SET password = ? WHERE id = ?'''
            cursor.execute(sql, (new_hashed_password, user_id,))
            db.commit()
            flash('Password updated successfully')
    return render_template("settings.html",
                           title="Settings")


@app.route('/delete_account', methods=['POST', 'GET'])
def delete_account():
    '''
    This route is for a page where the user can delete their account.
    They will have to confirm it's deletion by inputting their password and
    checking a box. User needs to be logged in and not in a hand to access
    this page
    '''
    # User must be logged in and not in a hand to access this page
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
            cursor = db.cursor()
            # Fetching password to compare to entered password
            sql = '''SELECT password FROM Player WHERE id = ?'''
            cursor.execute(sql, (user_id,))
            password = cursor.fetchone()
            password = password[0]
            input_password = request.form.get('password')
            checkbox = request.form.get('delete_account_checkbox')
            if input_password is None:
                flash('Please input your password and check the box provided')
                return render_template('delete_account.html',
                                       title='Delete Account',)
            # Hashing the input password
            # We do this so we can compare the hashes of the old password
            # Hashing the password
            h = hashlib.new("SHA256")
            h.update(input_password.encode())
            hashed_input_password = h.hexdigest()
            if checkbox == 'Checked':  # Box must be checked to change password
                # checking that the passwords match
                if hashed_input_password == password:
                    # If passwords match, all records of the player are deleted
                    sql = '''DELETE FROM Player WHERE id = ?'''
                    cursor.execute(sql, (user_id,))
                    # Deleting player awards
                    sql = '''DELETE FROM PlayerAward WHERE pid = ?'''
                    cursor.execute(sql, (user_id,))
                    session.clear()
                    db.commit()
                    print("Account deleted successfully")
                    flash('Account deleted successfully')
                    return redirect('/login')
                else:
                    flash('Password is incorrect')
            else:
                flash('Please check the box to delete your account')

    return render_template('delete_account.html',
                           title='Delete Account',)


@app.route('/secret')
def secret():
    '''
    Nothing to see here.
    Easter egg inside my website
    '''
    user_id = session.get('user_id')
    if user_id == 1:  # user must be me to see this page
        return render_template('secret.html',
                               title='Secret')
    else:
        return redirect('/home')


@app.route('/log_out')
def logout():
    '''This route is for logging out the user, clearing the session data.'''
    session.clear()
    print("Session has been cleared")
    return redirect('/login')


# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    '''
    Custom 404 page not found page. If the player is in a hand they will be
    redirected back to playing the hand
    '''
    if session.get("logged_in"):
        if session.get('active_hand'):
            flash("You need to finish your current hand")
            return redirect('/play')
    return render_template("404.html", title="Page Not Found"), 404


@app.errorhandler(500)
def error_500(e):
    '''Custom error 500 page'''
    return render_template("500.html", title="Error 500"), 500


if __name__ == "__main__":
    app.run(debug=False)
# AA
